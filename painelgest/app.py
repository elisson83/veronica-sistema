import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'painelgest2024super')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///painelgest.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

PLANOS = {
    'basico': {
        'nome': 'Básico', 'preco': 99.90, 'cor': 'info', 'icone': 'fa-seedling',
        'descricao': 'Ideal para pequenos negócios',
        'recursos': ['Até 5 clientes iFood', '2 perfis de redes sociais', 'Suporte por e-mail'],
    },
    'pro': {
        'nome': 'Pro', 'preco': 199.90, 'cor': 'primary', 'icone': 'fa-rocket',
        'descricao': 'Para negócios em crescimento',
        'recursos': ['Até 20 clientes iFood', '10 perfis de redes sociais', 'Suporte prioritário', 'Cardápio digital'],
    },
    'premium': {
        'nome': 'Premium', 'preco': 399.90, 'cor': 'warning', 'icone': 'fa-crown',
        'descricao': 'Para grandes operações',
        'recursos': ['Clientes ilimitados', 'Redes sociais ilimitadas', 'Suporte 24/7', 'API dedicada', 'Cardápio avançado'],
    },
}

REDES_SOCIAIS = {
    'instagram':  {'nome': 'Instagram',         'icone': 'fab fa-instagram',    'cor': '#E1306C'},
    'facebook':   {'nome': 'Facebook',           'icone': 'fab fa-facebook',     'cor': '#1877F2'},
    'tiktok':     {'nome': 'TikTok',             'icone': 'fab fa-tiktok',       'cor': '#010101'},
    'youtube':    {'nome': 'YouTube',            'icone': 'fab fa-youtube',      'cor': '#FF0000'},
    'whatsapp':   {'nome': 'WhatsApp Business',  'icone': 'fab fa-whatsapp',     'cor': '#25D366'},
    'pinterest':  {'nome': 'Pinterest',          'icone': 'fab fa-pinterest',    'cor': '#E60023'},
}

# ══════════════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════════════

class SuperAdmin(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80), unique=True, nullable=False)
    password     = db.Column(db.String(120), nullable=False)
    email        = db.Column(db.String(120), nullable=True)
    criado_em    = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, username, password, email=None):
        self.username = username
        self.password = generate_password_hash(password)
        self.email = email


class Administrador(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    username        = db.Column(db.String(80), unique=True, nullable=False)
    password        = db.Column(db.String(120), nullable=False)
    email           = db.Column(db.String(120), nullable=True)
    nome_empresa    = db.Column(db.String(120), nullable=True)
    plano           = db.Column(db.String(20), default='basico')
    status          = db.Column(db.String(15), default='ativo')   # ativo | bloqueado | cancelado
    data_vencimento = db.Column(db.DateTime, nullable=True)
    criado_em       = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, username, password, email=None, nome_empresa=None, plano='basico'):
        self.username     = username
        self.password     = generate_password_hash(password)
        self.email        = email
        self.nome_empresa = nome_empresa
        self.plano        = plano

    @property
    def info_plano(self):
        return PLANOS.get(self.plano, PLANOS['basico'])

    @property
    def bloqueado(self):
        return self.status == 'bloqueado'

    @property
    def mrr(self):
        return self.info_plano['preco']

    @property
    def vencido(self):
        if self.data_vencimento:
            return self.data_vencimento.date() < date.today()
        return False


class Cliente(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    nome            = db.Column(db.String(80),  nullable=False)
    login           = db.Column(db.String(80),  unique=True, nullable=False)
    senha           = db.Column(db.String(120), nullable=False)
    status          = db.Column(db.String(10),  nullable=False, default='ativo')
    plano           = db.Column(db.String(20),  nullable=False, default='basico')
    telefone        = db.Column(db.String(20),  nullable=True)
    email           = db.Column(db.String(120), nullable=True)
    data_vencimento = db.Column(db.DateTime,    nullable=True)
    criado_em       = db.Column(db.DateTime,    default=datetime.utcnow)

    def __init__(self, nome, login, senha, status, plano='basico',
                 telefone=None, email=None, data_vencimento=None):
        self.nome = nome; self.login = login; self.senha = senha
        self.status = status; self.plano = plano
        self.telefone = telefone; self.email = email
        self.data_vencimento = data_vencimento

    @property
    def info_plano(self):
        return PLANOS.get(self.plano, PLANOS['basico'])

    @property
    def vencido(self):
        return bool(self.data_vencimento and self.data_vencimento.date() < date.today())

    @property
    def dias_para_vencer(self):
        if self.data_vencimento:
            return (self.data_vencimento.date() - date.today()).days
        return None


class PerfilRedeSocial(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(80),  nullable=False)
    rede          = db.Column(db.String(20),  nullable=False, default='instagram')
    login         = db.Column(db.String(120), nullable=False)
    senha         = db.Column(db.String(120), nullable=False)
    postagem      = db.Column(db.Text,        nullable=True)
    data_postagem = db.Column(db.DateTime,    nullable=True)
    status        = db.Column(db.String(20),  default='ativo')
    criado_em     = db.Column(db.DateTime,    default=datetime.utcnow)

    def __init__(self, nome, rede, login, senha, postagem=None, data_postagem=None):
        self.nome = nome; self.rede = rede; self.login = login
        self.senha = senha; self.postagem = postagem
        self.data_postagem = data_postagem

    @property
    def info_rede(self):
        return REDES_SOCIAIS.get(self.rede, REDES_SOCIAIS['instagram'])


# ─── Manter retrocompatibilidade ───────────────────────────────────────────
class PerfilInstagram(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(80),  nullable=False)
    login         = db.Column(db.String(80),  nullable=False)
    senha         = db.Column(db.String(120), nullable=False)
    postagem      = db.Column(db.Text,        nullable=False)
    data_postagem = db.Column(db.DateTime,    nullable=False)

    def __init__(self, nome, login, senha, postagem, data_postagem):
        self.nome = nome; self.login = login; self.senha = senha
        self.postagem = postagem; self.data_postagem = data_postagem


class Vencimento(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    descricao       = db.Column(db.String(80), nullable=False)
    valor           = db.Column(db.Float,      nullable=False)
    data_vencimento = db.Column(db.DateTime,   nullable=False)
    status          = db.Column(db.String(10), nullable=False)

    def __init__(self, descricao, valor, data_vencimento, status):
        self.descricao = descricao; self.valor = valor
        self.data_vencimento = data_vencimento; self.status = status


class Cobranca(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    cliente_id       = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    cliente          = db.relationship('Cliente', backref='cobrancas')
    valor            = db.Column(db.Float,      nullable=False)
    descricao        = db.Column(db.String(200), nullable=True)
    status           = db.Column(db.String(20),  default='pendente')
    mp_preference_id = db.Column(db.String(200), nullable=True)
    mp_payment_id    = db.Column(db.String(200), nullable=True)
    mp_link          = db.Column(db.String(500), nullable=True)
    criado_em        = db.Column(db.DateTime,    default=datetime.utcnow)
    pago_em          = db.Column(db.DateTime,    nullable=True)

    def __init__(self, cliente_id, valor, descricao=None):
        self.cliente_id = cliente_id; self.valor = valor; self.descricao = descricao


class Restaurante(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    nome            = db.Column(db.String(80),  nullable=False)
    username        = db.Column(db.String(80),  unique=True, nullable=False)
    password        = db.Column(db.String(120), nullable=False)
    cliente_id      = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)
    data_vencimento = db.Column(db.DateTime,    nullable=True)
    link_pagamento  = db.Column(db.String(200), nullable=True)
    chave_pix       = db.Column(db.String(200), nullable=True)
    telefone        = db.Column(db.String(30),  nullable=True)
    endereco        = db.Column(db.String(200), nullable=True)
    descricao       = db.Column(db.Text,        nullable=True)
    cor_primaria    = db.Column(db.String(10),  default='#6366f1')

    def __init__(self, nome, username, password, cliente_id=None):
        self.nome = nome; self.username = username
        self.password = generate_password_hash(password)
        self.cliente_id = cliente_id


class Categoria(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    restaurante_id= db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    restaurante   = db.relationship('Restaurante', backref='categorias')
    nome          = db.Column(db.String(80),  nullable=False)
    descricao     = db.Column(db.String(200), nullable=True)
    ordem         = db.Column(db.Integer,     default=0)
    ativo         = db.Column(db.Boolean,     default=True)
    icone         = db.Column(db.String(50),  default='fa-utensils')

    def __init__(self, restaurante_id, nome, descricao=None, icone='fa-utensils'):
        self.restaurante_id = restaurante_id; self.nome = nome
        self.descricao = descricao; self.icone = icone


class ItemCardapio(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    categoria    = db.relationship('Categoria', backref='itens')
    nome         = db.Column(db.String(120), nullable=False)
    descricao    = db.Column(db.Text,        nullable=True)
    preco        = db.Column(db.Float,       nullable=False)
    preco_promo  = db.Column(db.Float,       nullable=True)
    disponivel   = db.Column(db.Boolean,     default=True)
    destaque     = db.Column(db.Boolean,     default=False)
    imagem_path  = db.Column(db.String(300), nullable=True)
    criado_em    = db.Column(db.DateTime,    default=datetime.utcnow)

    def __init__(self, categoria_id, nome, preco, descricao=None, preco_promo=None):
        self.categoria_id = categoria_id; self.nome = nome
        self.preco = preco; self.descricao = descricao; self.preco_promo = preco_promo

    @property
    def preco_fmt(self):
        return f"R$ {self.preco:.2f}".replace('.', ',')

    @property
    def preco_promo_fmt(self):
        if self.preco_promo:
            return f"R$ {self.preco_promo:.2f}".replace('.', ',')
        return None


class PostAgendado(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    perfil_id     = db.Column(db.Integer, db.ForeignKey('perfil_rede_social.id'))
    perfil        = db.relationship('PerfilRedeSocial', backref='posts_agendados')
    imagem_path   = db.Column(db.String(500), nullable=True)
    legenda       = db.Column(db.Text,        nullable=True)
    data_postagem = db.Column(db.DateTime,    nullable=False)
    status        = db.Column(db.String(20),  default='agendado')  # agendado|publicado|erro|cancelado
    erro          = db.Column(db.Text,        nullable=True)
    criado_em     = db.Column(db.DateTime,    default=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_mp_sdk():
    token = os.environ.get('MERCADOPAGO_ACCESS_TOKEN')
    if not token:
        return None
    try:
        import mercadopago
        return mercadopago.SDK(token)
    except ImportError:
        return None


def formatar_valor(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_mrr():
    """Calcula MRR da plataforma somando planos ativos de todos os gestores."""
    gestores = Administrador.query.filter_by(status='ativo').all()
    return sum(g.mrr for g in gestores)


def postar_instagram(perfil, legenda, imagem_path=None):
    """Faz upload de um post no Instagram usando instagrapi."""
    if not imagem_path or not os.path.exists(imagem_path):
        return False, 'Imagem não encontrada. Posts no Instagram exigem uma imagem.'
    try:
        from instagrapi import Client
        cl = Client()
        cl.login(perfil.login, perfil.senha)
        cl.photo_upload(imagem_path, legenda or '')
        cl.logout()
        return True, None
    except Exception as e:
        return False, str(e)


def processar_posts_agendados():
    """Scheduler: executa a cada 5 minutos e publica posts com data vencida."""
    with app.app_context():
        agora = datetime.utcnow()
        posts = PostAgendado.query.filter(
            PostAgendado.status == 'agendado',
            PostAgendado.data_postagem <= agora
        ).all()
        for post in posts:
            perfil = PerfilRedeSocial.query.get(post.perfil_id)
            if not perfil:
                post.status = 'erro'
                post.erro = 'Perfil não encontrado'
                db.session.commit()
                continue
            if perfil.rede != 'instagram':
                post.status = 'erro'
                post.erro = f'Postagem automática ainda não suportada para {perfil.rede}'
                db.session.commit()
                continue
            ok, erro = postar_instagram(perfil, post.legenda, post.imagem_path)
            post.status = 'publicado' if ok else 'erro'
            post.erro = erro
            db.session.commit()


def requer_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'administrador' not in session:
            return redirect(url_for('login'))
        admin = Administrador.query.filter_by(username=session['administrador']).first()
        if admin and admin.bloqueado:
            session.pop('administrador', None)
            flash('Sua conta foi bloqueada. Entre em contato com o suporte.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def requer_super(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'super_admin' not in session:
            return redirect(url_for('super_login'))
        return f(*args, **kwargs)
    return decorated


def requer_restaurante(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'restaurante' not in session:
            return redirect(url_for('restaurante_login'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_globals():
    return {
        'admin_user': session.get('administrador'),
        'PLANOS': PLANOS,
        'REDES_SOCIAIS': REDES_SOCIAIS,
        'mp_ativo': bool(os.environ.get('MERCADOPAGO_ACCESS_TOKEN')),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — AUTENTICAÇÃO ADMIN
# ══════════════════════════════════════════════════════════════════════════════

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
            if admin.bloqueado:
                flash('Conta bloqueada. Entre em contato com o suporte.', 'danger')
                return render_template('login.html')
            session['administrador'] = username
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('administrador', None)
    return redirect(url_for('login'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — SUPER ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/super/login', methods=['GET', 'POST'])
def super_login():
    if 'super_admin' in session:
        return redirect(url_for('super_dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        sa = SuperAdmin.query.filter_by(username=username).first()
        if sa and check_password_hash(sa.password, password):
            session['super_admin'] = username
            return redirect(url_for('super_dashboard'))
        flash('Credenciais inválidas.', 'danger')
    return render_template('super_login.html')


@app.route('/super/logout')
def super_logout():
    session.pop('super_admin', None)
    return redirect(url_for('super_login'))


@app.route('/super/dashboard')
@requer_super
def super_dashboard():
    hoje = date.today()
    em7dias = hoje + timedelta(days=7)

    gestores       = Administrador.query.all()
    gestores_ativos   = [g for g in gestores if g.status == 'ativo']
    gestores_bloqueados = [g for g in gestores if g.status == 'bloqueado']
    gestores_vencendo = [g for g in gestores_ativos
                         if g.data_vencimento and g.data_vencimento.date() <= em7dias]

    mrr_total = calcular_mrr()

    # Distribuição por plano
    dist_planos = {}
    for key in PLANOS:
        dist_planos[key] = Administrador.query.filter_by(plano=key, status='ativo').count()

    # Receita por plano
    receita_planos = {k: v * PLANOS[k]['preco'] for k, v in dist_planos.items()}

    total_clientes  = Cliente.query.count()
    total_restaurantes = Restaurante.query.count()
    cobrancas_pendentes = Cobranca.query.filter_by(status='pendente').count()

    return render_template('super_dashboard.html',
        gestores=gestores, gestores_ativos=gestores_ativos,
        gestores_bloqueados=gestores_bloqueados,
        gestores_vencendo=gestores_vencendo,
        mrr_total=formatar_valor(mrr_total),
        mrr_raw=mrr_total,
        dist_planos=dist_planos,
        receita_planos={k: formatar_valor(v) for k, v in receita_planos.items()},
        total_clientes=total_clientes,
        total_restaurantes=total_restaurantes,
        cobrancas_pendentes=cobrancas_pendentes,
    )


@app.route('/super/gestores')
@requer_super
def super_gestores():
    gestores = Administrador.query.order_by(Administrador.criado_em.desc()).all()
    return render_template('super_gestores.html', gestores=gestores)


@app.route('/super/gestores/novo', methods=['GET', 'POST'])
@requer_super
def super_novo_gestor():
    if request.method == 'POST':
        data_venc = None
        if request.form.get('data_vencimento'):
            data_venc = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')
        gestor = Administrador(
            username    = request.form['username'],
            password    = request.form['password'],
            email       = request.form.get('email') or None,
            nome_empresa= request.form.get('nome_empresa') or None,
            plano       = request.form.get('plano', 'basico'),
        )
        gestor.data_vencimento = data_venc
        db.session.add(gestor)
        try:
            db.session.commit()
            flash('Gestor criado com sucesso!', 'success')
            return redirect(url_for('super_gestores'))
        except Exception:
            db.session.rollback()
            flash('Usuário já existe. Escolha outro username.', 'danger')
    return render_template('super_novo_gestor.html')


@app.route('/super/gestores/<int:id>/bloquear')
@requer_super
def super_bloquear_gestor(id):
    gestor = Administrador.query.get_or_404(id)
    gestor.status = 'bloqueado'
    db.session.commit()
    flash(f'Gestor "{gestor.username}" bloqueado.', 'warning')
    return redirect(url_for('super_gestores'))


@app.route('/super/gestores/<int:id>/desbloquear')
@requer_super
def super_desbloquear_gestor(id):
    gestor = Administrador.query.get_or_404(id)
    gestor.status = 'ativo'
    db.session.commit()
    flash(f'Gestor "{gestor.username}" desbloqueado.', 'success')
    return redirect(url_for('super_gestores'))


@app.route('/super/gestores/<int:id>/excluir')
@requer_super
def super_excluir_gestor(id):
    gestor = Administrador.query.get_or_404(id)
    db.session.delete(gestor)
    db.session.commit()
    flash(f'Gestor excluído.', 'success')
    return redirect(url_for('super_gestores'))


@app.route('/super/gestores/<int:id>/editar', methods=['GET', 'POST'])
@requer_super
def super_editar_gestor(id):
    gestor = Administrador.query.get_or_404(id)
    if request.method == 'POST':
        gestor.email        = request.form.get('email') or None
        gestor.nome_empresa = request.form.get('nome_empresa') or None
        gestor.plano        = request.form.get('plano', 'basico')
        gestor.status       = request.form.get('status', 'ativo')
        if request.form.get('password'):
            gestor.password = generate_password_hash(request.form['password'])
        if request.form.get('data_vencimento'):
            gestor.data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')
        else:
            gestor.data_vencimento = None
        db.session.commit()
        flash('Gestor atualizado!', 'success')
        return redirect(url_for('super_gestores'))
    return render_template('super_editar_gestor.html', gestor=gestor)


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — DASHBOARD ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/dashboard')
@requer_login
def dashboard():
    hoje     = date.today()
    em7dias  = hoje + timedelta(days=7)

    clientes_total    = Cliente.query.count()
    clientes_ativos   = Cliente.query.filter_by(status='ativo').count()
    instagram_total   = PerfilRedeSocial.query.count()
    vencimentos_prox  = Vencimento.query.filter(
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

    ultimos_clientes  = Cliente.query.order_by(Cliente.id.desc()).limit(6).all()

    return render_template('dashboard.html',
        clientes_total=clientes_total, clientes_ativos=clientes_ativos,
        instagram_total=instagram_total, vencimentos_proximos=vencimentos_prox,
        receita=formatar_valor(receita), cobrancas_pendentes=cobrancas_pendentes,
        clientes_vencendo=clientes_vencendo, ultimos_clientes=ultimos_clientes,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — CLIENTES
# ══════════════════════════════════════════════════════════════════════════════

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
            nome=request.form['nome'], login=request.form['login'],
            senha=request.form['senha'], status=request.form['status'],
            plano=request.form.get('plano', 'basico'),
            telefone=request.form.get('telefone') or None,
            email=request.form.get('email') or None,
            data_vencimento=data_venc,
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente cadastrado!', 'success')
        return redirect(url_for('clientes'))
    return render_template('cadastrar_cliente.html')


@app.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
@requer_login
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    if request.method == 'POST':
        cliente.nome     = request.form['nome']
        cliente.login    = request.form['login']
        if request.form.get('senha'):
            cliente.senha = request.form['senha']
        cliente.status   = request.form['status']
        cliente.plano    = request.form.get('plano', 'basico')
        cliente.telefone = request.form.get('telefone') or None
        cliente.email    = request.form.get('email') or None
        cliente.data_vencimento = (
            datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')
            if request.form.get('data_vencimento') else None
        )
        db.session.commit()
        flash('Cliente atualizado!', 'success')
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


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — REDES SOCIAIS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/redes_sociais')
@requer_login
def redes_sociais():
    perfis = PerfilRedeSocial.query.order_by(PerfilRedeSocial.rede, PerfilRedeSocial.nome).all()
    por_rede = {}
    for rede_key in REDES_SOCIAIS:
        por_rede[rede_key] = [p for p in perfis if p.rede == rede_key]
    return render_template('redes_sociais.html', perfis=perfis, por_rede=por_rede)


@app.route('/cadastrar_rede_social', methods=['GET', 'POST'])
@requer_login
def cadastrar_rede_social():
    if request.method == 'POST':
        data_postagem = None
        if request.form.get('data_postagem'):
            data_postagem = datetime.strptime(request.form['data_postagem'], '%Y-%m-%dT%H:%M')
        perfil = PerfilRedeSocial(
            nome=request.form['nome'],
            rede=request.form['rede'],
            login=request.form['login'],
            senha=request.form['senha'],
            postagem=request.form.get('postagem') or None,
            data_postagem=data_postagem,
        )
        db.session.add(perfil)
        db.session.commit()
        flash('Perfil cadastrado!', 'success')
        return redirect(url_for('redes_sociais'))
    rede_pre = request.args.get('rede', 'instagram')
    return render_template('cadastrar_rede_social.html', rede_pre=rede_pre)


@app.route('/editar_rede_social/<int:id>', methods=['GET', 'POST'])
@requer_login
def editar_rede_social(id):
    perfil = PerfilRedeSocial.query.get_or_404(id)
    if request.method == 'POST':
        perfil.nome = request.form['nome']
        perfil.rede = request.form['rede']
        perfil.login = request.form['login']
        if request.form.get('senha'):
            perfil.senha = request.form['senha']
        perfil.postagem = request.form.get('postagem') or None
        if request.form.get('data_postagem'):
            perfil.data_postagem = datetime.strptime(request.form['data_postagem'], '%Y-%m-%dT%H:%M')
        db.session.commit()
        flash('Perfil atualizado!', 'success')
        return redirect(url_for('redes_sociais'))
    return render_template('editar_rede_social.html', perfil=perfil)


@app.route('/excluir_rede_social/<int:id>')
@requer_login
def excluir_rede_social(id):
    perfil = PerfilRedeSocial.query.get_or_404(id)
    db.session.delete(perfil)
    db.session.commit()
    flash('Perfil excluído.', 'success')
    return redirect(url_for('redes_sociais'))


# Manter rotas antigas do Instagram para não quebrar links existentes
@app.route('/perfis_instagram')
@requer_login
def perfis_instagram():
    return redirect(url_for('redes_sociais'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — VENCIMENTOS
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — PLANOS E COBRANÇAS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/planos')
@requer_login
def planos():
    stats = {key: Cliente.query.filter_by(plano=key).count() for key in PLANOS}
    receita_planos = {k: formatar_valor(v * PLANOS[k]['preco']) for k, v in stats.items()}
    return render_template('planos.html', stats=stats, receita_planos=receita_planos)


@app.route('/cobrancas')
@requer_login
def cobrancas():
    lista = Cobranca.query.order_by(Cobranca.criado_em.desc()).all()
    total_pago     = sum(c.valor for c in lista if c.status == 'pago')
    total_pendente = sum(c.valor for c in lista if c.status == 'pendente')
    return render_template('cobrancas.html', cobrancas=lista,
        total_pago=formatar_valor(total_pago), total_pendente=formatar_valor(total_pendente))


@app.route('/gerar_cobranca/<int:cliente_id>', methods=['POST'])
@requer_login
def gerar_cobranca(cliente_id):
    cliente  = Cliente.query.get_or_404(cliente_id)
    valor    = float(request.form.get('valor', cliente.info_plano['preco']))
    descricao = request.form.get('descricao') or f"Plano {cliente.info_plano['nome']} — {cliente.nome}"
    cobranca = Cobranca(cliente_id=cliente.id, valor=valor, descricao=descricao)
    sdk = get_mp_sdk()
    if sdk:
        base_url = request.host_url.rstrip('/')
        pref_data = {
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
        }
        result = sdk.preference().create(pref_data)
        if result["status"] == 201:
            pref = result["response"]
            cobranca.mp_preference_id = pref["id"]
            cobranca.mp_link = pref.get("init_point")
    db.session.add(cobranca)
    db.session.commit()
    flash('Cobrança gerada!' + (' Link MP criado.' if cobranca.mp_link else ''), 'success')
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
                cobranca = Cobranca.query.filter_by(mp_preference_id=payment.get('preference_id')).first()
                if cobranca and payment.get('status') == 'approved':
                    cobranca.status = 'pago'
                    cobranca.mp_payment_id = str(payment_id)
                    cobranca.pago_em = datetime.utcnow()
                    db.session.commit()
    return jsonify({'status': 'ok'}), 200


@app.route('/mp/sucesso')
def mp_sucesso():
    flash('Pagamento aprovado!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/mp/falha')
def mp_falha():
    flash('Pagamento não aprovado.', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/mp/pendente')
def mp_pendente():
    flash('Pagamento pendente.', 'warning')
    return redirect(url_for('dashboard'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — RESTAURANTE (login + dashboard + cardápio)
# ══════════════════════════════════════════════════════════════════════════════

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
@requer_restaurante
def restaurante_dashboard():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    categorias  = Categoria.query.filter_by(restaurante_id=restaurante.id, ativo=True).all()
    total_itens = ItemCardapio.query.join(Categoria).filter(
        Categoria.restaurante_id == restaurante.id
    ).count()
    itens_disponiveis = ItemCardapio.query.join(Categoria).filter(
        Categoria.restaurante_id == restaurante.id,
        ItemCardapio.disponivel == True
    ).count()
    destaques = ItemCardapio.query.join(Categoria).filter(
        Categoria.restaurante_id == restaurante.id,
        ItemCardapio.destaque == True,
        ItemCardapio.disponivel == True
    ).all()
    return render_template('dashboard_restaurante.html',
        restaurante=restaurante, categorias=categorias,
        total_itens=total_itens, itens_disponiveis=itens_disponiveis,
        destaques=destaques,
    )


@app.route('/restaurante/logout')
def restaurante_logout():
    session.pop('restaurante', None)
    session.pop('restaurante_id', None)
    return redirect(url_for('restaurante_login'))


# ── Cardápio — Gerenciamento ──────────────────────────────────────────────────

@app.route('/restaurante/cardapio')
@requer_restaurante
def restaurante_cardapio():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    categorias  = Categoria.query.filter_by(restaurante_id=restaurante.id)\
                                 .order_by(Categoria.ordem, Categoria.nome).all()
    return render_template('cardapio.html', restaurante=restaurante, categorias=categorias)


@app.route('/restaurante/cardapio/categoria/nova', methods=['GET', 'POST'])
@requer_restaurante
def nova_categoria():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        cat = Categoria(
            restaurante_id=restaurante.id,
            nome=request.form['nome'],
            descricao=request.form.get('descricao') or None,
            icone=request.form.get('icone', 'fa-utensils'),
        )
        cat.ordem = int(request.form.get('ordem', 0))
        db.session.add(cat)
        db.session.commit()
        flash('Categoria criada!', 'success')
        return redirect(url_for('restaurante_cardapio'))
    return render_template('nova_categoria.html', restaurante=restaurante)


@app.route('/restaurante/cardapio/categoria/<int:id>/editar', methods=['GET', 'POST'])
@requer_restaurante
def editar_categoria(id):
    cat = Categoria.query.get_or_404(id)
    if request.method == 'POST':
        cat.nome     = request.form['nome']
        cat.descricao= request.form.get('descricao') or None
        cat.icone    = request.form.get('icone', 'fa-utensils')
        cat.ordem    = int(request.form.get('ordem', 0))
        cat.ativo    = 'ativo' in request.form
        db.session.commit()
        flash('Categoria atualizada!', 'success')
        return redirect(url_for('restaurante_cardapio'))
    return render_template('editar_categoria.html', cat=cat)


@app.route('/restaurante/cardapio/categoria/<int:id>/excluir')
@requer_restaurante
def excluir_categoria(id):
    cat = Categoria.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    flash('Categoria excluída.', 'success')
    return redirect(url_for('restaurante_cardapio'))


@app.route('/restaurante/cardapio/item/novo', methods=['GET', 'POST'])
@requer_restaurante
def novo_item():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    categorias  = Categoria.query.filter_by(restaurante_id=restaurante.id, ativo=True).all()
    if request.method == 'POST':
        item = ItemCardapio(
            categoria_id=int(request.form['categoria_id']),
            nome=request.form['nome'],
            preco=float(request.form['preco']),
            descricao=request.form.get('descricao') or None,
            preco_promo=float(request.form['preco_promo']) if request.form.get('preco_promo') else None,
        )
        item.destaque   = 'destaque' in request.form
        item.disponivel = 'disponivel' in request.form
        db.session.add(item)
        db.session.commit()
        flash('Item adicionado ao cardápio!', 'success')
        return redirect(url_for('restaurante_cardapio'))
    cat_pre = request.args.get('categoria_id')
    return render_template('novo_item.html', restaurante=restaurante, categorias=categorias, cat_pre=cat_pre)


@app.route('/restaurante/cardapio/item/<int:id>/editar', methods=['GET', 'POST'])
@requer_restaurante
def editar_item(id):
    item = ItemCardapio.query.get_or_404(id)
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    categorias  = Categoria.query.filter_by(restaurante_id=restaurante.id, ativo=True).all()
    if request.method == 'POST':
        item.categoria_id = int(request.form['categoria_id'])
        item.nome         = request.form['nome']
        item.descricao    = request.form.get('descricao') or None
        item.preco        = float(request.form['preco'])
        item.preco_promo  = float(request.form['preco_promo']) if request.form.get('preco_promo') else None
        item.destaque     = 'destaque' in request.form
        item.disponivel   = 'disponivel' in request.form
        db.session.commit()
        flash('Item atualizado!', 'success')
        return redirect(url_for('restaurante_cardapio'))
    return render_template('editar_item.html', item=item, categorias=categorias)


@app.route('/restaurante/cardapio/item/<int:id>/excluir')
@requer_restaurante
def excluir_item(id):
    item = ItemCardapio.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Item removido.', 'success')
    return redirect(url_for('restaurante_cardapio'))


@app.route('/restaurante/cardapio/item/<int:id>/toggle')
@requer_restaurante
def toggle_item(id):
    item = ItemCardapio.query.get_or_404(id)
    item.disponivel = not item.disponivel
    db.session.commit()
    status = 'disponível' if item.disponivel else 'indisponível'
    flash(f'"{item.nome}" marcado como {status}.', 'success')
    return redirect(url_for('restaurante_cardapio'))


# ── Cardápio público (sem autenticação) ──────────────────────────────────────

@app.route('/cardapio/<username>')
def cardapio_publico(username):
    restaurante = Restaurante.query.filter_by(username=username).first_or_404()
    categorias  = Categoria.query.filter_by(restaurante_id=restaurante.id, ativo=True)\
                                 .order_by(Categoria.ordem, Categoria.nome).all()
    # Filtra só itens disponíveis para o público
    for cat in categorias:
        cat.itens_disponiveis = [i for i in cat.itens if i.disponivel]
    return render_template('cardapio_publico.html', restaurante=restaurante, categorias=categorias)


# ── Upload imagem restaurante ──────────────────────────────────────────────

@app.route('/restaurante/upload', methods=['POST'])
@requer_restaurante
def restaurante_upload():
    if 'imagem' not in request.files:
        flash('Nenhuma imagem enviada!', 'danger')
        return redirect(url_for('restaurante_dashboard'))
    from pathlib import Path
    imagem = request.files['imagem']
    upload_dir = Path('static/uploads')
    upload_dir.mkdir(parents=True, exist_ok=True)
    imagem.save(str(upload_dir / imagem.filename))
    flash('Imagem enviada!', 'success')
    return redirect(url_for('restaurante_dashboard'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — ADMIN: GESTÃO DE RESTAURANTES
# ══════════════════════════════════════════════════════════════════════════════

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
        restaurante.telefone = request.form.get('telefone') or None
        restaurante.endereco = request.form.get('endereco') or None
        db.session.add(restaurante)
        db.session.commit()
        flash('Restaurante criado!', 'success')
        return redirect(url_for('admin_restaurantes'))
    return render_template('novo_restaurante.html')


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — AGENDAMENTOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/agendamentos')
@requer_login
def agendamentos():
    posts = PostAgendado.query.order_by(PostAgendado.data_postagem.desc()).all()
    perfis_instagram = PerfilRedeSocial.query.filter_by(rede='instagram').all()
    return render_template('agendamentos.html', posts=posts, perfis=perfis_instagram, now=datetime.now())


@app.route('/agendar_post', methods=['POST'])
@requer_login
def agendar_post():
    perfil_id = request.form.get('perfil_id')
    data_str  = request.form.get('data_postagem')
    if not perfil_id or not data_str:
        flash('Perfil e data são obrigatórios.', 'danger')
        return redirect(url_for('agendamentos'))
    data_postagem = datetime.strptime(data_str, '%Y-%m-%dT%H:%M')
    imagem_path = None
    if 'imagem' in request.files and request.files['imagem'].filename:
        from pathlib import Path
        imagem = request.files['imagem']
        upload_dir = Path(app.root_path) / 'static' / 'uploads'
        upload_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"post_{perfil_id}_{ts}_{imagem.filename}"
        full_path = upload_dir / filename
        imagem.save(str(full_path))
        imagem_path = str(full_path)
    post = PostAgendado(
        perfil_id=int(perfil_id),
        legenda=request.form.get('legenda') or None,
        data_postagem=data_postagem,
    )
    post.imagem_path = imagem_path
    db.session.add(post)
    db.session.commit()
    flash('Post agendado com sucesso!', 'success')
    return redirect(url_for('agendamentos'))


@app.route('/cancelar_agendamento/<int:id>')
@requer_login
def cancelar_agendamento(id):
    post = PostAgendado.query.get_or_404(id)
    if post.status == 'agendado':
        post.status = 'cancelado'
        db.session.commit()
    flash('Agendamento cancelado.', 'warning')
    return redirect(url_for('agendamentos'))


@app.route('/excluir_agendamento/<int:id>')
@requer_login
def excluir_agendamento(id):
    post = PostAgendado.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash('Post excluído.', 'success')
    return redirect(url_for('agendamentos'))


# ══════════════════════════════════════════════════════════════════════════════
# BANCO — MIGRAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

def migrate_db():
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'painelgest.db')
    if not os.path.exists(db_path):
        return
    conn   = sqlite3.connect(db_path)
    cursor = conn.cursor()

    def add_col(table, col, definition):
        cursor.execute(f"PRAGMA table_info({table})")
        cols = {r[1] for r in cursor.fetchall()}
        if col not in cols:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            except Exception:
                pass

    # Administrador
    add_col('administrador', 'email',           'VARCHAR(120)')
    add_col('administrador', 'nome_empresa',     'VARCHAR(120)')
    add_col('administrador', 'plano',            "VARCHAR(20) DEFAULT 'basico'")
    add_col('administrador', 'status',           "VARCHAR(15) DEFAULT 'ativo'")
    add_col('administrador', 'data_vencimento',  'DATETIME')
    add_col('administrador', 'criado_em',        'DATETIME')

    # Cliente
    add_col('cliente', 'plano',           "VARCHAR(20) DEFAULT 'basico'")
    add_col('cliente', 'telefone',        'VARCHAR(20)')
    add_col('cliente', 'email',           'VARCHAR(120)')
    add_col('cliente', 'data_vencimento', 'DATETIME')
    add_col('cliente', 'criado_em',       'DATETIME')

    # Restaurante
    add_col('restaurante', 'telefone',    'VARCHAR(30)')
    add_col('restaurante', 'endereco',    'VARCHAR(200)')
    add_col('restaurante', 'descricao',   'TEXT')
    add_col('restaurante', 'cor_primaria',"VARCHAR(10) DEFAULT '#6366f1'")

    # PostAgendado
    add_col('post_agendado', 'erro',       'TEXT')
    add_col('post_agendado', 'imagem_path','VARCHAR(500)')

    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    with app.app_context():
        migrate_db()
        db.create_all()

        if not Administrador.query.first():
            db.session.add(Administrador('admin', 'admin123', plano='premium'))
            db.session.commit()
            print("Admin padrão criado → admin / admin123")

        if not SuperAdmin.query.first():
            db.session.add(SuperAdmin('superadmin', 'super@2026'))
            db.session.commit()
            print("Super Admin criado → superadmin / super@2026")

    scheduler = BackgroundScheduler()
    scheduler.add_job(processar_posts_agendados, 'interval', minutes=5, id='posts_scheduler')
    scheduler.start()
    print("Scheduler de posts iniciado (intervalo: 5 minutos)")

    try:
        app.run(debug=True, port=5002, use_reloader=False)
    finally:
        scheduler.shutdown()
