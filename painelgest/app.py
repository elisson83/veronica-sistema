import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'painelgest2024')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///painelgest.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

PLANOS = {
    'basico': {
        'nome': 'Básico',
        'preco': 99.90,
        'cor': 'info',
        'icone': 'fa-seedling',
        'descricao': 'Ideal para pequenos negócios',
        'recursos': ['Até 5 clientes iFood', '2 perfis Instagram', 'Suporte por e-mail'],
    },
    'pro': {
        'nome': 'Pro',
        'preco': 199.90,
        'cor': 'primary',
        'icone': 'fa-rocket',
        'descricao': 'Para negócios em crescimento',
        'recursos': ['Até 20 clientes iFood', '10 perfis Instagram', 'Suporte prioritário', 'Relatórios avançados'],
    },
    'premium': {
        'nome': 'Premium',
        'preco': 399.90,
        'cor': 'warning',
        'icone': 'fa-crown',
        'descricao': 'Para grandes operações',
        'recursos': ['Clientes ilimitados', 'Instagram ilimitado', 'Suporte 24/7', 'API dedicada'],
    },
}

# ── Models ────────────────────────────────────────────────────────────────────

class Administrador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password)


class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    login = db.Column(db.String(80), unique=True, nullable=False)
    senha = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(10), nullable=False, default='ativo')
    plano = db.Column(db.String(20), nullable=False, default='basico')
    telefone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    data_vencimento = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, nome, login, senha, status, plano='basico',
                 telefone=None, email=None, data_vencimento=None):
        self.nome = nome
        self.login = login
        self.senha = senha
        self.status = status
        self.plano = plano
        self.telefone = telefone
        self.email = email
        self.data_vencimento = data_vencimento

    @property
    def info_plano(self):
        return PLANOS.get(self.plano, PLANOS['basico'])

    @property
    def vencido(self):
        if self.data_vencimento:
            return self.data_vencimento.date() < date.today()
        return False

    @property
    def dias_para_vencer(self):
        if self.data_vencimento:
            return (self.data_vencimento.date() - date.today()).days
        return None


class PerfilInstagram(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    login = db.Column(db.String(80), nullable=False)
    senha = db.Column(db.String(120), nullable=False)
    postagem = db.Column(db.Text, nullable=False)
    data_postagem = db.Column(db.DateTime, nullable=False)

    def __init__(self, nome, login, senha, postagem, data_postagem):
        self.nome = nome
        self.login = login
        self.senha = senha
        self.postagem = postagem
        self.data_postagem = data_postagem


class Vencimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(80), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(10), nullable=False)

    def __init__(self, descricao, valor, data_vencimento, status):
        self.descricao = descricao
        self.valor = valor
        self.data_vencimento = data_vencimento
        self.status = status


class Cobranca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    cliente = db.relationship('Cliente', backref='cobrancas')
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='pendente')
    mp_preference_id = db.Column(db.String(200), nullable=True)
    mp_payment_id = db.Column(db.String(200), nullable=True)
    mp_link = db.Column(db.String(500), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    pago_em = db.Column(db.DateTime, nullable=True)

    def __init__(self, cliente_id, valor, descricao=None):
        self.cliente_id = cliente_id
        self.valor = valor
        self.descricao = descricao


class Restaurante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)
    data_vencimento = db.Column(db.DateTime, nullable=True)
    link_pagamento = db.Column(db.String(200), nullable=True)
    chave_pix = db.Column(db.String(200), nullable=True)

    def __init__(self, nome, username, password, cliente_id=None):
        self.nome = nome
        self.username = username
        self.password = generate_password_hash(password)
        self.cliente_id = cliente_id


class PostAgendado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    perfil_id = db.Column(db.Integer, db.ForeignKey('perfil_instagram.id'))
    imagem_path = db.Column(db.String(200), nullable=True)
    legenda = db.Column(db.Text, nullable=True)
    data_postagem = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='agendado')
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_mp_sdk():
    token = os.environ.get('MERCADOPAGO_ACCESS_TOKEN')
    if not token:
        return None
    try:
        import mercadopago
        return mercadopago.SDK(token)
    except ImportError:
        return None


def requer_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'administrador' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def formatar_valor(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.context_processor
def inject_globals():
    return {
        'admin_user': session.get('administrador'),
        'PLANOS': PLANOS,
        'mp_ativo': bool(os.environ.get('MERCADOPAGO_ACCESS_TOKEN')),
    }


# ── Rotas — Autenticação ──────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'administrador' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'administrador' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = Administrador.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password, password):
            session['administrador'] = username
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('administrador', None)
    return redirect(url_for('login'))


# ── Rotas — Dashboard ─────────────────────────────────────────────────────────

@app.route('/dashboard')
@requer_login
def dashboard():
    hoje = date.today()
    em7dias = hoje + timedelta(days=7)

    clientes_total = Cliente.query.count()
    clientes_ativos = Cliente.query.filter_by(status='ativo').count()
    instagram_total = PerfilInstagram.query.count()
    vencimentos_proximos = Vencimento.query.filter(
        Vencimento.data_vencimento <= datetime.combine(em7dias, datetime.max.time()),
        Vencimento.status != 'pago'
    ).count()
    receita = sum(v.valor for v in Vencimento.query.filter_by(status='pago').all())
    cobrancas_pendentes = Cobranca.query.filter_by(status='pendente').count()

    clientes_vencendo = Cliente.query.filter(
        Cliente.data_vencimento <= datetime.combine(em7dias, datetime.max.time()),
        Cliente.data_vencimento >= datetime.combine(hoje, datetime.min.time()),
        Cliente.status == 'ativo'
    ).order_by(Cliente.data_vencimento).limit(5).all()

    ultimos_clientes = Cliente.query.order_by(Cliente.id.desc()).limit(5).all()

    return render_template('dashboard.html',
        clientes_total=clientes_total,
        clientes_ativos=clientes_ativos,
        instagram_total=instagram_total,
        vencimentos_proximos=vencimentos_proximos,
        receita=formatar_valor(receita),
        cobrancas_pendentes=cobrancas_pendentes,
        clientes_vencendo=clientes_vencendo,
        ultimos_clientes=ultimos_clientes,
    )


# ── Rotas — Clientes ──────────────────────────────────────────────────────────

@app.route('/clientes')
@requer_login
def clientes():
    lista = Cliente.query.order_by(Cliente.nome).all()
    return render_template('clientes.html', clientes=lista)


@app.route('/cadastrar_cliente', methods=['GET', 'POST'])
@requer_login
def cadastrar_cliente():
    if request.method == 'POST':
        data_venc = None
        if request.form.get('data_vencimento'):
            data_venc = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')
        cliente = Cliente(
            nome=request.form['nome'],
            login=request.form['login'],
            senha=request.form['senha'],
            status=request.form['status'],
            plano=request.form.get('plano', 'basico'),
            telefone=request.form.get('telefone') or None,
            email=request.form.get('email') or None,
            data_vencimento=data_venc,
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente cadastrado com sucesso!', 'success')
        return redirect(url_for('clientes'))
    return render_template('cadastrar_cliente.html')


@app.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
@requer_login
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    if request.method == 'POST':
        cliente.nome = request.form['nome']
        cliente.login = request.form['login']
        if request.form.get('senha'):
            cliente.senha = request.form['senha']
        cliente.status = request.form['status']
        cliente.plano = request.form.get('plano', 'basico')
        cliente.telefone = request.form.get('telefone') or None
        cliente.email = request.form.get('email') or None
        if request.form.get('data_vencimento'):
            cliente.data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')
        else:
            cliente.data_vencimento = None
        db.session.commit()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('clientes'))
    return render_template('editar_cliente.html', cliente=cliente)


@app.route('/excluir_cliente/<int:id>')
@requer_login
def excluir_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente excluído.', 'success')
    return redirect(url_for('clientes'))


# ── Rotas — Perfis Instagram ──────────────────────────────────────────────────

@app.route('/perfis_instagram')
@requer_login
def perfis_instagram():
    perfis = PerfilInstagram.query.all()
    return render_template('perfis_instagram.html', perfis=perfis)


@app.route('/cadastrar_perfil_instagram', methods=['GET', 'POST'])
@requer_login
def cadastrar_perfil_instagram():
    if request.method == 'POST':
        perfil = PerfilInstagram(
            nome=request.form['nome'],
            login=request.form['login'],
            senha=request.form['senha'],
            postagem=request.form['postagem'],
            data_postagem=datetime.strptime(request.form['data_postagem'], '%Y-%m-%dT%H:%M'),
        )
        db.session.add(perfil)
        db.session.commit()
        flash('Perfil cadastrado com sucesso!', 'success')
        return redirect(url_for('perfis_instagram'))
    return render_template('cadastrar_perfil_instagram.html')


@app.route('/editar_perfil_instagram/<int:id>', methods=['GET', 'POST'])
@requer_login
def editar_perfil_instagram(id):
    perfil = PerfilInstagram.query.get_or_404(id)
    if request.method == 'POST':
        perfil.nome = request.form['nome']
        perfil.login = request.form['login']
        if request.form.get('senha'):
            perfil.senha = request.form['senha']
        perfil.postagem = request.form['postagem']
        perfil.data_postagem = datetime.strptime(request.form['data_postagem'], '%Y-%m-%dT%H:%M')
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('perfis_instagram'))
    return render_template('editar_perfil_instagram.html', perfil=perfil)


@app.route('/excluir_perfil_instagram/<int:id>')
@requer_login
def excluir_perfil_instagram(id):
    perfil = PerfilInstagram.query.get_or_404(id)
    db.session.delete(perfil)
    db.session.commit()
    flash('Perfil excluído.', 'success')
    return redirect(url_for('perfis_instagram'))


# ── Rotas — Vencimentos ───────────────────────────────────────────────────────

@app.route('/vencimentos')
@requer_login
def vencimentos():
    lista = Vencimento.query.order_by(Vencimento.data_vencimento).all()
    return render_template('vencimentos.html', vencimentos=lista)


@app.route('/cadastrar_vencimento', methods=['GET', 'POST'])
@requer_login
def cadastrar_vencimento():
    if request.method == 'POST':
        vencimento = Vencimento(
            descricao=request.form['descricao'],
            valor=float(request.form['valor']),
            data_vencimento=datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d'),
            status=request.form['status'],
        )
        db.session.add(vencimento)
        db.session.commit()
        flash('Vencimento cadastrado!', 'success')
        return redirect(url_for('vencimentos'))
    return render_template('cadastrar_vencimento.html')


@app.route('/editar_vencimento/<int:id>', methods=['GET', 'POST'])
@requer_login
def editar_vencimento(id):
    vencimento = Vencimento.query.get_or_404(id)
    if request.method == 'POST':
        vencimento.descricao = request.form['descricao']
        vencimento.valor = float(request.form['valor'])
        vencimento.data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')
        vencimento.status = request.form['status']
        db.session.commit()
        flash('Vencimento atualizado!', 'success')
        return redirect(url_for('vencimentos'))
    return render_template('editar_vencimento.html', vencimento=vencimento)


@app.route('/excluir_vencimento/<int:id>')
@requer_login
def excluir_vencimento(id):
    vencimento = Vencimento.query.get_or_404(id)
    db.session.delete(vencimento)
    db.session.commit()
    flash('Vencimento excluído.', 'success')
    return redirect(url_for('vencimentos'))


# ── Rotas — Planos ────────────────────────────────────────────────────────────

@app.route('/planos')
@requer_login
def planos():
    stats = {key: Cliente.query.filter_by(plano=key).count() for key in PLANOS}
    receita_planos = {}
    for key, info in PLANOS.items():
        qtd = stats[key]
        receita_planos[key] = formatar_valor(qtd * info['preco'])
    return render_template('planos.html', stats=stats, receita_planos=receita_planos)


# ── Rotas — Cobranças / Mercado Pago ─────────────────────────────────────────

@app.route('/cobrancas')
@requer_login
def cobrancas():
    lista = Cobranca.query.order_by(Cobranca.criado_em.desc()).all()
    total_pago = sum(c.valor for c in lista if c.status == 'pago')
    total_pendente = sum(c.valor for c in lista if c.status == 'pendente')
    return render_template('cobrancas.html', cobrancas=lista,
        total_pago=formatar_valor(total_pago),
        total_pendente=formatar_valor(total_pendente))


@app.route('/gerar_cobranca/<int:cliente_id>', methods=['POST'])
@requer_login
def gerar_cobranca(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    valor = float(request.form.get('valor', cliente.info_plano['preco']))
    descricao = request.form.get('descricao') or f"Plano {cliente.info_plano['nome']} — {cliente.nome}"

    cobranca = Cobranca(cliente_id=cliente.id, valor=valor, descricao=descricao)
    sdk = get_mp_sdk()

    if sdk:
        base_url = request.host_url.rstrip('/')
        preference_data = {
            "items": [{"title": descricao, "quantity": 1, "unit_price": valor, "currency_id": "BRL"}],
            "payer": {"name": cliente.nome, "email": cliente.email or "cliente@painelgest.com"},
            "back_urls": {
                "success": f"{base_url}/mp/sucesso",
                "failure": f"{base_url}/mp/falha",
                "pending": f"{base_url}/mp/pendente",
            },
            "auto_return": "approved",
            "notification_url": f"{base_url}/mp/webhook",
            "external_reference": str(cliente.id),
            "statement_descriptor": "PainelGest",
        }
        result = sdk.preference().create(preference_data)
        if result["status"] == 201:
            pref = result["response"]
            cobranca.mp_preference_id = pref["id"]
            cobranca.mp_link = pref.get("init_point")

    db.session.add(cobranca)
    db.session.commit()

    if cobranca.mp_link:
        flash(f'Link de pagamento gerado com sucesso!', 'success')
    else:
        flash('Cobrança registrada. Configure MERCADOPAGO_ACCESS_TOKEN no .env para gerar links automáticos.', 'warning')
    return redirect(url_for('cobrancas'))


@app.route('/cancelar_cobranca/<int:id>')
@requer_login
def cancelar_cobranca(id):
    cobranca = Cobranca.query.get_or_404(id)
    cobranca.status = 'cancelado'
    db.session.commit()
    flash('Cobrança cancelada.', 'success')
    return redirect(url_for('cobrancas'))


@app.route('/mp/webhook', methods=['POST'])
def mp_webhook():
    data = request.json or {}
    if data.get('type') == 'payment':
        payment_id = data.get('data', {}).get('id')
        sdk = get_mp_sdk()
        if sdk and payment_id:
            result = sdk.payment().get(payment_id)
            if result["status"] == 200:
                payment = result["response"]
                cobranca = Cobranca.query.filter_by(
                    mp_preference_id=payment.get('preference_id')
                ).first()
                if cobranca and payment.get('status') == 'approved':
                    cobranca.status = 'pago'
                    cobranca.mp_payment_id = str(payment_id)
                    cobranca.pago_em = datetime.utcnow()
                    db.session.commit()
    return jsonify({'status': 'ok'}), 200


@app.route('/mp/sucesso')
def mp_sucesso():
    flash('Pagamento aprovado! Obrigado.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/mp/falha')
def mp_falha():
    flash('Pagamento não aprovado. Tente novamente.', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/mp/pendente')
def mp_pendente():
    flash('Pagamento pendente. Aguardando confirmação.', 'warning')
    return redirect(url_for('dashboard'))


# ── Rotas — Restaurantes ──────────────────────────────────────────────────────

@app.route('/restaurante/login', methods=['GET', 'POST'])
def restaurante_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        restaurante = Restaurante.query.filter_by(username=username).first()
        if restaurante and check_password_hash(restaurante.password, password):
            session['restaurante'] = username
            session['restaurante_id'] = restaurante.id
            return redirect(url_for('restaurante_dashboard'))
        flash('Login ou senha inválidos.', 'danger')
    return render_template('login_restaurante.html')


@app.route('/restaurante/dashboard')
def restaurante_dashboard():
    if 'restaurante' not in session:
        return redirect(url_for('restaurante_login'))
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    posts = PostAgendado.query.filter_by(status='agendado').all()
    return render_template('dashboard_restaurante.html', restaurante=restaurante, posts=posts)


@app.route('/restaurante/logout')
def restaurante_logout():
    session.pop('restaurante', None)
    session.pop('restaurante_id', None)
    return redirect(url_for('restaurante_login'))


@app.route('/restaurante/upload', methods=['POST'])
def restaurante_upload():
    if 'restaurante' not in session:
        return redirect(url_for('restaurante_login'))
    if 'imagem' not in request.files:
        flash('Nenhuma imagem enviada!', 'danger')
        return redirect(url_for('restaurante_dashboard'))
    from pathlib import Path
    imagem = request.files['imagem']
    upload_dir = Path('static/uploads')
    upload_dir.mkdir(parents=True, exist_ok=True)
    imagem.save(str(upload_dir / imagem.filename))
    flash('Imagem enviada com sucesso!', 'success')
    return redirect(url_for('restaurante_dashboard'))


@app.route('/admin/restaurantes')
@requer_login
def admin_restaurantes():
    restaurantes = Restaurante.query.all()
    return render_template('restaurantes.html', restaurantes=restaurantes)


@app.route('/admin/restaurantes/novo', methods=['GET', 'POST'])
@requer_login
def novo_restaurante():
    if request.method == 'POST':
        restaurante = Restaurante(
            nome=request.form['nome'],
            username=request.form['username'],
            password=request.form['password'],
        )
        db.session.add(restaurante)
        db.session.commit()
        flash('Restaurante criado com sucesso!', 'success')
        return redirect(url_for('admin_restaurantes'))
    return render_template('novo_restaurante.html')


# ── Inicialização ─────────────────────────────────────────────────────────────

def migrate_db():
    """Adiciona colunas novas ao banco existente sem perder dados."""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'painelgest.db')
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(cliente)")
    cols = {row[1] for row in cursor.fetchall()}

    novas_colunas = [
        ("plano",           "ALTER TABLE cliente ADD COLUMN plano VARCHAR(20) DEFAULT 'basico'"),
        ("telefone",        "ALTER TABLE cliente ADD COLUMN telefone VARCHAR(20)"),
        ("email",           "ALTER TABLE cliente ADD COLUMN email VARCHAR(120)"),
        ("data_vencimento", "ALTER TABLE cliente ADD COLUMN data_vencimento DATETIME"),
        ("criado_em",       "ALTER TABLE cliente ADD COLUMN criado_em DATETIME"),
    ]
    for col, sql in novas_colunas:
        if col not in cols:
            cursor.execute(sql)

    conn.commit()
    conn.close()


if __name__ == '__main__':
    with app.app_context():
        migrate_db()
        db.create_all()
        if not Administrador.query.first():
            db.session.add(Administrador('admin', 'admin123'))
            db.session.commit()
            print("Admin padrão criado → usuário: admin | senha: admin123")
    app.run(debug=True, port=5002)
