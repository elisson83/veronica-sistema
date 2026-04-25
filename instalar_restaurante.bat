@echo off
title Instalador App Restaurante
chcp 65001 > nul
color 0E

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║      INSTALADOR — APP RESTAURANTE            ║
echo  ║   Cardapio, Pedidos, Kanban, Perfil          ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Instalando dependencias...
pip install flask flask-sqlalchemy flask-login werkzeug python-dotenv pillow qrcode requests
echo.

echo [2/4] Inicializando banco de dados...
python -c "import sys; sys.path.insert(0,'painelgest'); from app import app, db; app.app_context().__enter__(); db.create_all(); print('OK')"
echo.

echo [3/4] Verificando modulos do restaurante...
if exist painelgest\templates\kanban.html (echo  kanban.html         OK) else (echo  kanban.html         FALTANDO)
if exist painelgest\templates\cardapio.html (echo  cardapio.html       OK) else (echo  cardapio.html       FALTANDO)
if exist painelgest\templates\perfil_restaurante.html (echo  perfil_restaurante  OK) else (echo  perfil_restaurante  FALTANDO)
echo.

echo [4/4] Iniciando PainelGest (inclui modulo restaurante) na porta 5002...
echo.
echo  Acesse: http://localhost:5002/restaurante
echo  Login:  use credenciais do restaurante
echo.
start "" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python -m flask --app painelgest/app.py run --port 5002"

echo  App Restaurante iniciado!
pause
