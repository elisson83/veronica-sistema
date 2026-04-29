# ESTRUTURA DO PROJETO — Verônica IA

> Ecossistema de 7 produtos rodando em paralelo. Cada produto tem sua própria pasta, banco de dados e requirements.

---

## Serviços e Portas

| Produto | Arquivo principal | Porta | Descrição |
|---|---|---|---|
| Dashboard IA | `dashboard.py` | 5000 | Painel web da Verônica IA |
| API REST | `api_veronica.py` | 5001 | API pública com autenticação por chave |
| PainelGest | `painelgest/app.py` | 5002 | Super Admin + Gestão de restaurantes, clientes, vencimentos |
| AppMotoboy | `appmotoboy/app.py` | 5003 | App do motoboy — GPS, entregas, ganhos |
| PainelFrota | `painelfrota/app.py` | 5004 | Gestão de frota — motoboys, turnos, financeiro |
| PainelDono | `run_dono_5005.py` | 5005 | Acesso restrito do dono da empresa |
| Bot Telegram | `main.py` | — | @veronica_assistente_bot |
| Zeus (Segurança) | `zeus.py` | — | @zeus_guardiao_bot |

---

## Estrutura de Pastas

```
veronica/
│
├── main.py                  # Bot Telegram Verônica (100+ comandos)
├── zeus.py                  # Bot Telegram Zeus (segurança/monitoramento)
├── dashboard.py             # Dashboard web Flask (porta 5000)
├── api_veronica.py          # REST API com auth por X-API-Key (porta 5001)
├── run_dono_5005.py         # Painel do Dono — roda painelgest na porta 5005
├── config.py                # Configurações globais
│
├── modules/                 # Módulos Python compartilhados por todos os serviços
│   ├── ai_brain.py          # Roteamento de IA (Ollama → Groq → Gemini)
│   ├── dual_brain.py        # Fallback entre provedores de IA
│   ├── memory.py            # Memória de curto prazo (últimas 20 msgs/usuário)
│   ├── memoria_permanente.py# Memória de longo prazo (fatos, preferências)
│   ├── telegram_bot.py      # Handlers do bot Telegram (~63KB, 100+ comandos)
│   ├── email_utils.py       # Envio de e-mail Gmail SMTP (reset senha, PDF, notificações)
│   ├── conteudo.py          # eBooks, scripts de vídeo, posts sociais
│   ├── financeiro.py        # Cotações em tempo real via yfinance
│   ├── marketing.py         # Copy de campanhas, análise de tendências
│   ├── visao.py             # Captura de tela (Windows only — mss)
│   ├── visao_ia.py          # Análise de imagens com IA
│   ├── visao_geradora.py    # Geração de imagens
│   ├── controle_pc.py       # Automação teclado/mouse (Windows — pyautogui)
│   ├── cyber.py             # Scan de rede, integração Kali Linux
│   ├── twitter_bot.py       # Posts no Twitter via Tweepy
│   ├── pesquisa.py          # Busca web/notícias via DuckDuckGo
│   ├── licenca.py           # Registro e verificação de licenças
│   ├── seguranca.py         # Vault de senhas, autorização de usuários
│   ├── gerenciador_chaves.py# Rotação e gestão de chaves API
│   ├── auto_update.py       # Auto-atualização do sistema
│   ├── agente.py            # Agente autônomo de tarefas
│   ├── conhecimento.py      # Base de conhecimento geral
│   └── evolucao.py          # Self-learning (erros e acertos)
│
├── painelgest/              # PainelGest — porta 5002
│   ├── app.py               # Flask app principal (~57KB)
│   ├── scheduler.py         # Tarefas agendadas (Instagram, vencimentos)
│   ├── restaurante.py       # Módulo de restaurante
│   ├── requirements.txt     # Dependências específicas
│   ├── .env                 # Vars: MERCADOPAGO, WHATSAPP, SMTP
│   ├── templates/           # 60+ templates HTML
│   └── instance/            # painelgest.db (SQLite)
│
├── appmotoboy/              # AppMotoboy — porta 5003
│   ├── app.py               # App do motoboy (GPS, entregas, ganhos)
│   ├── requirements.txt     # Dependências específicas
│   ├── templates/           # 12 templates HTML
│   └── instance/            # motoboy.db (SQLite)
│
├── painelfrota/             # PainelFrota — porta 5004
│   ├── app.py               # Gestão de frota, financeiro, QR Code
│   ├── requirements.txt     # Dependências específicas
│   ├── templates/           # 22 templates HTML
│   └── instance/            # frota.db (SQLite)
│
├── data/                    # Dados persistentes da Verônica IA
│   ├── users.json           # Memória de curto prazo por usuário
│   ├── memoria_permanente.json # Fatos e preferências de longo prazo
│   ├── conhecimento.json    # Base de conhecimento
│   ├── evolucao.json        # Padrões de self-learning
│   ├── marketing.json       # Dados de marketing
│   └── licenca.json         # Informações de licença
│
├── templates/               # Templates do Dashboard e API (porta 5000/5001)
│   ├── dashboard.html
│   └── status.html
│
├── assets/                  # Imagens geradas, eBooks, screenshots
│   └── geradas/             # Imagens criadas pela IA
│
├── site/                    # Site estático de apresentação
│   └── index.html
│
├── scripts/                 # Scripts utilitários (não fazem parte do sistema em produção)
│   └── escrever_bot.py      # Script de patch aplicado ao telegram_bot.py
│
├── logs/                    # Logs do sistema
│
├── .env                     # Todas as chaves API (NUNCA commitar)
├── requirements.txt         # Dependências da Verônica IA (bots + dashboard + API)
├── organizar.py             # Script de backup para HD G e HD E
├── testar_email.py          # Testa envio de e-mail via Gmail SMTP
├── iniciar.bat              # Inicia todos os 7 serviços + Ollama
├── desligar.bat             # Encerra todos os processos Python/Ollama
├── backup.bat               # Git push + cópia para HD G: e HD E:
├── Procfile                 # Heroku: worker: python main.py
├── CLAUDE.md                # Instruções para o Claude Code
├── ESTRUTURA.md             # Este arquivo
└── README.md                # Documentação do projeto
```

---

## Como Iniciar

```bat
# Iniciar tudo (abre 9 terminais)
iniciar.bat

# Parar tudo
desligar.bat

# Backup GitHub + HDs
backup.bat

# Testar e-mail
python testar_email.py
```

## Banco de Dados

Cada produto tem seu próprio SQLite isolado:

| Produto | Arquivo |
|---|---|
| PainelGest | `painelgest/instance/painelgest.db` |
| AppMotoboy | `appmotoboy/instance/motoboy.db` |
| PainelFrota | `painelfrota/instance/frota.db` |

## Variáveis de Ambiente (.env)

Veja o `.env` na raiz. As principais:

| Variável | Obrigatória | Para quê |
|---|---|---|
| `GROQ_API_KEY` | ✅ | IA principal (LLaMA 3) |
| `GEMINI_API_KEY` | ✅ | Fallback de IA |
| `TELEGRAM_TOKEN` | ✅ | Bot @veronica_assistente_bot |
| `ZEUS_TOKEN` | ✅ | Bot @zeus_guardiao_bot |
| `SMTP_USER` / `SMTP_PASS` | ✅ | E-mails (reset senha, PDF, notificações) |
| `OPENAI_API_KEY` | ⚡ | DALL-E e GPT-4 |
| `WHATSAPP_ACCESS_TOKEN` | ⚡ | Mensagens WhatsApp |
| `INSTAGRAM_TOKEN` | ⚡ | Posts automáticos Instagram |
| `REPLICATE_API_TOKEN` | ⚡ | Imagens estilo Midjourney |
| `YOUTUBE_API_KEY` | ⚡ | Publicar no YouTube |

✅ = Obrigatória · ⚡ = Opcional (funcionalidade extra)
