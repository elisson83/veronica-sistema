@echo off
title Instalador Super Admin
chcp 65001 > nul
color 09

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       INSTALADOR — SUPER ADMIN               ║
echo  ║   MRR · Gestores · Planos · Bloqueios        ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d %USERPROFILE%\Desktop\veronica

echo [1/4] Instalando dependências...
pip install flask flask-sqlalchemy flask-login werkzeug apscheduler ^
    mercadopago python-dotenv requests qrcode
echo.

echo [2/4] Criando SuperAdmin no banco...
python -c "
import sys, os
sys.path.insert(0,'painelgest')
os.chdir('painelgest')
from app import app, db, SuperAdmin
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
"
echo.

echo [3/4] Verificando módulo Super Admin...
if exist painelgest\templates\super_dashboard.html     (echo  super_dashboard        OK) else (echo  super_dashboard        FALTANDO)
if exist painelgest\templates\super_gestores.html      (echo  super_gestores         OK) else (echo  super_gestores         FALTANDO)
if exist painelgest\templates\super_novo_gestor.html   (echo  super_novo_gestor      OK) else (echo  super_novo_gestor      FALTANDO)
if exist painelgest\templates\super_editar_gestor.html (echo  super_editar_gestor    OK) else (echo  super_editar_gestor    FALTANDO)
echo.

echo [4/4] Iniciando PainelGest na porta 5002...
echo.
echo  Super Admin: http://localhost:5002/super/login
echo  Login: superadmin / admin123
echo.
start "SuperAdmin-5002" cmd /k "cd /d %USERPROFILE%\Desktop\veronica\painelgest && python app.py"

echo  Super Admin iniciado!
pause
