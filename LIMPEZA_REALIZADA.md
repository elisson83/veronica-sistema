# LIMPEZA E REFATORAÇÃO — Ecossistema Verônica

**Data:** 2026-05-09
**Executado por:** Verônica (Claude Code)

---

## FASE 1 — Limpeza de Código

### appmotoboy/app.py
- Removidos imports mortos: `smtplib`, `email.mime.text.MIMEText`, `email.mime.multipart.MIMEMultipart`

### painelfrota/app.py
- Removidos imports mortos: `math`, `json`, `smtplib`, `email.mime.text.MIMEText`, `email.mime.multipart.MIMEMultipart`

---

## FASE 2 — Correção Mobile

### appmotoboy/app.py
- `app.run()` agora usa `host='0.0.0.0'` para aceitar conexões da rede local (mobile)
- `debug=True` → `debug=False` (produção segura)

### painelfrota/app.py
- Idem: `host='0.0.0.0'`, `debug=False`

### painelgest/app.py
- Idem: `host='0.0.0.0'`, `debug=False`

### painelrestaurante/app.py
- Já estava correto (`host='0.0.0.0'`, `debug=False`). Sem alteração.

**Templates:** Todos os `base.html` já tinham `<meta name="viewport">`. Sem alteração necessária.

---

## FASE 3 — Segurança Avançada

### modules/seguranca_web.py
- Adicionado header `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HSTS)

### appmotoboy/app.py
- Importado `rate_limit` de `seguranca_web`
- Aplicado `@rate_limit(60/min)` nas rotas: `/api/motoboys_disponiveis`, `/api/motoboys`, `/api/motoboy/<id>`, `/api/entregas/<id>`
- Aplicado `@rate_limit(30/min)` na rota: `/api/nova_entrega` (mutação — limite mais restrito)

### painelfrota/app.py
- Importado `rate_limit` de `seguranca_web`
- Aplicado `@rate_limit(60/min)` nas rotas: `/api/qr/<token>/info`, `/api/motoboy_token/<token>`
- Aplicado `@rate_limit(30/min)` na rota: `/api/stats`

---

## FASE 4 — Nginx

### nginx/veronica.conf
- Configuração Nginx com proxy reverso para os 4 apps
- Redirecionamento HTTP → HTTPS automático
- SSL via Let's Encrypt (Certbot)
- Cache de arquivos estáticos com `Cache-Control: immutable`
- Headers de proxy corretos (`X-Forwarded-For`, `X-Forwarded-Proto`)

### nginx/instalar_nginx.sh
- Script de deploy automático do Nginx no servidor

---

## FASE 5 — Sistema de Chave USB

### pendrive/gerador_chave.py
- Gera arquivo `.veronica_key` com token de 128 hex + checksum SHA-256
- Para uso único: gera a chave e copia para o pen drive autorizado

### pendrive/verificador_chave.py
- `verificar()`: retorna True/False se pen drive com chave válida está conectado
- `exigir_pendrive()`: interrompe processo se pen drive não encontrado
- Suporte a Windows (D: a Z:) e Linux (/media, /mnt)

---

## O que NÃO foi alterado
- Lógica de negócio de nenhum app
- Banco de dados (modelos SQLAlchemy)
- Templates HTML (exceto o que já estava correto)
- `painelrestaurante/app.py` (já estava com host correto e debug=False)
- Autenticação Flask-Login (mantida — JWT seria uma refatoração maior separada)
