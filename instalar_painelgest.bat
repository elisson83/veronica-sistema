@echo off
title Instalador PainelGest
chcp 65001 > nul
color 0B

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║        INSTALADOR — PAINELGEST               ║
echo  ║    Painel de Gestão · Super Admin · SaaS     ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Instalando dependências Python...
pip install flask flask-sqlalchemy flask-login werkzeug apscheduler ^
    instagrapi mercadopago python-dotenv pillow qrcode requests fpdf2
echo.

echo [2/4] Inicializando banco de dados...
python -c "
import sys, os
sys.path.insert(0, 'painelgest')
os.chdir('painelgest')
from app import app, db, SuperAdmin, Administrador
with app.app_context():
    db.create_all()
    if not SuperAdmin.query.filter_by(username='superadmin').first():
        from werkzeug.security import generate_password_hash
        sa = SuperAdmin(username='superadmin', senha_hash=generate_password_hash('admin123'))
        db.session.add(sa)
        db.session.commit()
        print('  SuperAdmin criado: superadmin / admin123')
    else:
        print('  SuperAdmin ja existe')
    if not Administrador.query.filter_by(username='admin').first():
        adm = Administrador('admin', 'admin123', plano='premium')
        db.session.add(adm)
        db.session.commit()
        print('  Admin criado: admin / admin123')
    else:
        print('  Admin ja existe')
print('  Banco PainelGest: OK')
"
echo.

echo [3/4] Verificando estrutura...
if exist painelgest\app.py                              (echo  app.py                OK) else (echo  app.py                FALTANDO)
if exist painelgest\instance\painelgest.db              (echo  painelgest.db         OK) else (echo  painelgest.db        sera criado)
if exist painelgest\templates\dashboard.html            (echo  templates\            OK) else (echo  templates\           FALTANDO)
if exist painelgest\templates\super_dashboard.html      (echo  super_dashboard       OK) else (echo  super_dashboard       FALTANDO)
if exist painelgest\templates\dashboard_restaurante.html (echo  dashboard_restaurante OK) else (echo  dashboard_restaurante FALTANDO)
echo.

echo [4/4] Iniciando PainelGest na porta 5002...
echo.
echo  Super Admin  : http://localhost:5002/super/login
echo  Admin/Gestor : http://localhost:5002/login
echo  Restaurante  : http://localhost:5002/restaurante/login
echo  Login padrao : superadmin / admin123
echo.
start "PainelGest-5002" cmd /k "cd /d %USERPROFILE%\Desktop\veronica\painelgest && python app.py"

echo  PainelGest iniciado!
pause
