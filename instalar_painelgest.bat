@echo off
title Instalador PainelGest
chcp 65001 > nul
color 0B

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║        INSTALADOR — PAINELGEST               ║
echo  ║    Painel de Gestao de Restaurantes          ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Instalando dependencias Python...
pip install flask flask-sqlalchemy flask-login werkzeug apscheduler instagrapi mercadopago python-dotenv pillow qrcode requests
echo.

echo [2/4] Inicializando banco de dados...
python -c "import sys; sys.path.insert(0,'painelgest'); from app import app, db; app.app_context().__enter__(); db.create_all(); print('Banco criado OK')"
echo.

echo [3/4] Verificando estrutura...
if exist painelgest\app.py (echo  app.py        OK) else (echo  app.py        FALTANDO)
if exist painelgest\instance\painelgest.db (echo  banco.db      OK) else (echo  banco.db      FALTANDO)
if exist painelgest\templates (echo  templates\    OK) else (echo  templates\    FALTANDO)
echo.

echo [4/4] Iniciando PainelGest na porta 5002...
echo.
echo  Acesse: http://localhost:5002
echo  Login:  superadmin / admin123
echo.
start "" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python -m flask --app painelgest/app.py run --port 5002"

echo  PainelGest iniciado!
pause
