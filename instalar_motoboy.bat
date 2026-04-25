@echo off
title Instalador AppMotoboy
chcp 65001 > nul
color 0C

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       INSTALADOR — APP MOTOBOY               ║
echo  ║   GPS, Entregas, Historico, Ganhos           ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Instalando dependencias...
pip install flask flask-sqlalchemy flask-login werkzeug python-dotenv requests qrcode
echo.

echo [2/4] Inicializando banco AppMotoboy...
if not exist appmotoboy mkdir appmotoboy
if not exist appmotoboy\instance mkdir appmotoboy\instance
python -c "
import sys, os
sys.path.insert(0,'appmotoboy')
try:
    from app import app, db
    with app.app_context():
        db.create_all()
    print('Banco AppMotoboy criado OK')
except Exception as e:
    print('Banco sera criado na primeira execucao:', e)
"
echo.

echo [3/4] Verificando arquivos...
if exist appmotoboy\app.py (echo  appmotoboy\app.py   OK) else (echo  appmotoboy\app.py   FALTANDO — crie o app primeiro)
echo.

echo [4/4] Iniciando AppMotoboy na porta 5003...
echo.
echo  Acesse: http://localhost:5003
echo.
if exist appmotoboy\app.py (
    start "" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python appmotoboy/app.py"
) else (
    echo  ERRO: appmotoboy\app.py nao encontrado. Execute instalar_tudo.bat primeiro.
)

pause
