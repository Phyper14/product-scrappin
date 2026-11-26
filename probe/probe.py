import re, urllib.request
MOB = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": MOB, "Accept-Language": "pt-BR,pt;q=0.9"}), timeout=25).read(2_000_000).decode("utf-8", "replace")
a = get("https://www.amazon.com.br/gp/aw/d/B0FPGF9J2J")
print("AMZ title:", re.findall(r"<title[^>]*>(.*?)</title>", a, re.S)[:1])
for m in list(re.finditer(r"R\$\s*[\d.]+,\d{2}", a))[:12]:
    print("AMZ ctx:", re.sub(r"\s+", " ", a[max(0, m.start()-90):m.end()+30]))
print("AMZ a-offscreen:", re.findall(r'a-offscreen">([^<]+)<', a)[:8])
print("AMZ has Astro:", "Astro" in a, "| Digital:", "Digital" in a)
b = get("https://www.mercadolivre.com.br/p/MLB54963150")
print("ML title:", re.findall(r"<title[^>]*>(.*?)</title>", b, re.S)[:1])
print("ML ld+json:", len(re.findall("application/ld\\+json", b)), "| andes-money:", len(re.findall("andes-money-amount", b)))
for m in list(re.finditer(r'"price"\s*:\s*[\d.]+|"amount"\s*:\s*[\d.]+|aria-label="[^"]*reais[^"]*"', b))[:10]:
    print("ML ctx:", re.sub(r"\s+", " ", b[max(0, m.start()-60):m.end()+30]))
