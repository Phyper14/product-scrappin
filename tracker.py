#!/usr/bin/env python3
"""Monitor de promoções: verifica preços e avisa no Telegram."""
import json
import os
import re
import sys
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

STATE_FILE = Path("state.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def parse_price(text):
    """'R$ 1.299,90' / '1,299.90' / 1299.9 -> float (ou None)."""
    if text is None:
        return None
    s = re.sub(r"[^\d.,]", "", str(text))
    if not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
        s = s.replace(thou, "").replace(dec, ".")
    elif "," in s:
        s = s.replace(",", ".") if re.search(r",\d{1,2}$", s) else s.replace(",", "")
    elif "." in s and not re.search(r"\.\d{1,2}$", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def extract_price(html, selector=None):
    soup = BeautifulSoup(html, "html.parser")
    if selector:
        el = soup.select_one(selector)
        return parse_price(el.get_text(" ", strip=True)) if el else None
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except ValueError:
            continue
        for node in _walk(data):
            for key in ("price", "lowPrice"):
                if key in node and not isinstance(node[key], (dict, list)):
                    p = parse_price(node[key])
                    if p:
                        return p
    for attrs in ({"property": "product:price:amount"},
                  {"property": "og:price:amount"},
                  {"itemprop": "price"}):
        el = soup.find(attrs=attrs)
        if el:
            p = parse_price(el.get("content") or el.get_text())
            if p:
                return p
    return None


def should_notify(price, last_price, last_notified, target=None, drop_pct=None):
    """Retorna motivo (str) se deve avisar, senão None."""
    if price == last_notified:
        return None  # já avisei sobre este preço
    if target is not None and price <= target:
        return f"abaixo da meta (R$ {target:.2f})"
    if drop_pct and last_price and price <= last_price * (1 - drop_pct / 100):
        return f"queda de {100 * (1 - price / last_price):.0f}% (era R$ {last_price:.2f})"
    return None


def notify(message):
    print(message)
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("(Telegram não configurado; aviso só no console)")
        return
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat, "text": message}, timeout=20)
    r.raise_for_status()


def main(config_path="config.yaml"):
    cfg = yaml.safe_load(Path(config_path).read_text())
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    for prod in cfg.get("products", []):
        url, name = prod["url"], prod.get("name", prod["url"])
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            price = extract_price(resp.text, prod.get("selector"))
        except requests.RequestException as e:
            print(f"[erro] {name}: {e}")
            continue
        if price is None:
            print(f"[aviso] {name}: preço não encontrado (defina 'selector' no config)")
            continue
        st = state.get(url, {})
        reason = should_notify(price, st.get("last_price"), st.get("last_notified"),
                               prod.get("target_price"), prod.get("drop_percent"))
        print(f"[ok] {name}: R$ {price:.2f}")
        if reason:
            notify(f"🔥 PROMOÇÃO: {name}\nR$ {price:.2f} — {reason}\n{url}")
            st["last_notified"] = price
        st["last_price"] = price
        state[url] = st
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
