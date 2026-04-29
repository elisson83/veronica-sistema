@echo off
title Verônica IA — Iniciando todos os serviços
chcp 65001 > nul
color 0A
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║          VERÔNICA IA — INICIANDO ECOSSISTEMA             ║
echo  ║  7 Produtos · IA em Cascata · GPS Real-time · PIX Auto   ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/9] Ollama (LLM local — llama3)...
start "Ollama LLM" cmd /k "ollama run llama3"
timeout /t 5 /nobreak > nul

echo [2/9] Dashboard Verônica (porta 5000)...
start "Dashboard-5000" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python dashboard.py"
timeout /t 2 /nobreak > nul

echo [3/9] API Verônica REST (porta 5001)...
start "API-5001" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python api_veronica.py"
timeout /t 2 /nobreak > nul

echo [4/9] PainelGest — Super Admin + Restaurantes (porta 5002)...
start "PainelGest-5002" cmd /k "cd /d %USERPROFILE%\Desktop\veronica\painelgest && python app.py"
timeout /t 2 /nobreak > nul

echo [5/9] AppMotoboy — GPS + Entregas + Ganhos (porta 5003)...
start "AppMotoboy-5003" cmd /k "cd /d %USERPROFILE%\Desktop\veronica\appmotoboy && python app.py"
timeout /t 2 /nobreak > nul

echo [6/9] PainelFrota — Gestão de Frota (porta 5004)...
start "PainelFrota-5004" cmd /k "cd /d %USERPROFILE%\Desktop\veronica\painelfrota && python app.py"
timeout /t 2 /nobreak > nul

echo [7/9] PainelDono — Acesso do Dono (porta 5005)...
start "PainelDono-5005" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python run_dono_5005.py"
timeout /t 2 /nobreak > nul

echo [8/9] Verônica Bot (Telegram)...
start "Verônica-Telegram" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python main.py"
timeout /t 2 /nobreak > nul

echo [9/9] Zeus Guardião (Segurança — Telegram)...
start "Zeus-Telegram" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python zeus.py"

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║               TODOS OS SERVIÇOS ATIVOS!                  ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║  Dashboard     http://localhost:5000                     ║
echo  ║  API REST      http://localhost:5001                     ║
echo  ║  PainelGest    http://localhost:5002                     ║
echo  ║  Super Admin   http://localhost:5002/super/login         ║
echo  ║  AppMotoboy    http://localhost:5003                     ║
echo  ║  PainelFrota   http://localhost:5004                     ║
echo  ║  PainelDono    http://localhost:5005/dono/login          ║
echo  ║  Verônica      @veronica_assistente_bot                  ║
echo  ║  Zeus          @zeus_guardiao_bot                        ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║  Site          site\index.html                           ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Dica: use desligar.bat para encerrar todos os servicos.
echo.
pause
