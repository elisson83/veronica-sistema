@echo off
title Instalador Completo — Veronica IA + PainelGest + Frota
chcp 65001 > nul
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║           INSTALADOR COMPLETO — VERONICA IA          ║
echo  ║                                                      ║
echo  ║  PainelGest  (5002)  Restaurantes + Super Admin      ║
echo  ║  AppMotoboy  (5003)  App dos Motoboys                ║
echo  ║  PainelFrota (5004)  Gestao da Frota                 ║
echo  ║  Veronica IA (5000)  Dashboard + Bot Telegram        ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

:: ── Dependencias ────────────────────────────────────────────
echo ═══════════════════════════════════════════════════════
echo  [ETAPA 1/6] Instalando todas as dependencias Python...
echo ═══════════════════════════════════════════════════════
pip install flask flask-sqlalchemy flask-login werkzeug apscheduler ^
    instagrapi mercadopago python-dotenv pillow qrcode requests ^
    groq google-generativeai openai python-telegram-bot ^
    yfinance duckduckgo-search tweepy pyautogui mss
echo.

:: ── Banco PainelGest ────────────────────────────────────────
echo ═══════════════════════════════════════════════════════
echo  [ETAPA 2/6] Inicializando banco PainelGest...
echo ═══════════════════════════════════════════════════════
python -c "
import sys
sys.path.insert(0,'painelgest')
from app import app, db, SuperAdmin
with app.app_context():
    db.create_all()
    if not SuperAdmin.query.filter_by(username='superadmin').first():
        from werkzeug.security import generate_password_hash
        sa = SuperAdmin(username='superadmin', senha_hash=generate_password_hash('admin123'))
        db.session.add(sa)
        db.session.commit()
    print('PainelGest OK — superadmin/admin123')
"
echo.

:: ── AppMotoboy ──────────────────────────────────────────────
echo ═══════════════════════════════════════════════════════
echo  [ETAPA 3/6] Inicializando AppMotoboy...
echo ═══════════════════════════════════════════════════════
if not exist appmotoboy mkdir appmotoboy
if not exist appmotoboy\instance mkdir appmotoboy\instance
if not exist appmotoboy\templates mkdir appmotoboy\templates
if not exist appmotoboy\static mkdir appmotoboy\static
python -c "
import sys
sys.path.insert(0,'appmotoboy')
try:
    from app import app, db
    with app.app_context():
        db.create_all()
    print('AppMotoboy OK')
except Exception as e:
    print('AppMotoboy: sera criado agora —', str(e)[:60])
"
echo.

:: ── PainelFrota ─────────────────────────────────────────────
echo ═══════════════════════════════════════════════════════
echo  [ETAPA 4/6] Inicializando PainelFrota...
echo ═══════════════════════════════════════════════════════
if not exist painelfrota mkdir painelfrota
if not exist painelfrota\instance mkdir painelfrota\instance
if not exist painelfrota\templates mkdir painelfrota\templates
if not exist painelfrota\static mkdir painelfrota\static
python -c "
import sys
sys.path.insert(0,'painelfrota')
try:
    from app import app, db
    with app.app_context():
        db.create_all()
    print('PainelFrota OK')
except Exception as e:
    print('PainelFrota: sera criado agora —', str(e)[:60])
"
echo.

:: ── Backup inicial ──────────────────────────────────────────
echo ═══════════════════════════════════════════════════════
echo  [ETAPA 5/6] Backup inicial nos HDs...
echo ═══════════════════════════════════════════════════════
python organizar.py backup
echo.

:: ── Iniciar todos os servicos ────────────────────────────────
echo ═══════════════════════════════════════════════════════
echo  [ETAPA 6/6] Iniciando todos os servicos...
echo ═══════════════════════════════════════════════════════
echo.

start "" cmd /k "title PainelGest-5002 && cd /d %USERPROFILE%\Desktop\veronica && python -m flask --app painelgest/app.py run --port 5002"
timeout /t 2 /nobreak >nul

if exist appmotoboy\app.py (
    start "" cmd /k "title AppMotoboy-5003 && cd /d %USERPROFILE%\Desktop\veronica && python appmotoboy/app.py"
    timeout /t 2 /nobreak >nul
)

if exist painelfrota\app.py (
    start "" cmd /k "title PainelFrota-5004 && cd /d %USERPROFILE%\Desktop\veronica && python painelfrota/app.py"
    timeout /t 2 /nobreak >nul
)

:: ── Sumario ─────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║                 INSTALACAO CONCLUIDA!                ║
echo  ╠══════════════════════════════════════════════════════╣
echo  ║  Super Admin   http://localhost:5002/super/login     ║
echo  ║  PainelGest    http://localhost:5002                 ║
echo  ║  AppMotoboy    http://localhost:5003                 ║
echo  ║  PainelFrota   http://localhost:5004                 ║
echo  ╠══════════════════════════════════════════════════════╣
echo  ║  Login padrao: superadmin / admin123                 ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Instalacao concluida!`nPainelGest: http://localhost:5002`nAppMotoboy: http://localhost:5003`nPainelFrota: http://localhost:5004', 'Veronica IA', 'OK', 'Information')" 2>nul

pause
