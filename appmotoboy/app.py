import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from decimal import Decimal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'motoboy-secret-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'motoboy.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ─── MODELOS ─────────────────────────────────────────────────────────────────

class Motoboy(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(100), nullable=False)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    senha_hash    = db.Column(db.String(200), nullable=False)
    telefone      = db.Column(db.String(20))
    moto_placa    = db.Column(db.String(10))
    moto_modelo   = db.Column(db.String(50))
    foto_path     = db.Column(db.String(200))
    ativo         = db.Column(db.Boolean, default=True)
    disponivel    = db.Column(db.Boolean, default=False)
    lat_atual     = db.Column(db.Float)
    lng_atual     = db.Column(db.Float)
    ultima_loc    = db.Column(db.DateTime)
    # financeiro
    taxa_entrega  = db.Column(db.Float, default=5.0)   # valor por entrega
    saldo_dia     = db.Column(db.Float, default=0.0)
    saldo_total   = db.Column(db.Float, default=0.0)
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)
    # relacionamentos
    entregas      = db.relationship('Entrega', backref='motoboy', lazy=True)
    turnos        = db.relationship('Turno', backref='motoboy', lazy=True)

    def set_senha(self, senha): self.senha_hash = generate_password_hash(senha)
    def check_senha(self, senha): return check_password_hash(self.senha_hash, senha)

class Entrega(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    motoboy_id      = db.Column(db.Integer, db.ForeignKey('motoboy.id'), nullable=False)
    restaurante_nome= db.Column(db.String(100))
    cliente_nome    = db.Column(db.String(100))
    cliente_endereco= db.Column(db.String(200))
    codigo_ifood    = db.Column(db.String(30))
    origem          = db.Column(db.String(20), default='direto')  # direto | ifood | whatsapp
    status          = db.Column(db.String(20), default='pendente')  # pendente | aceita | retirada | entregue | cancelada
    valor_pedido    = db.Column(db.Float, default=0.0)
    taxa_entrega    = db.Column(db.Float, default=5.0)
    adicional_chuva = db.Column(db.Float, default=0.0)
    adicional_pico  = db.Column(db.Float, default=0.0)
    adicional_noturno=db.Column(db.Float, default=0.0)
    valor_total_taxa= db.Column(db.Float, default=5.0)
    distancia_km    = db.Column(db.Float)
    observacao      = db.Column(db.Text)
    criado_em       = db.Column(db.DateTime, default=datetime.utcnow)
    aceito_em       = db.Column(db.DateTime)
    retirado_em     = db.Column(db.DateTime)
    entregue_em     = db.Column(db.DateTime)

    @property
    def duracao_minutos(self):
        if self.entregue_em and self.aceito_em:
            return int((self.entregue_em - self.aceito_em).total_seconds() / 60)
        return None

class Turno(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    motoboy_id  = db.Column(db.Integer, db.ForeignKey('motoboy.id'), nullable=False)
    inicio      = db.Column(db.DateTime, default=datetime.utcnow)
    fim         = db.Column(db.DateTime)
    ativo       = db.Column(db.Boolean, default=True)

    @property
    def duracao_horas(self):
        fim = self.fim or datetime.utcnow()
        return round((fim - self.inicio).total_seconds() / 3600, 1)

# ─── LOGIN ────────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(uid): return Motoboy.query.get(int(uid))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        mb = Motoboy.query.filter_by(username=request.form['username']).first()
        if mb and mb.check_senha(request.form['senha']):
            login_user(mb)
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha incorretos', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ─── DASHBOARD PRINCIPAL ──────────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    hoje = date.today()
    entregas_hoje = Entrega.query.filter(
        Entrega.motoboy_id == current_user.id,
        db.func.date(Entrega.criado_em) == hoje
    ).all()
    entregues_hoje = [e for e in entregas_hoje if e.status == 'entregue']
    ganhos_hoje    = sum(e.valor_total_taxa for e in entregues_hoje)
    turno_ativo    = Turno.query.filter_by(motoboy_id=current_user.id, ativo=True).first()
    pendentes      = Entrega.query.filter_by(motoboy_id=current_user.id, status='pendente').all()

    return render_template('dashboard.html',
        entregas_hoje=entregas_hoje,
        entregues_hoje=entregues_hoje,
        ganhos_hoje=ganhos_hoje,
        turno_ativo=turno_ativo,
        pendentes=pendentes,
        hoje=hoje
    )

# ─── GPS / DISPONIBILIDADE ────────────────────────────────────────────────────

@app.route('/toggle_disponivel', methods=['POST'])
@login_required
def toggle_disponivel():
    mb = current_user
    mb.disponivel = not mb.disponivel
    if mb.disponivel:
        turno = Turno(motoboy_id=mb.id)
        db.session.add(turno)
    else:
        turno = Turno.query.filter_by(motoboy_id=mb.id, ativo=True).first()
        if turno:
            turno.fim = datetime.utcnow()
            turno.ativo = False
    db.session.commit()
    return jsonify({'disponivel': mb.disponivel, 'ok': True})

@app.route('/atualizar_gps', methods=['POST'])
@login_required
def atualizar_gps():
    data = request.get_json()
    mb = current_user
    mb.lat_atual   = data.get('lat')
    mb.lng_atual   = data.get('lng')
    mb.ultima_loc  = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True})

# ─── ENTREGAS ─────────────────────────────────────────────────────────────────

@app.route('/entregas')
@login_required
def listar_entregas():
    page   = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    q      = Entrega.query.filter_by(motoboy_id=current_user.id)
    if status:
        q = q.filter_by(status=status)
    entregas = q.order_by(Entrega.criado_em.desc()).paginate(page=page, per_page=20)
    return render_template('entregas.html', entregas=entregas, status=status)

@app.route('/entregas/<int:eid>/aceitar', methods=['POST'])
@login_required
def aceitar_entrega(eid):
    e = Entrega.query.get_or_404(eid)
    if e.motoboy_id != current_user.id: return jsonify({'erro':'não autorizado'}), 403
    e.status   = 'aceita'
    e.aceito_em = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'status': e.status})

@app.route('/entregas/<int:eid>/retirar', methods=['POST'])
@login_required
def retirar_entrega(eid):
    e = Entrega.query.get_or_404(eid)
    if e.motoboy_id != current_user.id: return jsonify({'erro':'não autorizado'}), 403
    e.status      = 'retirada'
    e.retirado_em  = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'status': e.status})

@app.route('/entregas/<int:eid>/entregar', methods=['POST'])
@login_required
def entregar(eid):
    e = Entrega.query.get_or_404(eid)
    if e.motoboy_id != current_user.id: return jsonify({'erro':'não autorizado'}), 403
    e.status       = 'entregue'
    e.entregue_em   = datetime.utcnow()
    mb = current_user
    mb.saldo_dia   += e.valor_total_taxa
    mb.saldo_total += e.valor_total_taxa
    db.session.commit()
    return jsonify({'ok': True, 'status': e.status, 'ganho': e.valor_total_taxa})

@app.route('/entregas/<int:eid>/cancelar', methods=['POST'])
@login_required
def cancelar_entrega(eid):
    e = Entrega.query.get_or_404(eid)
    if e.motoboy_id != current_user.id: return jsonify({'erro':'não autorizado'}), 403
    e.status = 'cancelada'
    db.session.commit()
    return jsonify({'ok': True})

# ─── HISTÓRICO ────────────────────────────────────────────────────────────────

@app.route('/historico')
@login_required
def historico():
    dias = request.args.get('dias', 7, type=int)
    desde = datetime.utcnow() - timedelta(days=dias)
    entregas = Entrega.query.filter(
        Entrega.motoboy_id == current_user.id,
        Entrega.status == 'entregue',
        Entrega.entregue_em >= desde
    ).order_by(Entrega.entregue_em.desc()).all()
    total_ganho   = sum(e.valor_total_taxa for e in entregas)
    total_pedidos = sum(e.valor_pedido for e in entregas)
    return render_template('historico.html',
        entregas=entregas, total_ganho=total_ganho,
        total_pedidos=total_pedidos, dias=dias
    )

# ─── GANHOS ───────────────────────────────────────────────────────────────────

@app.route('/ganhos')
@login_required
def ganhos():
    hoje   = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes    = hoje.replace(day=1)

    def soma(desde):
        rs = Entrega.query.filter(
            Entrega.motoboy_id == current_user.id,
            Entrega.status == 'entregue',
            db.func.date(Entrega.entregue_em) >= desde
        ).all()
        return sum(e.valor_total_taxa for e in rs), len(rs)

    ganhos_dia,    qtd_dia    = soma(hoje)
    ganhos_semana, qtd_semana = soma(inicio_semana)
    ganhos_mes,    qtd_mes    = soma(inicio_mes)
    ganhos_total              = current_user.saldo_total

    ultimas = Entrega.query.filter(
        Entrega.motoboy_id == current_user.id,
        Entrega.status == 'entregue'
    ).order_by(Entrega.entregue_em.desc()).limit(10).all()

    return render_template('ganhos.html',
        ganhos_dia=ganhos_dia, qtd_dia=qtd_dia,
        ganhos_semana=ganhos_semana, qtd_semana=qtd_semana,
        ganhos_mes=ganhos_mes, qtd_mes=qtd_mes,
        ganhos_total=ganhos_total, ultimas=ultimas
    )

# ─── PERFIL ───────────────────────────────────────────────────────────────────

@app.route('/perfil', methods=['GET','POST'])
@login_required
def perfil():
    if request.method == 'POST':
        mb = current_user
        mb.nome         = request.form.get('nome', mb.nome)
        mb.telefone     = request.form.get('telefone', mb.telefone)
        mb.moto_placa   = request.form.get('moto_placa', mb.moto_placa)
        mb.moto_modelo  = request.form.get('moto_modelo', mb.moto_modelo)
        nova_senha = request.form.get('nova_senha')
        if nova_senha:
            mb.set_senha(nova_senha)
        db.session.commit()
        flash('Perfil atualizado!', 'success')
    return render_template('perfil.html')

# ─── API INTERNA (para PainelFrota) ──────────────────────────────────────────

@app.route('/api/motoboys_disponiveis')
def api_motoboys_disponiveis():
    mbs = Motoboy.query.filter_by(disponivel=True, ativo=True).all()
    return jsonify([{
        'id': mb.id, 'nome': mb.nome, 'lat': mb.lat_atual, 'lng': mb.lng_atual,
        'ultima_loc': mb.ultima_loc.isoformat() if mb.ultima_loc else None
    } for mb in mbs])

@app.route('/api/nova_entrega', methods=['POST'])
def api_nova_entrega():
    data = request.get_json()
    e = Entrega(
        motoboy_id       = data['motoboy_id'],
        restaurante_nome = data.get('restaurante_nome',''),
        cliente_nome     = data.get('cliente_nome',''),
        cliente_endereco = data.get('cliente_endereco',''),
        codigo_ifood     = data.get('codigo_ifood',''),
        origem           = data.get('origem','direto'),
        valor_pedido     = data.get('valor_pedido', 0),
        taxa_entrega     = data.get('taxa_entrega', 5.0),
        adicional_chuva  = data.get('adicional_chuva', 0),
        adicional_pico   = data.get('adicional_pico', 0),
        adicional_noturno= data.get('adicional_noturno', 0),
        valor_total_taxa = data.get('valor_total_taxa', 5.0),
        distancia_km     = data.get('distancia_km'),
        observacao       = data.get('observacao',''),
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True, 'id': e.id})

# ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────

def migrate_db():
    with app.app_context():
        db.create_all()
        if not Motoboy.query.filter_by(username='demo').first():
            mb = Motoboy(nome='Motoboy Demo', username='demo')
            mb.set_senha('demo123')
            db.session.add(mb)
            db.session.commit()

if __name__ == '__main__':
    migrate_db()
    app.run(port=5003, debug=True)
