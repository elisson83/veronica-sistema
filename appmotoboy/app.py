import os
import sys
import math
import secrets
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, send_from_directory

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.seguranca_web import registrar_falha, ip_bloqueado, limpar_falhas, get_ip, init_seguranca, rate_limit, validar_upload
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY_MOTOBOY', 'motoboy-secret-2025-change-me')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
init_seguranca(app)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'motoboy.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

PAINELGEST_URL = os.getenv('PAINELGEST_URL', 'http://localhost:5002')

HORARIO_PICO    = [(11, 14), (18, 21)]
HORARIO_NOTURNO = (22, 6)


def _gerar_codigo_motoboy(valor=None):
    """4 últimos dígitos de telefone/CPF ou 4 dígitos aleatórios."""
    import random
    digitos = ''.join(filter(str.isdigit, str(valor or '')))
    if len(digitos) >= 4:
        base = digitos[-4:]
        candidato = base
        sufixo = 1
        while Motoboy.query.filter_by(codigo=candidato).first():
            candidato = digitos[-3:] + str(sufixo)
            sufixo += 1
            if sufixo > 9:
                break
        if not Motoboy.query.filter_by(codigo=candidato).first():
            return candidato
    while True:
        c = str(random.randint(1000, 9999))
        if not Motoboy.query.filter_by(codigo=c).first():
            return c


# ─── MODELOS ─────────────────────────────────────────────────────────────────

class Motoboy(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    codigo        = db.Column(db.String(4), unique=True)    # ex: M392
    nome          = db.Column(db.String(100), nullable=False)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    senha_hash    = db.Column(db.String(200), nullable=False)
    telefone      = db.Column(db.String(20))
    email         = db.Column(db.String(120))
    cpf_cnpj      = db.Column(db.String(20))
    tipo_doc      = db.Column(db.String(5), default='cpf')
    chave_pix     = db.Column(db.String(100))
    moto_placa    = db.Column(db.String(10))
    moto_modelo   = db.Column(db.String(50))
    foto_path     = db.Column(db.String(200))
    token_frota   = db.Column(db.String(64), unique=True)
    ativo         = db.Column(db.Boolean, default=True)
    disponivel    = db.Column(db.Boolean, default=False)
    lat_atual     = db.Column(db.Float)
    lng_atual     = db.Column(db.Float)
    ultima_loc    = db.Column(db.DateTime)
    taxa_entrega  = db.Column(db.Float, default=5.0)
    saldo_dia     = db.Column(db.Float, default=0.0)
    saldo_total   = db.Column(db.Float, default=0.0)
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)
    entregas      = db.relationship('Entrega', backref='motoboy', lazy=True)
    turnos        = db.relationship('Turno', backref='motoboy', lazy=True)

    def set_senha(self, senha): self.senha_hash = generate_password_hash(senha)
    def check_senha(self, senha): return check_password_hash(self.senha_hash, senha)

    @property
    def entregas_ativas(self):
        return Entrega.query.filter(
            Entrega.motoboy_id == self.id,
            Entrega.status.in_(['aceita', 'retirada'])
        ).count()


class Entrega(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    motoboy_id       = db.Column(db.Integer, db.ForeignKey('motoboy.id'), nullable=False)
    restaurante_nome = db.Column(db.String(100))
    cliente_nome     = db.Column(db.String(100))
    cliente_endereco = db.Column(db.String(200))
    destino_lat      = db.Column(db.Float)
    destino_lng      = db.Column(db.Float)
    codigo_ifood     = db.Column(db.String(30))
    origem           = db.Column(db.String(20), default='direto')
    status           = db.Column(db.String(20), default='pendente')
    valor_pedido     = db.Column(db.Float, default=0.0)
    taxa_entrega     = db.Column(db.Float, default=5.0)
    adicional_chuva  = db.Column(db.Float, default=0.0)
    adicional_pico   = db.Column(db.Float, default=0.0)
    adicional_noturno= db.Column(db.Float, default=0.0)
    valor_total_taxa = db.Column(db.Float, default=5.0)
    distancia_km     = db.Column(db.Float)
    observacao       = db.Column(db.Text)
    expira_em        = db.Column(db.DateTime)   # 15s para aceitar
    criado_em        = db.Column(db.DateTime, default=datetime.utcnow)
    aceito_em        = db.Column(db.DateTime)
    retirado_em      = db.Column(db.DateTime)
    entregue_em      = db.Column(db.DateTime)

    @property
    def duracao_minutos(self):
        if self.entregue_em and self.aceito_em:
            return int((self.entregue_em - self.aceito_em).total_seconds() / 60)
        return None

    @property
    def segundos_para_expirar(self):
        if self.expira_em and self.status == 'pendente':
            delta = (self.expira_em - datetime.utcnow()).total_seconds()
            return max(0, int(delta))
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

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _dist_km(lat1, lng1, lat2, lng2):
    if None in (lat1, lng1, lat2, lng2):
        return None
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def _bearing(lat1, lng1, lat2, lng2):
    """Calcula bearing (direção) entre dois pontos."""
    if None in (lat1, lng1, lat2, lng2):
        return None
    dlng = math.radians(lng2 - lng1)
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    x = math.sin(dlng) * math.cos(lat2r)
    y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlng)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def pode_receber_entrega(mb, dest_lat, dest_lng):
    """
    Rota inteligente: motoboy com 2 entregas ativas → não pode receber.
    Com 1 entrega ativa → pode receber somente se destino novo está na mesma
    direção (bearing <45°) e a menos de 500m do destino atual.
    """
    ativas = mb.entregas_ativas
    if ativas >= 2:
        return False, 'Máximo de 2 entregas simultâneas atingido'
    if ativas == 0:
        return True, None
    # Tem 1 entrega ativa: verificar direção e distância
    entrega_atual = Entrega.query.filter(
        Entrega.motoboy_id == mb.id,
        Entrega.status.in_(['aceita', 'retirada'])
    ).first()
    if not entrega_atual or not entrega_atual.destino_lat:
        return True, None
    dist_m = (_dist_km(entrega_atual.destino_lat, entrega_atual.destino_lng, dest_lat, dest_lng) or 1) * 1000
    if dist_m > 500:
        return False, f'Destino muito longe do trajeto atual ({dist_m:.0f}m)'
    bearing_atual = _bearing(mb.lat_atual, mb.lng_atual, entrega_atual.destino_lat, entrega_atual.destino_lng)
    bearing_novo  = _bearing(mb.lat_atual, mb.lng_atual, dest_lat, dest_lng)
    if bearing_atual is None or bearing_novo is None:
        return True, None
    diff = abs(bearing_atual - bearing_novo)
    if diff > 180:
        diff = 360 - diff
    if diff > 45:
        return False, f'Direção diferente do trajeto atual ({diff:.0f}°)'
    return True, None


def em_horario_pico():
    h = datetime.now().hour
    for ini, fim in HORARIO_PICO:
        if ini <= h < fim:
            return True
    return False


def expirar_entregas_pendentes():
    """APScheduler: cancela entregas pendentes que expiraram (15s sem aceitar)."""
    with app.app_context():
        agora = datetime.utcnow()
        vencidas = Entrega.query.filter(
            Entrega.status == 'pendente',
            Entrega.expira_em != None,
            Entrega.expira_em < agora
        ).all()
        for e in vencidas:
            e.status = 'expirada'
        if vencidas:
            db.session.commit()

# ─── LOGIN ────────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(uid): return Motoboy.query.get(int(uid))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        ip = get_ip()
        if ip_bloqueado(ip):
            flash('Muitas tentativas. Aguarde 15 minutos.', 'danger')
            return render_template('login.html')
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        mb = (Motoboy.query.filter(db.func.lower(Motoboy.email) == email).first() or
              Motoboy.query.filter_by(username=email).first())
        if mb and mb.check_senha(senha):
            limpar_falhas(ip)
            login_user(mb, remember=True)
            return redirect(url_for('dashboard'))
        bloqueou = registrar_falha(ip)
        if bloqueou:
            flash('Conta bloqueada por 15 min por excesso de tentativas.', 'danger')
        else:
            flash('E-mail ou senha incorretos', 'danger')
    return render_template('login.html')


@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome    = request.form.get('nome', '').strip()
        email   = request.form.get('email', '').strip().lower()
        senha   = request.form.get('senha', '')
        confirm = request.form.get('confirm', '')
        telefone = request.form.get('telefone', '').strip()
        cpf_cnpj = request.form.get('cpf_cnpj', '').strip()
        if not nome or not email or not senha:
            flash('Preencha todos os campos.', 'danger')
            return render_template('cadastrar.html')
        if senha != confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('cadastrar.html')
        if len(senha) < 6:
            flash('Senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('cadastrar.html')
        if Motoboy.query.filter(db.func.lower(Motoboy.email) == email).first():
            flash('Já existe uma conta com este e-mail.', 'danger')
            return render_template('cadastrar.html')
        username = email.split('@')[0][:30]
        base = username; counter = 1
        while Motoboy.query.filter_by(username=username).first():
            username = f"{base}{counter}"; counter += 1
        mb = Motoboy(nome=nome, username=username, email=email)
        mb.telefone  = telefone or None
        mb.cpf_cnpj  = cpf_cnpj or None
        mb.codigo    = _gerar_codigo_motoboy(cpf_cnpj or telefone)
        mb.set_senha(senha)
        db.session.add(mb)
        db.session.commit()
        login_user(mb, remember=True)
        flash(f'Bem-vindo(a), {nome}! Seu código: {mb.codigo}', 'success')
        return redirect(url_for('dashboard'))
    return render_template('cadastrar.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/demo-login')
def demo_login():
    """Login automático como Demo — Super Admin visualiza AppMotoboy com acesso total."""
    demo = Motoboy.query.filter_by(email='demo@painelgest.com').first()
    if not demo:
        flash('Conta demo não encontrada.', 'danger')
        return redirect(url_for('login'))
    login_user(demo, remember=False)
    return redirect(url_for('dashboard'))


# ─── REGISTRO VIA QR CODE ─────────────────────────────────────────────────────

@app.route('/registrar/<token>', methods=['GET', 'POST'])
def registrar_via_qr(token):
    """Motoboy escaneia QR do PainelFrota e cria conta no AppMotoboy."""
    # Verifica se já existe motoboy com esse token
    existente = Motoboy.query.filter_by(token_frota=token).first()
    if existente:
        login_user(existente)
        flash('Conta já existente — você foi conectado!', 'success')
        return redirect(url_for('dashboard'))

    # Busca info do motoboy no PainelFrota via API
    nome_frota = ''
    try:
        r = __import__('requests').get(f'{PAINELGEST_URL.replace("5002","5004")}/api/motoboy_token/{token}', timeout=2)
        if r.ok:
            dados = r.json()
            nome_frota = dados.get('nome', '')
    except Exception:
        pass

    if request.method == 'POST':
        username = request.form['username'].strip()
        senha    = request.form['senha']
        nome     = request.form['nome'].strip()
        if Motoboy.query.filter_by(username=username).first():
            flash('Esse usuário já existe. Escolha outro.', 'danger')
            return render_template('registrar.html', token=token, nome_frota=nome_frota)
        mb = Motoboy(
            nome        = nome,
            username    = username,
            telefone    = request.form.get('telefone'),
            token_frota = token,
        )
        mb.set_senha(senha)
        db.session.add(mb)
        db.session.commit()
        login_user(mb)
        flash('Conta criada e vinculada à frota!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('registrar.html', token=token, nome_frota=nome_frota)


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
    pico_agora     = em_horario_pico()

    # Vagas disponíveis do PainelGest
    vagas_count = 0
    try:
        import requests as req_lib
        r = req_lib.get(f'{PAINELGEST_URL}/api/vagas_disponiveis', timeout=1)
        vagas_count = len(r.json()) if r.ok else 0
    except Exception:
        pass

    return render_template('dashboard.html',
        entregas_hoje=entregas_hoje, entregues_hoje=entregues_hoje,
        ganhos_hoje=ganhos_hoje, turno_ativo=turno_ativo,
        pendentes=pendentes, hoje=hoje,
        pico_agora=pico_agora, vagas_count=vagas_count
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

# ─── VAGAS ────────────────────────────────────────────────────────────────────

@app.route('/vagas')
@login_required
def vagas():
    vagas_list = []
    try:
        import requests as req_lib
        r = req_lib.get(f'{PAINELGEST_URL}/api/vagas_disponiveis', timeout=2)
        vagas_list = r.json() if r.ok else []
    except Exception:
        pass
    return render_template('vagas.html', vagas=vagas_list)

@app.route('/vagas/<int:vid>/aceitar', methods=['POST'])
@login_required
def aceitar_vaga(vid):
    try:
        import requests as req_lib
        r = req_lib.post(f'{PAINELGEST_URL}/api/vagas/{vid}/aceitar', json={
            'motoboy_id': current_user.id,
            'motoboy_nome': current_user.nome,
        }, timeout=2)
        d = r.json()
        if d.get('ok'):
            flash('Plantão confirmado!', 'success')
        else:
            flash(d.get('erro', 'Vaga não disponível'), 'danger')
    except Exception:
        flash('Erro ao confirmar vaga. Tente novamente.', 'danger')
    return redirect(url_for('vagas'))

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
    if e.expira_em and e.expira_em < datetime.utcnow():
        return jsonify({'erro': 'Entrega expirada', 'expirada': True}), 400
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

# ─── RANKING ─────────────────────────────────────────────────────────────────

@app.route('/ranking')
@login_required
def ranking():
    inicio_mes = date.today().replace(day=1)
    mbs = Motoboy.query.filter_by(ativo=True).all()

    lista = []
    for mb in mbs:
        qtd = Entrega.query.filter(
            Entrega.motoboy_id == mb.id,
            Entrega.status == 'entregue',
            db.func.date(Entrega.entregue_em) >= inicio_mes
        ).count()
        ganho = db.session.query(db.func.sum(Entrega.valor_total_taxa)).filter(
            Entrega.motoboy_id == mb.id,
            Entrega.status == 'entregue',
            db.func.date(Entrega.entregue_em) >= inicio_mes
        ).scalar() or 0.0
        lista.append({'id': mb.id, 'nome': mb.nome, 'codigo': mb.codigo, 'qtd': qtd, 'ganho': ganho})

    lista.sort(key=lambda x: x['qtd'], reverse=True)

    for pos, item in enumerate(lista, 1):
        item['posicao'] = pos
        item['eu'] = (item['id'] == current_user.id)

    minha_pos = next((x for x in lista if x['eu']), None)
    return render_template('ranking.html', lista=lista, minha_pos=minha_pos, mes=inicio_mes)


# ─── TURNOS SEMANAIS ─────────────────────────────────────────────────────────

@app.route('/turnos')
@login_required
def turnos():
    hoje    = date.today()
    semana  = [hoje - timedelta(days=i) for i in range(6, -1, -1)]
    dados   = []
    for dia in semana:
        ts = Turno.query.filter(
            Turno.motoboy_id == current_user.id,
            db.func.date(Turno.inicio) == dia
        ).all()
        horas = sum(t.duracao_horas for t in ts)
        ents  = Entrega.query.filter(
            Entrega.motoboy_id == current_user.id,
            Entrega.status == 'entregue',
            db.func.date(Entrega.entregue_em) == dia
        ).all()
        ganho = sum(e.valor_total_taxa for e in ents)
        dados.append({'dia': dia, 'horas': horas, 'qtd': len(ents), 'ganho': ganho})
    return render_template('turnos.html', dados=dados, hoje=hoje)

# ─── PERFIL ───────────────────────────────────────────────────────────────────

@app.route('/perfil', methods=['GET','POST'])
@login_required
def perfil():
    if request.method == 'POST':
        mb = current_user
        mb.nome         = request.form.get('nome', mb.nome)
        mb.telefone     = request.form.get('telefone', mb.telefone)
        mb.email        = request.form.get('email', mb.email)
        mb.cpf_cnpj     = request.form.get('cpf_cnpj', mb.cpf_cnpj)
        mb.tipo_doc     = request.form.get('tipo_doc', mb.tipo_doc)
        mb.chave_pix    = request.form.get('chave_pix', mb.chave_pix)
        mb.moto_placa   = request.form.get('moto_placa', mb.moto_placa)
        mb.moto_modelo  = request.form.get('moto_modelo', mb.moto_modelo)
        nova_senha = request.form.get('nova_senha')
        if nova_senha:
            mb.set_senha(nova_senha)
        db.session.commit()
        flash('Perfil atualizado!', 'success')
    return render_template('perfil.html')

# ─── APIs INTERNAS ────────────────────────────────────────────────────────────

@app.route('/mapa')
@login_required
def mapa_motoboy():
    return render_template('mapa.html', motoboy=current_user)


@app.route('/api/motoboys_disponiveis')
@rate_limit(max_req=60, janela=60)
def api_motoboys_disponiveis():
    mbs = Motoboy.query.filter_by(disponivel=True, ativo=True).all()
    return jsonify([{
        'id': mb.id, 'nome': mb.nome, 'lat': mb.lat_atual, 'lng': mb.lng_atual,
        'ultima_loc': mb.ultima_loc.isoformat() if mb.ultima_loc else None
    } for mb in mbs])


@app.route('/api/motoboys')
@rate_limit(max_req=60, janela=60)
def api_motoboys_todos():
    mbs = Motoboy.query.filter_by(ativo=True).all()
    return jsonify([{
        'id': mb.id, 'nome': mb.nome, 'disponivel': mb.disponivel,
    } for mb in mbs])


@app.route('/api/motoboy/<int:mid>')
@rate_limit(max_req=60, janela=60)
def api_motoboy_detalhe(mid):
    mb = Motoboy.query.get_or_404(mid)
    return jsonify({
        'id': mb.id, 'nome': mb.nome, 'telefone': mb.telefone,
    })


@app.route('/api/poll_pendentes')
@login_required
@rate_limit(max_req=120, janela=60)
def api_poll_pendentes():
    """AJAX rápido: retorna entregas pendentes sem recarregar a página."""
    agora = datetime.utcnow()
    pendentes = Entrega.query.filter(
        Entrega.motoboy_id == current_user.id,
        Entrega.status == 'pendente',
        Entrega.expira_em > agora,
    ).all()
    return jsonify({
        'count': len(pendentes),
        'disponivel': current_user.disponivel,
        'ganhos_hoje': current_user.saldo_dia,
        'entregas': [{
            'id': e.id,
            'cliente_nome': e.cliente_nome or 'Cliente',
            'cliente_endereco': e.cliente_endereco,
            'restaurante_nome': e.restaurante_nome,
            'codigo_ifood': e.codigo_ifood,
            'valor_total_taxa': e.valor_total_taxa,
            'segundos_para_expirar': e.segundos_para_expirar,
        } for e in pendentes],
    })


@app.route('/api/entrega_status/<int:eid>')
@rate_limit(max_req=120, janela=60)
def api_entrega_status(eid):
    """Status de uma entrega específica — usado pelo PainelFrota para re-despacho."""
    e = Entrega.query.get_or_404(eid)
    return jsonify({'id': e.id, 'status': e.status, 'motoboy_id': e.motoboy_id})


@app.route('/api/entregas/<int:mid>')
@rate_limit(max_req=60, janela=60)
def api_entregas_motoboy(mid):
    inicio_str = request.args.get('inicio')
    fim_str    = request.args.get('fim')
    try:
        inicio = datetime.fromisoformat(inicio_str) if inicio_str else datetime.utcnow() - timedelta(days=7)
        fim    = datetime.fromisoformat(fim_str)    if fim_str    else datetime.utcnow()
    except Exception:
        inicio = datetime.utcnow() - timedelta(days=7)
        fim    = datetime.utcnow()
    ents = Entrega.query.filter(
        Entrega.motoboy_id == mid,
        Entrega.status == 'entregue',
        Entrega.entregue_em >= inicio,
        Entrega.entregue_em <= fim
    ).all()
    return jsonify([{
        'id': e.id, 'cliente': e.cliente_nome, 'endereco': e.cliente_endereco,
        'taxa': e.valor_total_taxa, 'data': e.entregue_em.strftime('%d/%m/%Y %H:%M') if e.entregue_em else '',
        'status': e.status,
    } for e in ents])


@app.route('/api/nova_entrega', methods=['POST'])
@rate_limit(max_req=30, janela=60)
def api_nova_entrega():
    """Cria entrega com rota inteligente: máx 2 simultâneas, 15s para aceitar."""
    data = request.get_json()
    mb_id    = data.get('motoboy_id')
    dest_lat = data.get('destino_lat')
    dest_lng = data.get('destino_lng')

    if mb_id:
        mb = Motoboy.query.get(mb_id)
        if mb:
            pode, motivo = pode_receber_entrega(mb, dest_lat, dest_lng)
            if not pode:
                return jsonify({'ok': False, 'erro': motivo}), 400

    e = Entrega(
        motoboy_id       = mb_id,
        restaurante_nome = data.get('restaurante_nome', ''),
        cliente_nome     = data.get('cliente_nome', ''),
        cliente_endereco = data.get('cliente_endereco', ''),
        destino_lat      = dest_lat,
        destino_lng      = dest_lng,
        codigo_ifood     = data.get('codigo_ifood', ''),
        origem           = data.get('origem', 'direto'),
        valor_pedido     = data.get('valor_pedido', 0),
        taxa_entrega     = data.get('taxa_entrega', 5.0),
        adicional_chuva  = data.get('adicional_chuva', 0),
        adicional_pico   = data.get('adicional_pico', 0),
        adicional_noturno= data.get('adicional_noturno', 0),
        valor_total_taxa = data.get('valor_total_taxa', 5.0),
        distancia_km     = data.get('distancia_km'),
        observacao       = data.get('observacao', ''),
        expira_em        = datetime.utcnow() + timedelta(seconds=15),
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True, 'id': e.id, 'expira_em': e.expira_em.isoformat()})

# ── Reset de Senha ────────────────────────────────────────────────────────────

class TokenResetMotoboy(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    email     = db.Column(db.String(120), nullable=False)
    token     = db.Column(db.String(64), unique=True, nullable=False)
    usado     = db.Column(db.Boolean, default=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    expira_em = db.Column(db.DateTime, nullable=False)

    def __init__(self, email):
        self.email    = email.lower()
        self.token    = secrets.token_urlsafe(32)
        self.expira_em = datetime.utcnow() + timedelta(hours=2)

    @property
    def valido(self):
        return not self.usado and datetime.utcnow() < self.expira_em


def _enviar_email_motoboy(para, assunto, corpo):
    import sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.email_utils import enviar_email
    ok, _ = enviar_email(para, assunto, corpo)
    return ok


@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha_motoboy():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        mb = Motoboy.query.filter(db.func.lower(Motoboy.email) == email).first()
        if mb and mb.email:
            TokenResetMotoboy.query.filter_by(email=email, usado=False).update({'usado': True})
            db.session.commit()
            tok = TokenResetMotoboy(email)
            db.session.add(tok)
            db.session.commit()
            link = url_for('resetar_senha_motoboy', token=tok.token, _external=True)
            corpo = f"Olá {mb.nome}!\n\nRedefina sua senha:\n{link}\n\nVálido por 2 horas.\n\nAppMotoboy"
            _enviar_email_motoboy(email, 'Redefinir senha — AppMotoboy', corpo)
        flash('Se esse e-mail estiver cadastrado, você receberá o link.', 'info')
        return redirect(url_for('login'))
    return render_template('esqueci_senha.html')


@app.route('/resetar-senha/<token>', methods=['GET', 'POST'])
def resetar_senha_motoboy(token):
    tok = TokenResetMotoboy.query.filter_by(token=token).first_or_404()
    if not tok.valido:
        flash('Link expirado ou já utilizado.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        nova = request.form.get('senha', '')
        conf = request.form.get('confirm', '')
        if len(nova) < 6:
            flash('Mínimo 6 caracteres.', 'danger')
        elif nova != conf:
            flash('Senhas não coincidem.', 'danger')
        else:
            mb = Motoboy.query.filter(db.func.lower(Motoboy.email) == tok.email).first()
            if mb:
                mb.set_senha(nova); tok.usado = True; db.session.commit()
                flash('Senha redefinida! Faça login.', 'success')
                return redirect(url_for('login'))
    return render_template('resetar_senha.html', token=token)


# ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────

def migrate_db():
    import sqlite3
    db_path = os.path.join(BASE_DIR, 'instance', 'motoboy.db')
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

    add_col('motoboy', 'email',       'VARCHAR(120)')
    add_col('motoboy', 'cpf_cnpj',   'VARCHAR(20)')
    add_col('motoboy', 'tipo_doc',   "VARCHAR(5) DEFAULT 'cpf'")
    add_col('motoboy', 'chave_pix',  'VARCHAR(100)')
    add_col('motoboy', 'token_frota','VARCHAR(64)')
    add_col('motoboy', 'codigo',     'VARCHAR(4)')
    add_col('entrega', 'destino_lat','FLOAT')
    add_col('entrega', 'destino_lng','FLOAT')
    add_col('entrega', 'expira_em',  'DATETIME')
    conn.commit()
    conn.close()

    with app.app_context():
        demo = Motoboy.query.filter_by(email='demo@painelgest.com').first()
        if not demo:
            demo = Motoboy(nome='Motoboy Demo', username='demo', email='demo@painelgest.com')
            demo.set_senha('demo2026')
            demo.codigo = '0000'
            db.session.add(demo)
            db.session.commit()
        else:
            demo.set_senha('demo2026')
            db.session.commit()


# ── Chat interno ─────────────────────────────────────────────────────────────

class MensagemChat(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    painel_origem = db.Column(db.String(30), nullable=False)
    usuario_nome  = db.Column(db.String(80), nullable=False)
    mensagem      = db.Column(db.Text, nullable=False)
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, painel, nome, msg):
        self.painel_origem = painel
        self.usuario_nome  = nome
        self.mensagem      = msg


@app.route('/chat')
@login_required
def chat():
    msgs = MensagemChat.query.order_by(MensagemChat.criado_em.desc()).limit(50).all()
    msgs.reverse()
    return render_template('chat.html', msgs=msgs, usuario_nome=current_user.nome, painel='motoboy')


@app.route('/chat/enviar', methods=['POST'])
@login_required
def chat_enviar():
    texto = request.json.get('mensagem', '').strip()
    if not texto:
        return jsonify({'ok': False}), 400
    msg = MensagemChat('motoboy', current_user.nome, texto)
    db.session.add(msg)
    db.session.commit()
    return jsonify({'ok': True, 'id': msg.id, 'criado_em': msg.criado_em.strftime('%H:%M')})


@app.route('/chat/mensagens')
@login_required
def chat_mensagens():
    desde = request.args.get('desde', 0, type=int)
    msgs = MensagemChat.query.filter(MensagemChat.id > desde)\
                             .order_by(MensagemChat.criado_em).limit(50).all()
    return jsonify([{'id': m.id, 'painel': m.painel_origem, 'nome': m.usuario_nome,
                     'msg': m.mensagem, 'hora': m.criado_em.strftime('%H:%M')} for m in msgs])


@app.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    mb = current_user
    if request.method == 'POST':
        acao = request.form.get('acao', '')
        if acao == 'trocar_senha':
            atual = request.form.get('senha_atual', '')
            nova  = request.form.get('senha_nova', '')
            conf  = request.form.get('senha_conf', '')
            if not mb.check_senha(atual):
                flash('Senha atual incorreta.', 'danger')
            elif len(nova) < 6:
                flash('Nova senha deve ter pelo menos 6 caracteres.', 'danger')
            elif nova != conf:
                flash('As senhas não coincidem.', 'danger')
            else:
                mb.set_senha(nova)
                db.session.commit()
                flash('Senha alterada com sucesso!', 'success')
        elif acao == 'excluir_perfil':
            senha_conf = request.form.get('senha_excluir', '')
            if not mb.check_senha(senha_conf):
                flash('Senha incorreta.', 'danger')
            else:
                logout_user()
                db.session.delete(mb)
                db.session.commit()
                flash('Perfil excluído.', 'info')
                return redirect(url_for('login'))
    return render_template('configuracoes.html', motoboy=mb)


@app.route('/links')
@login_required
def links_cadastro():
    from urllib.parse import urlparse
    parsed   = urlparse(request.host_url)
    base_h   = f"{parsed.scheme}://{parsed.hostname}"
    links = {
        'restaurante': os.getenv('PAINELREST_URL',  base_h + ':5006') + '/cadastrar',
        'motoboy_ref': os.getenv('APPMOTOBOY_URL',  base_h + ':5003') + url_for('cadastrar'),
    }
    return render_template('links_cadastro.html', links=links, motoboy=current_user)


@app.route('/sw.js')
def service_worker():
    return send_from_directory(app.static_folder, 'sw.js',
                               mimetype='application/javascript')


if __name__ == '__main__':
    migrate_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(expirar_entregas_pendentes, 'interval', seconds=15, id='expirar_job')
    scheduler.start()
    try:
        app.run(host='0.0.0.0', port=5003, debug=False, use_reloader=False)
    finally:
        scheduler.shutdown()
