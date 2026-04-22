@echo off
title Verônica IA - Iniciando...
chcp 65001 > nul
echo.
echo ================================================
echo    VERONICA IA — Subindo todos os servicos...
echo ================================================
echo.

echo [1/6] Ollama (LLM local)...
start "Ollama" cmd /k "ollama run llama3"
timeout /t 5 /nobreak > nul

echo [2/6] Dashboard (porta 5000)...
start "Dashboard" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python dashboard.py"
timeout /t 2 /nobreak > nul

echo [3/6] API Veronica (porta 5001)...
start "API Verônica" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python api_veronica.py"
timeout /t 2 /nobreak > nul

echo [4/6] PainelGest (porta 5002)...
start "PainelGest" cmd /k "cd /d %USERPROFILE%\Desktop\veronica\painelgest && python app.py"
timeout /t 2 /nobreak > nul

echo [5/6] Bot Veronica (Telegram)...
start "Verônica Bot" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python main.py"
timeout /t 2 /nobreak > nul

echo [6/6] Zeus Guardiao (Telegram)...
start "Zeus Guardiao" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python zeus.py"

echo.
echo ================================================
echo    TUDO INICIADO COM SUCESSO!
echo ================================================
echo.
echo   Dashboard :  http://localhost:5000
echo   API       :  http://localhost:5001
echo   PainelGest:  http://localhost:5002
echo   Veronica  :  @veronica_assistente_bot
echo   Zeus      :  @zeus_guardiao_bot
echo.
pause
