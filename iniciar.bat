@echo off
title Verônica IA - Iniciando...
chcp 65001 > nul
echo Iniciando ecossistema Verônica IA...
echo.

start "Ollama" cmd /k "ollama run llama3"
timeout /t 5 /nobreak > nul

start "Dashboard" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python dashboard.py"
timeout /t 2 /nobreak > nul

start "API Verônica" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python api_veronica.py"
timeout /t 2 /nobreak > nul

start "Verônica Bot" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python main.py"
timeout /t 2 /nobreak > nul

start "Zeus Guardiao" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python zeus.py"

echo.
echo Tudo iniciado!
echo Dashboard: http://localhost:5000
echo API Veronica: http://localhost:5001
echo Telegram Veronica: @veronica_assistente_bot
echo Telegram Zeus: @zeus_guardiao_bot
echo.
pause