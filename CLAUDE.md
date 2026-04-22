# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Verônica IA** is a multi-component AI assistant ecosystem built in Python. It exposes five distinct services that run in parallel:

| Service | File | Port/Channel |
|---|---|---|
| Telegram Bot | `main.py` | @veronica_assistente_bot |
| Web Dashboard | `dashboard.py` | localhost:5000 |
| REST API | `api_veronica.py` | localhost:5001 |
| Admin Panel | `painelgest/app.py` | localhost:5002 |
| Security Bot | `zeus.py` | @zeus_guardiao_bot |

## Commands

### Start / Stop

```batch
# Windows — starts all 5 services in separate terminals
iniciar.bat

# Stop all
desligar.bat
```

```bash
# Individual services
python main.py
python dashboard.py
python api_veronica.py
cd painelgest && python app.py
python zeus.py
```

### Install dependencies

```bash
pip install -r requirements.txt
pip install -r painelgest/requirements.txt
```

### Test the API manually

```bash
# Health check
curl -H "X-API-Key: <VERONICA_API_KEY>" http://localhost:5001/api/status

# Ask a question
curl -X POST http://localhost:5001/api/perguntar \
  -H "X-API-Key: <VERONICA_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Olá!"}'
```

There is no automated test suite and no linter is configured.

### Heroku deployment

```bash
git push heroku main   # Procfile runs: worker: python main.py
```

## Architecture

### AI Provider Layer (`modules/dual_brain.py` + `modules/ai_brain.py`)

The system uses a **fallback chain**: local Ollama (LLaMA 3) → Groq → Google Gemini. `dual_brain.py` pings each provider and returns the first live one; `ai_brain.py` uses that result to route questions, optionally enriching prompts with web search results and user memory.

### Memory System (`modules/memory.py`, `modules/memoria_permanente.py`)

Two-tier memory:
- **Short-term** (`data/users.json`): last 20 messages per user ID, loaded into every prompt.
- **Long-term** (`data/memoria_permanente.json`): structured facts, preferences, reminders — retrieved selectively by `buscar_memorias()`.

`data/evolucao.json` tracks errors and success patterns for self-learning; `data/conhecimento.json` is a general knowledge base.

### Telegram Bot (`modules/telegram_bot.py`, ~63 KB)

The main interaction surface. Handles 100+ commands, user authentication (authorized by `ADMIN_TELEGRAM_ID` or password), and routes requests to the appropriate module (content, finance, vision, PC control, etc.).

### Specialized Modules (`modules/`)

| Module | Responsibility |
|---|---|
| `conteudo.py` | eBooks, YouTube analysis, video scripts, social posts |
| `financeiro.py` | Real-time market quotes via yfinance |
| `marketing.py` | Campaign copy, trend analysis |
| `visao.py` / `visao_ia.py` | Screenshot capture, image analysis |
| `controle_pc.py` | Keyboard/mouse automation via pyautogui |
| `cyber.py` | Network scanning, Kali Linux integration |
| `twitter_bot.py` | Tweet posting via Tweepy |
| `pesquisa.py` | Web/news search via DuckDuckGo |
| `licenca.py` | License registration and verification |
| `auto_update.py` | Self-update logic |
| `gerenciador_chaves.py` | API key rotation |
| `seguranca.py` | Password vault, user authorization |

### Admin Panel (`painelgest/app.py`)

Flask + Flask-SQLAlchemy app with SQLite (`painelgest/instance/painelgest.db`). Manages:
- Administrators (login with `werkzeug` password hashing)
- Clients (nome, login, senha, status)
- Instagram profiles (scheduled posting)
- Vencimentos/payments (tracking)

### REST API (`api_veronica.py`)

All routes require `X-API-Key` header or `?api_key=` query param.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/status` | System health |
| POST | `/api/perguntar` | Ask a question |
| POST | `/api/imagem` | Generate an image |
| POST | `/api/marketing` | Create a marketing post |
| GET | `/api/memorias` | Retrieve user facts |
| POST | `/api/lembrar` | Save a new fact |

## Configuration

All secrets go in `.env` (never commit this file):

```
GROQ_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
TELEGRAM_TOKEN=
ZEUS_TOKEN=
ADMIN_TELEGRAM_ID=8106101043
TWITTER_CONSUMER_KEY=
TWITTER_CONSUMER_SECRET=
TWITTER_BEARER_TOKEN=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=
MODEL_PROVIDER=groq          # groq | openai | gemini | local
MODEL_NAME=llama-3.3-70b-versatile
VERONICA_API_KEY=
ZEUS_KEY=
```

## Key Conventions

- Code and comments are written in **Portuguese**.
- Module functions follow the pattern `verb_noun()` (e.g., `buscar_memorias`, `salvar_mensagem`, `chamar_groq`).
- User ID `8106101043` (Elisson) is the default admin; additional users gain access via a shared password defined in `seguranca.py`.
- `controle_pc.py` and `mss` (screenshots) are **Windows-only**; avoid introducing cross-platform assumptions here.
- The painelgest admin panel stores client passwords in **plaintext** — intentional for the current scope, do not add complexity without direction.
