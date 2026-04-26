@echo off
title Instalador App Restaurante
chcp 65001 > nul
color 0E

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║      INSTALADOR — APP RESTAURANTE            ║
echo  ║  Cardápio · Pedidos · Kanban · QR Frota      ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Instalando dependências...
pip install flask flask-sqlalchemy flask-login werkzeug python-dotenv ^
    pillow qrcode requests fpdf2
echo.

echo [2/4] Inicializando banco de dados...
python -c "
import sys, os
sys.path.insert(0,'painelgest')
os.chdir('painelgest')
from app import app, db
with app.app_context():
    db.create_all()
    print('  Banco do Restaurante: OK')
"
echo.

echo [3/4] Verificando módulos do restaurante...
if exist painelgest\templates\kanban.html              (echo  kanban.html            OK) else (echo  kanban.html           FALTANDO)
if exist painelgest\templates\cardapio.html            (echo  cardapio.html          OK) else (echo  cardapio.html         FALTANDO)
if exist painelgest\templates\perfil_restaurante.html  (echo  perfil_restaurante     OK) else (echo  perfil_restaurante    FALTANDO)
if exist painelgest\templates\vagas_restaurante.html   (echo  vagas_restaurante      OK) else (echo  vagas_restaurante     FALTANDO)
if exist painelgest\templates\qr_frota.html            (echo  qr_frota.html          OK) else (echo  qr_frota.html         FALTANDO)
echo.

echo [4/4] Iniciando PainelGest na porta 5002...
echo.
echo  Login Restaurante: http://localhost:5002/restaurante/login
echo  Credenciais: criadas pelo gestor no PainelGest
echo.
start "Restaurante-5002" cmd /k "cd /d %USERPROFILE%\Desktop\veronica\painelgest && python app.py"

echo  App Restaurante iniciado!
pause
