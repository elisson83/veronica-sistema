@echo off
title Instalador Verônica IA
chcp 65001 > nul
color 05

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║         INSTALADOR — VERÔNICA IA                 ║
echo  ║  Bot Telegram · Dashboard · API · Zeus           ║
echo  ╚══════════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/5] Instalando dependências da IA...
pip install flask flask-cors python-telegram-bot groq google-generativeai ^
    openai yfinance duckduckgo-search tweepy pyautogui mss pillow ^
    requests beautifulsoup4 psutil
echo.

echo [2/5] Verificando arquivo .env...
if exist .env (
    echo  .env encontrado OK
    findstr /C:"TELEGRAM_TOKEN" .env >nul 2>&1
    if errorlevel 1 (echo  AVISO: TELEGRAM_TOKEN nao encontrado em .env) else (echo  TELEGRAM_TOKEN    OK)
    findstr /C:"GROQ_API_KEY" .env >nul 2>&1
    if errorlevel 1 (echo  AVISO: GROQ_API_KEY nao encontrado em .env) else (echo  GROQ_API_KEY      OK)
    findstr /C:"ADMIN_TELEGRAM_ID" .env >nul 2>&1
    if errorlevel 1 (echo  AVISO: ADMIN_TELEGRAM_ID nao encontrado em .env) else (echo  ADMIN_TELEGRAM_ID OK)
) else (
    echo  AVISO: Arquivo .env nao encontrado!
    echo  Crie o arquivo .env na raiz com as chaves de API.
    echo  Veja README.md para a lista de variaveis necessarias.
)
echo.

echo [3/5] Verificando estrutura do projeto...
if exist main.py        (echo  main.py         OK) else (echo  main.py         FALTANDO)
if exist dashboard.py   (echo  dashboard.py    OK) else (echo  dashboard.py    FALTANDO)
if exist api_veronica.py (echo  api_veronica.py OK) else (echo  api_veronica.py FALTANDO)
if exist zeus.py        (echo  zeus.py         OK) else (echo  zeus.py         FALTANDO)
if exist modules\       (echo  modules\        OK) else (echo  modules\        FALTANDO)
if exist data\          (echo  data\           OK) else (echo  data\           FALTANDO)
echo.

echo [4/5] Verificando Ollama (LLM local opcional)...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo  Ollama NAO instalado. A IA usara Groq ou Gemini.
    echo  Para instalar Ollama: https://ollama.com/download
) else (
    echo  Ollama instalado OK
)
echo.

echo [5/5] Iniciando todos os servicos Verônica...
echo.
start "Dashboard-5000"  cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python dashboard.py"
timeout /t 2 /nobreak > nul
start "API-5001"        cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python api_veronica.py"
timeout /t 2 /nobreak > nul
start "Veronica-Bot"    cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python main.py"
timeout /t 2 /nobreak > nul
start "Zeus-Bot"        cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python zeus.py"

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║               VERÔNICA IA ATIVA!                 ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║  Dashboard  http://localhost:5000                ║
echo  ║  API REST   http://localhost:5001                ║
echo  ║  Bot        @veronica_assistente_bot             ║
echo  ║  Zeus       @zeus_guardiao_bot                   ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
