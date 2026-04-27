# Verônica IA — Ecossistema Completo

Plataforma SaaS multi-produto para gestão de restaurantes, frotas de motoboys e inteligência artificial conversacional. Composta por 6 produtos integrados via QR Code e APIs internas.

---

## Produtos do Ecossistema

| Produto | Arquivo principal | Porta | Login padrão |
|---------|-------------------|-------|--------------|
| **Bot Verônica** (Telegram) | `main.py` | — | @veronica_assistente_bot |
| **Dashboard Web** | `dashboard.py` | 5000 | — |
| **API REST** | `api_veronica.py` | 5001 | X-API-Key no `.env` |
| **PainelGest** (SaaS restaurantes) | `painelgest/app.py` | 5002 | super / super123 |
| **AppMotoboy** (app do entregador) | `appmotoboy/app.py` | 5003 | — |
| **PainelFrota** (gestão de frotas) | `painelfrota/app.py` | 5004 | admin / admin123 |

### Acessos especiais PainelGest

| Perfil | URL | Credenciais padrão |
|--------|-----|--------------------|
| Super Admin | `/super/login` | super / super123 |
| Gestor (Admin) | `/login` | criado pelo Super Admin |
| Dono da Empresa | `/dono/login` | dono / dono123 |
| Restaurante | `/restaurante/login` | criado pelo Gestor |

---

## Pré-requisitos

- Python 3.10+
- pip
- Windows 10/11 (scripts `.bat`) — Linux/Mac requer adaptação manual
- Conta Telegram (para os bots)
- Chaves de API: Groq, Gemini, OpenAI (opcional)

---

## Instalação Rápida

```bash
# 1. Clonar o repositório
git clone https://github.com/seu-usuario/veronica.git
cd veronica

# 2. Instalar dependências globais
pip install -r requirements.txt

# 3. Instalar dependências do PainelGest
pip install -r painelgest/requirements.txt

# 4. Copiar e configurar variáveis de ambiente
copy .env.example .env
# Editar .env com suas chaves

# 5. Inicializar todos os bancos de dados
python painelgest/app.py &   # cria painelgest.db com tabelas e usuários padrão
python appmotoboy/app.py &   # cria motoboy.db
python painelfrota/app.py &  # cria frota.db
# Ctrl+C em cada terminal após "Running on..."

# 6. Iniciar todos os serviços
iniciar.bat
```

---

## Configuração do `.env`

```env
# IA / LLM
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...
MODEL_PROVIDER=groq
MODEL_NAME=llama-3.3-70b-versatile

# Telegram
TELEGRAM_TOKEN=...
ZEUS_TOKEN=...
ADMIN_TELEGRAM_ID=8106101043

# Twitter/X (opcional)
TWITTER_CONSUMER_KEY=
TWITTER_CONSUMER_SECRET=
TWITTER_BEARER_TOKEN=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=

# API Verônica
VERONICA_API_KEY=sua_chave_secreta
ZEUS_KEY=

# Email / Relatório Financeiro
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu@email.com
SMTP_PASS=senha_de_app
EMAIL_CONTADOR=contador@escritorio.com

# Mercado Pago (PainelGest)
MP_ACCESS_TOKEN=APP_USR-...
```

---

## Iniciar / Parar

```batch
iniciar.bat      # Abre 8 terminais — todos os serviços
desligar.bat     # Encerra todos os serviços
```

Serviços individuais:

```bash
python main.py                          # Bot Verônica
python dashboard.py                     # Dashboard web (porta 5000)
python api_veronica.py                  # API REST (porta 5001)
cd painelgest && python app.py          # PainelGest (porta 5002)
cd appmotoboy && python app.py          # AppMotoboy (porta 5003)
cd painelfrota && python app.py         # PainelFrota (porta 5004)
python zeus.py                          # Bot Zeus (segurança)
```

---

## API REST (`api_veronica.py` — porta 5001)

Todas as rotas exigem o header `X-API-Key` ou o parâmetro `?api_key=`.

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/status` | Health check do sistema |
| POST | `/api/perguntar` | Fazer uma pergunta à Verônica |
| POST | `/api/imagem` | Gerar imagem com IA |
| POST | `/api/marketing` | Criar post de marketing |
| GET | `/api/memorias` | Recuperar fatos salvos do usuário |
| POST | `/api/lembrar` | Salvar novo fato na memória |

```bash
# Health check
curl -H "X-API-Key: SUA_CHAVE" http://localhost:5001/api/status

# Pergunta
curl -X POST http://localhost:5001/api/perguntar \
  -H "X-API-Key: SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Olá, tudo bem?"}'
```

---

## Sistema QR Code (Integração entre painéis)

O ecossistema usa tokens QR Code para vincular os três painéis operacionais:

1. **PainelFrota** gera um token único (`/frota/gerar_qr`)
2. **AppMotoboy** escaneia e se vincula ao grupo (`/motoboy/vincular/<token>`)
3. **PainelGest** monitora as entregas via API interna

Endpoint de estatísticas do PainelFrota (chamado pelo Super Admin):
```
GET http://localhost:5004/api/stats
→ { "total_motoboys": N, "corridas_hoje": N, "receita_total": N.NN }
```

---

## PainelGest — Funcionalidades

### Super Admin
- Dashboard com MRR, receita total e ADMs ativos
- Gestão de gestores (criar, editar, bloquear, excluir)
- Planos de assinatura com integração Mercado Pago
- **Grupos de Motoboys** — vinculação com PainelFrota, stats ao vivo
- **Cobrança por Grupo** — por corrida (ex: R$ 0,60/corrida) ou mensalidade fixa
- **Relatório Financeiro** — exportação PDF e envio por email ao contador

### Painel do Dono
- Visão executiva: vendas em tempo real, funcionários ativos, motoboys online
- Kanban de pedidos de todos os restaurantes
- Log de acessos ao sistema
- Relatório financeiro semanal/mensal com gráficos

### Gestor (Admin)
- Cadastro de restaurantes e subadministradores
- Monitoramento de pedidos
- Redes sociais e postagem agendada no Instagram

### Restaurante
- Dashboard Kanban de pedidos
- Cardápio digital com QR Code
- **CRM de Clientes** — histórico, segmentação (VIP/Frequente/Inativo), notas
- Relatórios de vendas e financeiro

---

## Código Único de 4 Caracteres

Cada entidade do ecossistema recebe um código único no formato `L000` (letra + 3 dígitos):
- Clientes PainelGest: ex. `A392`
- Restaurantes PainelGest: ex. `B847`
- Motoboys AppMotoboy: ex. `Z003`
- Motoboys PainelFrota: ex. `M512`

Esses códigos facilitam identificação rápida no suporte e nos relatórios.

---

## CRM de Clientes

Disponível para cada restaurante em `/restaurante/crm`:

- **Importação automática** a partir dos pedidos existentes
- **Segmentação automática:**
  - VIP: ≥10 pedidos ou ticket médio ≥ R$ 80
  - Frequente: ≥5 pedidos (e não VIP)
  - Inativo: último pedido há mais de 30 dias
  - Regular: demais clientes
- **Perfil do cliente:** total de pedidos, valor total, ticket médio, frequência, preferências
- **Notas:** campo livre para observações internas

---

## Backup

```bash
# Backup automático para HDs externos
python organizar.py backup

# Cria pasta timestampada em:
# G:\Backup Veronica\veronica_AAAAMMDD_HHMMSS\
# E:\Backup Veronica\veronica_AAAAMMDD_HHMMSS\
```

---

## Arquitetura da IA

Cadeia de fallback: **Ollama (LLaMA 3 local)** → **Groq** → **Google Gemini**

O módulo `dual_brain.py` verifica qual provedor está disponível e roteia automaticamente.

### Memória
- **Curta duração:** `data/users.json` — últimas 20 mensagens por usuário
- **Longa duração:** `data/memoria_permanente.json` — fatos, preferências, lembretes
- **Evolução:** `data/evolucao.json` — padrões de erro e acerto para auto-aprendizado

---

## Estrutura de Arquivos

```
veronica/
├── main.py                    # Bot Telegram principal
├── dashboard.py               # Dashboard web
├── api_veronica.py            # API REST
├── zeus.py                    # Bot de segurança
├── iniciar.bat                # Iniciar todos os serviços
├── desligar.bat               # Encerrar todos os serviços
├── organizar.py               # Backup e organização
├── requirements.txt
├── .env                       # Secrets (não commitar!)
├── modules/                   # Módulos da Verônica
│   ├── dual_brain.py          # Roteamento de IA
│   ├── ai_brain.py            # Lógica de resposta
│   ├── memory.py              # Memória curta duração
│   ├── memoria_permanente.py  # Memória longa duração
│   ├── conteudo.py            # eBooks, scripts, posts
│   ├── financeiro.py          # Cotações e finanças
│   ├── marketing.py           # Campanhas e cópias
│   ├── visao.py               # Captura de tela
│   ├── controle_pc.py         # Automação keyboard/mouse
│   ├── cyber.py               # Segurança e scanning
│   └── ...
├── painelgest/                # SaaS de restaurantes (porta 5002)
│   ├── app.py
│   ├── requirements.txt
│   ├── templates/
│   └── instance/painelgest.db
├── appmotoboy/                # App do entregador (porta 5003)
│   ├── app.py
│   └── instance/motoboy.db
└── painelfrota/               # Gestão de frotas (porta 5004)
    ├── app.py
    └── instance/frota.db
```

---

## Suporte

- Issues: [github.com/seu-usuario/veronica/issues](https://github.com/seu-usuario/veronica/issues)
- Email: tradermilionarioemds@gmail.com
