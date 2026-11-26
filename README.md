# product-scrappin

Bot que monitora o preço de produtos e avisa no **Telegram** quando entram em promoção.

## Como usar
1. Edite `config.yaml` com a URL do produto, `target_price` (preço-alvo) e/ou `drop_percent` (% de queda).
2. Crie um bot no Telegram com o [@BotFather](https://t.me/BotFather) (guarde o token) e pegue seu `chat_id` (mande uma mensagem ao bot e abra `https://api.telegram.org/bot<TOKEN>/getUpdates`).
3. No GitHub: *Settings → Secrets and variables → Actions* → crie `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.
4. Pronto: o workflow roda a cada 3h (ou manualmente em *Actions → Verificar preços → Run workflow*).

Rodar localmente:
```
pip install -r requirements.txt
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python tracker.py
pytest
```

## Observações
- O preço é detectado automaticamente (JSON-LD, meta tags). Se falhar, informe um `selector` CSS.
- Sites com proteção anti-bot (ex.: alguns marketplaces) podem bloquear requisições simples; nesses casos é preciso um navegador headless ou API oficial.
- Respeite os termos de uso do site e mantenha intervalos razoáveis.
