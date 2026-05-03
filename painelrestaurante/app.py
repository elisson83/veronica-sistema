import os
import io
import json
import math
import secrets
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), encoding='utf-8-sig')

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, jsonify, make_response, send_file)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'painelrest2026super')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///painelrestaurante.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO)

PLANOS = {
    'basico': {
        'nome': 'Básico', 'preco': 79.90, 'cor': 'info', 'icone': 'fa-seedling',
        'descricao': 'Cardápio + Kanban de Pedidos',
        'recursos': ['Cardápio digital', 'Kanban de pedidos', 'Perfil do restaurante'],
    },
    'pro': {
        'nome': 'Pro', 'preco': 149.90, 'cor': 'primary', 'icone': 'fa-rocket',
        'descricao': 'Tudo do Básico + Mesas e Motoboys',
        'recursos': ['Tudo do Básico', 'Gestão de mesas', 'Vagas de motoboys',
                     'CRM de clientes', 'Mapa de entregas'],
    },
    'premium': {
        'nome': 'Premium', 'preco': 299.90, 'cor': 'warning', 'icone': 'fa-crown',
        'descricao': 'Tudo do Pro + App de Saída e Integrações',
        'recursos': ['Tudo do Pro', 'App Saída (tablet)', 'Integração PainelFrota',
                     'Integração AppMotoboy', 'Webhooks WhatsApp'],
    },
}

COLUNAS_KANBAN = [
    {'key': 'novo',      'nome': 'Novos',       'icone': 'fa-bell',          'cor': '#f97316'},
    {'key': 'preparo',   'nome': 'Em Preparo',  'icone': 'fa-fire-burner',   'cor': '#f59e0b'},
    {'key': 'pronto',    'nome': 'Pronto',      'icone': 'fa-check-circle',  'cor': '#22c55e'},
    {'key': 'entrega',   'nome': 'Em Entrega',  'icone': 'fa-motorcycle',    'cor': '#06b6d4'},
    {'key': 'concluido', 'nome': 'Concluído',   'icone': 'fa-flag-checkered','cor': '#64748b'},
]

FORMAS_PAGAMENTO = [
    'Dinheiro', 'Cartão de Débito', 'Cartão de Crédito', 'Pix',
    'Vale Refeição', 'Vale Alimentação', 'iFood Crédito',
]

# ══════════════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════════════

def _gerar_codigo_unico(modelo, campo='codigo'):
    import random, string as _s
    while True:
        c = random.choice(_s.ascii_uppercase) + str(random.randint(100, 999))
        if not modelo.query.filter_by(**{campo: c}).first():
            return c


class Restaurante(db.Model):
    id                    = db.Column(db.Integer, primary_key=True)
    codigo                = db.Column(db.String(4), unique=True, nullable=True)
    nome                  = db.Column(db.String(80), nullable=False)
    username              = db.Column(db.String(80), unique=True, nullable=False)
    password              = db.Column(db.String(120), nullable=False)
    email                 = db.Column(db.String(120), nullable=True)
    plano                 = db.Column(db.String(20), default='basico')
    status                = db.Column(db.String(15), default='ativo')
    data_vencimento       = db.Column(db.DateTime, nullable=True)
    link_pagamento        = db.Column(db.String(200), nullable=True)
    chave_pix             = db.Column(db.String(200), nullable=True)
    telefone              = db.Column(db.String(30), nullable=True)
    endereco              = db.Column(db.String(200), nullable=True)
    descricao             = db.Column(db.Text, nullable=True)
    cor_primaria          = db.Column(db.String(10), default='#f97316')
    logo_path             = db.Column(db.String(300), nullable=True)
    formas_pagamento_json = db.Column(db.Text, nullable=True)
    instagram             = db.Column(db.String(100), nullable=True)
    facebook              = db.Column(db.String(100), nullable=True)
    whatsapp              = db.Column(db.String(30), nullable=True)
    token_frota           = db.Column(db.String(64), nullable=True, unique=True)
    frota_url             = db.Column(db.String(200), nullable=True)
    lat                   = db.Column(db.Float, nullable=True)
    lng                   = db.Column(db.Float, nullable=True)
    raio_entrega_km       = db.Column(db.Float, default=5.0)
    session_token         = db.Column(db.String(64), nullable=True)
    criado_em             = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, nome, username, password, email=None, plano='basico'):
        self.nome = nome
        self.username = username
        self.password = generate_password_hash(password)
        self.email = email
        self.plano = plano
        self.codigo = _gerar_codigo_unico(Restaurante)

    @property
    def formas_pagamento(self):
        try:
            return json.loads(self.formas_pagamento_json or '[]')
        except Exception:
            return []

    @property
    def info_plano(self):
        return PLANOS.get(self.plano, PLANOS['basico'])

    @property
    def is_premium(self):
        return self.plano == 'premium'

    @property
    def is_pro_ou_premium(self):
        return self.plano in ('pro', 'premium')

    @property
    def vencido(self):
        return bool(self.data_vencimento and self.data_vencimento.date() < date.today())


class ConexaoExterna(db.Model):
    """Conexão do restaurante com painéis externos."""
    id             = db.Column(db.Integer, primary_key=True)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    tipo           = db.Column(db.String(30), nullable=False)  # painelgest|painelfrota|appmotoboy|gestor
    url_painel     = db.Column(db.String(300), nullable=True)
    token_conexao  = db.Column(db.String(64), nullable=True)
    descricao      = db.Column(db.String(200), nullable=True)
    solicitante    = db.Column(db.String(100), nullable=True)
    ativa          = db.Column(db.Boolean, default=True)
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)
    restaurante    = db.relationship('Restaurante', backref='conexoes')

    def __init__(self, restaurante_id, tipo, url_painel=None, descricao=None, solicitante=None):
        self.restaurante_id = restaurante_id
        self.tipo = tipo
        self.url_painel = url_painel
        self.descricao = descricao
        self.solicitante = solicitante
        self.token_conexao = secrets.token_hex(16)


class Categoria(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    restaurante    = db.relationship('Restaurante', backref='categorias')
    nome           = db.Column(db.String(80), nullable=False)
    descricao      = db.Column(db.String(200), nullable=True)
    ordem          = db.Column(db.Integer, default=0)
    ativo          = db.Column(db.Boolean, default=True)
    icone          = db.Column(db.String(50), default='fa-utensils')

    def __init__(self, restaurante_id, nome, descricao=None, icone='fa-utensils'):
        self.restaurante_id = restaurante_id
        self.nome = nome
        self.descricao = descricao
        self.icone = icone


class ItemCardapio(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    categoria    = db.relationship('Categoria', backref='itens')
    nome         = db.Column(db.String(120), nullable=False)
    descricao    = db.Column(db.Text, nullable=True)
    preco        = db.Column(db.Float, nullable=False)
    preco_promo  = db.Column(db.Float, nullable=True)
    disponivel   = db.Column(db.Boolean, default=True)
    destaque     = db.Column(db.Boolean, default=False)
    imagem_path  = db.Column(db.String(300), nullable=True)
    criado_em    = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, categoria_id, nome, preco, descricao=None, preco_promo=None):
        self.categoria_id = categoria_id
        self.nome = nome
        self.preco = preco
        self.descricao = descricao
        self.preco_promo = preco_promo

    @property
    def preco_fmt(self):
        return f"R$ {self.preco:.2f}".replace('.', ',')

    @property
    def preco_promo_fmt(self):
        return f"R$ {self.preco_promo:.2f}".replace('.', ',') if self.preco_promo else None


class PedidoKanban(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    restaurante_id  = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    restaurante_rel = db.relationship('Restaurante', backref='pedidos')
    numero          = db.Column(db.Integer, nullable=False, default=1)
    cliente_nome    = db.Column(db.String(80), nullable=True)
    itens_json      = db.Column(db.Text, nullable=True)
    total           = db.Column(db.Float, default=0.0)
    coluna          = db.Column(db.String(20), default='novo')
    origem          = db.Column(db.String(20), default='balcao')
    codigo_ifood    = db.Column(db.String(20), nullable=True)
    forma_pagamento = db.Column(db.String(30), nullable=True)
    observacoes     = db.Column(db.Text, nullable=True)
    criado_em       = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em   = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, restaurante_id, numero, cliente_nome=None, total=0.0,
                 origem='balcao', forma_pagamento=None, observacoes=None, codigo_ifood=None):
        self.restaurante_id = restaurante_id
        self.numero = numero
        self.cliente_nome = cliente_nome
        self.total = total
        self.origem = origem
        self.forma_pagamento = forma_pagamento
        self.observacoes = observacoes
        self.codigo_ifood = codigo_ifood

    @property
    def itens(self):
        try:
            return json.loads(self.itens_json or '[]')
        except Exception:
            return []

    @property
    def total_fmt(self):
        return f"R$ {self.total:.2f}".replace('.', ',')


class Mesa(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    numero         = db.Column(db.Integer, nullable=False)
    nome           = db.Column(db.String(30), nullable=True)
    capacidade     = db.Column(db.Integer, default=4)
    status         = db.Column(db.String(20), default='livre')
    ativa          = db.Column(db.Boolean, default=True)
    restaurante    = db.relationship('Restaurante', backref='mesas')

    def __init__(self, restaurante_id, numero, nome=None, capacidade=4):
        self.restaurante_id = restaurante_id
        self.numero = numero
        self.nome = nome
        self.capacidade = capacidade

    @property
    def label(self):
        return self.nome or f"Mesa {self.numero}"


class ClientePresente(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    restaurante_id   = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    mesa_id          = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=True)
    telefone         = db.Column(db.String(20), nullable=False)
    nome             = db.Column(db.String(80), nullable=True)
    whatsapp_enviado = db.Column(db.Boolean, default=False)
    entrada_em       = db.Column(db.DateTime, default=datetime.utcnow)
    saiu             = db.Column(db.Boolean, default=False)
    saiu_em          = db.Column(db.DateTime, nullable=True)
    restaurante      = db.relationship('Restaurante', backref='clientes_presentes')
    mesa             = db.relationship('Mesa', backref='clientes_presentes')


class ContaMesa(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    restaurante_id  = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    cliente_id      = db.Column(db.Integer, db.ForeignKey('cliente_presente.id'), nullable=True)
    mesa_id         = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=True)
    itens_json      = db.Column(db.Text, default='[]')
    total           = db.Column(db.Float, default=0.0)
    status          = db.Column(db.String(20), default='aberta')
    forma_pagamento = db.Column(db.String(30), nullable=True)
    pix_payload     = db.Column(db.Text, nullable=True)
    criado_em       = db.Column(db.DateTime, default=datetime.utcnow)
    pago_em         = db.Column(db.DateTime, nullable=True)
    restaurante     = db.relationship('Restaurante', backref='contas_mesas')
    cliente         = db.relationship('ClientePresente', backref='contas')
    mesa_rel        = db.relationship('Mesa', backref='contas')

    def __init__(self, restaurante_id, mesa_id=None, cliente_id=None):
        self.restaurante_id = restaurante_id
        self.mesa_id = mesa_id
        self.cliente_id = cliente_id

    @property
    def itens(self):
        try:
            return json.loads(self.itens_json or '[]')
        except Exception:
            return []

    @property
    def total_fmt(self):
        return f"R$ {self.total:.2f}".replace('.', ',')


class CRMCliente(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    restaurante_id   = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    nome_cliente     = db.Column(db.String(100))
    telefone         = db.Column(db.String(20))
    total_pedidos    = db.Column(db.Integer, default=0)
    valor_total      = db.Column(db.Float, default=0.0)
    ticket_medio     = db.Column(db.Float, default=0.0)
    ultimo_pedido    = db.Column(db.DateTime)
    notas            = db.Column(db.Text)
    criado_em        = db.Column(db.DateTime, default=datetime.utcnow)
    restaurante      = db.relationship('Restaurante', backref='clientes_crm')

    @property
    def segmento(self):
        if self.total_pedidos >= 10 or (self.ticket_medio or 0) >= 80:
            return ('VIP', 'warning')
        if self.total_pedidos >= 5:
            return ('Frequente', 'success')
        if self.ultimo_pedido and (datetime.utcnow() - self.ultimo_pedido).days > 30:
            return ('Inativo', 'secondary')
        return ('Regular', 'info')


class VagaPlantao(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    data           = db.Column(db.Date, default=date.today)
    vagas_total    = db.Column(db.Integer, default=2)
    vagas_preench  = db.Column(db.Integer, default=0)
    horario_inicio = db.Column(db.String(5), default='18:00')
    horario_fim    = db.Column(db.String(5), default='23:00')
    observacao     = db.Column(db.String(200))
    status         = db.Column(db.String(20), default='aberta')
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def vagas_livres(self):
        return max(0, self.vagas_total - self.vagas_preench)


class MotoboyParceiro(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    restaurante_id = db.Column(db.Integer, db.ForeignKey('restaurante.id'), nullable=False)
    nome           = db.Column(db.String(100), nullable=False)
    telefone       = db.Column(db.String(20))
    lat            = db.Column(db.Float)
    lng            = db.Column(db.Float)
    ativo          = db.Column(db.Boolean, default=True)
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def distancia_km(lat1, lng1, lat2, lng2):
    if None in (lat1, lng1, lat2, lng2):
        return None
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2)
    return round(R * 2 * math.asin(math.sqrt(a)), 2)


def gerar_pix_payload(chave, nome_beneficiario, cidade, valor, txid='PAINELREST'):
    def crc16(data):
        crc = 0xFFFF
        for b in data.encode('utf-8'):
            crc ^= b << 8
            for _ in range(8):
                crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
        return format(crc & 0xFFFF, '04X')

    def tlv(tag, val):
        return f"{tag}{len(val):02d}{val}"

    chave_pix    = tlv('01', chave)
    merchant_acc = tlv('00', 'BR.GOV.BCB.PIX') + chave_pix
    valor_str    = f"{valor:.2f}"
    payload  = '000201'
    payload += tlv('26', merchant_acc)
    payload += '52040000'
    payload += '5303986'
    payload += tlv('54', valor_str)
    payload += '5802BR'
    payload += tlv('59', nome_beneficiario[:25])
    payload += tlv('60', cidade[:15])
    payload += tlv('62', tlv('05', txid[:25]))
    payload += '6304'
    payload += crc16(payload)
    return payload


def enviar_whatsapp(telefone, mensagem):
    import requests as _req
    phone_id     = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
    access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
    if not phone_id or not access_token:
        return False, 'WhatsApp API não configurada'
    tel = ''.join(filter(str.isdigit, str(telefone)))
    if not tel.startswith('55'):
        tel = '55' + tel
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    payload = {
        'messaging_product': 'whatsapp', 'recipient_type': 'individual',
        'to': tel, 'type': 'text', 'text': {'preview_url': False, 'body': mensagem},
    }
    try:
        resp = _req.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and data.get('messages'):
            return True, data['messages'][0].get('id', 'ok')
        return False, data.get('error', {}).get('message', resp.text[:200])
    except Exception as e:
        return False, str(e)


def gerar_comprovante_pdf(restaurante, motoboy_dados, entregas, periodo_inicio, periodo_fim):
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    pdf = FPDF(format='A4')
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'COMPROVANTE DE PAGAMENTO', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f'Restaurante: {restaurante.nome}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 7, f'Período: {periodo_inicio.strftime("%d/%m/%Y")} a {periodo_fim.strftime("%d/%m/%Y")}',
             new_x='LMARGIN', new_y='NEXT')
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'DADOS DO MOTOBOY', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f'Nome: {motoboy_dados.get("nome", "—")}', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 6, f'Telefone: {motoboy_dados.get("telefone", "—")}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(4)
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
        pdf.cell(60, 6, str(e.get('cliente', ''))[:30], border=1, fill=fill)
        pdf.cell(35, 6, str(e.get('data', '')), border=1, fill=fill)
        pdf.cell(30, 6, f"R$ {taxa:.2f}", border=1, fill=fill)
        pdf.cell(0, 6, str(e.get('status', 'entregue')), border=1, fill=fill, new_x='LMARGIN', new_y='NEXT')
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, f'TOTAL A PAGAR: R$ {total:.2f}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f'Emitido em {datetime.now().strftime("%d/%m/%Y às %H:%M")}',
             new_x='LMARGIN', new_y='NEXT')
    return bytes(pdf.output())


# ══════════════════════════════════════════════════════════════════════════════
# DECORATORS
# ══════════════════════════════════════════════════════════════════════════════

def requer_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'restaurante' not in session:
            return redirect(url_for('login'))
        rest = Restaurante.query.filter_by(username=session['restaurante']).first()
        if not rest:
            session.clear()
            return redirect(url_for('login'))
        if rest.session_token and session.get('restaurante_token') != rest.session_token:
            session.clear()
            flash('Sessão encerrada — outro dispositivo fez login.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def requer_premium(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        rest = Restaurante.query.filter_by(username=session.get('restaurante', '')).first()
        if not rest or not rest.is_premium:
            flash('Esta funcionalidade está disponível apenas no Plano Premium.', 'warning')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def requer_pro(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        rest = Restaurante.query.filter_by(username=session.get('restaurante', '')).first()
        if not rest or not rest.is_pro_ou_premium:
            flash('Esta funcionalidade está disponível no Plano Pro ou Premium.', 'warning')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_globals():
    rest = None
    if 'restaurante' in session:
        rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    return {
        'restaurante_atual': rest,
        'PLANOS': PLANOS,
        'today': date.today(),
        'mp_ativo': bool(os.environ.get('MERCADOPAGO_ACCESS_TOKEN')),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ROTAS — AUTENTICAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    if 'restaurante' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'restaurante' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        rest = Restaurante.query.filter_by(username=username).first()
        if rest and check_password_hash(rest.password, password):
            tok = secrets.token_hex(16)
            rest.session_token = tok
            db.session.commit()
            session['restaurante']       = username
            session['restaurante_id']    = rest.id
            session['restaurante_token'] = tok
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ══════════════════════════════════════════════════════════════════════════════
# ROTA — CADASTRO (registro do restaurante com geração de código único)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    """
    Página de cadastro pública. Qualquer pessoa pode compartilhar o link.
    ?ref=R492  →  indica quem compartilhou (apenas informativo por ora)
    """
    ref = request.args.get('ref', '')
    if request.method == 'POST':
        nome     = request.form.get('nome', '').strip()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        email    = request.form.get('email', '').strip().lower()
        plano    = request.form.get('plano', 'basico')

        if not nome or not username or not password:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return render_template('cadastrar.html', ref=ref)
        if password != confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('cadastrar.html', ref=ref)
        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('cadastrar.html', ref=ref)
        if Restaurante.query.filter_by(username=username).first():
            flash('Este nome de usuário já está em uso.', 'danger')
            return render_template('cadastrar.html', ref=ref)

        rest = Restaurante(nome=nome, username=username, password=password,
                           email=email or None, plano=plano)
        db.session.add(rest)
        db.session.commit()

        tok = secrets.token_hex(16)
        rest.session_token = tok
        db.session.commit()

        session['restaurante']       = username
        session['restaurante_id']    = rest.id
        session['restaurante_token'] = tok
        flash(f'Bem-vindo(a), {nome}! Seu código de identificação é: {rest.codigo}', 'success')
        return redirect(url_for('dashboard'))
    return render_template('cadastrar.html', ref=ref, PLANOS=PLANOS)


# ══════════════════════════════════════════════════════════════════════════════
# ROTA — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/dashboard')
@requer_login
def dashboard():
    rest       = Restaurante.query.filter_by(username=session['restaurante']).first()
    categorias = Categoria.query.filter_by(restaurante_id=rest.id, ativo=True).all()
    total_itens = ItemCardapio.query.join(Categoria).filter(
        Categoria.restaurante_id == rest.id
    ).count()
    itens_disponiveis = ItemCardapio.query.join(Categoria).filter(
        Categoria.restaurante_id == rest.id, ItemCardapio.disponivel == True
    ).count()
    destaques = ItemCardapio.query.join(Categoria).filter(
        Categoria.restaurante_id == rest.id,
        ItemCardapio.destaque == True, ItemCardapio.disponivel == True
    ).all()
    pedidos_abertos = PedidoKanban.query.filter(
        PedidoKanban.restaurante_id == rest.id,
        PedidoKanban.coluna.in_(['novo', 'preparo', 'pronto'])
    ).count()
    conexoes = ConexaoExterna.query.filter_by(restaurante_id=rest.id, ativa=True).all()
    return render_template('dashboard.html',
        restaurante=rest, categorias=categorias,
        total_itens=total_itens, itens_disponiveis=itens_disponiveis,
        destaques=destaques, pedidos_abertos=pedidos_abertos, conexoes=conexoes)


# ══════════════════════════════════════════════════════════════════════════════
# SISTEMA DE CONEXÃO POR CÓDIGO
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/conexoes')
@requer_login
def conexoes():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    conexoes = ConexaoExterna.query.filter_by(restaurante_id=rest.id).order_by(
        ConexaoExterna.criado_em.desc()
    ).all()
    link_cadastro = request.host_url.rstrip('/') + url_for('cadastrar') + f'?ref={rest.codigo}'
    return render_template('conexoes.html', restaurante=rest, conexoes=conexoes,
                           link_cadastro=link_cadastro)


@app.route('/conexoes/nova', methods=['POST'])
@requer_login
def nova_conexao():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    tipo        = request.form.get('tipo', '')
    url_painel  = request.form.get('url_painel', '').strip()
    descricao   = request.form.get('descricao', '').strip()
    if not tipo:
        flash('Tipo de conexão obrigatório.', 'danger')
        return redirect(url_for('conexoes'))
    cx = ConexaoExterna(rest.id, tipo, url_painel or None, descricao or None, solicitante=rest.username)
    db.session.add(cx)
    db.session.commit()
    flash(f'Conexão com {tipo} adicionada! Token: {cx.token_conexao}', 'success')
    return redirect(url_for('conexoes'))


@app.route('/conexoes/<int:cid>/desativar', methods=['POST'])
@requer_login
def desativar_conexao(cid):
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    cx = ConexaoExterna.query.filter_by(id=cid, restaurante_id=rest.id).first_or_404()
    cx.ativa = False
    db.session.commit()
    flash('Conexão desativada.', 'info')
    return redirect(url_for('conexoes'))


# ── API pública — painéis externos consultam restaurante pelo código ─────────

@app.route('/api/restaurante/<codigo>')
def api_restaurante_por_codigo(codigo):
    """API pública usada por PainelGest, PainelFrota e AppMotoboy para buscar restaurante."""
    rest = Restaurante.query.filter_by(codigo=codigo.upper()).first()
    if not rest:
        return jsonify({'ok': False, 'erro': 'Código não encontrado'}), 404
    return jsonify({
        'ok': True,
        'codigo': rest.codigo,
        'nome': rest.nome,
        'username': rest.username,
        'telefone': rest.telefone or '',
        'endereco': rest.endereco or '',
        'whatsapp': rest.whatsapp or '',
        'plano': rest.plano,
        'token_frota': rest.token_frota or '',
    })


@app.route('/api/conectar', methods=['POST'])
def api_conectar():
    """Painel externo solicita conexão informando o código do restaurante."""
    data       = request.get_json() or {}
    codigo     = data.get('codigo', '').upper()
    tipo       = data.get('tipo', '')
    url_painel = data.get('url_painel', '')
    descricao  = data.get('descricao', '')
    solicitante= data.get('solicitante', '')
    rest = Restaurante.query.filter_by(codigo=codigo).first()
    if not rest:
        return jsonify({'ok': False, 'erro': 'Código não encontrado'}), 404
    cx = ConexaoExterna(rest.id, tipo, url_painel or None, descricao or None, solicitante=solicitante or None)
    db.session.add(cx)
    db.session.commit()
    return jsonify({'ok': True, 'token': cx.token_conexao,
                    'nome_restaurante': rest.nome, 'codigo': rest.codigo})


@app.route('/api/vagas_disponiveis')
def api_vagas_disponiveis():
    vagas = VagaPlantao.query.filter_by(status='aberta').filter(
        VagaPlantao.data == date.today()
    ).all()
    return jsonify([{
        'id': v.id, 'restaurante_id': v.restaurante_id,
        'vagas_total': v.vagas_total, 'vagas_preench': v.vagas_preench,
        'vagas_livres': v.vagas_livres,
        'horario_inicio': v.horario_inicio, 'horario_fim': v.horario_fim,
        'observacao': v.observacao,
    } for v in vagas])


# ══════════════════════════════════════════════════════════════════════════════
# CARDÁPIO
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/cardapio')
@requer_login
def cardapio():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    cats = Categoria.query.filter_by(restaurante_id=rest.id).order_by(Categoria.ordem, Categoria.nome).all()
    return render_template('cardapio.html', restaurante=rest, categorias=cats)


@app.route('/cardapio/categoria/nova', methods=['GET', 'POST'])
@requer_login
def nova_categoria():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        cat = Categoria(rest.id, request.form['nome'],
                        request.form.get('descricao') or None,
                        request.form.get('icone', 'fa-utensils'))
        cat.ordem = int(request.form.get('ordem', 0))
        db.session.add(cat)
        db.session.commit()
        flash('Categoria criada!', 'success')
        return redirect(url_for('cardapio'))
    return render_template('nova_categoria.html', restaurante=rest)


@app.route('/cardapio/categoria/<int:id>/editar', methods=['GET', 'POST'])
@requer_login
def editar_categoria(id):
    cat = Categoria.query.get_or_404(id)
    if request.method == 'POST':
        cat.nome      = request.form['nome']
        cat.descricao = request.form.get('descricao') or None
        cat.icone     = request.form.get('icone', 'fa-utensils')
        cat.ordem     = int(request.form.get('ordem', 0))
        cat.ativo     = 'ativo' in request.form
        db.session.commit()
        flash('Categoria atualizada!', 'success')
        return redirect(url_for('cardapio'))
    return render_template('editar_categoria.html', cat=cat)


@app.route('/cardapio/categoria/<int:id>/excluir')
@requer_login
def excluir_categoria(id):
    cat = Categoria.query.get_or_404(id)
    db.session.delete(cat)
    db.session.commit()
    flash('Categoria excluída.', 'success')
    return redirect(url_for('cardapio'))


@app.route('/cardapio/item/novo', methods=['GET', 'POST'])
@requer_login
def novo_item():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    cats = Categoria.query.filter_by(restaurante_id=rest.id, ativo=True).all()
    if request.method == 'POST':
        item = ItemCardapio(
            int(request.form['categoria_id']),
            request.form['nome'],
            float(request.form['preco']),
            request.form.get('descricao') or None,
            float(request.form['preco_promo']) if request.form.get('preco_promo') else None,
        )
        item.destaque   = 'destaque' in request.form
        item.disponivel = 'disponivel' in request.form
        db.session.add(item)
        db.session.commit()
        flash('Item adicionado!', 'success')
        return redirect(url_for('cardapio'))
    return render_template('novo_item.html', restaurante=rest, categorias=cats,
                           cat_pre=request.args.get('categoria_id'))


@app.route('/cardapio/item/<int:id>/editar', methods=['GET', 'POST'])
@requer_login
def editar_item(id):
    item = ItemCardapio.query.get_or_404(id)
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    cats = Categoria.query.filter_by(restaurante_id=rest.id, ativo=True).all()
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
        return redirect(url_for('cardapio'))
    return render_template('editar_item.html', item=item, categorias=cats)


@app.route('/cardapio/item/<int:id>/excluir')
@requer_login
def excluir_item(id):
    item = ItemCardapio.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Item removido.', 'success')
    return redirect(url_for('cardapio'))


@app.route('/cardapio/item/<int:id>/toggle')
@requer_login
def toggle_item(id):
    item = ItemCardapio.query.get_or_404(id)
    item.disponivel = not item.disponivel
    db.session.commit()
    return redirect(url_for('cardapio'))


@app.route('/cardapio/publico/<username>')
def cardapio_publico(username):
    rest = Restaurante.query.filter_by(username=username).first_or_404()
    cats = Categoria.query.filter_by(restaurante_id=rest.id, ativo=True)\
                          .order_by(Categoria.ordem, Categoria.nome).all()
    for cat in cats:
        cat.itens_disponiveis = [i for i in cat.itens if i.disponivel]
    return render_template('cardapio_publico.html', restaurante=rest, categorias=cats)


@app.route('/upload', methods=['POST'])
@requer_login
def upload():
    if 'imagem' not in request.files:
        flash('Nenhuma imagem enviada!', 'danger')
        return redirect(url_for('dashboard'))
    from pathlib import Path
    imagem = request.files['imagem']
    upload_dir = Path(app.root_path) / 'static' / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)
    imagem.save(str(upload_dir / imagem.filename))
    flash('Imagem enviada!', 'success')
    return redirect(url_for('dashboard'))


# ══════════════════════════════════════════════════════════════════════════════
# KANBAN
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/kanban')
@requer_login
def kanban():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    pedidos_por_coluna = {}
    for col in COLUNAS_KANBAN:
        pedidos_por_coluna[col['key']] = PedidoKanban.query.filter_by(
            restaurante_id=rest.id, coluna=col['key']
        ).order_by(PedidoKanban.criado_em).all()
    cats = Categoria.query.filter_by(restaurante_id=rest.id, ativo=True).all()
    return render_template('kanban.html', restaurante=rest,
                           pedidos=pedidos_por_coluna, colunas=COLUNAS_KANBAN, categorias=cats)


@app.route('/kanban/novo', methods=['GET', 'POST'])
@requer_login
def novo_pedido():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        ultimo = PedidoKanban.query.filter_by(restaurante_id=rest.id)\
                             .order_by(PedidoKanban.numero.desc()).first()
        numero = (ultimo.numero + 1) if ultimo else 1
        pedido = PedidoKanban(
            restaurante_id=rest.id, numero=numero,
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
        return redirect(url_for('kanban'))
    cats = Categoria.query.filter_by(restaurante_id=rest.id, ativo=True).all()
    return render_template('novo_pedido.html', restaurante=rest,
                           categorias=cats, formas=rest.formas_pagamento)


@app.route('/kanban/<int:id>/mover', methods=['POST'])
@requer_login
def mover_pedido(id):
    rest   = Restaurante.query.filter_by(username=session['restaurante']).first()
    pedido = PedidoKanban.query.filter_by(id=id, restaurante_id=rest.id).first_or_404()
    coluna = (request.json.get('coluna') if request.is_json else request.form.get('coluna'))
    if coluna in [c['key'] for c in COLUNAS_KANBAN]:
        pedido.coluna        = coluna
        pedido.atualizado_em = datetime.utcnow()
        db.session.commit()
    return jsonify({'ok': True, 'coluna': pedido.coluna})


@app.route('/kanban/api')
@requer_login
def kanban_api():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    resultado = {}
    for col in COLUNAS_KANBAN:
        pedidos = PedidoKanban.query.filter_by(
            restaurante_id=rest.id, coluna=col['key']
        ).order_by(PedidoKanban.criado_em).all()
        resultado[col['key']] = [{
            'id': p.id, 'numero': p.numero,
            'cliente_nome': p.cliente_nome or 'Cliente',
            'total_fmt': p.total_fmt, 'origem': p.origem,
            'forma_pagamento': p.forma_pagamento or '',
            'observacoes': p.observacoes or '',
            'itens': p.itens[:3], 'itens_total': len(p.itens),
            'hora': p.criado_em.strftime('%H:%M'),
        } for p in pedidos]
    return jsonify(resultado)


@app.route('/kanban/<int:id>/excluir', methods=['POST', 'GET'])
@requer_login
def excluir_pedido(id):
    rest   = Restaurante.query.filter_by(username=session['restaurante']).first()
    pedido = PedidoKanban.query.filter_by(id=id, restaurante_id=rest.id).first_or_404()
    db.session.delete(pedido)
    db.session.commit()
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True})
    flash('Pedido removido.', 'success')
    return redirect(url_for('kanban'))


@app.route('/kanban/<int:id>/comanda')
@requer_login
def comanda(id):
    rest   = Restaurante.query.filter_by(username=session['restaurante']).first()
    pedido = PedidoKanban.query.filter_by(id=id, restaurante_id=rest.id).first_or_404()
    return render_template('comanda.html', restaurante=rest, pedido=pedido)


# ══════════════════════════════════════════════════════════════════════════════
# PERFIL
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/perfil', methods=['GET', 'POST'])
@requer_login
def perfil():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        rest.nome            = request.form.get('nome') or rest.nome
        rest.telefone        = request.form.get('telefone') or None
        rest.endereco        = request.form.get('endereco') or None
        rest.descricao       = request.form.get('descricao') or None
        rest.cor_primaria    = request.form.get('cor_primaria', '#f97316')
        rest.chave_pix       = request.form.get('chave_pix') or None
        rest.link_pagamento  = request.form.get('link_pagamento') or None
        rest.instagram       = request.form.get('instagram') or None
        rest.facebook        = request.form.get('facebook') or None
        rest.whatsapp        = request.form.get('whatsapp') or None
        try:
            rest.raio_entrega_km = float(request.form.get('raio_entrega_km') or 5)
        except (ValueError, TypeError):
            rest.raio_entrega_km = 5.0
        try:
            lat_v = request.form.get('lat_restaurante')
            lng_v = request.form.get('lng_restaurante')
            if lat_v: rest.lat = float(lat_v)
            if lng_v: rest.lng = float(lng_v)
        except (ValueError, TypeError):
            pass
        formas = request.form.getlist('forma_pagamento')
        rest.formas_pagamento_json = json.dumps(formas)
        if 'logo' in request.files and request.files['logo'].filename:
            from pathlib import Path
            logo = request.files['logo']
            upload_dir = Path(app.root_path) / 'static' / 'uploads'
            upload_dir.mkdir(parents=True, exist_ok=True)
            ext = logo.filename.rsplit('.', 1)[-1].lower()
            filename = f"logo_{rest.id}.{ext}"
            logo.save(str(upload_dir / filename))
            rest.logo_path = f"uploads/{filename}"
        if request.form.get('nova_senha'):
            nova = request.form.get('nova_senha', '')
            conf = request.form.get('conf_senha', '')
            if len(nova) >= 6 and nova == conf:
                rest.password = generate_password_hash(nova)
            else:
                flash('Senha inválida: mínimo 6 caracteres e as senhas devem coincidir.', 'warning')
        db.session.commit()
        flash('Perfil atualizado!', 'success')
        return redirect(url_for('perfil'))
    return render_template('perfil.html', restaurante=rest,
                           formas_disponiveis=FORMAS_PAGAMENTO, PLANOS=PLANOS)


# ══════════════════════════════════════════════════════════════════════════════
# MESAS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/mesas')
@requer_login
@requer_pro
def mesas():
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    mesas = Mesa.query.filter_by(restaurante_id=rest.id).order_by(Mesa.numero).all()
    return render_template('mesas.html', restaurante=rest, mesas=mesas)


@app.route('/mesas/salvar', methods=['POST'])
@requer_login
@requer_pro
def mesas_salvar():
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    dados = request.get_json()
    if not dados:
        return jsonify({'ok': False, 'erro': 'Dados inválidos'}), 400
    Mesa.query.filter_by(restaurante_id=rest.id).delete()
    for m in dados.get('mesas', []):
        numero = int(m.get('numero', 0))
        if numero < 1 or numero > 50:
            continue
        mesa = Mesa(rest.id, numero, m.get('nome', '').strip() or None,
                    int(m.get('capacidade', 4)))
        db.session.add(mesa)
    db.session.commit()
    return jsonify({'ok': True, 'total': Mesa.query.filter_by(restaurante_id=rest.id).count()})


@app.route('/mesas/status/<int:mid>', methods=['POST'])
@requer_login
def mesa_status(mid):
    mesa = Mesa.query.get_or_404(mid)
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if mesa.restaurante_id != rest.id:
        return jsonify({'ok': False}), 403
    mesa.status = request.json.get('status', 'livre')
    db.session.commit()
    return jsonify({'ok': True})


# ══════════════════════════════════════════════════════════════════════════════
# ATENDIMENTO WHATSAPP
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/atendimento')
@requer_login
@requer_pro
def atendimento():
    rest     = Restaurante.query.filter_by(username=session['restaurante']).first()
    mesas    = Mesa.query.filter_by(restaurante_id=rest.id, ativa=True).order_by(Mesa.numero).all()
    presentes = ClientePresente.query.filter_by(
        restaurante_id=rest.id, saiu=False
    ).order_by(ClientePresente.entrada_em.desc()).all()
    return render_template('atendimento.html', restaurante=rest, mesas=mesas, presentes=presentes)


@app.route('/atendimento/registrar', methods=['POST'])
@requer_login
@requer_pro
def atendimento_registrar():
    rest     = Restaurante.query.filter_by(username=session['restaurante']).first()
    telefone = ''.join(filter(str.isdigit, request.form.get('telefone', '')))
    nome     = request.form.get('nome', '').strip()
    mesa_id  = request.form.get('mesa_id') or None
    if not telefone:
        flash('Informe o telefone do cliente.', 'danger')
        return redirect(url_for('atendimento'))
    existente = ClientePresente.query.filter_by(
        restaurante_id=rest.id, telefone=telefone, saiu=False
    ).first()
    if existente:
        flash(f'Cliente com telefone {telefone} já está registrado.', 'warning')
        return redirect(url_for('atendimento'))
    cliente = ClientePresente(
        restaurante_id=rest.id, mesa_id=int(mesa_id) if mesa_id else None,
        telefone=telefone, nome=nome or None
    )
    db.session.add(cliente)
    if mesa_id:
        mesa = Mesa.query.get(int(mesa_id))
        if mesa:
            mesa.status = 'ocupada'
    db.session.commit()
    cardapio_link = request.host_url.rstrip('/') + url_for('cardapio_publico', username=rest.username)
    mensagem = (
        f"Olá! 👋 Bem-vindo(a) ao *{rest.nome}*!\n\n"
        f"📱 Acesse nosso cardápio digital:\n{cardapio_link}\n\n"
        f"💬 Responda:\n*1* — Fazer pedido\n*2* — Fechar conta\n*3* — Chamar garçom\n\n"
        f"_Bom apetite! 🍽️_"
    )
    ok, resultado = enviar_whatsapp(telefone, mensagem)
    cliente.whatsapp_enviado = ok
    db.session.commit()
    if ok:
        flash(f'✅ WhatsApp enviado para {telefone}!', 'success')
    else:
        import urllib.parse
        wa_link = f"https://wa.me/55{telefone}?text={urllib.parse.quote(mensagem)}"
        flash(f'Cliente registrado. <a href="{wa_link}" target="_blank" class="alert-link">Enviar WhatsApp manualmente →</a>', 'warning')
    return redirect(url_for('atendimento'))


@app.route('/atendimento/saida/<int:cid>', methods=['POST'])
@requer_login
def atendimento_cliente_saida(cid):
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
# CONTAS / PAGAMENTOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/conta')
@requer_login
@requer_pro
def conta_lista():
    rest   = Restaurante.query.filter_by(username=session['restaurante']).first()
    contas = ContaMesa.query.filter_by(restaurante_id=rest.id, status='aberta')\
                            .order_by(ContaMesa.criado_em.desc()).all()
    mesas  = Mesa.query.filter_by(restaurante_id=rest.id, ativa=True).order_by(Mesa.numero).all()
    return render_template('conta.html', restaurante=rest, contas=contas, mesas=mesas)


@app.route('/conta/abrir', methods=['POST'])
@requer_login
@requer_pro
def conta_abrir():
    rest    = Restaurante.query.filter_by(username=session['restaurante']).first()
    mesa_id = request.form.get('mesa_id') or None
    conta = ContaMesa(restaurante_id=rest.id, mesa_id=int(mesa_id) if mesa_id else None)
    db.session.add(conta)
    if mesa_id:
        mesa = Mesa.query.get(int(mesa_id))
        if mesa:
            mesa.status = 'ocupada'
    db.session.commit()
    return redirect(url_for('conta_detalhe', cid=conta.id))


@app.route('/conta/<int:cid>')
@requer_login
@requer_pro
def conta_detalhe(cid):
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    conta = ContaMesa.query.get_or_404(cid)
    if conta.restaurante_id != rest.id:
        return redirect(url_for('conta_lista'))
    itens_cardapio = ItemCardapio.query.join(Categoria).filter(
        Categoria.restaurante_id == rest.id, ItemCardapio.disponivel == True
    ).order_by(ItemCardapio.nome).all()
    pix_payload = None
    if conta.total > 0 and rest.chave_pix:
        pix_payload = gerar_pix_payload(rest.chave_pix, rest.nome, 'Brasil', conta.total, f'CONTA{conta.id}')
    return render_template('conta_detalhe.html', restaurante=rest, conta=conta,
                           itens_cardapio=itens_cardapio, pix_payload=pix_payload)


@app.route('/conta/<int:cid>/item', methods=['POST'])
@requer_login
def conta_item(cid):
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


@app.route('/conta/<int:cid>/pagar', methods=['POST'])
@requer_login
def conta_pagar(cid):
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


@app.route('/conta/<int:cid>/cancelar', methods=['POST'])
@requer_login
def conta_cancelar(cid):
    rest  = Restaurante.query.filter_by(username=session['restaurante']).first()
    conta = ContaMesa.query.get_or_404(cid)
    if conta.restaurante_id != rest.id:
        return jsonify({'ok': False}), 403
    conta.status = 'cancelada'
    if conta.mesa_rel:
        conta.mesa_rel.status = 'livre'
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/conta/historico')
@requer_login
@requer_pro
def conta_historico():
    rest   = Restaurante.query.filter_by(username=session['restaurante']).first()
    contas = ContaMesa.query.filter_by(restaurante_id=rest.id)\
                            .filter(ContaMesa.status.in_(['paga', 'cancelada']))\
                            .order_by(ContaMesa.pago_em.desc()).limit(100).all()
    return render_template('conta_historico.html', restaurante=rest, contas=contas)


# ══════════════════════════════════════════════════════════════════════════════
# APP SAÍDA — TABLET (PREMIUM ONLY)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/saida')
def saida_app():
    """
    Página pública para tablet na entrada/saída do restaurante.
    Acesso via: /saida?r=username_do_restaurante
    Disponível apenas para restaurantes com plano Premium.
    """
    username = request.args.get('r', '')
    rest = Restaurante.query.filter_by(username=username).first()
    if not rest:
        return render_template('saida.html', restaurante=None,
                               erro='Restaurante não encontrado. Use o link correto.')
    if not rest.is_premium:
        return render_template('saida.html', restaurante=rest,
                               erro='App de Saída disponível apenas no Plano Premium.')
    return render_template('saida.html', restaurante=rest, conta=None)


@app.route('/saida/consultar', methods=['POST'])
def saida_consultar():
    username = request.form.get('username', '')
    telefone = ''.join(filter(str.isdigit, request.form.get('telefone', '')))
    rest = Restaurante.query.filter_by(username=username).first()
    if not rest:
        return jsonify({'ok': False, 'erro': 'Restaurante não encontrado'}), 404
    if not rest.is_premium:
        return jsonify({'ok': False, 'erro': 'Plano Premium necessário'}), 403
    cliente = ClientePresente.query.filter_by(
        restaurante_id=rest.id, telefone=telefone, saiu=False
    ).order_by(ClientePresente.entrada_em.desc()).first()
    if not cliente:
        return jsonify({'ok': False, 'erro': 'Nenhuma conta aberta para este telefone.'})
    conta = ContaMesa.query.filter_by(
        restaurante_id=rest.id, cliente_id=cliente.id, status='aberta'
    ).first()
    return jsonify({
        'ok': True,
        'cliente_id': cliente.id,
        'nome': cliente.nome or f'Cliente ...{telefone[-4:]}',
        'entrada': cliente.entrada_em.strftime('%H:%M'),
        'conta_id': conta.id if conta else None,
        'total': conta.total if conta else 0,
        'total_fmt': conta.total_fmt if conta else 'R$ 0,00',
        'itens': conta.itens if conta else [],
    })


@app.route('/saida/confirmar', methods=['POST'])
def saida_confirmar():
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
    return jsonify({'ok': True, 'mensagem': 'Pagamento confirmado! Boa visita! 👋'})


# ══════════════════════════════════════════════════════════════════════════════
# VAGAS / MOTOBOYS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/vagas', methods=['GET', 'POST'])
@requer_login
@requer_pro
def vagas():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        v = VagaPlantao(
            restaurante_id=rest.id, data=date.today(),
            vagas_total=int(request.form.get('vagas_total', 2)),
            horario_inicio=request.form.get('horario_inicio', '18:00'),
            horario_fim=request.form.get('horario_fim', '23:00'),
            observacao=request.form.get('observacao', ''),
            status='aberta',
        )
        db.session.add(v)
        db.session.commit()
        flash(f'Vaga aberta: {v.vagas_total} motoboy(s) para hoje!', 'success')
        return redirect(url_for('vagas'))
    vagas_lista = VagaPlantao.query.filter_by(restaurante_id=rest.id)\
                                   .order_by(VagaPlantao.criado_em.desc()).limit(10).all()
    return render_template('vagas.html', restaurante=rest, vagas_hoje=vagas_lista)


@app.route('/vagas/<int:vid>/fechar', methods=['POST'])
@requer_login
def fechar_vaga(vid):
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    vaga = VagaPlantao.query.filter_by(id=vid, restaurante_id=rest.id).first_or_404()
    vaga.status = 'encerrada'
    db.session.commit()
    flash('Vaga encerrada.', 'info')
    return redirect(url_for('vagas'))


@app.route('/parceiros', methods=['GET', 'POST'])
@requer_login
@requer_pro
def parceiros():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if request.method == 'POST':
        acao = request.form.get('acao', 'novo')
        if acao == 'novo':
            p = MotoboyParceiro(
                restaurante_id=rest.id,
                nome=request.form['nome'],
                telefone=request.form.get('telefone', '').replace(' ', '').replace('-', ''),
                lat=float(request.form['lat']) if request.form.get('lat') else None,
                lng=float(request.form['lng']) if request.form.get('lng') else None,
            )
            db.session.add(p)
            db.session.commit()
            flash(f'Parceiro {p.nome} adicionado!', 'success')
        return redirect(url_for('parceiros'))
    lista = MotoboyParceiro.query.filter_by(restaurante_id=rest.id, ativo=True).all()
    return render_template('parceiros.html', restaurante=rest, parceiros=lista)


@app.route('/parceiros/<int:pid>/excluir', methods=['POST'])
@requer_login
def excluir_parceiro(pid):
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    p = MotoboyParceiro.query.filter_by(id=pid, restaurante_id=rest.id).first_or_404()
    p.ativo = False
    db.session.commit()
    flash('Parceiro removido.', 'info')
    return redirect(url_for('parceiros'))


# ══════════════════════════════════════════════════════════════════════════════
# COMPROVANTE MOTOBOY
# ══════════════════════════════════════════════════════════════════════════════

MOTOBOY_API_URL = os.getenv('MOTOBOY_API_URL', 'http://localhost:5003')


def _buscar_motoboy_api(motoboy_id):
    try:
        import requests as req_lib
        r = req_lib.get(f'{MOTOBOY_API_URL}/api/motoboy/{motoboy_id}', timeout=3)
        return r.json() if r.ok else {}
    except Exception:
        return {}


def _buscar_entregas_api(motoboy_id, inicio, fim):
    try:
        import requests as req_lib
        r = req_lib.get(f'{MOTOBOY_API_URL}/api/entregas/{motoboy_id}',
                        params={'inicio': inicio.isoformat(), 'fim': fim.isoformat()}, timeout=3)
        return r.json() if r.ok else []
    except Exception:
        return []


@app.route('/comprovante', methods=['GET', 'POST'])
@requer_login
def comprovante():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    motoboys = []
    try:
        import requests as req_lib
        r = req_lib.get(f'{MOTOBOY_API_URL}/api/motoboys', timeout=2)
        motoboys = r.json() if r.ok else []
    except Exception:
        pass
    return render_template('comprovante.html', restaurante=rest, motoboys=motoboys)


@app.route('/comprovante/pdf')
@requer_login
def comprovante_pdf():
    rest       = Restaurante.query.filter_by(username=session['restaurante']).first()
    motoboy_id = request.args.get('motoboy_id', '')
    periodo    = request.args.get('periodo', '7')
    hoje       = date.today()
    dias       = {'7': 7, '15': 15, '30': hoje.day - 1}.get(periodo, 7)
    inicio     = hoje - timedelta(days=dias)
    motoboy_dados = _buscar_motoboy_api(motoboy_id)
    entregas      = _buscar_entregas_api(motoboy_id, inicio, hoje)
    pdf_bytes     = gerar_comprovante_pdf(rest, motoboy_dados, entregas, inicio, hoje)
    if not pdf_bytes:
        flash('Erro ao gerar PDF. Verifique se fpdf2 está instalado.', 'danger')
        return redirect(url_for('comprovante'))
    nome = f"comprovante_{hoje.strftime('%Y%m%d')}.pdf"
    resp = make_response(pdf_bytes)
    resp.headers['Content-Type']        = 'application/pdf'
    resp.headers['Content-Disposition'] = f'attachment; filename="{nome}"'
    return resp


# ══════════════════════════════════════════════════════════════════════════════
# CRM
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/crm')
@requer_login
@requer_pro
def crm():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    clientes = CRMCliente.query.filter_by(restaurante_id=rest.id)\
                               .order_by(CRMCliente.total_pedidos.desc()).all()
    return render_template('crm_lista.html', clientes_crm=clientes, restaurante=rest)


@app.route('/crm/novo', methods=['GET', 'POST'])
@requer_login
@requer_pro
def crm_novo():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
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
        return redirect(url_for('crm'))
    return render_template('crm_novo.html', restaurante=rest)


@app.route('/crm/<int:cid>')
@requer_login
@requer_pro
def crm_detalhe(cid):
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    c = CRMCliente.query.filter_by(id=cid, restaurante_id=rest.id).first_or_404()
    return render_template('crm_detalhe.html', cliente=c, restaurante=rest)


@app.route('/crm/<int:cid>/nota', methods=['POST'])
@requer_login
def crm_nota(cid):
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    c = CRMCliente.query.filter_by(id=cid, restaurante_id=rest.id).first_or_404()
    nova_nota = request.form.get('nota', '').strip()
    if nova_nota:
        ts = datetime.now().strftime('%d/%m/%Y %H:%M')
        c.notas = f"[{ts}] {nova_nota}\n{c.notas or ''}"
        db.session.commit()
        flash('Nota adicionada!', 'success')
    return redirect(url_for('crm_detalhe', cid=cid))


@app.route('/crm/importar', methods=['POST'])
@requer_login
def crm_importar():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    pedidos = PedidoKanban.query.filter_by(restaurante_id=rest.id).all()
    from collections import defaultdict
    grupos = defaultdict(list)
    for p in pedidos:
        nome = (p.cliente_nome or '').strip()
        if nome:
            grupos[nome].append(p)
    criados = 0
    for nome_cliente, lista in grupos.items():
        existente = CRMCliente.query.filter_by(restaurante_id=rest.id, nome_cliente=nome_cliente).first()
        if existente:
            existente.total_pedidos = len(lista)
            existente.valor_total   = sum(p.total for p in lista)
            existente.ticket_medio  = existente.valor_total / len(lista)
            existente.ultimo_pedido = max(p.criado_em for p in lista)
        else:
            vt = sum(p.total for p in lista)
            c = CRMCliente(restaurante_id=rest.id, nome_cliente=nome_cliente,
                           total_pedidos=len(lista), valor_total=vt,
                           ticket_medio=vt / len(lista),
                           ultimo_pedido=max(p.criado_em for p in lista))
            db.session.add(c)
            criados += 1
    db.session.commit()
    flash(f'{criados} cliente(s) importado(s) dos pedidos!', 'success')
    return redirect(url_for('crm'))


# ══════════════════════════════════════════════════════════════════════════════
# QR CODE FROTA
# ══════════════════════════════════════════════════════════════════════════════

def _gerar_qr_bytes(url_destino):
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


@app.route('/frota_qr')
@requer_login
def frota_qr():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if not rest.token_frota:
        rest.token_frota = secrets.token_hex(16)
        db.session.commit()
    frota_url    = os.environ.get('PAINELFROTA_URL', 'http://localhost:5004')
    url_conexao  = f"{frota_url}/conectar_restaurante/{rest.codigo}"
    return render_template('qr_frota.html', restaurante=rest, url_conexao=url_conexao)


@app.route('/frota_qr.png')
@requer_login
def frota_qr_png():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    if not rest.token_frota:
        rest.token_frota = secrets.token_hex(16)
        db.session.commit()
    frota_url   = os.environ.get('PAINELFROTA_URL', 'http://localhost:5004')
    url_conexao = f"{frota_url}/conectar_restaurante/{rest.codigo}"
    buf = _gerar_qr_bytes(url_conexao)
    if not buf:
        return 'QR indisponível', 503
    return send_file(buf, mimetype='image/png')


# ══════════════════════════════════════════════════════════════════════════════
# MAPA DE ENTREGA
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/mapa')
@requer_login
@requer_pro
def mapa():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    motoboys = []
    try:
        import requests as _req
        r = _req.get(f'{MOTOBOY_API_URL}/api/motoboys_disponiveis', timeout=2)
        motoboys = r.json() if r.ok else []
    except Exception:
        pass
    return render_template('mapa.html', restaurante=rest, motoboys=motoboys)


@app.route('/mapa/salvar_pos', methods=['POST'])
@requer_login
def mapa_salvar_pos():
    rest = Restaurante.query.filter_by(username=session['restaurante']).first()
    data = request.get_json() or {}
    try:
        rest.lat = float(data.get('lat'))
        rest.lng = float(data.get('lng'))
        db.session.commit()
    except (TypeError, ValueError):
        pass
    return jsonify({'ok': True})


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

with app.app_context():
    db.create_all()
    # Cria restaurante de demonstração se banco vazio
    if Restaurante.query.count() == 0:
        demo = Restaurante('Restaurante Demo', 'demo', 'demo123', plano='premium')
        db.session.add(demo)
        db.session.commit()
        print(f"[INFO] Restaurante demo criado. Código: {demo.codigo} | Login: demo / demo123")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5006))
    print(f"[PainelRestaurante] Iniciando na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
