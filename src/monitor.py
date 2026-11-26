"""Monitora preços de produtos e gera alertas quando caem abaixo do teto.

Uso: python src/monitor.py [--config config/targets.json] [--state state/prices.json]
     [--alerts alerts.md]
Saída: atualiza o state, escreve alerts.md só se houver alerta.
Exit 0 sempre que ao menos um preço foi lido; 1 se TODAS as lojas falharam
(provável bloqueio de IP), para o workflow ficar vermelho em vez de silenciar.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

MOBILE_UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/124.0 Mobile Safari/537.36")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
MAX_BYTES = 3_000_000
MIN_PLAUSIBLE, MAX_PLAUSIBLE = 100.0, 100_000.0


def to_float(raw):
    """'1.234,56' | '1234.56' | 1234.5 -> float, ou None."""
    if isinstance(raw, (int, float)):
        return float(raw)
    s = re.sub(r"[^\d.,]", "", str(raw))
    if not s:
        return None
    if "," in s:  # formato BR: ponto = milhar, vírgula = decimal
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _walk_offers(node, found):
    if isinstance(node, dict):
        for key in ("price", "lowPrice"):
            if key in node and node.get("@type") in ("Offer", "AggregateOffer", None):
                v = to_float(node[key])
                if v:
                    found.append(v)
        for v in node.values():
            _walk_offers(v, found)
    elif isinstance(node, list):
        for v in node:
            _walk_offers(v, found)


def extract_price(html):
    """Menor preço plausível via JSON-LD, meta tags ou markup Amazon."""
    candidates = []
    for block in re.findall(
            r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            _walk_offers(json.loads(block), candidates)
        except ValueError:
            continue
    for m in re.finditer(
            r'<meta[^>]+(?:property|itemprop|name)=["\'](?:product:price:amount|price)["\']'
            r'[^>]+content=["\']([^"\']+)["\']', html, re.I):
        v = to_float(m.group(1))
        if v:
            candidates.append(v)
    # Amazon mobile: preço no JSON do buybox e preço com desconto Pix no rótulo de economia
    for m in re.finditer(r'"priceAmount":\s*([\d.]+)', html):
        candidates.append(float(m.group(1)))
    for m in re.finditer(r'por cento de desconto"[^>]*>\s*R\$\s*([\d.,]+)', html):
        v = to_float(m.group(1))
        if v:
            candidates.append(v)
    if not candidates:
        m = re.search(r'class="a-offscreen">\s*R\$\s*([\d.,]+)', html)
        if m and to_float(m.group(1)):
            candidates.append(to_float(m.group(1)))
    plausible = [p for p in candidates if MIN_PLAUSIBLE <= p <= MAX_PLAUSIBLE]
    return min(plausible) if plausible else None


def fetch(url, timeout=25):
    # Amazon desktop serve captcha a IPs de datacenter; a página mobile abre
    ua = MOBILE_UA if "amazon." in url else UA
    req = urllib.request.Request(url, headers={
        "User-Agent": ua, "Accept-Language": "pt-BR,pt;q=0.9",
        "Accept": "text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec: URLs vêm do config versionado
        return r.read(MAX_BYTES).decode("utf-8", "replace")


def decide(price, entry, max_price):
    """Alerta se <= teto e (primeira vez abaixo do teto OU novo mínimo)."""
    if price is None or price > max_price:
        return False
    last_alerted = entry.get("last_alert_price")
    return last_alerted is None or price < last_alerted


def dropped(price, prev, pct):
    """Queda brusca: preço atual >= pct% abaixo da leitura anterior (vale mesmo acima do teto)."""
    return bool(pct) and prev is not None and price <= prev * (1 - pct / 100)


def run(targets, state, fetcher=fetch, now=None):
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    alerts, ok = [], 0
    for t in targets:
        entry = state.setdefault(t["id"], {"history": []})
        try:
            price = extract_price(fetcher(t["url"]))
        except Exception as exc:  # rede/HTTP: registra e segue
            print(f"[erro] {t['id']}: {exc}", file=sys.stderr)
            price = None
        if price is None:
            print(f"[sem preço] {t['id']}", file=sys.stderr)
            continue
        ok += 1
        reasons = []
        if decide(price, entry, t["max_price"]):
            reasons.append("abaixo do teto")
            entry["last_alert_price"] = price
        if dropped(price, entry.get("last_price"), t.get("drop_percent")):
            reasons.append(f"queda de {t['drop_percent']}%+")
        if reasons:
            alerts.append((t, price, " e ".join(reasons)))
        if price > t["max_price"]:
            entry.pop("last_alert_price", None)  # saiu da faixa: rearma o alerta
        entry["last_price"], entry["last_seen"] = price, now
        entry["min_price"] = min(price, entry.get("min_price", price))
        if not entry["history"] or entry["history"][-1]["price"] != price:
            entry["history"] = (entry["history"] + [{"t": now, "price": price}])[-200:]
        time.sleep(1)
    return alerts, ok


def render_alerts(alerts):
    lines = ["# 🔔 Preço abaixo do teto", ""]
    for t, p, why in alerts:
        lines.append(f"- **{t['name']}**: R$ {p:,.2f} ({why}; teto R$ {t['max_price']:,.2f}) — {t['url']}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/targets.json")
    ap.add_argument("--state", default="state/prices.json")
    ap.add_argument("--alerts", default="alerts.md")
    a = ap.parse_args()
    targets = json.load(open(a.config))
    try:
        state = json.load(open(a.state))
    except FileNotFoundError:
        state = {}
    alerts, ok = run(targets, state)
    os.makedirs(os.path.dirname(a.state) or ".", exist_ok=True)
    json.dump(state, open(a.state, "w"), indent=1, ensure_ascii=False, sort_keys=True)
    if alerts:
        open(a.alerts, "w").write(render_alerts(alerts))
    print(f"{ok}/{len(targets)} preços lidos, {len(alerts)} alertas")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
