import os
import io
import math
import json
import secrets
import requests
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, make_response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'frota-secret-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'frota.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

MOTOBOY_API      = os.getenv('MOTOBOY_API_URL', 'http://localhost:5003')
PAINELGEST_URL   = os.getenv('PAINELGEST_URL',  'http://localhost:5002')

ADICIONAL_CHUVA   = float(os.getenv('ADICIONAL_CHUVA',   '3.0'))
ADICIONAL_PICO    = float(os.getenv('ADICIONAL_PICO',    '2.0'))
ADICIONAL_NOTURNO = float(os.getenv('ADICIONAL_NOTURNO', '2.5'))
ADICIONAL_FERIADO = float(os.getenv('ADICIONAL_FERIADO', '4.0'))
ADICIONAL_CHUVA_FORTE = float(os.getenv('ADICIONAL_CHUVA_FORTE', '5.0'))

HORARIO_PICO    = [(11, 14), (18, 21)]
HORARIO_NOTURNO = (22, 6)

NIVEIS_ADM = {
    'super':        'Super ADM',
    'financeiro':   'ADM Financeiro',
    'operacional':  'ADM Operacional',
    'visualizador': 'Visualizador',
}

MODOS_REMUNERACAO = {
    'corrida':     'Por Corrida (valor fixo)',
    'porcentagem': 'Porcentagem do valor',
    'diaria':      'Diária fixa',
    'misto':       'Misto (corrida + diária)',
}

# ─── MODELOS ─────────────────────────────────────────────────────────────────

class AdminFrota(UserMixin, db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    nome       = db.Column(db.String(100), nullable=False)
    username   = db.Column(db.String(50), unique=True, nullable=False)
    email      = db.Column(db.String(120))
    senha_hash = db.Column(db.String(200), nullable=False)
    nivel      = db.Column(db.String(20), default='visualizador')
    ativo      = db.Column(db.Boolean, default=True)
    criado_em  = db.Column(db.DateTime, default=datetime.utcnow)

    def set_senha(self, s): self.senha_hash = generate_password_hash(s)
    def check_senha(self, s): return check_password_hash(self.senha_hash, s)


class MotoboyFrota(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    codigo           = db.Column(db.String(4), unique=True)    # ex: F847
    nome             = db.Column(db.String(100), nullable=False)
    telefone         = db.Column(db.String(20))
    cpf_cnpj         = db.Column(db.String(20))
    tipo_doc         = db.Column(db.String(5), default='cpf')
    chave_pix        = db.Column(db.String(100))
    email            = db.Column(db.String(120))
    moto_placa       = db.Column(db.String(10))
    moto_modelo      = db.Column(db.String(50))
    motoboy_app_id   = db.Column(db.Integer)
    token_app        = db.Column(db.String(64), unique=True)
    ativo            = db.Column(db.Boolean, default=True)
    parceiro         = db.Column(db.Boolean, default=False)  # True = parceiro externo
    # Remuneração
    modo_remuneracao = db.Column(db.String(20), default='corrida')  # corrida|porcentagem|diaria|misto
    taxa_entrega     = db.Column(db.Float, default=5.0)    # valor fixo por corrida
    percentual_motoboy = db.Column(db.Float, default=80.0) # % que o motoboy fica
    valor_diaria     = db.Column(db.Float, default=0.0)    # diária fixa
    criado_em        = db.Column(db.DateTime, default=datetime.utcnow)
    turnos           = db.relationship('TurnoFrota', backref='motoboy', lazy=True)
    pagamentos       = db.relationship('PagamentoMotoboy', backref='motoboy', lazy=True)

    @property
    def percentual_frota(self):
        return round(100 - self.percentual_motoboy, 1)

    def calcular_ganho_motoboy(self, total_taxa):
        if self.modo_remuneracao == 'corrida':
            return self.taxa_entrega
        elif self.modo_remuneracao == 'porcentagem':
            return round(total_taxa * self.percentual_motoboy / 100, 2)
        elif self.modo_remuneracao == 'diaria':
            return 0.0  # pago ao final do dia como diária
        elif self.modo_remuneracao == 'misto':
            return round(self.taxa_entrega + total_taxa * self.percentual_motoboy / 100 * 0.5, 2)
        return self.taxa_entrega


class EntregaFrota(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    motoboy_id       = db.Column(db.Integer, db.ForeignKey('motoboy_frota.id'))
    restaurante_id   = db.Column(db.Integer, db.ForeignKey('restaurante_conectado.id'), nullable=True)
    restaurante_nome = db.Column(db.String(100))
    cliente_nome     = db.Column(db.String(100))
    cliente_endereco = db.Column(db.String(200))
    codigo_ifood     = db.Column(db.String(30))
    origem           = db.Column(db.String(20), default='direto')
    status           = db.Column(db.String(20), default='pendente')
    valor_pedido     = db.Column(db.Float, default=0.0)
    taxa_base        = db.Column(db.Float, default=5.0)
    adicional_chuva  = db.Column(db.Float, default=0.0)
    adicional_pico   = db.Column(db.Float, default=0.0)
    adicional_noturno= db.Column(db.Float, default=0.0)
    adicional_feriado= db.Column(db.Float, default=0.0)
    valor_total_taxa = db.Column(db.Float, default=5.0)
    ganho_motoboy    = db.Column(db.Float, default=4.0)
    ganho_frota      = db.Column(db.Float, default=1.0)
    distancia_km     = db.Column(db.Float)
    observacao       = db.Column(db.Text)
    criado_em        = db.Column(db.DateTime, default=datetime.utcnow)
    entregue_em      = db.Column(db.DateTime)
    motoboy          = db.relationship('MotoboyFrota', backref='entregas', foreign_keys=[motoboy_id])
    restaurante_rel  = db.relationship('RestauranteConectado', backref='entregas', foreign_keys=[restaurante_id])


class TurnoFrota(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    motoboy_id = db.Column(db.Integer, db.ForeignKey('motoboy_frota.id'), nullable=False)
    dia        = db.Column(db.Date, default=date.today)
    inicio     = db.Column(db.DateTime, default=datetime.utcnow)
    fim        = db.Column(db.DateTime)
    ativo      = db.Column(db.Boolean, default=True)

    @property
    def duracao_horas(self):
        f = self.fim or datetime.utcnow()
        return round((f - self.inicio).total_seconds() / 3600, 1)


class PagamentoMotoboy(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    motoboy_id     = db.Column(db.Integer, db.ForeignKey('motoboy_frota.id'), nullable=False)
    valor          = db.Column(db.Float, nullable=False)
    tipo           = db.Column(db.String(20), default='pix')
    chave_pix_dest = db.Column(db.String(100))
    referencia     = db.Column(db.String(200))
    periodo_inicio = db.Column(db.Date)
    periodo_fim    = db.Column(db.Date)
    status         = db.Column(db.String(20), default='pendente')
    automatico     = db.Column(db.Boolean, default=False)
    criado_em      = db.Column(db.DateTime, default=datetime.utcnow)
    pago_em        = db.Column(db.DateTime)


class RestauranteConectado(db.Model):
    """Restaurante conectado ao PainelFrota via QR Code."""
    id              = db.Column(db.Integer, primary_key=True)
    nome            = db.Column(db.String(100), nullable=False)
    token_qr        = db.Column(db.String(64), unique=True, nullable=False)
    painelgest_id   = db.Column(db.Integer, nullable=True)   # ID no PainelGest
    telefone        = db.Column(db.String(20))
    endereco        = db.Column(db.String(200))
    taxa_padrao     = db.Column(db.Float, default=5.0)
    ativo           = db.Column(db.Boolean, default=True)
    conectado_em    = db.Column(db.DateTime, default=datetime.utcnow)
    ultima_entrega  = db.Column(db.DateTime)


class ConfigFrota(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(500))


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def calcular_adicionais(hora=None, chuva=False, feriado=False):
    hora = hora if hora is not None else datetime.now().hour
    ad_chuva = ADICIONAL_CHUVA if chuva else 0.0
    ad_feriado = ADICIONAL_FERIADO if feriado else 0.0
    ad_noturno = ADICIONAL_NOTURNO if (hora >= 22 or hora < 6) else 0.0
    ad_pico = 0.0
    for (h_ini, h_fim) in HORARIO_PICO:
        if h_ini <= hora < h_fim:
            ad_pico = ADICIONAL_PICO
            break
    return ad_chuva, ad_pico, ad_noturno, ad_feriado


def conf(chave, padrao=''):
    c = ConfigFrota.query.filter_by(chave=chave).first()
    return c.valor if c else padrao


def set_conf(chave, valor):
    c = ConfigFrota.query.filter_by(chave=chave).first()
    if c:
        c.valor = str(valor)
    else:
        db.session.add(ConfigFrota(chave=chave, valor=str(valor)))
    db.session.commit()


def gerar_qr_bytes(url_destino):
    """Gera imagem QR Code como bytes PNG."""
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


def fechamento_automatico():
    """Executa fechamento financeiro diário — paga motoboys automaticamente."""
    with app.app_context():
        hoje = date.today()
        ontem = hoje - timedelta(days=1)
        motoboys = MotoboyFrota.query.filter_by(ativo=True).all()
        pagos = 0
        for mb in motoboys:
            # Entregas entregues ontem ainda não pagas
            entregas = EntregaFrota.query.filter(
                EntregaFrota.motoboy_id == mb.id,
                EntregaFrota.status == 'entregue',
                db.func.date(EntregaFrota.entregue_em) == ontem
            ).all()
            # Verificar se já tem pagamento para esse dia
            ja_pago = PagamentoMotoboy.query.filter(
                PagamentoMotoboy.motoboy_id == mb.id,
                PagamentoMotoboy.periodo_inicio == ontem,
                PagamentoMotoboy.status == 'pago'
            ).first()
            if ja_pago or not entregas:
                continue
            # Calcular valor
            if mb.modo_remuneracao == 'diaria':
                valor = mb.valor_diaria
            else:
                valor = sum(e.ganho_motoboy for e in entregas)
            if valor <= 0:
                continue
            pag = PagamentoMotoboy(
                motoboy_id     = mb.id,
                valor          = round(valor, 2),
                tipo           = 'pix',
                chave_pix_dest = mb.chave_pix,
                referencia     = f'Fechamento automático {ontem.strftime("%d/%m/%Y")}',
                periodo_inicio = ontem,
                periodo_fim    = ontem,
                status         = 'pago',
                automatico     = True,
                pago_em        = datetime.utcnow(),
            )
            db.session.add(pag)
            pagos += 1
        db.session.commit()
        if pagos:
            print(f'[Fechamento] {pagos} pagamentos automáticos registrados para {ontem}')


def requer_nivel(*niveis):
    def dec(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_user.nivel not in niveis:
                flash('Acesso negado para seu nível.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return dec


# ─── LOGIN ────────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(uid): return AdminFrota.query.get(int(uid))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        adm = (AdminFrota.query.filter(db.func.lower(AdminFrota.email) == email).first() or
               AdminFrota.query.filter_by(username=email).first())
        if adm and adm.check_senha(senha):
            login_user(adm)
            return redirect(url_for('dashboard'))
        flash('E-mail ou senha incorretos', 'danger')
    return render_template('login.html')


@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome    = request.form.get('nome', '').strip()
        email   = request.form.get('email', '').strip().lower()
        senha   = request.form.get('senha', '')
        confirm = request.form.get('confirm', '')
        if not nome or not email or not senha:
            flash('Preencha todos os campos.', 'danger')
            return render_template('cadastrar.html')
        if senha != confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('cadastrar.html')
        if len(senha) < 6:
            flash('Senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('cadastrar.html')
        if AdminFrota.query.filter(db.func.lower(AdminFrota.email) == email).first():
            flash('Já existe uma conta com este e-mail.', 'danger')
            return render_template('cadastrar.html')
        username = email.split('@')[0][:30]
        base = username; counter = 1
        while AdminFrota.query.filter_by(username=username).first():
            username = f"{base}{counter}"; counter += 1
        adm = AdminFrota(nome=nome, username=username, email=email, nivel='operacional')
        adm.set_senha(senha)
        db.session.add(adm)
        db.session.commit()
        login_user(adm)
        flash(f'Bem-vindo(a), {nome}!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('cadastrar.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    hoje = date.today()
    total_motoboys    = MotoboyFrota.query.filter_by(ativo=True, parceiro=False).count()
    total_parceiros   = MotoboyFrota.query.filter_by(ativo=True, parceiro=True).count()
    total_restaurantes= RestauranteConectado.query.filter_by(ativo=True).count()
    turnos_ativos     = TurnoFrota.query.filter_by(ativo=True).count()
    entregas_hoje     = EntregaFrota.query.filter(db.func.date(EntregaFrota.criado_em) == hoje).count()
    receita_hoje      = db.session.query(db.func.sum(EntregaFrota.ganho_frota)).filter(
        db.func.date(EntregaFrota.criado_em) == hoje,
        EntregaFrota.status == 'entregue'
    ).scalar() or 0.0
    receita_mes       = db.session.query(db.func.sum(EntregaFrota.ganho_frota)).filter(
        db.func.extract('month', EntregaFrota.criado_em) == hoje.month,
        db.func.extract('year',  EntregaFrota.criado_em) == hoje.year,
        EntregaFrota.status == 'entregue'
    ).scalar() or 0.0
    ultimas_entregas  = EntregaFrota.query.order_by(EntregaFrota.criado_em.desc()).limit(8).all()
    return render_template('dashboard.html',
        total_motoboys=total_motoboys, total_parceiros=total_parceiros,
        total_restaurantes=total_restaurantes, turnos_ativos=turnos_ativos,
        entregas_hoje=entregas_hoje, receita_hoje=receita_hoje,
        receita_mes=receita_mes, ultimas_entregas=ultimas_entregas,
        hoje=hoje, NIVEIS_ADM=NIVEIS_ADM,
        MODOS_REMUNERACAO=MODOS_REMUNERACAO
    )


# ─── MOTOBOYS ────────────────────────────────────────────────────────────────

@app.route('/motoboys')
@login_required
def motoboys():
    fixos     = MotoboyFrota.query.filter_by(ativo=True, parceiro=False).order_by(MotoboyFrota.nome).all()
    parceiros = MotoboyFrota.query.filter_by(ativo=True, parceiro=True).order_by(MotoboyFrota.nome).all()
    return render_template('motoboys.html', motoboys=fixos, parceiros=parceiros,
                           NIVEIS_ADM=NIVEIS_ADM, MODOS_REMUNERACAO=MODOS_REMUNERACAO)


@app.route('/motoboys/novo', methods=['GET', 'POST'])
@login_required
@requer_nivel('super', 'operacional')
def novo_motoboy():
    if request.method == 'POST':
        mb = MotoboyFrota(
            nome              = request.form['nome'],
            telefone          = request.form.get('telefone'),
            cpf_cnpj          = request.form.get('cpf_cnpj'),
            tipo_doc          = request.form.get('tipo_doc', 'cpf'),
            chave_pix         = request.form.get('chave_pix'),
            email             = request.form.get('email'),
            moto_placa        = request.form.get('moto_placa'),
            moto_modelo       = request.form.get('moto_modelo'),
            parceiro          = 'parceiro' in request.form,
            modo_remuneracao  = request.form.get('modo_remuneracao', 'corrida'),
            taxa_entrega      = float(request.form.get('taxa_entrega', 5.0)),
            percentual_motoboy= float(request.form.get('percentual_motoboy', 80.0)),
            valor_diaria      = float(request.form.get('valor_diaria', 0.0)),
        )
        db.session.add(mb)
        db.session.commit()
        flash(f'{"Parceiro" if mb.parceiro else "Motoboy"} {mb.nome} cadastrado!', 'success')
        return redirect(url_for('motoboys'))
    return render_template('novo_motoboy.html', MODOS_REMUNERACAO=MODOS_REMUNERACAO)


@app.route('/motoboys/<int:mid>/editar', methods=['GET', 'POST'])
@login_required
@requer_nivel('super', 'operacional')
def editar_motoboy(mid):
    mb = MotoboyFrota.query.get_or_404(mid)
    if request.method == 'POST':
        mb.nome               = request.form['nome']
        mb.telefone           = request.form.get('telefone')
        mb.cpf_cnpj           = request.form.get('cpf_cnpj')
        mb.tipo_doc           = request.form.get('tipo_doc', 'cpf')
        mb.chave_pix          = request.form.get('chave_pix')
        mb.email              = request.form.get('email')
        mb.moto_placa         = request.form.get('moto_placa')
        mb.moto_modelo        = request.form.get('moto_modelo')
        mb.parceiro           = 'parceiro' in request.form
        mb.modo_remuneracao   = request.form.get('modo_remuneracao', 'corrida')
        mb.taxa_entrega       = float(request.form.get('taxa_entrega', 5.0))
        mb.percentual_motoboy = float(request.form.get('percentual_motoboy', 80.0))
        mb.valor_diaria       = float(request.form.get('valor_diaria', 0.0))
        mb.ativo              = 'ativo' in request.form
        db.session.commit()
        flash('Motoboy atualizado!', 'success')
        return redirect(url_for('motoboys'))
    return render_template('editar_motoboy.html', motoboy=mb, MODOS_REMUNERACAO=MODOS_REMUNERACAO)


@app.route('/motoboys/<int:mid>/qr')
@login_required
def motoboy_qr(mid):
    mb = MotoboyFrota.query.get_or_404(mid)
    if not mb.token_app:
        mb.token_app = secrets.token_hex(16)
        db.session.commit()
    url_reg = f"http://localhost:5003/registrar/{mb.token_app}"
    return render_template('motoboy_qr.html', motoboy=mb, url_reg=url_reg, NIVEIS_ADM=NIVEIS_ADM)


@app.route('/motoboys/<int:mid>/qr.png')
@login_required
def motoboy_qr_png(mid):
    mb = MotoboyFrota.query.get_or_404(mid)
    if not mb.token_app:
        mb.token_app = secrets.token_hex(16)
        db.session.commit()
    url_reg = f"http://localhost:5003/registrar/{mb.token_app}"
    buf = gerar_qr_bytes(url_reg)
    if not buf:
        return 'QR indisponível', 503
    return send_file(buf, mimetype='image/png')


@app.route('/motoboys/<int:mid>/excluir', methods=['POST'])
@login_required
@requer_nivel('super')
def excluir_motoboy(mid):
    mb = MotoboyFrota.query.get_or_404(mid)
    mb.ativo = False
    db.session.commit()
    flash('Motoboy desativado.', 'info')
    return redirect(url_for('motoboys'))


# ─── RESTAURANTES CONECTADOS (QR CODE) ───────────────────────────────────────

@app.route('/restaurantes')
@login_required
def restaurantes():
    lista = RestauranteConectado.query.filter_by(ativo=True).order_by(RestauranteConectado.nome).all()
    return render_template('restaurantes.html', restaurantes=lista, NIVEIS_ADM=NIVEIS_ADM)


@app.route('/restaurantes/novo', methods=['GET', 'POST'])
@login_required
@requer_nivel('super', 'operacional')
def novo_restaurante():
    if request.method == 'POST':
        token = secrets.token_hex(16)
        r = RestauranteConectado(
            nome         = request.form['nome'],
            token_qr     = token,
            telefone     = request.form.get('telefone'),
            endereco     = request.form.get('endereco'),
            taxa_padrao  = float(request.form.get('taxa_padrao', 5.0)),
        )
        db.session.add(r)
        db.session.commit()
        flash(f'Restaurante {r.nome} criado! QR Code gerado.', 'success')
        return redirect(url_for('restaurante_qr', rid=r.id))
    return render_template('novo_restaurante.html', NIVEIS_ADM=NIVEIS_ADM)


@app.route('/restaurantes/<int:rid>/qr')
@login_required
def restaurante_qr(rid):
    r = RestauranteConectado.query.get_or_404(rid)
    url_conexao = url_for('conectar_via_qr', token=r.token_qr, _external=True)
    return render_template('restaurante_qr.html', restaurante=r,
                           url_conexao=url_conexao, NIVEIS_ADM=NIVEIS_ADM)


@app.route('/restaurantes/<int:rid>/qr.png')
@login_required
def restaurante_qr_png(rid):
    r = RestauranteConectado.query.get_or_404(rid)
    url_conexao = url_for('conectar_via_qr', token=r.token_qr, _external=True)
    buf = gerar_qr_bytes(url_conexao)
    if not buf:
        return 'QR Code indisponível', 503
    return send_file(buf, mimetype='image/png')


@app.route('/conectar/<token>')
def conectar_via_qr(token):
    """Página aberta pelo restaurante ao escanear o QR — confirma conexão."""
    r = RestauranteConectado.query.filter_by(token_qr=token).first()
    if not r:
        return render_template('qr_invalido.html'), 404
    return render_template('qr_conectar.html', restaurante=r, token=token)


@app.route('/conectar/<token>/confirmar', methods=['POST'])
def confirmar_conexao(token):
    r = RestauranteConectado.query.filter_by(token_qr=token).first_or_404()
    r.ativo = True
    db.session.commit()
    return render_template('qr_confirmado.html', restaurante=r)


@app.route('/restaurantes/<int:rid>/excluir', methods=['POST'])
@login_required
@requer_nivel('super')
def excluir_restaurante(rid):
    r = RestauranteConectado.query.get_or_404(rid)
    r.ativo = False
    db.session.commit()
    flash('Restaurante desconectado.', 'info')
    return redirect(url_for('restaurantes'))


# ─── ENTREGAS ─────────────────────────────────────────────────────────────────

@app.route('/entregas/nova', methods=['GET', 'POST'])
@login_required
@requer_nivel('super', 'operacional')
def nova_entrega():
    motoboys_ativos = MotoboyFrota.query.filter_by(ativo=True).all()
    restaurantes    = RestauranteConectado.query.filter_by(ativo=True).all()
    ad_c, ad_p, ad_n, ad_f = calcular_adicionais()

    if request.method == 'POST':
        mb_id     = int(request.form['motoboy_id'])
        mb        = MotoboyFrota.query.get(mb_id)
        rest_id   = request.form.get('restaurante_id') or None
        taxa_base = float(request.form.get('taxa_base', mb.taxa_entrega if mb else 5.0))
        ad_chuva  = float(request.form.get('adicional_chuva', 0))
        ad_pico   = float(request.form.get('adicional_pico', 0))
        ad_not    = float(request.form.get('adicional_noturno', 0))
        ad_fer    = float(request.form.get('adicional_feriado', 0))
        total     = taxa_base + ad_chuva + ad_pico + ad_not + ad_fer
        ganho_mb  = mb.calcular_ganho_motoboy(total) if mb else total * 0.8
        ganho_fr  = round(total - ganho_mb, 2)

        e = EntregaFrota(
            motoboy_id       = mb_id,
            restaurante_id   = int(rest_id) if rest_id else None,
            restaurante_nome = request.form.get('restaurante_nome', ''),
            cliente_nome     = request.form.get('cliente_nome', ''),
            cliente_endereco = request.form.get('cliente_endereco', ''),
            codigo_ifood     = request.form.get('codigo_ifood', ''),
            origem           = request.form.get('origem', 'direto'),
            valor_pedido     = float(request.form.get('valor_pedido', 0)),
            taxa_base        = taxa_base,
            adicional_chuva  = ad_chuva,
            adicional_pico   = ad_pico,
            adicional_noturno= ad_not,
            adicional_feriado= ad_fer,
            valor_total_taxa = total,
            ganho_motoboy    = ganho_mb,
            ganho_frota      = ganho_fr,
            distancia_km     = float(request.form.get('distancia_km') or 0) or None,
            observacao       = request.form.get('observacao', ''),
        )
        db.session.add(e)
        # Atualizar último uso do restaurante
        if rest_id:
            rest = RestauranteConectado.query.get(int(rest_id))
            if rest:
                rest.ultima_entrega = datetime.utcnow()
        db.session.commit()
        flash(f'Entrega criada! Taxa R$ {total:.2f} → motoboy R$ {ganho_mb:.2f} / frota R$ {ganho_fr:.2f}', 'success')
        return redirect(url_for('listar_entregas'))

    return render_template('nova_entrega.html',
        motoboys=motoboys_ativos, restaurantes=restaurantes,
        sugestao_chuva=ad_c, sugestao_pico=ad_p,
        sugestao_noturno=ad_n, sugestao_feriado=ad_f,
        ADICIONAL_CHUVA=ADICIONAL_CHUVA, ADICIONAL_PICO=ADICIONAL_PICO,
        ADICIONAL_NOTURNO=ADICIONAL_NOTURNO, ADICIONAL_FERIADO=ADICIONAL_FERIADO,
        NIVEIS_ADM=NIVEIS_ADM, MODOS_REMUNERACAO=MODOS_REMUNERACAO
    )


@app.route('/entregas')
@login_required
def listar_entregas():
    page   = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    q = EntregaFrota.query
    if status:
        q = q.filter_by(status=status)
    entregas = q.order_by(EntregaFrota.criado_em.desc()).paginate(page=page, per_page=25)
    return render_template('entregas.html', entregas=entregas, status=status, NIVEIS_ADM=NIVEIS_ADM)


@app.route('/entregas/<int:eid>/status', methods=['POST'])
@login_required
def mudar_status_entrega(eid):
    e = EntregaFrota.query.get_or_404(eid)
    novo = request.form.get('status')
    e.status = novo
    if novo == 'entregue' and not e.entregue_em:
        e.entregue_em = datetime.utcnow()
    db.session.commit()
    flash(f'Status → {novo}', 'success')
    return redirect(url_for('listar_entregas'))


# ─── FINANCEIRO ──────────────────────────────────────────────────────────────

@app.route('/financeiro')
@login_required
@requer_nivel('super', 'financeiro')
def financeiro():
    hoje       = date.today()
    inicio_mes = hoje.replace(day=1)

    receita_mes = db.session.query(db.func.sum(EntregaFrota.ganho_frota)).filter(
        EntregaFrota.status == 'entregue',
        db.func.date(EntregaFrota.entregue_em) >= inicio_mes
    ).scalar() or 0.0

    pago_mes = db.session.query(db.func.sum(PagamentoMotoboy.valor)).filter(
        PagamentoMotoboy.status == 'pago',
        db.func.date(PagamentoMotoboy.pago_em) >= inicio_mes
    ).scalar() or 0.0

    lucro_mes = receita_mes - pago_mes

    motoboys_saldo = []
    for mb in MotoboyFrota.query.filter_by(ativo=True).all():
        if mb.modo_remuneracao == 'diaria':
            # Contagem de dias trabalhados
            dias = db.session.query(db.func.count(db.func.distinct(
                db.func.date(EntregaFrota.entregue_em)
            ))).filter(
                EntregaFrota.motoboy_id == mb.id,
                EntregaFrota.status == 'entregue',
                db.func.date(EntregaFrota.entregue_em) >= inicio_mes
            ).scalar() or 0
            saldo = dias * mb.valor_diaria
        else:
            saldo = db.session.query(db.func.sum(EntregaFrota.ganho_motoboy)).filter(
                EntregaFrota.motoboy_id == mb.id,
                EntregaFrota.status == 'entregue',
                db.func.date(EntregaFrota.entregue_em) >= inicio_mes
            ).scalar() or 0.0

        pago = db.session.query(db.func.sum(PagamentoMotoboy.valor)).filter(
            PagamentoMotoboy.motoboy_id == mb.id,
            PagamentoMotoboy.status == 'pago',
            db.func.date(PagamentoMotoboy.pago_em) >= inicio_mes
        ).scalar() or 0.0

        motoboys_saldo.append({
            'motoboy': mb, 'saldo': round(saldo, 2),
            'pago': round(pago, 2), 'a_pagar': round(max(0, saldo - pago), 2)
        })

    pagamentos_recentes = PagamentoMotoboy.query.order_by(
        PagamentoMotoboy.criado_em.desc()
    ).limit(15).all()

    return render_template('financeiro.html',
        receita_mes=receita_mes, pago_mes=pago_mes, lucro_mes=lucro_mes,
        motoboys_saldo=motoboys_saldo, pagamentos_recentes=pagamentos_recentes,
        hoje=hoje, inicio_mes=inicio_mes, NIVEIS_ADM=NIVEIS_ADM
    )


@app.route('/financeiro/pagar/<int:mid>', methods=['POST'])
@login_required
@requer_nivel('super', 'financeiro')
def pagar_motoboy(mid):
    mb   = MotoboyFrota.query.get_or_404(mid)
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    if mb.modo_remuneracao == 'diaria':
        dias = db.session.query(db.func.count(db.func.distinct(
            db.func.date(EntregaFrota.entregue_em)
        ))).filter(
            EntregaFrota.motoboy_id == mb.id,
            EntregaFrota.status == 'entregue',
            db.func.date(EntregaFrota.entregue_em) >= inicio_mes
        ).scalar() or 0
        saldo = dias * mb.valor_diaria
    else:
        saldo = db.session.query(db.func.sum(EntregaFrota.ganho_motoboy)).filter(
            EntregaFrota.motoboy_id == mb.id,
            EntregaFrota.status == 'entregue',
            db.func.date(EntregaFrota.entregue_em) >= inicio_mes
        ).scalar() or 0.0

    pago = db.session.query(db.func.sum(PagamentoMotoboy.valor)).filter(
        PagamentoMotoboy.motoboy_id == mb.id,
        PagamentoMotoboy.status == 'pago',
        db.func.date(PagamentoMotoboy.pago_em) >= inicio_mes
    ).scalar() or 0.0

    a_pagar = round(max(0, saldo - pago), 2)
    if a_pagar > 0:
        pag = PagamentoMotoboy(
            motoboy_id     = mb.id,
            valor          = a_pagar,
            tipo           = 'pix',
            chave_pix_dest = mb.chave_pix,
            referencia     = f'PIX {hoje.strftime("%d/%m/%Y")} — {MODOS_REMUNERACAO.get(mb.modo_remuneracao,"")}',
            periodo_inicio = inicio_mes,
            periodo_fim    = hoje,
            status         = 'pago',
            automatico     = False,
            pago_em        = datetime.utcnow(),
        )
        db.session.add(pag)
        db.session.commit()
        flash(f'PIX R$ {a_pagar:.2f} para {mb.nome} ({mb.chave_pix or "sem chave"}) registrado!', 'success')
    else:
        flash('Nenhum valor a pagar.', 'info')
    return redirect(url_for('financeiro'))


@app.route('/financeiro/fechamento', methods=['POST'])
@login_required
@requer_nivel('super', 'financeiro')
def executar_fechamento():
    fechamento_automatico()
    flash('Fechamento automático executado!', 'success')
    return redirect(url_for('financeiro'))


# ─── ADMs ────────────────────────────────────────────────────────────────────

@app.route('/adms')
@login_required
@requer_nivel('super')
def adms():
    lista = AdminFrota.query.order_by(AdminFrota.nome).all()
    return render_template('adms.html', adms=lista, NIVEIS_ADM=NIVEIS_ADM)


@app.route('/adms/novo', methods=['GET', 'POST'])
@login_required
@requer_nivel('super')
def novo_adm():
    if AdminFrota.query.count() >= 4:
        flash('Limite de 4 administradores atingido.', 'danger')
        return redirect(url_for('adms'))
    if request.method == 'POST':
        adm = AdminFrota(nome=request.form['nome'], username=request.form['username'],
                         nivel=request.form.get('nivel', 'visualizador'))
        adm.set_senha(request.form['senha'])
        db.session.add(adm)
        db.session.commit()
        flash('Administrador criado!', 'success')
        return redirect(url_for('adms'))
    return render_template('novo_adm.html', NIVEIS_ADM=NIVEIS_ADM)


@app.route('/adms/<int:aid>/excluir', methods=['POST'])
@login_required
@requer_nivel('super')
def excluir_adm(aid):
    if aid == current_user.id:
        flash('Você não pode se excluir.', 'danger')
        return redirect(url_for('adms'))
    adm = AdminFrota.query.get_or_404(aid)
    db.session.delete(adm)
    db.session.commit()
    flash('Administrador removido.', 'info')
    return redirect(url_for('adms'))


# ─── TURNOS E ESCALA ─────────────────────────────────────────────────────────

@app.route('/turnos')
@login_required
def turnos():
    hoje      = date.today()
    ativos    = TurnoFrota.query.filter_by(ativo=True).all()
    mb_ativos = {t.motoboy_id for t in ativos}
    motoboys  = MotoboyFrota.query.filter_by(ativo=True).order_by(MotoboyFrota.nome).all()
    return render_template('turnos.html', motoboys=motoboys, mb_ativos_ids=mb_ativos,
                           ativos=ativos, hoje=hoje, NIVEIS_ADM=NIVEIS_ADM)


@app.route('/turnos/<int:mid>/iniciar', methods=['POST'])
@login_required
@requer_nivel('super', 'operacional')
def iniciar_turno(mid):
    if not TurnoFrota.query.filter_by(motoboy_id=mid, ativo=True).first():
        db.session.add(TurnoFrota(motoboy_id=mid, dia=date.today()))
        db.session.commit()
        flash('Turno iniciado!', 'success')
    else:
        flash('Motoboy já tem turno ativo.', 'warning')
    return redirect(url_for('turnos'))


@app.route('/turnos/<int:mid>/encerrar', methods=['POST'])
@login_required
@requer_nivel('super', 'operacional')
def encerrar_turno(mid):
    t = TurnoFrota.query.filter_by(motoboy_id=mid, ativo=True).first()
    if t:
        t.fim   = datetime.utcnow()
        t.ativo = False
        db.session.commit()
        flash('Turno encerrado.', 'info')
    return redirect(url_for('turnos'))


@app.route('/escala')
@login_required
def escala():
    hoje    = date.today()
    semana  = [hoje - timedelta(days=i) for i in range(6, -1, -1)]
    motoboys= MotoboyFrota.query.filter_by(ativo=True).order_by(MotoboyFrota.nome).all()
    grade   = {}
    for mb in motoboys:
        grade[mb.id] = {}
        for dia in semana:
            ts    = TurnoFrota.query.filter_by(motoboy_id=mb.id, dia=dia).all()
            horas = sum((t.fim or datetime.utcnow() - t.inicio).total_seconds() / 3600
                        if isinstance(t.fim, type(None)) else (t.fim - t.inicio).total_seconds() / 3600
                        for t in ts)
            grade[mb.id][dia] = round(horas, 1)
    return render_template('escala.html', motoboys=motoboys, semana=semana,
                           grade=grade, hoje=hoje, NIVEIS_ADM=NIVEIS_ADM)


# ─── MAPA GPS ────────────────────────────────────────────────────────────────

@app.route('/mapa')
@login_required
def mapa():
    try:
        r = requests.get(f'{MOTOBOY_API}/api/motoboys_disponiveis', timeout=2)
        motoboys_online = r.json()
    except Exception:
        motoboys_online = []
    return render_template('mapa.html', motoboys_online=motoboys_online, NIVEIS_ADM=NIVEIS_ADM)


# ─── RELATÓRIOS ──────────────────────────────────────────────────────────────

@app.route('/relatorios')
@login_required
@requer_nivel('super', 'financeiro')
def relatorios():
    hoje      = date.today()
    inicio_mes= hoje.replace(day=1)
    inicio_sem= hoje - timedelta(days=hoje.weekday())

    def stats(desde):
        total = db.session.query(db.func.sum(EntregaFrota.valor_total_taxa)).filter(
            EntregaFrota.status == 'entregue',
            db.func.date(EntregaFrota.entregue_em) >= desde
        ).scalar() or 0
        frota = db.session.query(db.func.sum(EntregaFrota.ganho_frota)).filter(
            EntregaFrota.status == 'entregue',
            db.func.date(EntregaFrota.entregue_em) >= desde
        ).scalar() or 0
        qtd = EntregaFrota.query.filter(
            EntregaFrota.status == 'entregue',
            db.func.date(EntregaFrota.entregue_em) >= desde
        ).count()
        return {'total': total, 'frota': frota, 'qtd': qtd}

    # Dados dos últimos 14 dias para gráfico
    dias_labels, dias_qtd, dias_receita, dias_lucro = [], [], [], []
    for i in range(13, -1, -1):
        d = hoje - timedelta(days=i)
        dias_labels.append(d.strftime('%d/%m'))
        e_dia = EntregaFrota.query.filter(
            EntregaFrota.status == 'entregue',
            db.func.date(EntregaFrota.entregue_em) == d
        ).all()
        dias_qtd.append(len(e_dia))
        dias_receita.append(round(sum(e.valor_total_taxa for e in e_dia), 2))
        dias_lucro.append(round(sum(e.ganho_frota for e in e_dia), 2))

    # Top motoboys do mês
    top_motoboys = []
    for mb in MotoboyFrota.query.filter_by(ativo=True).all():
        qtd_mb = EntregaFrota.query.filter(
            EntregaFrota.motoboy_id == mb.id,
            EntregaFrota.status == 'entregue',
            db.func.date(EntregaFrota.entregue_em) >= inicio_mes
        ).count()
        if qtd_mb > 0:
            top_motoboys.append({'nome': mb.nome, 'qtd': qtd_mb})
    top_motoboys.sort(key=lambda x: x['qtd'], reverse=True)

    return render_template('relatorios.html',
        semana=stats(inicio_sem), mes=stats(inicio_mes),
        hoje=hoje, NIVEIS_ADM=NIVEIS_ADM,
        dias_labels=dias_labels, dias_qtd=dias_qtd,
        dias_receita=dias_receita, dias_lucro=dias_lucro,
        top_motoboys=top_motoboys[:5])


# ─── QR CODE — API PÚBLICA ────────────────────────────────────────────────────

@app.route('/api/qr/<token>/info')
def api_qr_info(token):
    r = RestauranteConectado.query.filter_by(token_qr=token).first()
    if not r:
        return jsonify({'ok': False}), 404
    return jsonify({'ok': True, 'nome': r.nome, 'taxa_padrao': r.taxa_padrao})


@app.route('/conectar_gestor/<token>')
def conectar_via_gestor(token):
    """Restaurante do PainelGest escaneia QR → cria RestauranteConectado no PainelFrota."""
    # Consulta dados no PainelGest
    dados = {}
    try:
        r = requests.get(f'{PAINELGEST_URL}/api/restaurante_token/{token}', timeout=2)
        if r.ok:
            dados = r.json()
    except Exception:
        pass

    if not dados.get('ok'):
        return render_template('qr_invalido.html'), 404

    # Verifica se já existe
    existente = RestauranteConectado.query.filter_by(token_qr=token).first()
    if existente:
        return render_template('qr_confirmado.html', restaurante=existente)

    return render_template('qr_conectar_gestor.html', dados=dados, token=token)


@app.route('/conectar_gestor/<token>/confirmar', methods=['POST'])
def confirmar_conexao_gestor(token):
    dados = {}
    try:
        r = requests.get(f'{PAINELGEST_URL}/api/restaurante_token/{token}', timeout=2)
        if r.ok:
            dados = r.json()
    except Exception:
        pass
    if not dados.get('ok'):
        return render_template('qr_invalido.html'), 404

    existente = RestauranteConectado.query.filter_by(token_qr=token).first()
    if not existente:
        novo = RestauranteConectado(
            nome      = dados['nome'],
            token_qr  = token,
            telefone  = dados.get('telefone'),
            endereco  = dados.get('endereco'),
        )
        db.session.add(novo)
        db.session.commit()
        existente = novo

    return render_template('qr_confirmado.html', restaurante=existente)


@app.route('/api/motoboy_token/<token>')
def api_motoboy_token(token):
    """AppMotoboy consulta dados do motoboy pelo token_app."""
    mb = MotoboyFrota.query.filter_by(token_app=token, ativo=True).first()
    if not mb:
        return jsonify({'ok': False}), 404
    return jsonify({
        'ok': True,
        'nome': mb.nome,
        'telefone': mb.telefone or '',
        'taxa_entrega': mb.taxa_entrega,
        'modo_remuneracao': mb.modo_remuneracao,
    })


@app.route('/api/stats')
def api_stats():
    """Super Admin consulta estatísticas desta frota."""
    from datetime import date as _date
    hoje = _date.today()
    total_mb = MotoboyFrota.query.filter_by(ativo=True, parceiro=False).count()
    corridas  = EntregaFrota.query.filter(
        db.func.date(EntregaFrota.criado_em) == hoje,
        EntregaFrota.status == 'entregue'
    ).count()
    receita = db.session.query(db.func.sum(EntregaFrota.ganho_frota)).scalar() or 0.0
    return jsonify({
        'total_motoboys': total_mb,
        'corridas_hoje':  corridas,
        'receita_total':  round(float(receita), 2),
    })


# ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────

def migrate_db():
    import sqlite3
    db_path = os.path.join(BASE_DIR, 'instance', 'frota.db')
    with app.app_context():
        db.create_all()
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

    add_col('admin_frota',   'email',              'VARCHAR(120)')
    add_col('motoboy_frota', 'cpf_cnpj',          'VARCHAR(20)')
    add_col('motoboy_frota', 'tipo_doc',           "VARCHAR(5) DEFAULT 'cpf'")
    add_col('motoboy_frota', 'chave_pix',          'VARCHAR(100)')
    add_col('motoboy_frota', 'email',              'VARCHAR(120)')
    add_col('motoboy_frota', 'parceiro',           'BOOLEAN DEFAULT 0')
    add_col('motoboy_frota', 'modo_remuneracao',   "VARCHAR(20) DEFAULT 'corrida'")
    add_col('motoboy_frota', 'percentual_motoboy', 'FLOAT DEFAULT 80.0')
    add_col('motoboy_frota', 'valor_diaria',       'FLOAT DEFAULT 0.0')
    add_col('motoboy_frota', 'token_app',          'VARCHAR(64)')
    add_col('motoboy_frota', 'codigo',             'VARCHAR(4)')
    add_col('entrega_frota', 'restaurante_id',     'INTEGER')
    add_col('pagamento_motoboy', 'chave_pix_dest', 'VARCHAR(100)')
    add_col('pagamento_motoboy', 'automatico',     'BOOLEAN DEFAULT 0')
    conn.commit()
    conn.close()

    with app.app_context():
        a = AdminFrota.query.filter_by(username='admin').first()
        if not a:
            a = AdminFrota(nome='Super Admin Frota', username='admin', nivel='super',
                           email='admin@painelfrota.com')
            a.set_senha('admin123')
            db.session.add(a)
            db.session.commit()
        elif not a.email:
            a.email = 'admin@painelfrota.com'
            db.session.commit()


if __name__ == '__main__':
    migrate_db()
    import logging
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    scheduler = BackgroundScheduler()
    # Fechamento automático todo dia à meia-noite
    scheduler.add_job(fechamento_automatico, 'cron', hour=0, minute=5, id='fechamento_diario')
    scheduler.start()
    try:
        app.run(port=5004, debug=True, use_reloader=False)
    finally:
        scheduler.shutdown()
