@echo off
title Instalador Super Admin
chcp 65001 > nul
color 09

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       INSTALADOR — SUPER ADMIN               ║
echo  ║   MRR, Gestores, Planos, Bloqueios           ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Instalando dependencias...
pip install flask flask-sqlalchemy flask-login werkzeug apscheduler mercadopago python-dotenv requests
echo.

echo [2/4] Criando superadmin no banco...
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
        print('SuperAdmin criado: superadmin / admin123')
    else:
        print('SuperAdmin ja existe')
"
echo.

echo [3/4] Verificando modulo super admin...
if exist painelgest\templates\super_dashboard.html (echo  super_dashboard     OK) else (echo  super_dashboard     FALTANDO)
if exist painelgest\templates\super_gestores.html  (echo  super_gestores      OK) else (echo  super_gestores      FALTANDO)
if exist painelgest\templates\super_planos.html    (echo  super_planos        OK) else (echo  super_planos        FALTANDO)
echo.

echo [4/4] Iniciando PainelGest (Super Admin incluso)...
echo.
echo  Super Admin: http://localhost:5002/super/login
echo  Login: superadmin / admin123
echo.
start "" cmd /k "cd /d %USERPROFILE%\Desktop\veronica && python -m flask --app painelgest/app.py run --port 5002"

echo  Super Admin iniciado!
pause
