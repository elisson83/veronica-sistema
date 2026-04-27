"""
Painel do Dono — porta 5005
Roda o mesmo PainelGest focado no acesso do Dono.
Acesse: http://localhost:5005/dono/login  (dono / dono123)
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'painelgest'))
os.chdir(os.path.join(os.path.dirname(__file__), 'painelgest'))

from app import app, db, DonoDaEmpresa, migrate_db
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    migrate_db()
    if not DonoDaEmpresa.query.filter_by(username='admin').first():
        d = DonoDaEmpresa(
            username='admin',
            nome='Administrador Dono',
            senha_hash=generate_password_hash('admin123')
        )
        db.session.add(d)
        db.session.commit()
        print('  Dono admin criado: admin / admin123')
    if not DonoDaEmpresa.query.filter_by(username='dono').first():
        d2 = DonoDaEmpresa(
            username='dono',
            nome='Dono da Empresa',
            senha_hash=generate_password_hash('dono123')
        )
        db.session.add(d2)
        db.session.commit()
        print('  Dono padrao criado: dono / dono123')

print('=' * 50)
print('  PAINEL DO DONO — porta 5005')
print('  http://localhost:5005/dono/login')
print('  Login: admin / admin123')
print('  Login: dono  / dono123')
print('=' * 50)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=False)
