# product-scrappin

Bot gratuito (GitHub Actions) que monitora preços de PS5 na Black Friday 2026 (BR) e avisa
quando o preço cai abaixo do teto definido em `config/targets.json`.

- **Roda a cada 30 min** (`.github/workflows/monitor.yml`); repo público = minutos grátis ilimitados, privado cabe nos 2.000 min/mês.
- **Alerta**: abre uma Issue (você recebe e-mail/notificação do GitHub). Opcional: Telegram via secrets `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`.
- **Anti-spam**: alerta na 1ª vez abaixo do teto ou em novo mínimo (rearma se o preço subir); `drop_percent` (opcional por produto) avisa também em queda brusca vs. a leitura anterior, mesmo acima do teto.
- **Histórico**: `state/prices.json`, commitado a cada mudança.
- **Adicionar produto**: nova entrada em `config/targets.json` (`id`, `name`, `url`, `max_price`).
- **Testes**: `python -I -m unittest discover -s tests`

## Limitações
Amazon/KaBuM!/Mercado Livre podem bloquear IPs de datacenter (captcha). Quando nenhum preço é lido
o job falha (fica vermelho) em vez de silenciar. Preços de página nem sempre refletem Pix/cupom/Prime:
confirme no carrinho. Casas Bahia é vendedor terceiro: confira reputação e NF.
