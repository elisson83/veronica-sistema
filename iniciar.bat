@echo off
title Verônica IA - Iniciando...
chcp 65001 > nul
echo Iniciando ecossistema Verônica IA...
echo.

start "Ollama" cmd /k "ollama run llama3"
timeout /t 5 /nobreak > nul

start "Dashboard" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python dashboard.py"
timeout /t 3 /nobreak > nul

start "Verônica Bot" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python main.py"

echo.
echo Tudo iniciado!
echo Dashboard: http://localhost:5000
echo Telegram: @veronica_assistente_bot
echo.
pause