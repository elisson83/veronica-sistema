import os
import sys
import io
import json
import math
import smtplib
import secrets
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), encoding='utf-8-sig')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.seguranca_web import registrar_falha, ip_bloqueado, limpar_falhas, get_ip, init_seguranca, validar_upload
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'painelgest2024super')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///painelgest.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
db = SQLAlchemy(app)
init_seguranca(app)
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
    codigo          = db.Column(db.String(4),   unique=True, nullable=True)
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
        if not self.codigo:
            import random
            digitos = ''.join(filter(str.isdigit, str(telefone or '')))
            candidato = digitos[-4:] if len(digitos) >= 4 else ''
            if candidato and not Cliente.query.filter_by(codigo=candidato).first():
                self.codigo = candidato
            else:
                while True:
                    c = str(random.randint(1000, 9999))
                    if not Cliente.query.filter_by(codigo=c).first():
                        self.codigo = c; break

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
    id                   = db.Column(db.Integer, primary_key=True)
    codigo               = db.Column(db.String(4),   unique=True, nullable=True)
    nome                 = db.Column(db.String(80),  nullable=False)
    username             = db.Column(db.String(80),  unique=True, nullable=False)
    password             = db.Column(db.String(120), nullable=False)
    cliente_id           = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=True)
    data_vencimento      = db.Column(db.DateTime,    nullable=True)
    link_pagamento       = db.Column(db.String(200), nullable=True)
    chave_pix            = db.Column(db.String(200), nullable=True)
    telefone             = db.Column(db.String(30),  nullable=True)
    endereco             = db.Column(db.String(200), nullable=True)
    descricao            = db.Column(db.Text,        nullable=True)
    cor_primaria         = db.Column(db.String(10),  default='#f97316')
    logo_path            = db.Column(db.String(300), nullable=True)
    formas_pagamento_json= db.Column(db.Text,        nullable=True)
    instagram            = db.Column(db.String(100), nullable=True)
    facebook             = db.Column(db.String(100), nullable=True)
    whatsapp             = db.Column(db.String(30),  nullable=True)
    token_frota          = db.Column(db.String(64),  nullable=True, unique=True)
    frota_url            = db.Column(db.String(200), nullable=True)
    lat                  = db.Column(db.Float,        nullable=True)
    lng                  = db.Column(db.Float,        nullable=True)
    raio_entrega_km      = db.Column(db.Float,        default=5.0)
    session_token        = db.Column(db.String(64),   nullable=True)

    def __init__(self, nome, username, password, cliente_id=None):
        self.nome = nome; self.username = username
        self.password = generate_password_hash(password)
        self.cliente_id = cliente_id
        if not self.codigo:
            import random, string as _s
            while True:
                c = random.choice(_s.ascii_uppercase) + str(random.randint(100, 999))
                if not Restaurante.query.filter_by(codigo=c).first():
                    self.codigo = c; break

    @property
    def formas_pagamento(self):
        try:
            return json.loads(self.formas_pagamento_json or '[]')
        except Exception:
            return []


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


class PlanoConfig(db.Model):
    """Preços dinâmicos dos planos — editável pelo Super Admin."""
    id    = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(20), unique=True, nullable=False)
    preco = db.Column(db.Float, nullable=False)

    def __init__(self, chave, preco):
        self.chave = chave
        self.preco = preco


class SubAdministrador(db.Model):
    """Sub-administradores vinculados a um Gestor — até 3 por conta."""
    id        = db.Column(db.Integer, primary_key=True)
    admin_id  = db.Column(db.Integer, db.ForeignKey('administrador.id'), nullable=False)
    admin     = db.relationship('Administrador', backref='sub_admins')
    username  = db.Column(db.String(80), unique=True, nullable=False)
    password  = db.Column(db.String(120), nullable=False)
    nome      = db.Column(db.String(80),  nullable=True)
    email     = db.Column(db.String(120), nullable=True)
    nivel     = db.Column(db.String(20),  default='operador')  # admin|operador|visualizador
    status    = db.Column(db.String(10),  default='ativo')
    criado_em = db.Column(db.DateTime,    default=datetime.utcnow)

    def __init__(self, admin_id, username, password, nome=None, email=None, nivel='operador'):
        self.admin_id = admin_id
        self.username = username
        self.password = generate_password_hash(password)
        self.nome     = nome
        self.email    = email
        self.nivel    = nivel


class PedidoKanban(db.Model):
    """Pedido no board Kanban do restaurante."""
    id              = db.Column(db.Integer, primary_key=True)
    restaurante_id  = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    restaurante_rel = db.relationship('Restaurante', backref='pedidos')
    numero          = db.Column(db.Integer, nullable=False, default=1)
    cliente_nome    = db.Column(db.String(80),  nullable=True)
    itens_json      = db.Column(db.Text,        nullable=True)
    total           = db.Column(db.Float,       default=0.0)
    coluna          = db.Column(db.String(20),  default='novo')
    origem          = db.Column(db.String(20),  default='balcao')
    codigo_ifood    = db.Column(db.String(20),  nullable=True)
    forma_pagamento = db.Column(db.String(30),  nullable=True)
    observacoes     = db.Column(db.Text,        nullable=True)
    criado_em       = db.Column(db.DateTime,    default=datetime.utcnow)
    atualizado_em   = db.Column(db.DateTime,    default=datetime.utcnow)

    def __init__(self, restaurante_id, numero, cliente_nome=None, total=0.0,
                 origem='balcao', forma_pagamento=None, observacoes=None, codigo_ifood=None):
        self.restaurante_id  = restaurante_id
        self.numero          = numero
        self.cliente_nome    = cliente_nome
        self.total           = total
        self.origem          = origem
        self.forma_pagamento = forma_pagamento
        self.observacoes     = observacoes
        self.codigo_ifood    = codigo_ifood

    @property
    def itens(self):
        try:
            return json.loads(self.itens_json or '[]')
        except Exception:
            return []

    @property
    def total_fmt(self):
        return f"R$ {self.total:.2f}".replace('.', ',')


class VagaPlantao(db.Model):
    """Vagas de plantão abertas pelo restaurante para motoboys da casa."""
    id             = db.Column(db.Integer, primary_key=True)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    data           = db.Column(db.Date, default=date.today)
    vagas_total    = db.Column(db.Integer, default=2)
    vagas_preench  = db.Column(db.Integer, default=0)
    horario_inicio = db.Column(db.String(5), default='18:00')
    horario_fim    = db.Column(db.String(5), default='23:00')
    observacao     = db.Column(db.String(200))
    status         = db.Column(db.String(20), default='aberta')  # aberta | fechada | encerrada
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)
    inscricoes     = db.relationship('InscricaoVaga', backref='vaga', lazy=True)

    @property
    def vagas_livres(self):
        return max(0, self.vagas_total - self.vagas_preench)

    @property
    def pct_preenchido(self):
        if self.vagas_total == 0:
            return 0
        return int((self.vagas_preench / self.vagas_total) * 100)


class InscricaoVaga(db.Model):
    """Motoboy confirmado em uma vaga de plantão."""
    id           = db.Column(db.Integer, primary_key=True)
    vaga_id      = db.Column(db.Integer, db.ForeignKey('vaga_plantao.id'), nullable=False)
    motoboy_id   = db.Column(db.Integer)
    motoboy_nome = db.Column(db.String(100))
    aceito_em    = db.Column(db.DateTime, default=datetime.utcnow)
    status       = db.Column(db.String(20), default='confirmado')  # confirmado | cancelado


class MotoboyParceiro(db.Model):
    """Motoboy parceiro (não fixo) cadastrado pelo restaurante."""
    id             = db.Column(db.Integer, primary_key=True)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    nome           = db.Column(db.String(100), nullable=False)
    telefone       = db.Column(db.String(20))
    lat            = db.Column(db.Float)
    lng            = db.Column(db.Float)
    ativo          = db.Column(db.Boolean, default=True)
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)


# ── Grupos de Motoboys (visão Super Admin) ───────────────────────────────────

class GrupoFrota(db.Model):
    """Grupo de motoboys gerenciado por um Administrador — visível no Super Admin."""
    id             = db.Column(db.Integer, primary_key=True)
    admin_id       = db.Column(db.Integer, db.ForeignKey('administrador.id'), nullable=False)
    nome           = db.Column(db.String(100), nullable=False)
    url_frota      = db.Column(db.String(200), default='http://localhost:5004')
    total_motoboys = db.Column(db.Integer, default=0)
    corridas_hoje  = db.Column(db.Integer, default=0)
    receita_total  = db.Column(db.Float,   default=0.0)
    ativo          = db.Column(db.Boolean, default=True)
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)
    admin          = db.relationship('Administrador', backref='grupos_frota')


class ConfigCobrancaGrupo(db.Model):
    """Configuração de cobrança por grupo de motoboys."""
    id                   = db.Column(db.Integer, primary_key=True)
    grupo_id             = db.Column(db.Integer, db.ForeignKey('grupo_frota.id'), unique=True, nullable=False)
    tipo                 = db.Column(db.String(20), default='corrida')  # corrida | fixo_mensal
    valor_por_corrida    = db.Column(db.Float, default=0.60)
    valor_mensal         = db.Column(db.Float, default=99.90)
    dia_vencimento       = db.Column(db.Integer, default=10)
    percentual_plataforma= db.Column(db.Float, default=40.0)
    percentual_adm       = db.Column(db.Float, default=60.0)
    ativo                = db.Column(db.Boolean, default=True)
    grupo                = db.relationship('GrupoFrota', backref=db.backref('config_cobranca', uselist=False))


class LancamentoCobranca(db.Model):
    """Lançamento mensal de cobrança por grupo."""
    id                 = db.Column(db.Integer, primary_key=True)
    grupo_id           = db.Column(db.Integer, db.ForeignKey('grupo_frota.id'), nullable=False)
    periodo            = db.Column(db.String(7))   # 'YYYY-MM'
    corridas           = db.Column(db.Integer, default=0)
    valor_total        = db.Column(db.Float, default=0.0)
    valor_plataforma   = db.Column(db.Float, default=0.0)
    valor_adm          = db.Column(db.Float, default=0.0)
    status             = db.Column(db.String(20), default='pendente')  # pendente | pago
    criado_em          = db.Column(db.DateTime, default=datetime.utcnow)
    grupo              = db.relationship('GrupoFrota', backref='lancamentos')


# ── Painel do Dono ────────────────────────────────────────────────────────────

class DonoDaEmpresa(db.Model):
    """Dono da empresa — acesso de alto nível com visão unificada."""
    id        = db.Column(db.Integer, primary_key=True)
    username  = db.Column(db.String(50), unique=True, nullable=False)
    senha_hash= db.Column(db.String(200), nullable=False)
    nome      = db.Column(db.String(100), nullable=False)
    email     = db.Column(db.String(120))
    ativo     = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, username, senha, nome='Dono', email=None):
        self.username  = username
        self.senha_hash= generate_password_hash(senha)
        self.nome      = nome
        self.email     = email

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)


class LogAcesso(db.Model):
    """Registro de acessos ao sistema — visível no Painel do Dono."""
    id          = db.Column(db.Integer, primary_key=True)
    usuario     = db.Column(db.String(80))
    tipo_usuario= db.Column(db.String(20))   # admin|restaurante|dono|superadmin
    rota        = db.Column(db.String(200))
    ip          = db.Column(db.String(50))
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)


# ── CRM Básico ────────────────────────────────────────────────────────────────

class CRMCliente(db.Model):
    """Perfil CRM de um cliente final (cliente do restaurante)."""
    id              = db.Column(db.Integer, primary_key=True)
    restaurante_id  = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    nome_cliente    = db.Column(db.String(100))
    telefone        = db.Column(db.String(20))
    total_pedidos   = db.Column(db.Integer, default=0)
    valor_total     = db.Column(db.Float, default=0.0)
    ticket_medio    = db.Column(db.Float, default=0.0)
    ultimo_pedido   = db.Column(db.DateTime)
    frequencia_dias = db.Column(db.Float)
    preferencias_json= db.Column(db.Text)
    notas           = db.Column(db.Text)
    criado_em       = db.Column(db.DateTime, default=datetime.utcnow)
    restaurante     = db.relationship('Restaurante', backref='clientes_crm')

    @property
    def segmento(self):
        if self.total_pedidos >= 10 or (self.ticket_medio or 0) >= 80:
            return ('VIP', 'warning')
        if self.total_pedidos >= 5:
            return ('Frequente', 'success')
        if self.ultimo_pedido and (datetime.utcnow() - self.ultimo_pedido).days > 30:
            return ('Inativo', 'secondary')
        return ('Regular', 'info')

    @property
    def preferencias(self):
        try:
            return json.loads(self.preferencias_json or '[]')
        except Exception:
            return []


# ── Acesso Temporário Super Admin ────────────────────────────────────────────

class AcessoTemporario(db.Model):
    """Token de acesso temporário: Super Admin entra no painel de um gestor."""
    id            = db.Column(db.Integer, primary_key=True)
    super_admin   = db.Column(db.String(80),  nullable=False)
    gestor_id     = db.Column(db.Integer, db.ForeignKey('administrador.id'), nullable=False)
    token         = db.Column(db.String(64),  unique=True, nullable=False)
    autorizado    = db.Column(db.Boolean,     default=False)
    usado         = db.Column(db.Boolean,     default=False)
    criado_em     = db.Column(db.DateTime,    default=datetime.utcnow)
    expira_em     = db.Column(db.DateTime,    nullable=False)
    ip_solicitante= db.Column(db.String(50),  nullable=True)
    gestor        = db.relationship('Administrador', backref='acessos_super')

    def __init__(self, super_admin, gestor_id, ip=None):
        self.super_admin    = super_admin
        self.gestor_id      = gestor_id
        self.token          = secrets.token_urlsafe(32)
        self.expira_em      = datetime.utcnow() + timedelta(hours=1)
        self.ip_solicitante = ip

    @property
    def valido(self):
        return self.autorizado and not self.usado and datetime.utcnow() < self.expira_em

    @property
    def expirado(self):
        return datetime.utcnow() >= self.expira_em


class AuditoriaAcesso(db.Model):
    """Registro de auditoria de ações do Super Admin no painel de gestores."""
    id            = db.Column(db.Integer, primary_key=True)
    acesso_id     = db.Column(db.Integer, db.ForeignKey('acesso_temporario.id'), nullable=True)
    super_admin   = db.Column(db.String(80),  nullable=False)
    gestor_id     = db.Column(db.Integer,     nullable=True)
    gestor_nome   = db.Column(db.String(120), nullable=True)
    acao          = db.Column(db.String(200), nullable=False)
    detalhes      = db.Column(db.Text,        nullable=True)
    ip            = db.Column(db.String(50),  nullable=True)
    criado_em     = db.Column(db.DateTime,    default=datetime.utcnow)


# ── Reset de Senha ────────────────────────────────────────────────────────────

class TokenResetSenha(db.Model):
    """Token para reset de senha por e-mail — todos os painéis."""
    id         = db.Column(db.Integer, primary_key=True)
    painel     = db.Column(db.String(20), nullable=False)  # gestor|dono|restaurante
    email      = db.Column(db.String(120), nullable=False)
    token      = db.Column(db.String(64), unique=True, nullable=False)
    usado      = db.Column(db.Boolean, default=False)
    criado_em  = db.Column(db.DateTime, default=datetime.utcnow)
    expira_em  = db.Column(db.DateTime, nullable=False)

    def __init__(self, painel, email):
        self.painel    = painel
        self.email     = email.lower()
        self.token     = secrets.token_urlsafe(32)
        self.expira_em = datetime.utcnow() + timedelta(hours=2)

    @property
    def valido(self):
        return not self.usado and datetime.utcnow() < self.expira_em


# ── Mesas do Restaurante ──────────────────────────────────────────────────────

class Mesa(db.Model):
    """Mesa do restaurante — numeração personalizável pelo dono."""
    id             = db.Column(db.Integer, primary_key=True)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    numero         = db.Column(db.Integer, nullable=False)
    nome           = db.Column(db.String(30), nullable=True)   # ex: "VIP", "Varanda"
    capacidade     = db.Column(db.Integer, default=4)
    status         = db.Column(db.String(20), default='livre')  # livre|ocupada|reservada
    ativa          = db.Column(db.Boolean, default=True)
    restaurante    = db.relationship('Restaurante', backref='mesas')

    def __init__(self, restaurante_id, numero, nome=None, capacidade=4):
        self.restaurante_id = restaurante_id
        self.numero         = numero
        self.nome           = nome
        self.capacidade     = capacidade

    @property
    def label(self):
        return self.nome or f"Mesa {self.numero}"


# ── Chat interno entre painéis ───────────────────────────────────────────────

class MensagemChat(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    painel_origem  = db.Column(db.String(30), nullable=False)   # admin|restaurante|motoboy|super
    usuario_nome   = db.Column(db.String(80), nullable=False)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=True)
    mensagem       = db.Column(db.Text, nullable=False)
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, painel_origem, usuario_nome, mensagem, restaurante_id=None):
        self.painel_origem  = painel_origem
        self.usuario_nome   = usuario_nome
        self.mensagem       = mensagem
        self.restaurante_id = restaurante_id


# ── Atendimento Inteligente ───────────────────────────────────────────────────

class ClientePresente(db.Model):
    """Cliente registrado na entrada via telefone."""
    id             = db.Column(db.Integer, primary_key=True)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    mesa_id        = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=True)
    telefone       = db.Column(db.String(20), nullable=False)
    nome           = db.Column(db.String(80), nullable=True)
    whatsapp_enviado = db.Column(db.Boolean, default=False)
    entrada_em     = db.Column(db.DateTime, default=datetime.utcnow)
    saiu           = db.Column(db.Boolean, default=False)
    saiu_em        = db.Column(db.DateTime, nullable=True)
    restaurante    = db.relationship('Restaurante', backref='clientes_presentes')
    mesa           = db.relationship('Mesa', backref='clientes_presentes')


class ContaMesa(db.Model):
    """Conta aberta de um cliente presente."""
    id                = db.Column(db.Integer, primary_key=True)
    restaurante_id    = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    cliente_id        = db.Column(db.Integer, db.ForeignKey('cliente_presente.id'), nullable=True)
    mesa_id           = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=True)
    itens_json        = db.Column(db.Text, default='[]')
    total             = db.Column(db.Float, default=0.0)
    status            = db.Column(db.String(20), default='aberta')  # aberta|paga|cancelada
    forma_pagamento   = db.Column(db.String(30), nullable=True)  # pix|cartao|dinheiro
    pix_payload       = db.Column(db.Text, nullable=True)
    criado_em         = db.Column(db.DateTime, default=datetime.utcnow)
    pago_em           = db.Column(db.DateTime, nullable=True)
    restaurante       = db.relationship('Restaurante', backref='contas_mesas')
    cliente           = db.relationship('ClientePresente', backref='contas')
    mesa_rel          = db.relationship('Mesa', backref='contas')

    def __init__(self, restaurante_id, mesa_id=None, cliente_id=None):
        self.restaurante_id = restaurante_id
        self.mesa_id        = mesa_id
        self.cliente_id     = cliente_id

    @property
    def itens(self):
        try:
            return json.loads(self.itens_json or '[]')
        except Exception:
            return []

    @property
    def total_fmt(self):
        return f"R$ {self.total:.2f}".replace('.', ',')


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


def get_planos_config():
    """Retorna PLANOS com preços sobrepostos pelos valores salvos no banco."""
    config = {k: dict(v) for k, v in PLANOS.items()}
    try:
        for pc in PlanoConfig.query.all():
            if pc.chave in config:
                config[pc.chave]['preco'] = pc.preco
    except Exception:
        pass
    return config


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


def distancia_km(lat1, lng1, lat2, lng2):
    """Cálculo de distância haversine entre dois pontos GPS."""
    if None in (lat1, lng1, lat2, lng2):
        return None
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return round(R * 2 * math.asin(math.sqrt(a)), 2)


def gerar_comprovante_pdf(restaurante, motoboy_dados, entregas, periodo_inicio, periodo_fim):
    """Gera PDF de comprovante de pagamento para motoboy usando fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    pdf = FPDF(format='A4')
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    # Cabeçalho
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'COMPROVANTE DE PAGAMENTO', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f'Restaurante: {restaurante.nome}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 7, f'Período: {periodo_inicio.strftime("%d/%m/%Y")} a {periodo_fim.strftime("%d/%m/%Y")}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(4)
    # Dados do motoboy
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'DADOS DO MOTOBOY', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f'Nome: {motoboy_dados.get("nome","—")}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f'CPF/CNPJ: {motoboy_dados.get("cpf_cnpj","—")}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f'Telefone: {motoboy_dados.get("telefone","—")}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(4)
    # Tabela de entregas
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, 'ENTREGAS REALIZADAS', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(40, 40, 60)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(15, 7, '#', border=1, fill=True)
    pdf.cell(60, 7, 'Cliente', border=1, fill=True)
    pdf.cell(35, 7, 'Data', border=1, fill=True)
    pdf.cell(30, 7, 'Taxa', border=1, fill=True)
    pdf.cell(0, 7, 'Status', border=1, fill=True, new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(0, 0, 0)
    total = 0.0
    for i, e in enumerate(entregas, 1):
        taxa = e.get('taxa', 0)
        total += taxa
        fill = (i % 2 == 0)
        pdf.set_fill_color(240, 240, 250) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(15, 6, str(i), border=1, fill=fill)
        pdf.cell(60, 6, str(e.get('cliente',''))[:30], border=1, fill=fill)
        pdf.cell(35, 6, str(e.get('data','')), border=1, fill=fill)
        pdf.cell(30, 6, f"R$ {taxa:.2f}", border=1, fill=fill)
        pdf.cell(0, 6, str(e.get('status','entregue')), border=1, fill=fill, new_x='LMARGIN', new_y='NEXT')
    # Total
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, f'TOTAL A PAGAR: R$ {total:.2f}', new_x='LMARGIN', new_y='NEXT')
    # Rodapé
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f'Emitido em {datetime.now().strftime("%d/%m/%Y às %H:%M")}', new_x='LMARGIN', new_y='NEXT')
    return bytes(pdf.output())


def enviar_email_comprovante(destinatario, assunto, corpo, pdf_bytes=None, nome_pdf='comprovante.pdf'):
    """Envia email com comprovante PDF em anexo."""
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    if not smtp_user:
        return False, 'SMTP não configurado no .env'
    try:
        msg = MIMEMultipart()
        msg['From']    = smtp_user
        msg['To']      = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        if pdf_bytes:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{nome_pdf}"')
            msg.attach(part)
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, destinatario, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


def requer_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'administrador' not in session:
            return redirect(url_for('login'))
        val = session['administrador']
        # Suporta sessões antigas (username) e novas (email)
        admin = (Administrador.query.filter_by(email=val).first() or
                 Administrador.query.filter_by(username=val).first())
        if not admin:
            session.pop('administrador', None)
            return redirect(url_for('login'))
        if admin.bloqueado:
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
        # Valida sessão única — verifica se o token ainda é o atual
        rest = Restaurante.query.filter_by(username=session['restaurante']).first()
        if rest and rest.session_token and session.get('restaurante_token') != rest.session_token:
            session.pop('restaurante', None)
            session.pop('restaurante_id', None)
            session.pop('restaurante_token', None)
            flash('Sessão encerrada — outro dispositivo fez login.', 'warning')
            return redirect(url_for('restaurante_login'))
        return f(*args, **kwargs)
    return decorated


def requer_dono(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'dono' not in session:
            return redirect(url_for('dono_login'))
        return f(*args, **kwargs)
    return decorated


def _registrar_acesso(usuario, tipo):
    try:
        log = LogAcesso(usuario=usuario, tipo_usuario=tipo,
                        rota=request.path, ip=request.remote_addr)
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass


@app.context_processor
def inject_globals():
    try:
        planos_dinamicos = get_planos_config()
    except Exception:
        planos_dinamicos = PLANOS
    return {
        'admin_user': session.get('administrador'),
        'PLANOS': planos_dinamicos,
        'REDES_SOCIAIS': REDES_SOCIAIS,
        'mp_ativo': bool(os.environ.get('MERCADOPAGO_ACCESS_TOKEN')),
        'today': date.today(),
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
        ip = get_ip()
        if ip_bloqueado(ip):
            flash('Muitas tentativas. Aguarde 15 minutos.', 'danger')
            return render_template('login.html')
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        admin = Administrador.query.filter(
            db.func.lower(Administrador.email) == email
        ).first()
        if admin and check_password_hash(admin.password, password):
            if admin.bloqueado:
                flash('Conta bloqueada. Entre em contato com o suporte.', 'danger')
                return render_template('login.html')
            limpar_falhas(ip)
            session.permanent = True
            session['administrador'] = admin.email
            return redirect(url_for('dashboard'))
        bloqueou = registrar_falha(ip)
        if bloqueou:
            flash('Conta bloqueada por 15 min por excesso de tentativas.', 'danger')
        else:
            flash('E-mail ou senha inválidos.', 'danger')
    return render_template('login.html')


@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if 'administrador' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        nome     = request.form.get('nome', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        if not nome or not email or not password:
            flash('Preencha todos os campos.', 'danger')
            return render_template('cadastrar.html')
        if password != confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('cadastrar.html')
        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('cadastrar.html')
        existente = Administrador.query.filter(db.func.lower(Administrador.email) == email).first()
        if existente:
            flash('Já existe uma conta com este e-mail.', 'danger')
            return render_template('cadastrar.html')
        username = email.split('@')[0][:30]
        # Garantir username único
        base = username
        counter = 1
        while Administrador.query.filter_by(username=username).first():
            username = f"{base}{counter}"
            counter += 1
        admin = Administrador(username=username, password=password, email=email,
                              nome_empresa=nome, plano='basico')
        db.session.add(admin)
        db.session.commit()
        session['administrador'] = admin.email
        flash(f'Bem-vindo(a), {nome}! Conta criada com sucesso.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('cadastrar.html')


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
        ip = get_ip()
        if ip_bloqueado(ip):
            flash('Muitas tentativas. Aguarde 15 minutos.', 'danger')
            return render_template('super_login.html')
        username = request.form['username']
        password = request.form['password']
        sa = SuperAdmin.query.filter_by(username=username).first()
        if sa and check_password_hash(sa.password, password):
            limpar_falhas(ip)
            session.permanent = True
            session['super_admin'] = username
            return redirect(url_for('super_dashboard'))
        bloqueou = registrar_falha(ip)
        if bloqueou:
            flash('Conta bloqueada por 15 min por excesso de tentativas.', 'danger')
        else:
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
    return render_template('super_gestores.html', gestores=gestores, today=date.today())


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
        ip = get_ip()
        if ip_bloqueado(ip):
            flash('Muitas tentativas. Aguarde 15 minutos.', 'danger')
            return render_template('login_restaurante.html')
        username = request.form['username']
        password = request.form['password']
        restaurante = Restaurante.query.filter_by(username=username).first()
        if restaurante and check_password_hash(restaurante.password, password):
            limpar_falhas(ip)
            tok = secrets.token_hex(16)
            restaurante.session_token = tok
            db.session.commit()
            session.permanent = True
            session['restaurante']       = username
            session['restaurante_id']    = restaurante.id
            session['restaurante_token'] = tok
            return redirect(url_for('restaurante_dashboard'))
        bloqueou = registrar_falha(ip)
        if bloqueou:
            flash('Conta bloqueada por 15 min por excesso de tentativas.', 'danger')
        else:
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
    rest = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    if cat.restaurante_id != rest.id:
        abort(403)
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
    rest = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    if cat.restaurante_id != rest.id:
        abort(403)
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
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    if item.categoria.restaurante_id != restaurante.id:
        abort(403)
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
    rest = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    if item.categoria.restaurante_id != rest.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    flash('Item removido.', 'success')
    return redirect(url_for('restaurante_cardapio'))


@app.route('/restaurante/cardapio/item/<int:id>/toggle')
@requer_restaurante
def toggle_item(id):
    item = ItemCardapio.query.get_or_404(id)
    rest = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    if item.categoria.restaurante_id != rest.id:
        abort(403)
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
    ok, resultado = validar_upload(imagem)
    if not ok:
        flash(resultado, 'danger')
        return redirect(url_for('restaurante_dashboard'))
    upload_dir = Path(app.root_path) / 'static' / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)
    imagem.save(str(upload_dir / resultado))
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
    posts  = PostAgendado.query.order_by(PostAgendado.data_postagem.desc()).all()
    perfis = PerfilRedeSocial.query.order_by(PerfilRedeSocial.rede, PerfilRedeSocial.nome).all()
    return render_template('agendamentos.html', posts=posts, perfis=perfis, now=datetime.now())


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
        ok, resultado = validar_upload(imagem)
        if not ok:
            flash(resultado, 'danger')
            return redirect(url_for('agendamentos'))
        upload_dir = Path(app.root_path) / 'static' / 'uploads'
        upload_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"post_{perfil_id}_{ts}_{resultado}"
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
# ROTAS — SUPER ADMIN: PLANOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/super/planos', methods=['GET', 'POST'])
@requer_super
def super_planos():
    if request.method == 'POST':
        for chave in PLANOS:
            preco_str = request.form.get(f'preco_{chave}', '').replace(',', '.')
            try:
                preco = float(preco_str)
                pc = PlanoConfig.query.filter_by(chave=chave).first()
                if pc:
                    pc.preco = preco
                else:
                    db.session.add(PlanoConfig(chave, preco))
            except (ValueError, TypeError):
                pass
        db.session.commit()
        flash('Preços dos planos atualizados com sucesso!', 'success')
        return redirect(url_for('super_planos'))
    planos_config = get_planos_config()
    return render_template('super_planos.html', planos_config=planos_config)


@app.route('/super/bloquear_inadimplentes', methods=['POST'])
@requer_super
def super_bloquear_inadimplentes():
    hoje = date.today()
    inadimplentes = Administrador.query.filter(
        Administrador.status == 'ativo',
        Administrador.data_vencimento.isnot(None),
        Administrador.data_vencimento < datetime.combine(hoje, datetime.min.time())
    ).all()
    count = len(inadimplentes)
    for g in inadimplentes:
        g.status = 'bloqueado'
    db.session.commit()
    if count:
        flash(f'{count} gestor(es) inadimplente(s) bloqueado(s).', 'warning')
    else:
        flash('Nenhum gestor inadimplente encontrado.', 'success')
    return redirect(url_for('super_gestores'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — SUPER ADMIN: GRUPOS DE MOTOBOYS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/super/grupos')
@requer_super
def super_grupos():
    grupos = GrupoFrota.query.filter_by(ativo=True).order_by(GrupoFrota.criado_em.desc()).all()
    # Tenta buscar dados ao vivo para cada grupo
    import requests as _req
    for g in grupos:
        try:
            r = _req.get(f"{g.url_frota.rstrip('/')}/api/stats", timeout=2)
            if r.ok:
                d = r.json()
                g.total_motoboys = d.get('total_motoboys', g.total_motoboys)
                g.corridas_hoje  = d.get('corridas_hoje',  g.corridas_hoje)
                g.receita_total  = d.get('receita_total',  g.receita_total)
                db.session.commit()
        except Exception:
            pass
    gestores = Administrador.query.filter_by(status='ativo').order_by(Administrador.username).all()
    return render_template('super_grupos.html', grupos=grupos, gestores=gestores)


@app.route('/super/grupos/novo', methods=['POST'])
@requer_super
def super_novo_grupo():
    admin_id  = int(request.form['admin_id'])
    nome      = request.form.get('nome', '').strip()
    url_frota = request.form.get('url_frota', 'http://localhost:5004').strip()
    if not nome:
        flash('Nome do grupo obrigatório.', 'danger')
        return redirect(url_for('super_grupos'))
    g = GrupoFrota(admin_id=admin_id, nome=nome, url_frota=url_frota)
    db.session.add(g)
    db.session.commit()
    flash(f'Grupo "{nome}" criado!', 'success')
    return redirect(url_for('super_grupos'))


@app.route('/super/grupos/<int:gid>/excluir', methods=['POST'])
@requer_super
def super_excluir_grupo(gid):
    g = GrupoFrota.query.get_or_404(gid)
    g.ativo = False
    db.session.commit()
    flash('Grupo desativado.', 'warning')
    return redirect(url_for('super_grupos'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — SUPER ADMIN: COBRANÇA POR GRUPO
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/super/cobranca')
@requer_super
def super_cobranca():
    grupos = GrupoFrota.query.filter_by(ativo=True).all()
    lancamentos = LancamentoCobranca.query.order_by(LancamentoCobranca.criado_em.desc()).limit(50).all()
    return render_template('super_cobranca.html', grupos=grupos, lancamentos=lancamentos)


@app.route('/super/cobranca/<int:gid>/configurar', methods=['POST'])
@requer_super
def super_configurar_cobranca(gid):
    g = GrupoFrota.query.get_or_404(gid)
    cfg = g.config_cobranca or ConfigCobrancaGrupo(grupo_id=gid)
    cfg.tipo                  = request.form.get('tipo', 'corrida')
    cfg.valor_por_corrida     = float(request.form.get('valor_por_corrida', 0.60) or 0.60)
    cfg.valor_mensal          = float(request.form.get('valor_mensal', 99.90) or 99.90)
    cfg.dia_vencimento        = int(request.form.get('dia_vencimento', 10) or 10)
    cfg.percentual_plataforma = float(request.form.get('percentual_plataforma', 40) or 40)
    cfg.percentual_adm        = 100.0 - cfg.percentual_plataforma
    if not cfg.id:
        db.session.add(cfg)
    db.session.commit()
    flash('Configuração de cobrança salva!', 'success')
    return redirect(url_for('super_cobranca'))


@app.route('/super/cobranca/<int:gid>/lancar', methods=['POST'])
@requer_super
def super_lancar_cobranca(gid):
    g = GrupoFrota.query.get_or_404(gid)
    cfg = g.config_cobranca
    if not cfg:
        flash('Configure a cobrança antes de lançar.', 'danger')
        return redirect(url_for('super_cobranca'))
    periodo = datetime.utcnow().strftime('%Y-%m')
    existente = LancamentoCobranca.query.filter_by(grupo_id=gid, periodo=periodo).first()
    if existente:
        flash('Já existe lançamento para este grupo no período atual.', 'warning')
        return redirect(url_for('super_cobranca'))
    corridas = g.corridas_hoje  # simplificado; em produção usaria acumulado do mês
    if cfg.tipo == 'corrida':
        valor_total = corridas * cfg.valor_por_corrida
    else:
        valor_total = cfg.valor_mensal
    valor_plataforma = valor_total * (cfg.percentual_plataforma / 100)
    valor_adm        = valor_total * (cfg.percentual_adm / 100)
    lanc = LancamentoCobranca(
        grupo_id=gid, periodo=periodo, corridas=corridas,
        valor_total=valor_total, valor_plataforma=valor_plataforma, valor_adm=valor_adm
    )
    db.session.add(lanc)
    db.session.commit()
    flash(f'Lançamento de R$ {valor_total:.2f} criado para {g.nome}!', 'success')
    return redirect(url_for('super_cobranca'))


@app.route('/super/cobranca/<int:lid>/pagar', methods=['POST'])
@requer_super
def super_pagar_lancamento(lid):
    lanc = LancamentoCobranca.query.get_or_404(lid)
    lanc.status = 'pago'
    db.session.commit()
    flash('Lançamento marcado como pago!', 'success')
    return redirect(url_for('super_cobranca'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — SUPER ADMIN: RELATÓRIO FINANCEIRO
# ══════════════════════════════════════════════════════════════════════════════

def _gerar_relatorio_pdf_super(mes, ano, dados):
    """Gera PDF do relatório financeiro do Super Admin."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    pdf = FPDF(format='A4')
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_fill_color(30, 30, 50)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, 'RELATÓRIO FINANCEIRO — SUPER ADMIN', fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f'Período: {mes:02d}/{ano}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 7, f'Emitido em: {datetime.now().strftime("%d/%m/%Y às %H:%M")}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(6)
    # Totais
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 9, 'RESUMO GERAL', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 11)
    for label, val in dados.get('resumo', []):
        pdf.cell(0, 7, f'{label}: R$ {val:.2f}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(6)
    # Grupos
    if dados.get('lancamentos'):
        pdf.set_font('Helvetica', 'B', 13)
        pdf.cell(0, 9, 'LANÇAMENTOS POR GRUPO', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(40, 40, 60); pdf.set_text_color(255, 255, 255)
        for col, w in [('Grupo', 60), ('Período', 25), ('Corridas', 25), ('Total', 35), ('Plataforma', 35), ('Status', 0)]:
            pdf.cell(w, 7, col, border=1, fill=True)
        pdf.ln()
        pdf.set_font('Helvetica', '', 9); pdf.set_text_color(0, 0, 0)
        for i, lanc in enumerate(dados['lancamentos']):
            fill = i % 2 == 0
            pdf.set_fill_color(245, 245, 255) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(60, 6, str(lanc.get('grupo',''))[:28], border=1, fill=fill)
            pdf.cell(25, 6, str(lanc.get('periodo','')), border=1, fill=fill)
            pdf.cell(25, 6, str(lanc.get('corridas',0)), border=1, fill=fill)
            pdf.cell(35, 6, f"R$ {lanc.get('total',0):.2f}", border=1, fill=fill)
            pdf.cell(35, 6, f"R$ {lanc.get('plataforma',0):.2f}", border=1, fill=fill)
            pdf.cell(0,  6, str(lanc.get('status','')), border=1, fill=fill, new_x='LMARGIN', new_y='NEXT')
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 8); pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, 'Documento gerado automaticamente pelo sistema Verônica IA.', align='C', new_x='LMARGIN', new_y='NEXT')
    return bytes(pdf.output())


@app.route('/super/relatorio')
@requer_super
def super_relatorio():
    mes = int(request.args.get('mes', datetime.utcnow().month))
    ano = int(request.args.get('ano', datetime.utcnow().year))
    gestores_ativos = Administrador.query.filter_by(status='ativo').all()
    mrr_total = sum(g.mrr for g in gestores_ativos)
    lancamentos_db = LancamentoCobranca.query.order_by(LancamentoCobranca.criado_em.desc()).all()
    total_cobrancas_pago    = sum(l.valor_plataforma for l in lancamentos_db if l.status == 'pago')
    total_cobrancas_pendente= sum(l.valor_plataforma for l in lancamentos_db if l.status == 'pendente')
    cobrancas_mp = Cobranca.query.filter_by(status='pago').all()
    total_mp = sum(c.valor for c in cobrancas_mp)
    resumo = [
        ('MRR (Gestores Ativos)', mrr_total),
        ('Cobrança Grupos — Pago', total_cobrancas_pago),
        ('Cobrança Grupos — Pendente', total_cobrancas_pendente),
        ('Mercado Pago — Recebido', total_mp),
        ('Total Geral', mrr_total + total_cobrancas_pago + total_mp),
    ]
    lancamentos_lista = [{
        'grupo': l.grupo.nome if l.grupo else '—',
        'periodo': l.periodo,
        'corridas': l.corridas,
        'total': l.valor_total,
        'plataforma': l.valor_plataforma,
        'status': l.status,
    } for l in lancamentos_db]
    return render_template('super_relatorio.html',
        mes=mes, ano=ano, resumo=resumo,
        lancamentos=lancamentos_db,
        total_lancamentos_pago=total_cobrancas_pago,
        total_lancamentos_pendente=total_cobrancas_pendente,
        mrr_total=mrr_total, total_mp=total_mp,
    )


@app.route('/super/relatorio/pdf')
@requer_super
def super_relatorio_pdf():
    mes = int(request.args.get('mes', datetime.utcnow().month))
    ano = int(request.args.get('ano', datetime.utcnow().year))
    lancamentos_db = LancamentoCobranca.query.order_by(LancamentoCobranca.criado_em.desc()).all()
    gestores_ativos = Administrador.query.filter_by(status='ativo').all()
    mrr_total = sum(g.mrr for g in gestores_ativos)
    total_pago   = sum(l.valor_plataforma for l in lancamentos_db if l.status == 'pago')
    total_mp     = sum(c.valor for c in Cobranca.query.filter_by(status='pago').all())
    dados = {
        'resumo': [
            ('MRR', mrr_total),
            ('Grupos Pago', total_pago),
            ('Mercado Pago', total_mp),
            ('Total Geral', mrr_total + total_pago + total_mp),
        ],
        'lancamentos': [{
            'grupo': l.grupo.nome if l.grupo else '—',
            'periodo': l.periodo, 'corridas': l.corridas,
            'total': l.valor_total, 'plataforma': l.valor_plataforma, 'status': l.status,
        } for l in lancamentos_db],
    }
    pdf_bytes = _gerar_relatorio_pdf_super(mes, ano, dados)
    if not pdf_bytes:
        flash('fpdf2 não instalado. Execute: pip install fpdf2', 'danger')
        return redirect(url_for('super_relatorio'))
    from flask import send_file
    return send_file(io.BytesIO(pdf_bytes),
                     download_name=f'relatorio_{ano}_{mes:02d}.pdf',
                     as_attachment=True, mimetype='application/pdf')


@app.route('/super/relatorio/email', methods=['POST'])
@requer_super
def super_relatorio_email():
    email_dest = request.form.get('email_contador', '').strip()
    if not email_dest:
        flash('Informe o email do contador.', 'danger')
        return redirect(url_for('super_relatorio'))
    mes = int(request.form.get('mes', datetime.utcnow().month))
    ano = int(request.form.get('ano', datetime.utcnow().year))
    lancamentos_db = LancamentoCobranca.query.order_by(LancamentoCobranca.criado_em.desc()).all()
    gestores_ativos = Administrador.query.filter_by(status='ativo').all()
    mrr_total = sum(g.mrr for g in gestores_ativos)
    total_pago = sum(l.valor_plataforma for l in lancamentos_db if l.status == 'pago')
    total_mp   = sum(c.valor for c in Cobranca.query.filter_by(status='pago').all())
    dados = {
        'resumo': [('MRR', mrr_total), ('Grupos', total_pago), ('MP', total_mp)],
        'lancamentos': [{'grupo': l.grupo.nome if l.grupo else '—', 'periodo': l.periodo,
                         'corridas': l.corridas, 'total': l.valor_total,
                         'plataforma': l.valor_plataforma, 'status': l.status}
                        for l in lancamentos_db],
    }
    pdf_bytes = _gerar_relatorio_pdf_super(mes, ano, dados)
    corpo = (f'Relatório financeiro referente a {mes:02d}/{ano}.\n'
             f'MRR: R$ {mrr_total:.2f} | Grupos: R$ {total_pago:.2f} | Total: R$ {mrr_total+total_pago+total_mp:.2f}\n\n'
             f'Gerado por Verônica IA — Sistema de Gestão.')
    ok, erro = enviar_email_comprovante(email_dest, f'Relatório Financeiro {mes:02d}/{ano}', corpo,
                                        pdf_bytes, f'relatorio_{ano}_{mes:02d}.pdf')
    if ok:
        flash(f'Relatório enviado para {email_dest}!', 'success')
    else:
        flash(f'Erro ao enviar: {erro}', 'danger')
    return redirect(url_for('super_relatorio'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — PAINEL DO DONO
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/dono/login', methods=['GET', 'POST'])
def dono_login():
    if 'dono' in session:
        return redirect(url_for('dono_dashboard'))
    if request.method == 'POST':
        ip = get_ip()
        if ip_bloqueado(ip):
            flash('Muitas tentativas. Aguarde 15 minutos.', 'danger')
            return render_template('dono_login.html')
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        dono  = DonoDaEmpresa.query.filter(
            db.func.lower(DonoDaEmpresa.email) == email,
            DonoDaEmpresa.ativo == True
        ).first()
        if dono and dono.check_senha(senha):
            limpar_falhas(ip)
            session.permanent = True
            session['dono'] = dono.email
            _registrar_acesso(dono.email, 'dono')
            return redirect(url_for('dono_dashboard'))
        bloqueou = registrar_falha(ip)
        if bloqueou:
            flash('Conta bloqueada por 15 min por excesso de tentativas.', 'danger')
        else:
            flash('E-mail ou senha inválidos.', 'danger')
    return render_template('dono_login.html')


@app.route('/dono/cadastrar', methods=['GET', 'POST'])
def dono_cadastrar():
    if 'dono' in session:
        return redirect(url_for('dono_dashboard'))
    if request.method == 'POST':
        nome    = request.form.get('nome', '').strip()
        email   = request.form.get('email', '').strip().lower()
        senha   = request.form.get('senha', '')
        confirm = request.form.get('confirm', '')
        if not nome or not email or not senha:
            flash('Preencha todos os campos.', 'danger')
            return render_template('dono_cadastrar.html')
        if senha != confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('dono_cadastrar.html')
        if len(senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('dono_cadastrar.html')
        existente = DonoDaEmpresa.query.filter(
            db.func.lower(DonoDaEmpresa.email) == email
        ).first()
        if existente:
            flash('Já existe uma conta com este e-mail.', 'danger')
            return render_template('dono_cadastrar.html')
        username = email.split('@')[0][:30]
        base = username; counter = 1
        while DonoDaEmpresa.query.filter_by(username=username).first():
            username = f"{base}{counter}"; counter += 1
        d = DonoDaEmpresa(username=username, senha=senha, nome=nome, email=email)
        db.session.add(d)
        db.session.commit()
        session['dono'] = d.email
        _registrar_acesso(d.email, 'dono')
        flash(f'Bem-vindo(a), {nome}!', 'success')
        return redirect(url_for('dono_dashboard'))
    return render_template('dono_cadastrar.html')


@app.route('/dono/logout')
def dono_logout():
    session.pop('dono', None)
    return redirect(url_for('dono_login'))


@app.route('/dono/dashboard')
@requer_dono
def dono_dashboard():
    hoje = date.today()
    _registrar_acesso(session['dono'], 'dono')
    # Pedidos do dia
    pedidos_hoje = PedidoKanban.query.filter(
        db.func.date(PedidoKanban.criado_em) == hoje
    ).all()
    vendas_hoje = sum(p.total for p in pedidos_hoje)
    pedidos_em_andamento = [p for p in pedidos_hoje if p.coluna not in ('entregue', 'cancelado')]
    # Funcionários
    total_admins = Administrador.query.filter_by(status='ativo').count()
    total_subs   = SubAdministrador.query.filter_by(status='ativo').count()
    total_restaurantes = Restaurante.query.count()
    # Motoboys via API
    motoboys_online = 0
    import requests as _req
    try:
        r = _req.get('http://localhost:5003/api/motoboys_disponiveis', timeout=2)
        if r.ok:
            motoboys_online = len(r.json())
    except Exception:
        pass
    # Últimos acessos
    acessos_recentes = LogAcesso.query.order_by(LogAcesso.timestamp.desc()).limit(10).all()
    return render_template('dono_dashboard.html',
        pedidos_hoje=len(pedidos_hoje), vendas_hoje=vendas_hoje,
        pedidos_em_andamento=pedidos_em_andamento,
        total_admins=total_admins, total_subs=total_subs,
        total_restaurantes=total_restaurantes, motoboys_online=motoboys_online,
        acessos_recentes=acessos_recentes, hoje=hoje,
    )


@app.route('/dono/vendas')
@requer_dono
def dono_vendas():
    page          = int(request.args.get('page', 1))
    per           = 30
    filtro_status = request.args.get('status', '')
    filtro_rest   = request.args.get('restaurante_id', '')
    filtro_data   = request.args.get('data', '')
    query = PedidoKanban.query
    if filtro_status:
        query = query.filter_by(coluna=filtro_status)
    if filtro_rest:
        try:
            query = query.filter_by(restaurante_id=int(filtro_rest))
        except (ValueError, TypeError):
            pass
    if filtro_data:
        try:
            from datetime import datetime as _dt2
            dia_f = _dt2.strptime(filtro_data, '%Y-%m-%d').date()
            query = query.filter(db.func.date(PedidoKanban.criado_em) == dia_f)
        except ValueError:
            pass
    query   = query.order_by(PedidoKanban.criado_em.desc())
    total   = query.count()
    pedidos = query.offset((page - 1) * per).limit(per).all()
    restaurantes = Restaurante.query.order_by(Restaurante.nome).all()
    rest_map     = {r.id: r.nome for r in restaurantes}
    return render_template('dono_vendas.html', pedidos=pedidos, rest_map=rest_map,
                           page=page, total=total, per=per,
                           restaurantes=restaurantes,
                           filtro_status=filtro_status,
                           filtro_rest=filtro_rest,
                           filtro_data=filtro_data)


@app.route('/dono/funcionarios')
@requer_dono
def dono_funcionarios():
    admins = Administrador.query.order_by(Administrador.status, Administrador.username).all()
    subs   = SubAdministrador.query.order_by(SubAdministrador.status, SubAdministrador.username).all()
    return render_template('dono_funcionarios.html', admins=admins, subs=subs)


@app.route('/dono/motoboys')
@requer_dono
def dono_motoboys():
    motoboys_disp = []
    import requests as _req
    try:
        r = _req.get('http://localhost:5003/api/motoboys', timeout=3)
        if r.ok:
            motoboys_disp = r.json()
    except Exception:
        pass
    return render_template('dono_motoboys.html', motoboys=motoboys_disp)


@app.route('/dono/pedidos')
@requer_dono
def dono_pedidos():
    em_andamento = PedidoKanban.query.filter(
        PedidoKanban.coluna.notin_(['entregue', 'cancelado'])
    ).order_by(PedidoKanban.criado_em.desc()).all()
    restaurantes = Restaurante.query.all()
    rest_map = {r.id: r.nome for r in restaurantes}
    return render_template('dono_pedidos.html', pedidos=em_andamento, rest_map=rest_map, now=datetime.utcnow())


@app.route('/dono/acessos')
@requer_dono
def dono_acessos():
    tipo_filtro = request.args.get('tipo', '')
    query = LogAcesso.query.order_by(LogAcesso.timestamp.desc())
    if tipo_filtro:
        query = query.filter_by(tipo_usuario=tipo_filtro)
    acessos = query.limit(200).all()
    return render_template('dono_acessos.html', acessos=acessos, tipo_filtro=tipo_filtro)


@app.route('/dono/relatorio')
@requer_dono
def dono_relatorio():
    hoje = date.today()
    # Últimos 7 dias de vendas
    dados_dias = []
    for i in range(6, -1, -1):
        dia = hoje - timedelta(days=i)
        pedidos_dia = PedidoKanban.query.filter(
            db.func.date(PedidoKanban.criado_em) == dia
        ).all()
        total_dia = sum(p.total for p in pedidos_dia)
        dados_dias.append({'dia': dia.strftime('%d/%m'), 'total': round(total_dia, 2), 'pedidos': len(pedidos_dia)})
    # Totais do mês
    inicio_mes = hoje.replace(day=1)
    pedidos_mes = PedidoKanban.query.filter(
        PedidoKanban.criado_em >= datetime.combine(inicio_mes, datetime.min.time())
    ).all()
    vendas_mes = sum(p.total for p in pedidos_mes)
    return render_template('dono_relatorio.html', dados_dias=dados_dias,
                           vendas_mes=vendas_mes, pedidos_mes=len(pedidos_mes))


@app.route('/dono/resumo_dia')
@requer_dono
def dono_resumo_dia():
    hoje = date.today()
    pedidos_hoje = PedidoKanban.query.filter(
        db.func.date(PedidoKanban.criado_em) == hoje
    ).all()
    import requests as _req
    motoboys_online = 0
    try:
        r = _req.get('http://localhost:5003/api/motoboys_disponiveis', timeout=2)
        if r.ok: motoboys_online = len(r.json())
    except Exception: pass
    return jsonify({
        'pedidos_hoje': len(pedidos_hoje),
        'vendas_hoje': round(sum(p.total for p in pedidos_hoje), 2),
        'em_andamento': sum(1 for p in pedidos_hoje if p.coluna not in ('entregue','cancelado')),
        'motoboys_online': motoboys_online,
    })


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — CRM BÁSICO (módulo restaurante)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/restaurante/crm')
@requer_restaurante
def restaurante_crm():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    clientes_crm = CRMCliente.query.filter_by(restaurante_id=rest.id).order_by(
        CRMCliente.total_pedidos.desc()
    ).all()
    return render_template('crm_lista.html', clientes_crm=clientes_crm, restaurante=rest)


@app.route('/restaurante/crm/novo', methods=['GET', 'POST'])
@requer_restaurante
def restaurante_crm_novo():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    if request.method == 'POST':
        c = CRMCliente(
            restaurante_id=rest.id,
            nome_cliente=request.form.get('nome_cliente', '').strip(),
            telefone=request.form.get('telefone', '').strip(),
            notas=request.form.get('notas', '').strip(),
        )
        db.session.add(c)
        db.session.commit()
        flash('Cliente CRM cadastrado!', 'success')
        return redirect(url_for('restaurante_crm'))
    return render_template('crm_novo.html', restaurante=rest)


@app.route('/restaurante/crm/<int:cid>')
@requer_restaurante
def restaurante_crm_detalhe(cid):
    rest = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    c = CRMCliente.query.filter_by(id=cid, restaurante_id=rest.id).first_or_404()
    return render_template('crm_detalhe.html', cliente=c, restaurante=rest)


@app.route('/restaurante/crm/<int:cid>/nota', methods=['POST'])
@requer_restaurante
def restaurante_crm_nota(cid):
    rest = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    c = CRMCliente.query.filter_by(id=cid, restaurante_id=rest.id).first_or_404()
    nova_nota = request.form.get('nota', '').strip()
    if nova_nota:
        ts = datetime.now().strftime('%d/%m/%Y %H:%M')
        c.notas = f"[{ts}] {nova_nota}\n{c.notas or ''}"
        db.session.commit()
        flash('Nota adicionada!', 'success')
    return redirect(url_for('restaurante_crm_detalhe', cid=cid))


@app.route('/restaurante/crm/importar', methods=['POST'])
@requer_restaurante
def restaurante_crm_importar():
    """Importa clientes únicos a partir dos PedidoKanban do restaurante."""
    rest = Restaurante.query.filter_by(username=session['restaurante']).first_or_404()
    pedidos = PedidoKanban.query.filter_by(restaurante_id=rest.id).all()
    from collections import defaultdict
    grupos = defaultdict(list)
    for p in pedidos:
        nome = (p.cliente_nome or '').strip()
        if nome:
            grupos[nome].append(p)
    criados = 0
    for nome_cliente, lista_pedidos in grupos.items():
        existente = CRMCliente.query.filter_by(restaurante_id=rest.id, nome_cliente=nome_cliente).first()
        if existente:
            existente.total_pedidos = len(lista_pedidos)
            existente.valor_total   = sum(p.total for p in lista_pedidos)
            existente.ticket_medio  = existente.valor_total / len(lista_pedidos)
            existente.ultimo_pedido = max(p.criado_em for p in lista_pedidos)
        else:
            valor_total = sum(p.total for p in lista_pedidos)
            c = CRMCliente(
                restaurante_id=rest.id, nome_cliente=nome_cliente,
                total_pedidos=len(lista_pedidos), valor_total=valor_total,
                ticket_medio=valor_total / len(lista_pedidos),
                ultimo_pedido=max(p.criado_em for p in lista_pedidos),
            )
            db.session.add(c)
            criados += 1
    db.session.commit()
    flash(f'{criados} cliente(s) importado(s) dos pedidos!', 'success')
    return redirect(url_for('restaurante_crm'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — SUB-ADMINISTRADORES
# ══════════════════════════════════════════════════════════════════════════════

NIVEIS_PERMISSAO = {
    'admin':       {'nome': 'Administrador', 'descricao': 'Acesso total ao painel'},
    'operador':    {'nome': 'Operador',      'descricao': 'Pode editar clientes e redes sociais'},
    'visualizador':{'nome': 'Visualizador',  'descricao': 'Apenas leitura, sem edição'},
}


@app.route('/sub_admins')
@requer_login
def sub_admins():
    _val  = session['administrador']
    admin = (Administrador.query.filter_by(email=_val).first() or
             Administrador.query.filter_by(username=_val).first())
    subs  = SubAdministrador.query.filter_by(admin_id=admin.id).all()
    return render_template('sub_admins.html', subs=subs, admin=admin,
                           niveis=NIVEIS_PERMISSAO)


@app.route('/sub_admins/novo', methods=['GET', 'POST'])
@requer_login
def novo_sub_admin():
    _val  = session['administrador']
    admin = (Administrador.query.filter_by(email=_val).first() or
             Administrador.query.filter_by(username=_val).first())
    if SubAdministrador.query.filter_by(admin_id=admin.id).count() >= 3:
        flash('Limite de 3 sub-administradores atingido.', 'warning')
        return redirect(url_for('sub_admins'))
    if request.method == 'POST':
        sub = SubAdministrador(
            admin_id=admin.id,
            username=request.form['username'],
            password=request.form['password'],
            nome=request.form.get('nome') or None,
            email=request.form.get('email') or None,
            nivel=request.form.get('nivel', 'operador'),
        )
        db.session.add(sub)
        try:
            db.session.commit()
            flash('Sub-administrador criado com sucesso!', 'success')
            return redirect(url_for('sub_admins'))
        except Exception:
            db.session.rollback()
            flash('Usuário já existe. Escolha outro username.', 'danger')
    return render_template('cadastrar_sub_admin.html', niveis=NIVEIS_PERMISSAO)


@app.route('/sub_admins/<int:id>/editar', methods=['GET', 'POST'])
@requer_login
def editar_sub_admin(id):
    _val  = session['administrador']
    admin = (Administrador.query.filter_by(email=_val).first() or
             Administrador.query.filter_by(username=_val).first())
    sub   = SubAdministrador.query.filter_by(id=id, admin_id=admin.id).first_or_404()
    if request.method == 'POST':
        sub.nome   = request.form.get('nome') or None
        sub.email  = request.form.get('email') or None
        sub.nivel  = request.form.get('nivel', 'operador')
        sub.status = request.form.get('status', 'ativo')
        if request.form.get('password'):
            sub.password = generate_password_hash(request.form['password'])
        db.session.commit()
        flash('Sub-administrador atualizado!', 'success')
        return redirect(url_for('sub_admins'))
    return render_template('editar_sub_admin.html', sub=sub, niveis=NIVEIS_PERMISSAO)


@app.route('/sub_admins/<int:id>/excluir')
@requer_login
def excluir_sub_admin(id):
    _val  = session['administrador']
    admin = (Administrador.query.filter_by(email=_val).first() or
             Administrador.query.filter_by(username=_val).first())
    sub   = SubAdministrador.query.filter_by(id=id, admin_id=admin.id).first_or_404()
    db.session.delete(sub)
    db.session.commit()
    flash('Sub-administrador excluído.', 'success')
    return redirect(url_for('sub_admins'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — KANBAN RESTAURANTE
# ══════════════════════════════════════════════════════════════════════════════

COLUNAS_KANBAN = [
    {'key': 'novo',      'nome': 'Novos',       'icone': 'fa-bell',          'cor': '#f97316'},
    {'key': 'preparo',   'nome': 'Em Preparo',  'icone': 'fa-fire-burner',   'cor': '#f59e0b'},
    {'key': 'pronto',    'nome': 'Pronto',      'icone': 'fa-check-circle',  'cor': '#22c55e'},
    {'key': 'entrega',   'nome': 'Em Entrega',  'icone': 'fa-motorcycle',    'cor': '#06b6d4'},
    {'key': 'concluido', 'nome': 'Concluído',   'icone': 'fa-flag-checkered','cor': '#64748b'},
]


@app.route('/restaurante/kanban')
@requer_restaurante
def restaurante_kanban():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    pedidos_por_coluna = {}
    for col in COLUNAS_KANBAN:
        pedidos_por_coluna[col['key']] = PedidoKanban.query.filter_by(
            restaurante_id=restaurante.id, coluna=col['key']
        ).order_by(PedidoKanban.criado_em).all()
    categorias = Categoria.query.filter_by(restaurante_id=restaurante.id, ativo=True).all()
    return render_template('kanban.html', restaurante=restaurante,
                           pedidos=pedidos_por_coluna, colunas=COLUNAS_KANBAN,
                           categorias=categorias)


@app.route('/restaurante/kanban/novo', methods=['GET', 'POST'])
@requer_restaurante
def novo_pedido_kanban():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        ultimo  = PedidoKanban.query.filter_by(restaurante_id=restaurante.id)\
                    .order_by(PedidoKanban.numero.desc()).first()
        numero  = (ultimo.numero + 1) if ultimo else 1
        pedido  = PedidoKanban(
            restaurante_id=restaurante.id,
            numero=numero,
            cliente_nome=request.form.get('cliente_nome') or None,
            total=float(request.form.get('total', 0) or 0),
            origem=request.form.get('origem', 'balcao'),
            forma_pagamento=request.form.get('forma_pagamento') or None,
            observacoes=request.form.get('observacoes') or None,
            codigo_ifood=request.form.get('codigo_ifood') or None,
        )
        nomes  = request.form.getlist('item_nome')
        qtds   = request.form.getlist('item_qtd')
        precos = request.form.getlist('item_preco')
        itens  = [{'nome': n.strip(), 'qtd': q, 'preco': p}
                  for n, q, p in zip(nomes, qtds, precos) if n.strip()]
        pedido.itens_json = json.dumps(itens, ensure_ascii=False)
        db.session.add(pedido)
        db.session.commit()
        flash(f'Pedido #{numero} criado!', 'success')
        return redirect(url_for('restaurante_kanban'))
    categorias = Categoria.query.filter_by(restaurante_id=restaurante.id, ativo=True).all()
    return render_template('novo_pedido.html', restaurante=restaurante,
                           categorias=categorias, formas=restaurante.formas_pagamento)


@app.route('/restaurante/kanban/<int:id>/mover', methods=['POST'])
@requer_restaurante
def mover_pedido(id):
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    pedido = PedidoKanban.query.filter_by(id=id, restaurante_id=restaurante.id).first_or_404()
    coluna = request.form.get('coluna') or request.json.get('coluna') if request.is_json else request.form.get('coluna')
    if request.is_json:
        coluna = request.json.get('coluna')
    chaves_validas = [c['key'] for c in COLUNAS_KANBAN]
    if coluna in chaves_validas:
        pedido.coluna = coluna
        pedido.atualizado_em = datetime.utcnow()
        db.session.commit()
    return jsonify({'ok': True, 'coluna': pedido.coluna})


@app.route('/restaurante/kanban/api')
@requer_restaurante
def kanban_api():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    resultado = {}
    for col in COLUNAS_KANBAN:
        pedidos = PedidoKanban.query.filter_by(
            restaurante_id=restaurante.id, coluna=col['key']
        ).order_by(PedidoKanban.criado_em).all()
        resultado[col['key']] = [{
            'id': p.id, 'numero': p.numero, 'cliente_nome': p.cliente_nome or 'Cliente',
            'total_fmt': p.total_fmt, 'origem': p.origem,
            'forma_pagamento': p.forma_pagamento or '',
            'codigo_ifood': p.codigo_ifood or '',
            'observacoes': p.observacoes or '',
            'itens': p.itens[:3],
            'itens_total': len(p.itens),
            'hora': p.criado_em.strftime('%H:%M'),
            'whatsapp_cliente': '',
        } for p in pedidos]
    return jsonify(resultado)


@app.route('/restaurante/kanban/<int:id>/excluir', methods=['POST', 'GET'])
@requer_restaurante
def excluir_pedido(id):
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    pedido = PedidoKanban.query.filter_by(id=id, restaurante_id=restaurante.id).first_or_404()
    db.session.delete(pedido)
    db.session.commit()
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True})
    flash('Pedido removido.', 'success')
    return redirect(url_for('restaurante_kanban'))


@app.route('/restaurante/kanban/<int:id>/comanda')
@requer_restaurante
def imprimir_comanda(id):
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    pedido = PedidoKanban.query.filter_by(id=id, restaurante_id=restaurante.id).first_or_404()
    return render_template('comanda.html', restaurante=restaurante, pedido=pedido)


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — PERFIL DO RESTAURANTE
# ══════════════════════════════════════════════════════════════════════════════

FORMAS_PAGAMENTO_DISPONIVEIS = [
    'Dinheiro', 'Cartão de Débito', 'Cartão de Crédito', 'Pix',
    'Vale Refeição', 'Vale Alimentação', 'iFood Crédito',
]


@app.route('/restaurante/perfil', methods=['GET', 'POST'])
@requer_restaurante
def editar_perfil_restaurante():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        restaurante.nome         = request.form.get('nome') or restaurante.nome
        restaurante.telefone     = request.form.get('telefone') or None
        restaurante.endereco     = request.form.get('endereco') or None
        restaurante.descricao    = request.form.get('descricao') or None
        restaurante.cor_primaria = request.form.get('cor_primaria', '#6366f1')
        restaurante.chave_pix    = request.form.get('chave_pix') or None
        restaurante.link_pagamento = request.form.get('link_pagamento') or None
        restaurante.instagram    = request.form.get('instagram') or None
        restaurante.facebook     = request.form.get('facebook') or None
        restaurante.whatsapp     = request.form.get('whatsapp') or None
        try:
            restaurante.raio_entrega_km = float(request.form.get('raio_entrega_km') or 5)
        except (ValueError, TypeError):
            restaurante.raio_entrega_km = 5.0
        try:
            lat_v = request.form.get('lat_restaurante')
            lng_v = request.form.get('lng_restaurante')
            if lat_v: restaurante.lat = float(lat_v)
            if lng_v: restaurante.lng = float(lng_v)
        except (ValueError, TypeError):
            pass
        formas = request.form.getlist('forma_pagamento')
        restaurante.formas_pagamento_json = json.dumps(formas)
        # Upload logo
        if 'logo' in request.files and request.files['logo'].filename:
            from pathlib import Path
            logo = request.files['logo']
            ok, resultado = validar_upload(logo)
            if not ok:
                flash(resultado, 'danger')
                return redirect(url_for('editar_perfil_restaurante'))
            upload_dir = Path(app.root_path) / 'static' / 'uploads'
            upload_dir.mkdir(parents=True, exist_ok=True)
            ext = resultado.rsplit('.', 1)[-1].lower()
            filename = f"logo_{restaurante.id}.{ext}"
            logo.save(str(upload_dir / filename))
            restaurante.logo_path = f"uploads/{filename}"
        db.session.commit()
        flash('Perfil do restaurante atualizado!', 'success')
        return redirect(url_for('editar_perfil_restaurante'))
    return render_template('perfil_restaurante.html', restaurante=restaurante,
                           formas_disponiveis=FORMAS_PAGAMENTO_DISPONIVEIS)


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — MAPA DE ENTREGA DO RESTAURANTE
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/restaurante/mapa')
@requer_restaurante
def mapa_restaurante():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    try:
        import requests as _req
        r = _req.get('http://localhost:5003/api/motoboys_disponiveis', timeout=2)
        motoboys = r.json()
    except Exception:
        motoboys = []
    return render_template('mapa_restaurante.html', restaurante=restaurante, motoboys=motoboys)


@app.route('/restaurante/mapa/salvar_pos', methods=['POST'])
@requer_restaurante
def mapa_restaurante_salvar_pos():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    data = request.get_json() or {}
    try:
        restaurante.lat = float(data.get('lat'))
        restaurante.lng = float(data.get('lng'))
        db.session.commit()
    except (TypeError, ValueError):
        pass
    return jsonify({'ok': True})


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — VAGAS DA CASA
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/restaurante/vagas', methods=['GET', 'POST'])
@requer_restaurante
def vagas_restaurante():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        vagas = VagaPlantao(
            restaurante_id = restaurante.id,
            data           = date.today(),
            vagas_total    = int(request.form.get('vagas_total', 2)),
            horario_inicio = request.form.get('horario_inicio', '18:00'),
            horario_fim    = request.form.get('horario_fim', '23:00'),
            observacao     = request.form.get('observacao', ''),
            status         = 'aberta',
        )
        db.session.add(vagas)
        db.session.commit()
        flash(f'Vaga aberta: {vagas.vagas_total} motoboy(s) para hoje!', 'success')
        return redirect(url_for('vagas_restaurante'))

    vagas_hoje = VagaPlantao.query.filter_by(restaurante_id=restaurante.id).order_by(VagaPlantao.criado_em.desc()).limit(10).all()
    return render_template('vagas_restaurante.html', restaurante=restaurante, vagas_hoje=vagas_hoje)


@app.route('/restaurante/vagas/<int:vid>/fechar', methods=['POST'])
@requer_restaurante
def fechar_vaga(vid):
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    vaga = VagaPlantao.query.filter_by(id=vid, restaurante_id=restaurante.id).first_or_404()
    vaga.status = 'encerrada'
    db.session.commit()
    flash('Vaga encerrada.', 'info')
    return redirect(url_for('vagas_restaurante'))


@app.route('/api/vagas_disponiveis')
def api_vagas_disponiveis():
    """API pública usada pelo AppMotoboy para listar vagas abertas."""
    vagas = VagaPlantao.query.filter_by(status='aberta').filter(
        VagaPlantao.data == date.today()
    ).all()
    return jsonify([{
        'id': v.id, 'restaurante_id': v.restaurante_id,
        'vagas_total': v.vagas_total, 'vagas_preench': v.vagas_preench,
        'vagas_livres': v.vagas_livres, 'horario_inicio': v.horario_inicio,
        'horario_fim': v.horario_fim, 'observacao': v.observacao,
    } for v in vagas])


@app.route('/api/vagas/<int:vid>/aceitar', methods=['POST'])
def api_aceitar_vaga(vid):
    """Motoboy aceita uma vaga — chamado pelo AppMotoboy."""
    data = request.get_json() or {}
    vaga = VagaPlantao.query.get_or_404(vid)
    if vaga.status != 'aberta' or vaga.vagas_livres <= 0:
        return jsonify({'ok': False, 'erro': 'Vaga fechada ou sem espaço'})
    inscricao = InscricaoVaga(
        vaga_id      = vid,
        motoboy_id   = data.get('motoboy_id'),
        motoboy_nome = data.get('motoboy_nome', 'Motoboy'),
    )
    db.session.add(inscricao)
    vaga.vagas_preench += 1
    if vaga.vagas_preench >= vaga.vagas_total:
        vaga.status = 'fechada'
    db.session.commit()
    return jsonify({'ok': True, 'vagas_livres': vaga.vagas_livres, 'status': vaga.status})


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — PARCEIROS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/restaurante/parceiros', methods=['GET', 'POST'])
@requer_restaurante
def parceiros_restaurante():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        acao = request.form.get('acao', 'novo')
        if acao == 'novo':
            p = MotoboyParceiro(
                restaurante_id = restaurante.id,
                nome           = request.form['nome'],
                telefone       = request.form.get('telefone', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', ''),
                lat            = float(request.form['lat']) if request.form.get('lat') else None,
                lng            = float(request.form['lng']) if request.form.get('lng') else None,
            )
            db.session.add(p)
            db.session.commit()
            flash(f'Parceiro {p.nome} adicionado!', 'success')
        return redirect(url_for('parceiros_restaurante'))

    parceiros = MotoboyParceiro.query.filter_by(restaurante_id=restaurante.id, ativo=True).all()
    # Ordena por distância do restaurante se tiver coordenadas
    r_lat = float(request.args.get('lat', 0) or 0)
    r_lng = float(request.args.get('lng', 0) or 0)
    for p in parceiros:
        p.distancia = distancia_km(r_lat, r_lng, p.lat, p.lng) if (r_lat and p.lat) else None
    parceiros.sort(key=lambda p: (p.distancia is None, p.distancia or 0))
    return render_template('parceiros_restaurante.html', restaurante=restaurante, parceiros=parceiros)


@app.route('/restaurante/parceiros/<int:pid>/excluir', methods=['POST'])
@requer_restaurante
def excluir_parceiro(pid):
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    p = MotoboyParceiro.query.filter_by(id=pid, restaurante_id=restaurante.id).first_or_404()
    p.ativo = False
    db.session.commit()
    flash('Parceiro removido.', 'info')
    return redirect(url_for('parceiros_restaurante'))


@app.route('/restaurante/parceiros/chamar_proximo')
@requer_restaurante
def chamar_parceiro_proximo():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    r_lat = float(request.args.get('lat', 0) or 0)
    r_lng = float(request.args.get('lng', 0) or 0)
    parceiros = MotoboyParceiro.query.filter_by(restaurante_id=restaurante.id, ativo=True).all()
    if not parceiros:
        return jsonify({'ok': False, 'erro': 'Nenhum parceiro cadastrado'})
    com_dist = [(p, distancia_km(r_lat, r_lng, p.lat, p.lng) or 9999) for p in parceiros if p.telefone]
    com_dist.sort(key=lambda x: x[1])
    if not com_dist:
        return jsonify({'ok': False, 'erro': 'Nenhum parceiro com telefone cadastrado'})
    proximo, dist = com_dist[0]
    pedido_texto = request.args.get('msg', 'Olá! Temos uma entrega disponível. Você pode pegar?')
    wa_link = f"https://wa.me/{proximo.telefone}?text={pedido_texto}"
    return jsonify({'ok': True, 'nome': proximo.nome, 'distancia_km': dist, 'wa_link': wa_link})


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — COMPROVANTE / NOTA FISCAL
# ══════════════════════════════════════════════════════════════════════════════

MOTOBOY_API_URL = os.getenv('MOTOBOY_API_URL', 'http://localhost:5003')


def _buscar_motoboy_api(motoboy_id):
    """Busca dados de um motoboy via API do AppMotoboy."""
    try:
        import requests as req_lib
        r = req_lib.get(f'{MOTOBOY_API_URL}/api/motoboy/{motoboy_id}', timeout=3)
        return r.json() if r.ok else {}
    except Exception:
        return {}


def _buscar_entregas_api(motoboy_id, inicio, fim):
    """Busca entregas de um motoboy via API do AppMotoboy."""
    try:
        import requests as req_lib
        r = req_lib.get(f'{MOTOBOY_API_URL}/api/entregas/{motoboy_id}',
                        params={'inicio': inicio.isoformat(), 'fim': fim.isoformat()}, timeout=3)
        return r.json() if r.ok else []
    except Exception:
        return []


@app.route('/restaurante/comprovante', methods=['GET', 'POST'])
@requer_restaurante
def comprovante_restaurante():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    motoboys = []
    try:
        import requests as req_lib
        r = req_lib.get(f'{MOTOBOY_API_URL}/api/motoboys_disponiveis', timeout=2)
        # Também busca todos (não apenas disponíveis)
        r2 = req_lib.get(f'{MOTOBOY_API_URL}/api/motoboys', timeout=2)
        motoboys = r2.json() if r2.ok else (r.json() if r.ok else [])
    except Exception:
        pass
    return render_template('comprovante_restaurante.html', restaurante=restaurante, motoboys=motoboys)


@app.route('/restaurante/comprovante/preview')
@requer_restaurante
def comprovante_preview():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    motoboy_id  = request.args.get('motoboy_id', '')
    periodo     = request.args.get('periodo', '7')
    hoje        = date.today()
    if periodo == '7':
        inicio = hoje - timedelta(days=7)
    elif periodo == '15':
        inicio = hoje - timedelta(days=15)
    elif periodo == '30':
        inicio = hoje.replace(day=1)
    else:
        inicio = hoje - timedelta(days=7)
    motoboy_dados = _buscar_motoboy_api(motoboy_id)
    entregas      = _buscar_entregas_api(motoboy_id, inicio, hoje)
    total         = sum(e.get('taxa', 0) for e in entregas)
    return render_template('comprovante_preview.html',
        restaurante=restaurante, motoboy=motoboy_dados,
        entregas=entregas, total=total,
        periodo_inicio=inicio, periodo_fim=hoje, now=datetime.now())


@app.route('/restaurante/comprovante/pdf')
@requer_restaurante
def comprovante_pdf():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    motoboy_id  = request.args.get('motoboy_id', '')
    periodo     = request.args.get('periodo', '7')
    hoje        = date.today()
    dias        = {'7': 7, '15': 15, '30': hoje.day - 1}.get(periodo, 7)
    inicio      = hoje - timedelta(days=dias)
    motoboy_dados = _buscar_motoboy_api(motoboy_id)
    entregas      = _buscar_entregas_api(motoboy_id, inicio, hoje)
    pdf_bytes     = gerar_comprovante_pdf(restaurante, motoboy_dados, entregas, inicio, hoje)
    if not pdf_bytes:
        flash('Erro ao gerar PDF. Verifique se fpdf2 está instalado.', 'danger')
        return redirect(url_for('comprovante_restaurante'))
    nome = f"comprovante_{motoboy_dados.get('nome','motoboy')}_{hoje.strftime('%Y%m%d')}.pdf".replace(' ', '_')
    resp = make_response(pdf_bytes)
    resp.headers['Content-Type']        = 'application/pdf'
    resp.headers['Content-Disposition'] = f'attachment; filename="{nome}"'
    return resp


@app.route('/restaurante/comprovante/email', methods=['POST'])
@requer_restaurante
def comprovante_email():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    motoboy_id  = request.form.get('motoboy_id', '')
    periodo     = request.form.get('periodo', '7')
    email_dest  = request.form.get('email', '')
    hoje        = date.today()
    dias        = {'7': 7, '15': 15, '30': hoje.day - 1}.get(periodo, 7)
    inicio      = hoje - timedelta(days=dias)
    motoboy_dados = _buscar_motoboy_api(motoboy_id)
    entregas      = _buscar_entregas_api(motoboy_id, inicio, hoje)
    pdf_bytes     = gerar_comprovante_pdf(restaurante, motoboy_dados, entregas, inicio, hoje)
    destino       = email_dest or motoboy_dados.get('email', '')
    if not destino:
        flash('E-mail de destino não informado.', 'danger')
        return redirect(url_for('comprovante_restaurante'))
    ok, erro = enviar_email_comprovante(
        destino,
        f'Comprovante {restaurante.nome} — {inicio.strftime("%d/%m")} a {hoje.strftime("%d/%m/%Y")}',
        f'Segue em anexo o comprovante de pagamento do período {inicio.strftime("%d/%m/%Y")} a {hoje.strftime("%d/%m/%Y")}.',
        pdf_bytes,
        f'comprovante_{hoje.strftime("%Y%m%d")}.pdf'
    )
    if ok:
        flash(f'Comprovante enviado para {destino}!', 'success')
    else:
        flash(f'Erro ao enviar e-mail: {erro}', 'danger')
    return redirect(url_for('comprovante_restaurante'))


# ══════════════════════════════════════════════════════════════════════════════
# QR CODE — CONEXÃO COM PAINELFROTA
# ══════════════════════════════════════════════════════════════════════════════

def _gerar_qr_bytes_gest(url_destino):
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(url_destino)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf
    except Exception:
        return None


@app.route('/restaurante/frota_qr')
@requer_restaurante
def restaurante_frota_qr():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    if not restaurante.token_frota:
        restaurante.token_frota = secrets.token_hex(16)
        db.session.commit()
    frota_url = os.environ.get('PAINELFROTA_URL', 'http://localhost:5004')
    url_conexao = f"{frota_url}/conectar_gestor/{restaurante.token_frota}"
    return render_template('qr_frota.html', restaurante=restaurante, url_conexao=url_conexao)


@app.route('/restaurante/frota_qr.png')
@requer_restaurante
def restaurante_frota_qr_png():
    restaurante = Restaurante.query.filter_by(username=session['restaurante']).first()
    if not restaurante.token_frota:
        restaurante.token_frota = secrets.token_hex(16)
        db.session.commit()
    frota_url = os.environ.get('PAINELFROTA_URL', 'http://localhost:5004')
    url_conexao = f"{frota_url}/conectar_gestor/{restaurante.token_frota}"
    buf = _gerar_qr_bytes_gest(url_conexao)
    if not buf:
        return 'QR indisponível', 503
    from flask import send_file
    return send_file(buf, mimetype='image/png')


@app.route('/api/restaurante_token/<token>')
def api_restaurante_token(token):
    """PainelFrota consulta dados do restaurante pelo token_frota."""
    r = Restaurante.query.filter_by(token_frota=token).first()
    if not r:
        return jsonify({'ok': False}), 404
    return jsonify({
        'ok': True,
        'nome': r.nome,
        'telefone': r.telefone or '',
        'endereco': r.endereco or '',
    })


# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# HELPERS — EMAIL RESET + PIX
# ══════════════════════════════════════════════════════════════════════════════

def enviar_whatsapp(telefone, mensagem):
    """
    Envia mensagem de texto via WhatsApp Business Cloud API (Meta).
    Retorna (True, message_id) em caso de sucesso ou (False, erro) em caso de falha.
    Telefone deve estar no formato internacional sem '+': ex: 5511999999999
    """
    import requests as _req
    phone_id    = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
    access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')

    if not phone_id or not access_token:
        return False, 'WHATSAPP_PHONE_NUMBER_ID ou WHATSAPP_ACCESS_TOKEN não configurado no .env'

    # Normaliza telefone: remove tudo que não é dígito, adiciona 55 se necessário
    tel = ''.join(filter(str.isdigit, str(telefone)))
    if not tel.startswith('55'):
        tel = '55' + tel

    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type':  'application/json',
    }
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type':    'individual',
        'to':                tel,
        'type':              'text',
        'text':              {'preview_url': False, 'body': mensagem},
    }
    try:
        resp = _req.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and data.get('messages'):
            return True, data['messages'][0].get('id', 'ok')
        erro = data.get('error', {}).get('message', resp.text[:200])
        return False, erro
    except Exception as e:
        return False, str(e)


def testar_whatsapp_api():
    """Testa a conexão com a API do WhatsApp (sem enviar mensagem)."""
    import requests as _req
    phone_id     = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
    business_id  = os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '')
    access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')

    if not phone_id or not access_token:
        return False, 'Credenciais não configuradas'

    url = f"https://graph.facebook.com/v19.0/{phone_id}"
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        resp = _req.get(url, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code == 200:
            nome = data.get('display_phone_number', phone_id)
            return True, f"Conectado — número: {nome} | Business ID: {business_id}"
        return False, data.get('error', {}).get('message', resp.text[:200])
    except Exception as e:
        return False, str(e)


def enviar_email_reset(destinatario, link_reset, nome_painel='PainelGest'):
    """Envia e-mail de redefinição de senha."""
    corpo = f"""Olá!

Recebemos um pedido de redefinição de senha para sua conta no {nome_painel}.

Clique no link abaixo para criar uma nova senha (válido por 2 horas):
{link_reset}

Se você não solicitou isso, ignore este e-mail.

Equipe {nome_painel}"""
    ok, err = enviar_email_comprovante(destinatario, f'Redefinir senha — {nome_painel}', corpo)
    return ok, err


def enviar_email_autorizacao_acesso(destinatario, gestor_nome, super_nome, link_autorizar, link_negar):
    """Envia e-mail pedindo autorização do gestor para acesso do Super Admin."""
    corpo = f"""Olá, {gestor_nome}!

O administrador "{super_nome}" solicitou acesso temporário (30 minutos) ao seu painel PainelGest para suporte técnico.

✅ AUTORIZAR acesso:
{link_autorizar}

❌ NEGAR acesso:
{link_negar}

Este link expira em 1 hora. Se você não reconhece esta solicitação, ignore este e-mail.

PainelGest — Sistema de Segurança"""
    ok, err = enviar_email_comprovante(destinatario, 'Autorização de acesso ao seu painel — PainelGest', corpo)
    return ok, err


def gerar_pix_payload(chave, nome_beneficiario, cidade, valor, txid='PAINELGEST'):
    """Gera payload PIX estático (EMVCo) para QR Code."""
    def crc16(data):
        crc = 0xFFFF
        for b in data.encode('utf-8'):
            crc ^= b << 8
            for _ in range(8):
                crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
        return format(crc & 0xFFFF, '04X')

    def tlv(tag, val):
        return f"{tag}{len(val):02d}{val}"

    chave_pix     = tlv('01', chave)
    merchant_acc  = tlv('00', 'BR.GOV.BCB.PIX') + chave_pix
    valor_str     = f"{valor:.2f}"
    nome_b        = nome_beneficiario[:25]
    cidade_b      = cidade[:15]

    payload  = '000201'                          # Payload Format Indicator
    payload += tlv('26', merchant_acc)           # Merchant Account
    payload += '52040000'                        # MCC
    payload += '5303986'                         # Currency BRL
    payload += tlv('54', valor_str)              # Transaction Amount
    payload += '5802BR'                          # Country
    payload += tlv('59', nome_b)                 # Merchant Name
    payload += tlv('60', cidade_b)               # Merchant City
    payload += tlv('62', tlv('05', txid[:25]))   # Additional Data
    payload += '6304'                            # CRC placeholder
    payload += crc16(payload)
    return payload


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — ACESSO TEMPORÁRIO SUPER ADMIN (Feature 1)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/super/gestores/<int:gid>/solicitar-acesso', methods=['POST'])
@requer_super
def super_solicitar_acesso(gid):
    gestor = Administrador.query.get_or_404(gid)
    if not gestor.email:
        flash('Este gestor não tem e-mail cadastrado. Impossível solicitar autorização.', 'danger')
        return redirect(url_for('super_gestores'))

    # Invalida tokens anteriores não usados
    AcessoTemporario.query.filter_by(gestor_id=gid, usado=False).update({'usado': True})
    db.session.commit()

    acesso = AcessoTemporario(
        super_admin=session['super_admin'],
        gestor_id=gid,
        ip=request.remote_addr
    )
    db.session.add(acesso)
    db.session.commit()

    link_autorizar = url_for('super_autorizar_acesso', token=acesso.token, acao='autorizar', _external=True)
    link_negar     = url_for('super_autorizar_acesso', token=acesso.token, acao='negar', _external=True)

    ok, err = enviar_email_autorizacao_acesso(
        gestor.email, gestor.nome_empresa or gestor.username,
        session['super_admin'], link_autorizar, link_negar
    )

    audit = AuditoriaAcesso(
        super_admin=session['super_admin'], gestor_id=gid,
        gestor_nome=gestor.nome_empresa or gestor.username,
        acao='Solicitação de acesso temporário',
        detalhes=f'E-mail enviado para {gestor.email}. Envio: {"OK" if ok else err}',
        ip=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()

    if ok:
        flash(f'E-mail de autorização enviado para {gestor.email}. Aguarde o gestor autorizar.', 'success')
    else:
        flash(f'Falha ao enviar e-mail: {err}. Configure SMTP_USER e SMTP_PASS no .env.', 'warning')

    return redirect(url_for('super_gestores'))


@app.route('/super/autorizar/<token>/<acao>')
def super_autorizar_acesso(token, acao):
    """Página pública — gestor clica no link do e-mail para autorizar ou negar."""
    acesso = AcessoTemporario.query.filter_by(token=token).first_or_404()
    if acesso.expirado:
        return render_template('super_autorizar.html', resultado='expirado')
    if acesso.usado:
        return render_template('super_autorizar.html', resultado='ja_usado')

    if acao == 'autorizar':
        acesso.autorizado = True
        resultado = 'autorizado'
        acao_texto = 'Acesso AUTORIZADO pelo gestor'
    else:
        acesso.autorizado = False
        acesso.usado = True
        resultado = 'negado'
        acao_texto = 'Acesso NEGADO pelo gestor'

    audit = AuditoriaAcesso(
        acesso_id=acesso.id,
        super_admin=acesso.super_admin,
        gestor_id=acesso.gestor_id,
        gestor_nome=acesso.gestor.nome_empresa or acesso.gestor.username,
        acao=acao_texto, ip=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()

    return render_template('super_autorizar.html', resultado=resultado,
                           gestor_nome=acesso.gestor.nome_empresa or acesso.gestor.username,
                           super_nome=acesso.super_admin)


@app.route('/super/entrar-como/<token>')
@requer_super
def super_entrar_como(token):
    """Super Admin entra no painel do gestor com token autorizado."""
    acesso = AcessoTemporario.query.filter_by(token=token).first_or_404()
    if not acesso.valido:
        flash('Token inválido, expirado ou não autorizado pelo gestor.', 'danger')
        return redirect(url_for('super_gestores'))

    acesso.expira_em = datetime.utcnow() + timedelta(minutes=30)
    db.session.commit()

    session['super_acesso_token']   = token
    session['super_acesso_expira']  = acesso.expira_em.isoformat()
    session['administrador']        = acesso.gestor.email or acesso.gestor.username

    audit = AuditoriaAcesso(
        acesso_id=acesso.id,
        super_admin=acesso.super_admin, gestor_id=acesso.gestor_id,
        gestor_nome=acesso.gestor.nome_empresa or acesso.gestor.username,
        acao='Sessão de acesso temporário INICIADA (30 min)',
        ip=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()

    flash(f'Acesso temporário ao painel de "{acesso.gestor.nome_empresa or acesso.gestor.username}" — expira em 30 minutos.', 'info')
    return redirect(url_for('dashboard'))


@app.route('/super/encerrar-acesso')
@requer_super
def super_encerrar_acesso():
    """Encerra o acesso temporário e volta para o super admin."""
    token = session.pop('super_acesso_token', None)
    session.pop('super_acesso_expira', None)
    session.pop('administrador', None)

    if token:
        acesso = AcessoTemporario.query.filter_by(token=token).first()
        if acesso:
            acesso.usado = True
            audit = AuditoriaAcesso(
                acesso_id=acesso.id,
                super_admin=acesso.super_admin, gestor_id=acesso.gestor_id,
                gestor_nome=acesso.gestor.nome_empresa or acesso.gestor.username,
                acao='Sessão de acesso temporário ENCERRADA manualmente',
                ip=request.remote_addr
            )
            db.session.add(audit)
            db.session.commit()

    flash('Acesso temporário encerrado.', 'success')
    return redirect(url_for('super_gestores'))


@app.route('/super/auditoria')
@requer_super
def super_auditoria():
    logs = AuditoriaAcesso.query.order_by(AuditoriaAcesso.criado_em.desc()).limit(200).all()
    return render_template('super_auditoria.html', logs=logs)


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — FINANGLASS (Analytics do app móvel)
# ══════════════════════════════════════════════════════════════════════════════

_finanglass_cache: dict = {'dados': None, 'atualizado_em': None}
_FINANGLASS_TTL = 300  # 5 minutos


def _buscar_metricas_finanglass():
    """Busca métricas do FinanGlass via Supabase REST API com cache de 5 min."""
    agora = datetime.utcnow()
    if (
        _finanglass_cache['dados'] is not None
        and _finanglass_cache['atualizado_em'] is not None
        and (agora - _finanglass_cache['atualizado_em']).total_seconds() < _FINANGLASS_TTL
    ):
        return _finanglass_cache['dados']

    supabase_url = os.environ.get('FINANGLASS_SUPABASE_URL', '')
    service_key  = os.environ.get('FINANGLASS_SERVICE_ROLE_KEY', '')

    if not supabase_url or not service_key:
        return {'erro': 'Credenciais do Supabase não configuradas.', 'resumo': [], 'ativos': []}

    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json',
    }

    dados = {'resumo': [], 'ativos': [], 'erro': None}

    try:
        import urllib.request, json as _json
        # Resumo por tipo
        req_resumo = urllib.request.Request(
            f'{supabase_url}/rest/v1/resumo_metricas?select=*',
            headers=headers,
        )
        with urllib.request.urlopen(req_resumo, timeout=8) as resp:
            dados['resumo'] = _json.loads(resp.read().decode())

        # Usuários ativos diários
        req_ativos = urllib.request.Request(
            f'{supabase_url}/rest/v1/usuarios_ativos_diarios?select=*&limit=30',
            headers=headers,
        )
        with urllib.request.urlopen(req_ativos, timeout=8) as resp:
            dados['ativos'] = _json.loads(resp.read().decode())

    except Exception as exc:
        dados['erro'] = str(exc)

    _finanglass_cache['dados'] = dados
    _finanglass_cache['atualizado_em'] = datetime.utcnow()
    return dados


@app.route('/super/suporte')
@requer_super
def super_suporte():
    import requests as _req, json as _json
    supabase_url = os.environ.get('FINANGLASS_SUPABASE_URL', '')
    service_key  = os.environ.get('FINANGLASS_SERVICE_ROLE_KEY', '')
    tickets = []
    erro = None

    if supabase_url and service_key:
        try:
            headers = {
                'apikey': service_key,
                'Authorization': f'Bearer {service_key}',
                'Content-Type': 'application/json',
            }
            r = _req.get(
                f'{supabase_url}/rest/v1/suporte_tickets'
                '?select=id,email,mensagem,status,resposta,respondido_em,criado_em'
                '&order=criado_em.desc&limit=200',
                headers=headers,
                timeout=8,
            )
            if r.ok:
                tickets = r.json()
            else:
                erro = f'Supabase retornou {r.status_code}'
        except Exception as exc:
            erro = str(exc)
    else:
        erro = 'Credenciais Supabase não configuradas (FINANGLASS_SUPABASE_URL / FINANGLASS_SERVICE_ROLE_KEY).'

    abertos    = sum(1 for t in tickets if t.get('status') == 'aberto')
    respondidos = sum(1 for t in tickets if t.get('status') == 'respondido')
    return render_template(
        'super_suporte.html',
        tickets=tickets,
        abertos=abertos,
        respondidos=respondidos,
        total=len(tickets),
        erro=erro,
    )


@app.route('/super/suporte/<int:ticket_id>/responder', methods=['POST'])
@requer_super
def super_suporte_responder(ticket_id):
    import requests as _req
    resposta   = request.form.get('resposta', '').strip()
    novo_status = request.form.get('status', 'respondido')

    if not resposta:
        flash('A resposta não pode ser vazia.', 'danger')
        return redirect(url_for('super_suporte'))

    supabase_url = os.environ.get('FINANGLASS_SUPABASE_URL', '')
    service_key  = os.environ.get('FINANGLASS_SERVICE_ROLE_KEY', '')

    if not supabase_url or not service_key:
        flash('Credenciais Supabase não configuradas.', 'danger')
        return redirect(url_for('super_suporte'))

    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
    }
    import json as _json, datetime as _dt2
    payload = {
        'resposta': resposta,
        'status': novo_status,
        'respondido_em': _dt2.datetime.utcnow().isoformat() + 'Z',
    }
    try:
        r = _req.patch(
            f'{supabase_url}/rest/v1/suporte_tickets?id=eq.{ticket_id}',
            headers=headers,
            data=_json.dumps(payload),
            timeout=8,
        )
        if r.ok:
            flash('Resposta enviada com sucesso.', 'success')
        else:
            flash(f'Erro ao responder: {r.status_code} — {r.text}', 'danger')
    except Exception as exc:
        flash(f'Erro de conexão: {exc}', 'danger')

    return redirect(url_for('super_suporte'))


@app.route('/super/finanglass/usuarios')
@requer_super
def super_finanglass_usuarios():
    import requests as _req
    supabase_url = os.environ.get('FINANGLASS_SUPABASE_URL', '')
    service_key  = os.environ.get('FINANGLASS_SERVICE_ROLE_KEY', '')
    usuarios = []
    planos   = {}
    erro     = None

    if supabase_url and service_key:
        headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json',
        }
        try:
            # Usuários via Auth Admin API
            r = _req.get(
                f'{supabase_url}/auth/v1/admin/users?per_page=1000',
                headers=headers,
                timeout=10,
            )
            if r.ok:
                usuarios = r.json().get('users', [])
            else:
                erro = f'Auth API retornou {r.status_code}: {r.text[:200]}'

            # Planos dos usuários
            r2 = _req.get(
                f'{supabase_url}/rest/v1/user_plans'
                '?select=user_id,plano,status,valido_ate,atualizado_em',
                headers=headers,
                timeout=8,
            )
            if r2.ok:
                for p in r2.json():
                    planos[p['user_id']] = p

        except Exception as exc:
            erro = str(exc)
    else:
        erro = 'Credenciais não configuradas (FINANGLASS_SUPABASE_URL / FINANGLASS_SERVICE_ROLE_KEY).'

    return render_template(
        'super_finanglass_usuarios.html',
        usuarios=usuarios,
        planos=planos,
        total=len(usuarios),
        erro=erro,
    )


@app.route('/super/finanglass')
@requer_super
def super_finanglass():
    metricas = _buscar_metricas_finanglass()
    atualizado_em = (
        _finanglass_cache['atualizado_em'].strftime('%d/%m/%Y %H:%M:%S UTC')
        if _finanglass_cache['atualizado_em'] else '—'
    )
    return render_template(
        'super_finanglass.html',
        metricas=metricas,
        atualizado_em=atualizado_em,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — ESQUECI SENHA (Feature 2)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        admin = Administrador.query.filter(db.func.lower(Administrador.email) == email).first()
        if admin and admin.email:
            TokenResetSenha.query.filter_by(painel='gestor', email=email, usado=False).update({'usado': True})
            db.session.commit()
            tok = TokenResetSenha('gestor', email)
            db.session.add(tok)
            db.session.commit()
            link = url_for('resetar_senha', token=tok.token, _external=True)
            enviar_email_reset(email, link, 'PainelGest Gestor')
        flash('Se esse e-mail estiver cadastrado, você receberá o link de redefinição.', 'info')
        return redirect(url_for('login'))
    return render_template('esqueci_senha.html', painel='gestor', volta=url_for('login'))


@app.route('/resetar-senha/<token>', methods=['GET', 'POST'])
def resetar_senha(token):
    tok = TokenResetSenha.query.filter_by(token=token, painel='gestor').first_or_404()
    if not tok.valido:
        flash('Link expirado ou já utilizado.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        nova = request.form.get('senha', '')
        conf = request.form.get('confirm', '')
        if len(nova) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
        elif nova != conf:
            flash('As senhas não coincidem.', 'danger')
        else:
            admin = Administrador.query.filter(db.func.lower(Administrador.email) == tok.email).first()
            if admin:
                admin.password = generate_password_hash(nova)
                tok.usado = True
                db.session.commit()
                flash('Senha redefinida com sucesso! Faça login.', 'success')
                return redirect(url_for('login'))
    return render_template('resetar_senha.html', token=token)


@app.route('/dono/esqueci-senha', methods=['GET', 'POST'])
def dono_esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        dono = DonoDaEmpresa.query.filter(db.func.lower(DonoDaEmpresa.email) == email).first()
        if dono and dono.email:
            TokenResetSenha.query.filter_by(painel='dono', email=email, usado=False).update({'usado': True})
            db.session.commit()
            tok = TokenResetSenha('dono', email)
            db.session.add(tok)
            db.session.commit()
            link = url_for('dono_resetar_senha', token=tok.token, _external=True)
            enviar_email_reset(email, link, 'Painel do Dono')
        flash('Se esse e-mail estiver cadastrado, você receberá o link de redefinição.', 'info')
        return redirect(url_for('dono_login'))
    return render_template('esqueci_senha.html', painel='dono', volta=url_for('dono_login'))


@app.route('/dono/resetar-senha/<token>', methods=['GET', 'POST'])
def dono_resetar_senha(token):
    tok = TokenResetSenha.query.filter_by(token=token, painel='dono').first_or_404()
    if not tok.valido:
        flash('Link expirado ou já utilizado.', 'danger')
        return redirect(url_for('dono_login'))
    if request.method == 'POST':
        nova = request.form.get('senha', '')
        conf = request.form.get('confirm', '')
        if len(nova) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
        elif nova != conf:
            flash('As senhas não coincidem.', 'danger')
        else:
            dono = DonoDaEmpresa.query.filter(db.func.lower(DonoDaEmpresa.email) == tok.email).first()
            if dono:
                dono.senha_hash = generate_password_hash(nova)
                tok.usado = True
                db.session.commit()
                flash('Senha redefinida! Faça login.', 'success')
                return redirect(url_for('dono_login'))
    return render_template('resetar_senha.html', token=token, volta=url_for('dono_login'))


@app.route('/restaurante/esqueci-senha', methods=['GET', 'POST'])
def restaurante_esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        rest = Restaurante.query.filter(db.func.lower(Restaurante.username) == email).first()
        if not rest:
            rest = Restaurante.query.filter(db.func.lower(Restaurante.username) == email.split('@')[0]).first()
        if rest:
            TokenResetSenha.query.filter_by(painel='restaurante', email=email, usado=False).update({'usado': True})
            db.session.commit()
            tok = TokenResetSenha('restaurante', rest.username)
            db.session.add(tok)
            db.session.commit()
            link = url_for('restaurante_resetar_senha', token=tok.token, _external=True)
            enviar_email_reset(email, link, 'Painel do Restaurante')
        flash('Se esse login estiver cadastrado, você receberá o link de redefinição.', 'info')
        return redirect(url_for('restaurante_login'))
    return render_template('esqueci_senha.html', painel='restaurante', volta=url_for('restaurante_login'))


@app.route('/restaurante/resetar-senha/<token>', methods=['GET', 'POST'])
def restaurante_resetar_senha(token):
    tok = TokenResetSenha.query.filter_by(token=token, painel='restaurante').first_or_404()
    if not tok.valido:
        flash('Link expirado ou já utilizado.', 'danger')
        return redirect(url_for('restaurante_login'))
    if request.method == 'POST':
        nova = request.form.get('senha', '')
        conf = request.form.get('confirm', '')
        if len(nova) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
        elif nova != conf:
            flash('As senhas não coincidem.', 'danger')
        else:
            rest = Restaurante.query.filter_by(username=tok.email).first()
            if rest:
                rest.password = generate_password_hash(nova)
                tok.usado = True
                db.session.commit()
                flash('Senha redefinida! Faça login.', 'success')
                return redirect(url_for('restaurante_login'))
    return render_template('resetar_senha.html', token=token, volta=url_for('restaurante_login'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — MESAS DO RESTAURANTE (Feature 3)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/restaurante/mesas')
@requer_restaurante
def restaurante_mesas():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    mesas = Mesa.query.filter_by(restaurante_id=rest.id).order_by(Mesa.numero).all()
    return render_template('restaurante_mesas.html', restaurante=rest, mesas=mesas)


@app.route('/restaurante/mesas/salvar', methods=['POST'])
@requer_restaurante
def restaurante_mesas_salvar():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    dados = request.get_json()
    if not dados:
        return jsonify({'ok': False, 'erro': 'Dados inválidos'}), 400

    # Remove mesas antigas e recria
    Mesa.query.filter_by(restaurante_id=rest.id).delete()
    for m in dados.get('mesas', []):
        numero = int(m.get('numero', 0))
        if numero < 1 or numero > 50:
            continue
        mesa = Mesa(
            restaurante_id=rest.id,
            numero=numero,
            nome=m.get('nome', '').strip() or None,
            capacidade=int(m.get('capacidade', 4))
        )
        db.session.add(mesa)
    db.session.commit()
    return jsonify({'ok': True, 'total': Mesa.query.filter_by(restaurante_id=rest.id).count()})


@app.route('/restaurante/mesas/status/<int:mid>', methods=['POST'])
@requer_restaurante
def restaurante_mesa_status(mid):
    mesa = Mesa.query.get_or_404(mid)
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if mesa.restaurante_id != rest.id:
        return jsonify({'ok': False}), 403
    mesa.status = request.json.get('status', 'livre')
    db.session.commit()
    return jsonify({'ok': True})


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — ATENDIMENTO INTELIGENTE WHATSAPP (Feature 4)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/restaurante/atendimento')
@requer_restaurante
def restaurante_atendimento():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    mesas = Mesa.query.filter_by(restaurante_id=rest.id, ativa=True).order_by(Mesa.numero).all()
    presentes = ClientePresente.query.filter_by(
        restaurante_id=rest.id, saiu=False
    ).order_by(ClientePresente.entrada_em.desc()).all()
    return render_template('restaurante_atendimento.html',
                           restaurante=rest, mesas=mesas, presentes=presentes)


@app.route('/restaurante/atendimento/registrar', methods=['POST'])
@requer_restaurante
def restaurante_atendimento_registrar():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    telefone = ''.join(filter(str.isdigit, request.form.get('telefone', '')))
    nome     = request.form.get('nome', '').strip()
    mesa_id  = request.form.get('mesa_id') or None
    if not telefone:
        flash('Informe o telefone do cliente.', 'danger')
        return redirect(url_for('restaurante_atendimento'))

    # Verifica se já está presente
    existente = ClientePresente.query.filter_by(
        restaurante_id=rest.id, telefone=telefone, saiu=False
    ).first()
    if existente:
        flash(f'Cliente com telefone {telefone} já está registrado.', 'warning')
        return redirect(url_for('restaurante_atendimento'))

    cliente = ClientePresente(
        restaurante_id=rest.id,
        mesa_id=int(mesa_id) if mesa_id else None,
        telefone=telefone,
        nome=nome or None
    )
    db.session.add(cliente)

    # Atualiza status da mesa
    if mesa_id:
        mesa = Mesa.query.get(int(mesa_id))
        if mesa:
            mesa.status = 'ocupada'

    db.session.commit()

    # Monta mensagem de boas-vindas
    cardapio_link = url_for('cardapio_publico', username=rest.username, _external=True) \
                   if 'cardapio_publico' in app.view_functions \
                   else f"http://localhost:5002/cardapio/{rest.username}"
    mensagem = (
        f"Olá! 👋 Bem-vindo(a) ao *{rest.nome}*!\n\n"
        f"📱 Acesse nosso cardápio digital:\n{cardapio_link}\n\n"
        f"💬 Responda com:\n"
        f"*1* — Fazer pedido (informe o número do produto)\n"
        f"*2* — Fechar conta\n"
        f"*3* — Chamar garçom\n\n"
        f"_Bom apetite! 🍽️_"
    )

    # Tenta envio via API oficial; fallback para link wa.me
    ok, resultado = enviar_whatsapp(telefone, mensagem)
    cliente.whatsapp_enviado = ok
    db.session.commit()

    import urllib.parse
    tel_wa  = f"55{telefone}"
    wa_link = f"https://wa.me/{tel_wa}?text={urllib.parse.quote(mensagem)}"

    if ok:
        flash(
            f'✅ WhatsApp enviado automaticamente via API para {telefone}! '
            f'<small style="opacity:.7">(ID: {resultado})</small>',
            'success'
        )
    else:
        flash(
            f'Cliente registrado. WhatsApp API indisponível ({resultado}). '
            f'<a href="{wa_link}" target="_blank" class="alert-link">Clique para enviar manualmente</a>',
            'warning'
        )
    return redirect(url_for('restaurante_atendimento'))


@app.route('/restaurante/atendimento/saida/<int:cid>', methods=['POST'])
@requer_restaurante
def restaurante_cliente_saida(cid):
    cliente = ClientePresente.query.get_or_404(cid)
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if cliente.restaurante_id != rest.id:
        return jsonify({'ok': False}), 403
    cliente.saiu    = True
    cliente.saiu_em = datetime.utcnow()
    if cliente.mesa_id:
        mesa = Mesa.query.get(cliente.mesa_id)
        if mesa:
            mesa.status = 'livre'
    db.session.commit()
    return jsonify({'ok': True})


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — CONTA / PAGAMENTO INTELIGENTE (Feature 5)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/restaurante/conta')
@requer_restaurante
def restaurante_conta_lista():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    contas = ContaMesa.query.filter_by(restaurante_id=rest.id, status='aberta')\
                            .order_by(ContaMesa.criado_em.desc()).all()
    mesas  = Mesa.query.filter_by(restaurante_id=rest.id, ativa=True).order_by(Mesa.numero).all()
    return render_template('restaurante_conta.html', restaurante=rest, contas=contas, mesas=mesas)


@app.route('/restaurante/conta/abrir', methods=['POST'])
@requer_restaurante
def restaurante_conta_abrir():
    rest    = Restaurante.query.filter_by(username=session['restaurante']).first()
    mesa_id = request.form.get('mesa_id') or None
    conta = ContaMesa(restaurante_id=rest.id, mesa_id=int(mesa_id) if mesa_id else None)
    db.session.add(conta)
    if mesa_id:
        mesa = Mesa.query.get(int(mesa_id))
        if mesa:
            mesa.status = 'ocupada'
    db.session.commit()
    return redirect(url_for('restaurante_conta_detalhe', cid=conta.id))


@app.route('/restaurante/conta/<int:cid>')
@requer_restaurante
def restaurante_conta_detalhe(cid):
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    conta = ContaMesa.query.get_or_404(cid)
    if conta.restaurante_id != rest.id:
        return redirect(url_for('restaurante_conta_lista'))
    itens_cardapio = ItemCardapio.query.join(Categoria).filter(
        Categoria.restaurante_id == rest.id, ItemCardapio.disponivel == True
    ).order_by(ItemCardapio.nome).all()
    pix_payload = None
    if conta.total > 0 and rest.chave_pix:
        pix_payload = gerar_pix_payload(
            rest.chave_pix, rest.nome, 'Brasil', conta.total, f'CONTA{conta.id}'
        )
    return render_template('restaurante_conta_detalhe.html',
                           restaurante=rest, conta=conta,
                           itens_cardapio=itens_cardapio, pix_payload=pix_payload)


@app.route('/restaurante/conta/<int:cid>/item', methods=['POST'])
@requer_restaurante
def restaurante_conta_item(cid):
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    conta = ContaMesa.query.get_or_404(cid)
    if conta.restaurante_id != rest.id or conta.status != 'aberta':
        return jsonify({'ok': False}), 400
    item_id  = request.json.get('item_id')
    qtd      = int(request.json.get('qtd', 1))
    item_obj = ItemCardapio.query.get(item_id)
    if not item_obj:
        return jsonify({'ok': False, 'erro': 'Item não encontrado'}), 404
    itens = conta.itens
    # Verifica se o item já está na conta
    for i in itens:
        if i['id'] == item_id:
            i['qtd'] += qtd
            i['subtotal'] = round(i['qtd'] * i['preco'], 2)
            break
    else:
        itens.append({'id': item_id, 'nome': item_obj.nome,
                      'preco': item_obj.preco, 'qtd': qtd,
                      'subtotal': round(item_obj.preco * qtd, 2)})
    conta.itens_json = json.dumps(itens)
    conta.total      = round(sum(i['subtotal'] for i in itens), 2)
    db.session.commit()
    return jsonify({'ok': True, 'total': conta.total, 'itens': itens})


@app.route('/restaurante/conta/<int:cid>/item/<int:idx>/remover', methods=['POST'])
@requer_restaurante
def restaurante_conta_remover_item(cid, idx):
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    conta = ContaMesa.query.get_or_404(cid)
    if conta.restaurante_id != rest.id or conta.status != 'aberta':
        return jsonify({'ok': False}), 400
    itens = conta.itens
    if 0 <= idx < len(itens):
        itens.pop(idx)
    conta.itens_json = json.dumps(itens)
    conta.total      = round(sum(i['subtotal'] for i in itens), 2)
    db.session.commit()
    return jsonify({'ok': True, 'total': conta.total})


@app.route('/restaurante/conta/<int:cid>/pagar', methods=['POST'])
@requer_restaurante
def restaurante_conta_pagar(cid):
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    conta = ContaMesa.query.get_or_404(cid)
    if conta.restaurante_id != rest.id:
        return jsonify({'ok': False}), 403
    forma = request.json.get('forma', 'dinheiro')
    conta.forma_pagamento = forma
    conta.status  = 'paga'
    conta.pago_em = datetime.utcnow()
    if conta.mesa_rel:
        conta.mesa_rel.status = 'livre'
    if conta.cliente:
        conta.cliente.saiu    = True
        conta.cliente.saiu_em = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'mensagem': f'Conta paga via {forma}!'})


@app.route('/restaurante/conta/<int:cid>/cancelar', methods=['POST'])
@requer_restaurante
def restaurante_conta_cancelar(cid):
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    conta = ContaMesa.query.get_or_404(cid)
    if conta.restaurante_id != rest.id:
        return jsonify({'ok': False}), 403
    conta.status = 'cancelada'
    if conta.mesa_rel:
        conta.mesa_rel.status = 'livre'
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/restaurante/conta/historico')
@requer_restaurante
def restaurante_conta_historico():
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    contas = ContaMesa.query.filter_by(restaurante_id=rest.id)\
                            .filter(ContaMesa.status.in_(['paga','cancelada']))\
                            .order_by(ContaMesa.pago_em.desc()).limit(100).all()
    return render_template('restaurante_conta_historico.html', restaurante=rest, contas=contas)


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — APP CONFIRMAÇÃO SAÍDA (Feature 6 — Premium)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/restaurante/saida')
def restaurante_saida_app():
    """Página pública para tablet/celular na saída — sem login de gestor."""
    username = request.args.get('r', '')
    rest = Restaurante.query.filter_by(username=username).first()
    if not rest:
        return render_template('restaurante_saida.html', restaurante=None, erro='Restaurante não encontrado.')
    return render_template('restaurante_saida.html', restaurante=rest, conta=None)


@app.route('/restaurante/saida/consultar', methods=['POST'])
def restaurante_saida_consultar():
    """Consulta pelo telefone se o cliente tem conta aberta."""
    username = request.form.get('username', '')
    telefone = ''.join(filter(str.isdigit, request.form.get('telefone', '')))
    rest = Restaurante.query.filter_by(username=username).first()
    if not rest:
        return jsonify({'ok': False, 'erro': 'Restaurante não encontrado'}), 404
    cliente = ClientePresente.query.filter_by(
        restaurante_id=rest.id, telefone=telefone, saiu=False
    ).order_by(ClientePresente.entrada_em.desc()).first()
    if not cliente:
        return jsonify({'ok': False, 'erro': 'Nenhuma conta aberta para este telefone.'})
    conta = ContaMesa.query.filter_by(
        restaurante_id=rest.id, cliente_id=cliente.id, status='aberta'
    ).first()
    resultado = {
        'ok': True,
        'cliente_id': cliente.id,
        'nome': cliente.nome or f'Cliente {telefone[-4:]}',
        'entrada': cliente.entrada_em.strftime('%H:%M'),
        'conta_id': conta.id if conta else None,
        'total': conta.total if conta else 0,
        'total_fmt': conta.total_fmt if conta else 'R$ 0,00',
        'itens': conta.itens if conta else [],
    }
    return jsonify(resultado)


@app.route('/restaurante/saida/confirmar', methods=['POST'])
def restaurante_saida_confirmar():
    """Confirma pagamento na saída."""
    cid   = request.json.get('conta_id')
    forma = request.json.get('forma', 'dinheiro')
    conta = ContaMesa.query.get(cid) if cid else None
    if not conta or conta.status != 'aberta':
        return jsonify({'ok': False, 'erro': 'Conta não encontrada ou já paga.'})
    conta.forma_pagamento = forma
    conta.status  = 'paga'
    conta.pago_em = datetime.utcnow()
    if conta.mesa_rel:
        conta.mesa_rel.status = 'livre'
    if conta.cliente:
        conta.cliente.saiu    = True
        conta.cliente.saiu_em = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'mensagem': 'Pagamento confirmado! Boa sorte! 👋'})


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — WHATSAPP BUSINESS API (Meta Cloud API)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/super/whatsapp/testar')
@requer_super
def super_whatsapp_testar():
    """Super Admin: testa conexão com a API do WhatsApp Business."""
    ok, msg = testar_whatsapp_api()
    return jsonify({
        'ok': ok,
        'mensagem': msg,
        'phone_number_id':      os.environ.get('WHATSAPP_PHONE_NUMBER_ID', ''),
        'business_account_id':  os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', ''),
        'token_configurado':    bool(os.environ.get('WHATSAPP_ACCESS_TOKEN')),
    })


@app.route('/restaurante/whatsapp/testar')
@requer_restaurante
def restaurante_whatsapp_testar():
    """Restaurante: testa conexão com WhatsApp e exibe status."""
    ok, msg = testar_whatsapp_api()
    return jsonify({'ok': ok, 'mensagem': msg})


@app.route('/restaurante/whatsapp/enviar-manual', methods=['POST'])
@requer_restaurante
def restaurante_whatsapp_enviar_manual():
    """Envia mensagem WhatsApp manualmente para um telefone."""
    rest     = Restaurante.query.filter_by(username=session['restaurante']).first()
    telefone = ''.join(filter(str.isdigit, request.json.get('telefone', '')))
    mensagem = request.json.get('mensagem', '').strip()
    if not telefone or not mensagem:
        return jsonify({'ok': False, 'erro': 'Telefone e mensagem são obrigatórios'}), 400

    ok, resultado = enviar_whatsapp(telefone, mensagem)
    return jsonify({'ok': ok, 'resultado': resultado})


@app.route('/whatsapp/webhook', methods=['GET'])
def whatsapp_webhook_verify():
    """Verificação do webhook Meta (GET) — necessário para configurar o webhook no painel Meta."""
    verify_token = os.environ.get('WHATSAPP_VERIFY_TOKEN', 'painelgest_webhook_2026')
    mode      = request.args.get('hub.mode')
    token     = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == verify_token:
        return challenge, 200
    return 'Forbidden', 403


@app.route('/whatsapp/webhook', methods=['POST'])
def whatsapp_webhook_receive():
    """
    Recebe mensagens do WhatsApp (POST) e processa o bot de atendimento.
    Bot: 1 = fazer pedido, 2 = fechar conta, 3 = chamar garçom
    """
    data = request.get_json(silent=True) or {}
    try:
        entry   = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        value   = changes.get('value', {})
        msgs    = value.get('messages', [])

        for msg in msgs:
            if msg.get('type') != 'text':
                continue
            telefone = msg.get('from', '')     # ex: "5511999998888"
            texto    = msg.get('text', {}).get('body', '').strip()

            # Busca cliente presente pelo telefone (remove 55 do início)
            tel_local = telefone.lstrip('55') if telefone.startswith('55') else telefone
            cliente = ClientePresente.query.filter(
                ClientePresente.telefone.in_([telefone, tel_local]),
                ClientePresente.saiu == False
            ).order_by(ClientePresente.entrada_em.desc()).first()

            if not cliente:
                continue

            rest  = Restaurante.query.get(cliente.restaurante_id)
            conta = ContaMesa.query.filter_by(
                restaurante_id=cliente.restaurante_id,
                cliente_id=cliente.id,
                status='aberta'
            ).first()

            resposta = None

            if texto == '1':
                # Faz pedido — lista os produtos disponíveis
                cats = Categoria.query.filter_by(restaurante_id=rest.id, ativo=True).all()
                linhas = ["🍽️ *Cardápio — escolha o número do produto:*\n"]
                idx = 1
                for cat in cats:
                    itens = ItemCardapio.query.filter_by(categoria_id=cat.id, disponivel=True).all()
                    if itens:
                        linhas.append(f"*{cat.nome}*")
                        for item in itens:
                            linhas.append(f"  {idx}. {item.nome} — R$ {item.preco:.2f}".replace('.', ','))
                            idx += 1
                linhas.append("\nDigite o *número* do produto para pedir.")
                resposta = '\n'.join(linhas)

            elif texto == '2':
                # Fechar conta
                if conta and conta.total > 0:
                    resposta = (
                        f"💳 *Sua conta:*\n"
                        + '\n'.join([f"  {i['qtd']}x {i['nome']} — R$ {i['subtotal']:.2f}".replace('.', ',')
                                     for i in conta.itens])
                        + f"\n\n*Total: R$ {conta.total:.2f}*".replace('.', ',')
                        + "\n\nUm garçom irá até você para finalizar o pagamento. ✅"
                    )
                else:
                    resposta = "Não encontrei uma conta aberta. Fale com o garçom. 😊"

            elif texto == '3':
                # Chamar garçom
                mesa_txt = f" (Mesa {cliente.mesa.label})" if cliente.mesa else ""
                resposta = f"🔔 Garçom chamado{mesa_txt}! Estaremos com você em instantes."

            elif texto.isdigit() and int(texto) > 3:
                # Tenta adicionar item à conta pelo número do cardápio
                cats = Categoria.query.filter_by(restaurante_id=rest.id, ativo=True).all()
                idx = 1
                item_alvo = None
                for cat in cats:
                    itens = ItemCardapio.query.filter_by(categoria_id=cat.id, disponivel=True).all()
                    for item in itens:
                        if idx == int(texto):
                            item_alvo = item
                            break
                        idx += 1
                    if item_alvo:
                        break

                if item_alvo:
                    if not conta:
                        conta = ContaMesa(
                            restaurante_id=rest.id,
                            mesa_id=cliente.mesa_id,
                            cliente_id=cliente.id
                        )
                        db.session.add(conta)
                        db.session.flush()
                    itens_lista = conta.itens
                    encontrado = False
                    for i in itens_lista:
                        if i['id'] == item_alvo.id:
                            i['qtd'] += 1
                            i['subtotal'] = round(i['qtd'] * i['preco'], 2)
                            encontrado = True
                            break
                    if not encontrado:
                        itens_lista.append({
                            'id': item_alvo.id, 'nome': item_alvo.nome,
                            'preco': item_alvo.preco, 'qtd': 1,
                            'subtotal': item_alvo.preco
                        })
                    import json as _json
                    conta.itens_json = _json.dumps(itens_lista)
                    conta.total = round(sum(i['subtotal'] for i in itens_lista), 2)
                    db.session.commit()
                    resposta = (
                        f"✅ *{item_alvo.nome}* adicionado!\n"
                        f"Subtotal atual: R$ {conta.total:.2f}".replace('.', ',')
                        + "\n\nDigite *2* para fechar a conta ou *3* para chamar o garçom."
                    )
                else:
                    resposta = "Número de produto não encontrado. Digite *1* para ver o cardápio."

            if resposta:
                enviar_whatsapp(telefone, resposta)

    except Exception as e:
        app.logger.error(f"WhatsApp webhook erro: {e}")

    return jsonify({'status': 'ok'}), 200


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
    add_col('restaurante', 'telefone',             'VARCHAR(30)')
    add_col('restaurante', 'endereco',             'VARCHAR(200)')
    add_col('restaurante', 'descricao',            'TEXT')
    add_col('restaurante', 'cor_primaria',         "VARCHAR(10) DEFAULT '#6366f1'")
    add_col('restaurante', 'logo_path',            'VARCHAR(300)')
    add_col('restaurante', 'formas_pagamento_json','TEXT')
    add_col('restaurante', 'instagram',            'VARCHAR(100)')
    add_col('restaurante', 'facebook',             'VARCHAR(100)')
    add_col('restaurante', 'whatsapp',             'VARCHAR(30)')
    add_col('restaurante', 'token_frota',          'VARCHAR(64)')
    add_col('restaurante', 'frota_url',            'VARCHAR(200)')
    add_col('restaurante', 'lat',                  'FLOAT')
    add_col('restaurante', 'lng',                  'FLOAT')
    add_col('restaurante', 'raio_entrega_km',      'FLOAT DEFAULT 5.0')

    # PostAgendado
    add_col('post_agendado', 'erro',       'TEXT')
    add_col('post_agendado', 'imagem_path','VARCHAR(500)')

    # Código único (4 chars) para Cliente e Restaurante
    add_col('cliente',     'codigo', 'VARCHAR(4)')
    add_col('restaurante', 'codigo', 'VARCHAR(4)')

    # Sessão única por restaurante
    add_col('restaurante', 'session_token', 'VARCHAR(64)')

    # Novas tabelas — criadas automaticamente pelo db.create_all()
    # acesso_temporario, auditoria_acesso, token_reset_senha, mesa, cliente_presente, conta_mesa
    # mensagem_chat

    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# V2.0 — MÓDULOS FUTUROS (estrutura preparada, não implementado)
# ══════════════════════════════════════════════════════════════════════════════
#
# --- ESTOQUE ---
# Modelo: ItemEstoque(id, restaurante_id, nome, quantidade, minimo, unidade)
# Rota: /restaurante/estoque → CRUD; deduzir ao fechar PedidoKanban
#
# --- WHATSAPP AUTOMÁTICO ---
# Integração: Evolution API ou Baileys (Node.js sidecar)
# Webhook: /api/whatsapp/webhook → processar mensagens recebidas
# Envio: notificar cliente ao mudar status do pedido
#
# --- PAINEL CONTADOR COMPLETO ---
# Modelo: Contador(id, admin_id, username, senha_hash, cnpj_escritorio)
# Rotas: /contador/* → read-only a relatórios e notas fiscais
# Export: DRE simplificado em PDF por período
#
# --- PAINEL DONO MULTI-EMPRESA ---
# Modelo: Empresa(id, nome, cnpj, dono_id) + EmpresaAdmin(empresa_id, admin_id)
# Rota: /dono/empresas → alternar entre empresas
# Isolamento: session['empresa_ativa'] filtra todas as queries
#
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES — TROCA DE SENHA + EXCLUSÃO DE PERFIL
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/configuracoes', methods=['GET', 'POST'])
@requer_login
def configuracoes():
    _val  = session['administrador']
    admin = (Administrador.query.filter_by(email=_val).first() or
             Administrador.query.filter_by(username=_val).first())
    if request.method == 'POST':
        acao = request.form.get('acao', '')
        if acao == 'trocar_senha':
            atual = request.form.get('senha_atual', '')
            nova  = request.form.get('senha_nova', '')
            conf  = request.form.get('senha_conf', '')
            if not check_password_hash(admin.password, atual):
                flash('Senha atual incorreta.', 'danger')
            elif len(nova) < 6:
                flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
            elif nova != conf:
                flash('As senhas não coincidem.', 'danger')
            else:
                admin.password = generate_password_hash(nova)
                db.session.commit()
                flash('Senha alterada com sucesso!', 'success')
        elif acao == 'excluir_perfil':
            senha_conf = request.form.get('senha_excluir', '')
            if not check_password_hash(admin.password, senha_conf):
                flash('Senha incorreta. Exclusão cancelada.', 'danger')
            else:
                session.pop('administrador', None)
                db.session.delete(admin)
                db.session.commit()
                flash('Perfil excluído permanentemente.', 'info')
                return redirect(url_for('login'))
    return render_template('configuracoes.html', admin=admin)


@app.route('/restaurante/configuracoes', methods=['GET', 'POST'])
@requer_restaurante
def restaurante_configuracoes():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        acao = request.form.get('acao', '')
        if acao == 'trocar_senha':
            atual = request.form.get('senha_atual', '')
            nova  = request.form.get('senha_nova', '')
            conf  = request.form.get('senha_conf', '')
            if not check_password_hash(rest.password, atual):
                flash('Senha atual incorreta.', 'danger')
            elif len(nova) < 6:
                flash('Nova senha deve ter pelo menos 6 caracteres.', 'danger')
            elif nova != conf:
                flash('As senhas não coincidem.', 'danger')
            else:
                rest.password = generate_password_hash(nova)
                db.session.commit()
                flash('Senha alterada!', 'success')
        elif acao == 'excluir_perfil':
            senha_conf = request.form.get('senha_excluir', '')
            if not check_password_hash(rest.password, senha_conf):
                flash('Senha incorreta.', 'danger')
            else:
                session.pop('restaurante', None)
                session.pop('restaurante_id', None)
                session.pop('restaurante_token', None)
                db.session.delete(rest)
                db.session.commit()
                flash('Perfil do restaurante excluído.', 'info')
                return redirect(url_for('restaurante_login'))
    return render_template('configuracoes.html', admin=rest, painel='restaurante')


@app.route('/dono/configuracoes', methods=['GET', 'POST'])
@requer_dono
def dono_configuracoes():
    dono = DonoDaEmpresa.query.filter(db.func.lower(DonoDaEmpresa.email) == session['dono']).first()
    if request.method == 'POST':
        acao = request.form.get('acao', '')
        if acao == 'trocar_senha':
            atual = request.form.get('senha_atual', '')
            nova  = request.form.get('senha_nova', '')
            conf  = request.form.get('senha_conf', '')
            if not dono.check_senha(atual):
                flash('Senha atual incorreta.', 'danger')
            elif len(nova) < 6:
                flash('Nova senha deve ter pelo menos 6 caracteres.', 'danger')
            elif nova != conf:
                flash('As senhas não coincidem.', 'danger')
            else:
                dono.senha_hash = generate_password_hash(nova)
                db.session.commit()
                flash('Senha alterada!', 'success')
        elif acao == 'excluir_perfil':
            senha_conf = request.form.get('senha_excluir', '')
            if not dono.check_senha(senha_conf):
                flash('Senha incorreta.', 'danger')
            else:
                session.pop('dono', None)
                db.session.delete(dono)
                db.session.commit()
                flash('Perfil excluído.', 'info')
                return redirect(url_for('dono_login'))
    return render_template('configuracoes.html', admin=dono, painel='dono')


# ══════════════════════════════════════════════════════════════════════════════
# CHAT INTERNO
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/chat')
@requer_login
def chat_gestor():
    _val  = session['administrador']
    admin = (Administrador.query.filter_by(email=_val).first() or
             Administrador.query.filter_by(username=_val).first())
    msgs = MensagemChat.query.order_by(MensagemChat.criado_em.desc()).limit(50).all()
    msgs.reverse()
    return render_template('chat.html', msgs=msgs, usuario_nome=admin.username, painel='admin')


@app.route('/chat/enviar', methods=['POST'])
@requer_login
def chat_enviar():
    _val  = session['administrador']
    admin = (Administrador.query.filter_by(email=_val).first() or
             Administrador.query.filter_by(username=_val).first())
    texto = request.json.get('mensagem', '').strip()
    if not texto:
        return jsonify({'ok': False}), 400
    msg = MensagemChat('admin', admin.username, texto)
    db.session.add(msg)
    db.session.commit()
    return jsonify({'ok': True, 'id': msg.id,
                    'criado_em': msg.criado_em.strftime('%H:%M')})


@app.route('/chat/mensagens')
@requer_login
def chat_mensagens():
    desde = request.args.get('desde', 0, type=int)
    msgs = MensagemChat.query.filter(MensagemChat.id > desde)\
                             .order_by(MensagemChat.criado_em).limit(50).all()
    return jsonify([{
        'id': m.id, 'painel': m.painel_origem, 'nome': m.usuario_nome,
        'msg': m.mensagem, 'hora': m.criado_em.strftime('%H:%M')
    } for m in msgs])


@app.route('/restaurante/chat/enviar', methods=['POST'])
@requer_restaurante
def restaurante_chat_enviar():
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    texto = request.json.get('mensagem', '').strip()
    if not texto:
        return jsonify({'ok': False}), 400
    msg = MensagemChat('restaurante', rest.nome, texto, restaurante_id=rest.id)
    db.session.add(msg)
    db.session.commit()
    return jsonify({'ok': True, 'id': msg.id,
                    'criado_em': msg.criado_em.strftime('%H:%M')})


@app.route('/restaurante/chat')
@requer_restaurante
def restaurante_chat():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    msgs = MensagemChat.query.order_by(MensagemChat.criado_em.desc()).limit(50).all()
    msgs.reverse()
    return render_template('chat.html', msgs=msgs, usuario_nome=rest.nome, painel='restaurante')


# ══════════════════════════════════════════════════════════════════════════════
# LINKS DE CADASTRO — botões copiar
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/links')
@requer_login
def links_cadastro():
    from urllib.parse import urlparse
    parsed = urlparse(request.host_url)
    base_h = f"{parsed.scheme}://{parsed.hostname}"
    base   = request.host_url.rstrip('/')
    _val   = session['administrador']
    admin  = (Administrador.query.filter_by(email=_val).first() or
              Administrador.query.filter_by(username=_val).first())
    links = {
        'gestor':      base + url_for('cadastrar'),
        'restaurante': os.getenv('PAINELREST_URL',  base_h + ':5006') + '/cadastrar',
        'motoboy':     os.getenv('APPMOTOBOY_URL',  base_h + ':5003') + '/cadastrar',
        'frota':       os.getenv('PAINELFROTA_URL', base_h + ':5004') + '/cadastrar',
    }
    return render_template('links_cadastro.html', links=links, admin=admin)


@app.route('/super/links')
@requer_super
def super_links_cadastro():
    from urllib.parse import urlparse
    parsed = urlparse(request.host_url)
    base_h = f"{parsed.scheme}://{parsed.hostname}"
    base   = request.host_url.rstrip('/')
    links = {
        'gestor':      base + url_for('cadastrar'),
        'restaurante': os.getenv('PAINELREST_URL',  base_h + ':5006') + '/cadastrar',
        'motoboy':     os.getenv('APPMOTOBOY_URL',  base_h + ':5003') + '/cadastrar',
        'frota':       os.getenv('PAINELFROTA_URL', base_h + ':5004') + '/cadastrar',
    }
    return render_template('links_cadastro.html', links=links, super_admin=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGAMENTO — PRIMEIRO MÊS GRÁTIS + FATURA AUTOMÁTICA
# ══════════════════════════════════════════════════════════════════════════════

def _enviar_fatura_email(admin_email, admin_nome, plano_nome, preco, link_pix=None):
    assunto = f'[PainelGest] Fatura do mês — Plano {plano_nome}'
    pix_info = f'\n\nLink PIX: {link_pix}' if link_pix else ''
    corpo = (
        f'Olá, {admin_nome}!\n\n'
        f'Seu período gratuito encerrou. A fatura do plano {plano_nome} é de R$ {preco:.2f}.'
        f'{pix_info}\n\n'
        f'Em caso de dúvidas, responda este e-mail.\n\nEquipe PainelGest'
    )
    return enviar_email_comprovante(admin_email, assunto, corpo)


def verificar_faturas_automaticas():
    """Scheduler diário: envia fatura no 2º mês após cadastro."""
    with app.app_context():
        hoje = date.today()
        gestores = Administrador.query.filter_by(status='ativo').all()
        for g in gestores:
            if not g.email or not g.criado_em:
                continue
            dias = (hoje - g.criado_em.date()).days
            if dias == 30:
                plano_info = g.info_plano
                _enviar_fatura_email(g.email, g.nome_empresa or g.username,
                                     plano_info['nome'], plano_info['preco'])


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

        if not DonoDaEmpresa.query.filter_by(username='dono').first():
            db.session.add(DonoDaEmpresa('dono', 'dono123', nome='Dono da Empresa'))
            db.session.commit()
            print("Dono criado → dono / dono123")

    scheduler = BackgroundScheduler()
    scheduler.add_job(processar_posts_agendados, 'interval', minutes=5, id='posts_scheduler')
    scheduler.add_job(verificar_faturas_automaticas, 'cron', hour=8, minute=0, id='faturas_scheduler')
    scheduler.start()
    print("Scheduler de posts e faturas iniciado")

    try:
        app.run(host='0.0.0.0', debug=False, port=5002, use_reloader=False)
    finally:
        scheduler.shutdown()
