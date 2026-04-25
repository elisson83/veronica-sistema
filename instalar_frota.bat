@echo off
title Instalador PainelFrota
chcp 65001 > nul
color 0D

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       INSTALADOR — PAINEL FROTA              ║
echo  ║   4 ADMs, 50 Motoboys, Financeiro            ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Instalando dependencias...
pip install flask flask-sqlalchemy flask-login werkzeug python-dotenv requests qrcode
echo.

echo [2/4] Inicializando banco PainelFrota...
if not exist painelfrota mkdir painelfrota
if not exist painelfrota\instance mkdir painelfrota\instance
python -c "
import sys
sys.path.insert(0,'painelfrota')
try:
    from app import app, db
    with app.app_context():
        db.create_all()
    print('Banco PainelFrota criado OK')
except Exception as e:
    print('Banco sera criado na primeira execucao:', e)
"
echo.

echo [3/4] Verificando arquivos...
if exist painelfrota\app.py (echo  painelfrota\app.py   OK) else (echo  painelfrota\app.py   FALTANDO — crie o app primeiro)
echo.

echo [4/4] Iniciando PainelFrota na porta 5004...
echo.
echo  Acesse: http://localhost:5004
echo.
if exist painelfrota\app.py (
    start "" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python painelfrota/app.py"
) else (
    echo  ERRO: painelfrota\app.py nao encontrado. Execute instalar_tudo.bat primeiro.
)

pause
