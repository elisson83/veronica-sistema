@echo off
title Instalador PainelFrota
chcp 65001 > nul
color 0D

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       INSTALADOR — PAINEL FROTA              ║
echo  ║  50 Motoboys · GPS · Remuneração · Financeiro ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Instalando dependências...
pip install flask flask-sqlalchemy flask-login werkzeug apscheduler ^
    python-dotenv requests qrcode pillow
echo.

echo [2/4] Inicializando banco PainelFrota...
if not exist painelfrota\instance mkdir painelfrota\instance
python -c "
import sys, os
sys.path.insert(0,'painelfrota')
os.chdir('painelfrota')
from app import app, db, AdminFrota
with app.app_context():
    db.create_all()
    if not AdminFrota.query.filter_by(username='admin').first():
        a = AdminFrota(nome='Super Admin Frota', username='admin', nivel='super')
        a.set_senha('admin123')
        db.session.add(a)
        db.session.commit()
        print('  Admin Frota criado: admin / admin123')
    else:
        print('  Admin Frota ja existe')
print('  Banco PainelFrota: OK')
"
echo.

echo [3/4] Verificando estrutura...
if exist painelfrota\app.py                       (echo  app.py           OK) else (echo  app.py           FALTANDO)
if exist painelfrota\templates\dashboard.html     (echo  dashboard.html   OK) else (echo  dashboard.html   FALTANDO)
if exist painelfrota\templates\motoboys.html      (echo  motoboys.html    OK) else (echo  motoboys.html    FALTANDO)
if exist painelfrota\templates\motoboy_qr.html    (echo  motoboy_qr.html  OK) else (echo  motoboy_qr.html  FALTANDO)
if exist painelfrota\templates\relatorios.html    (echo  relatorios.html  OK) else (echo  relatorios.html  FALTANDO)
echo.

echo [4/4] Iniciando PainelFrota na porta 5004...
echo.
echo  Acesse   : http://localhost:5004
echo  Login    : admin / admin123
echo  Motoboys : http://localhost:5004/motoboys
echo  Mapa GPS : http://localhost:5004/mapa
echo.
start "PainelFrota-5004" cmd /k "cd /d %USERPROFILE%\Desktop\veronica\painelfrota && python app.py"

echo  PainelFrota iniciado!
pause
