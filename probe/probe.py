import sys, urllib.request, urllib.error
sys.path.insert(0, "src")
from monitor import extract_price
DESK = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MOB = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
IPH = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
TESTS = [
 ("amz desk", "https://www.amazon.com.br/dp/B0FPGF9J2J", DESK),
 ("amz mobile-ua", "https://www.amazon.com.br/dp/B0FPGF9J2J", MOB),
 ("amz /gp/aw/d", "https://www.amazon.com.br/gp/aw/d/B0FPGF9J2J", MOB),
 ("amz offer-listing", "https://www.amazon.com.br/gp/offer-listing/B0FPGF9J2J", MOB),
 ("cb desk", "https://www.casasbahia.com.br/pack-console-playstation-5-edicao-digital-825gb-astro-bot-e-gran-turismo-7/p/1572582933", DESK),
 ("cb mobile-ua", "https://www.casasbahia.com.br/pack-console-playstation-5-edicao-digital-825gb-astro-bot-e-gran-turismo-7/p/1572582933", IPH),
 ("ml desk", "https://www.mercadolivre.com.br/p/MLB54963150", DESK),
 ("ml mobile-ua", "https://www.mercadolivre.com.br/p/MLB54963150", MOB),
 ("ml api products", "https://api.mercadolibre.com/products/MLB54963150", DESK),
 ("ml api items", "https://api.mercadolibre.com/products/MLB54963150/items", DESK),
]
for name, url, ua in TESTS:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Language": "pt-BR,pt;q=0.9"})
        body = urllib.request.urlopen(req, timeout=25).read(2_000_000).decode("utf-8", "replace")
        low = body.lower()
        print(f"{name:20} 200 len={len(body)} price={extract_price(body)} captcha={'captcha' in low or 'robot' in low} json_price={'\"price\"' in body}")
    except urllib.error.HTTPError as e:
        print(f"{name:20} HTTP {e.code}")
    except Exception as e:
        print(f"{name:20} ERR {e}")
