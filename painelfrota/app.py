import os
import json
import requests
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta, time as dtime
from functools import wraps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'frota-secret-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'frota.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# URL do AppMotoboy (para buscar motoboys disponíveis)
MOTOBOY_API = os.getenv('MOTOBOY_API_URL', 'http://localhost:5003')

# Adicionais de preço
ADICIONAL_CHUVA    = float(os.getenv('ADICIONAL_CHUVA', '3.0'))
ADICIONAL_PICO     = float(os.getenv('ADICIONAL_PICO', '2.0'))
ADICIONAL_NOTURNO  = float(os.getenv('ADICIONAL_NOTURNO', '2.5'))
ADICIONAL_FERIADO  = float(os.getenv('ADICIONAL_FERIADO', '4.0'))

HORARIO_PICO = [(11, 14), (18, 21)]  # (hora_inicio, hora_fim)
HORARIO_NOTURNO = (22, 6)            # 22h–6h

NIVEIS_ADM = {
    'super': 'Super ADM',
    'financeiro': 'ADM Financeiro',
    'operacional': 'ADM Operacional',
    'visualizador': 'Visualizador',
}

# ─── MODELOS ─────────────────────────────────────────────────────────────────

class AdminFrota(UserMixin, db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    nome       = db.Column(db.String(100), nullable=False)
    username   = db.Column(db.String(50), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    nivel      = db.Column(db.String(20), default='visualizador')
    ativo      = db.Column(db.Boolean, default=True)
    criado_em  = db.Column(db.DateTime, default=datetime.utcnow)

    def set_senha(self, s): self.senha_hash = generate_password_hash(s)
    def check_senha(self, s): return check_password_hash(self.senha_hash, s)

class MotoboyFrota(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(100), nullable=False)
    telefone      = db.Column(db.String(20))
    moto_placa    = db.Column(db.String(10))
    moto_modelo   = db.Column(db.String(50))
    motoboy_app_id= db.Column(db.Integer)  # ID no AppMotoboy
    ativo         = db.Column(db.Boolean, default=True)
    taxa_entrega  = db.Column(db.Float, default=5.0)
    percentual_frota = db.Column(db.Float, default=20.0)  # % que a frota fica
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)
    turnos        = db.relationship('TurnoFrota', backref='motoboy', lazy=True)
    pagamentos    = db.relationship('PagamentoMotoboy', backref='motoboy', lazy=True)

class EntregaFrota(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    motoboy_id      = db.Column(db.Integer, db.ForeignKey('motoboy_frota.id'))
    restaurante_nome= db.Column(db.String(100))
    cliente_nome    = db.Column(db.String(100))
    cliente_endereco= db.Column(db.String(200))
    codigo_ifood    = db.Column(db.String(30))
    origem          = db.Column(db.String(20), default='direto')
    status          = db.Column(db.String(20), default='pendente')
    valor_pedido    = db.Column(db.Float, default=0.0)
    taxa_base       = db.Column(db.Float, default=5.0)
    adicional_chuva = db.Column(db.Float, default=0.0)
    adicional_pico  = db.Column(db.Float, default=0.0)
    adicional_noturno = db.Column(db.Float, default=0.0)
    adicional_feriado = db.Column(db.Float, default=0.0)
    valor_total_taxa= db.Column(db.Float, default=5.0)
    ganho_motoboy   = db.Column(db.Float, default=4.0)
    ganho_frota     = db.Column(db.Float, default=1.0)
    distancia_km    = db.Column(db.Float)
    observacao      = db.Column(db.Text)
    criado_em       = db.Column(db.DateTime, default=datetime.utcnow)
    entregue_em     = db.Column(db.DateTime)
    motoboy         = db.relationship('MotoboyFrota', backref='entregas', foreign_keys=[motoboy_id])

class TurnoFrota(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    motoboy_id  = db.Column(db.Integer, db.ForeignKey('motoboy_frota.id'), nullable=False)
    dia         = db.Column(db.Date, default=date.today)
    inicio      = db.Column(db.DateTime, default=datetime.utcnow)
    fim         = db.Column(db.DateTime)
    ativo       = db.Column(db.Boolean, default=True)

class PagamentoMotoboy(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    motoboy_id  = db.Column(db.Integer, db.ForeignKey('motoboy_frota.id'), nullable=False)
    valor       = db.Column(db.Float, nullable=False)
    tipo        = db.Column(db.String(20), default='pix')
    referencia  = db.Column(db.String(100))
    periodo_inicio = db.Column(db.Date)
    periodo_fim    = db.Column(db.Date)
    status      = db.Column(db.String(20), default='pendente')
    criado_em   = db.Column(db.DateTime, default=datetime.utcnow)
    pago_em     = db.Column(db.DateTime)

class ConfigFrota(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(200))

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def calcular_adicionais(hora=None):
    hora = hora or datetime.now().hour
    chuva = noturno = pico = feriado = 0.0
    if hora >= 22 or hora < 6:
        noturno = ADICIONAL_NOTURNO
    for (h_ini, h_fim) in HORARIO_PICO:
        if h_ini <= hora < h_fim:
            pico = ADICIONAL_PICO
            break
    return chuva, pico, noturno, feriado

def conf(chave, padrao=''):
    c = ConfigFrota.query.filter_by(chave=chave).first()
    return c.valor if c else padrao

def requer_nivel(*niveis):
    def dec(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_user.nivel not in niveis:
                flash('Acesso negado para seu nível', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return dec

# ─── LOGIN ────────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(uid): return AdminFrota.query.get(int(uid))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        adm = AdminFrota.query.filter_by(username=request.form['username']).first()
        if adm and adm.check_senha(request.form['senha']):
            login_user(adm)
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha incorretos', 'danger')
    return render_template('login.html')

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
    total_motoboys  = MotoboyFrota.query.filter_by(ativo=True).count()
    turnos_ativos   = TurnoFrota.query.filter_by(ativo=True).count()
    entregas_hoje   = EntregaFrota.query.filter(
        db.func.date(EntregaFrota.criado_em) == hoje
    ).count()
    receita_hoje    = db.session.query(db.func.sum(EntregaFrota.ganho_frota)).filter(
        db.func.date(EntregaFrota.criado_em) == hoje,
        EntregaFrota.status == 'entregue'
    ).scalar() or 0.0
    receita_mes     = db.session.query(db.func.sum(EntregaFrota.ganho_frota)).filter(
        db.func.extract('month', EntregaFrota.criado_em) == hoje.month,
        db.func.extract('year', EntregaFrota.criado_em) == hoje.year,
        EntregaFrota.status == 'entregue'
    ).scalar() or 0.0
    ultimas_entregas = EntregaFrota.query.order_by(EntregaFrota.criado_em.desc()).limit(10).all()
    return render_template('dashboard.html',
        total_motoboys=total_motoboys, turnos_ativos=turnos_ativos,
        entregas_hoje=entregas_hoje, receita_hoje=receita_hoje,
        receita_mes=receita_mes, ultimas_entregas=ultimas_entregas,
        hoje=hoje, NIVEIS_ADM=NIVEIS_ADM
    )

# ─── MOTOBOYS ────────────────────────────────────────────────────────────────

@app.route('/motoboys')
@login_required
def motoboys():
    lista = MotoboyFrota.query.order_by(MotoboyFrota.nome).all()
    return render_template('motoboys.html', motoboys=lista, NIVEIS_ADM=NIVEIS_ADM)

@app.route('/motoboys/novo', methods=['GET','POST'])
@login_required
@requer_nivel('super','operacional')
def novo_motoboy():
    if request.method == 'POST':
        mb = MotoboyFrota(
            nome            = request.form['nome'],
            telefone        = request.form.get('telefone'),
            moto_placa      = request.form.get('moto_placa'),
            moto_modelo     = request.form.get('moto_modelo'),
            taxa_entrega    = float(request.form.get('taxa_entrega', 5.0)),
            percentual_frota= float(request.form.get('percentual_frota', 20.0)),
        )
        db.session.add(mb)
        db.session.commit()
        flash('Motoboy cadastrado!', 'success')
        return redirect(url_for('motoboys'))
    return render_template('novo_motoboy.html')

@app.route('/motoboys/<int:mid>/editar', methods=['GET','POST'])
@login_required
@requer_nivel('super','operacional')
def editar_motoboy(mid):
    mb = MotoboyFrota.query.get_or_404(mid)
    if request.method == 'POST':
        mb.nome             = request.form['nome']
        mb.telefone         = request.form.get('telefone')
        mb.moto_placa       = request.form.get('moto_placa')
        mb.moto_modelo      = request.form.get('moto_modelo')
        mb.taxa_entrega     = float(request.form.get('taxa_entrega', 5.0))
        mb.percentual_frota = float(request.form.get('percentual_frota', 20.0))
        mb.ativo            = 'ativo' in request.form
        db.session.commit()
        flash('Motoboy atualizado!', 'success')
        return redirect(url_for('motoboys'))
    return render_template('editar_motoboy.html', motoboy=mb)

@app.route('/motoboys/<int:mid>/excluir', methods=['POST'])
@login_required
@requer_nivel('super')
def excluir_motoboy(mid):
    mb = MotoboyFrota.query.get_or_404(mid)
    mb.ativo = False
    db.session.commit()
    flash('Motoboy desativado.', 'info')
    return redirect(url_for('motoboys'))

# ─── NOVA ENTREGA ────────────────────────────────────────────────────────────

@app.route('/entregas/nova', methods=['GET','POST'])
@login_required
@requer_nivel('super','operacional')
def nova_entrega():
    motoboys_ativos = MotoboyFrota.query.filter_by(ativo=True).all()
    chuva, pico, noturno, feriado = calcular_adicionais()

    if request.method == 'POST':
        mb_id       = int(request.form['motoboy_id'])
        mb          = MotoboyFrota.query.get(mb_id)
        taxa_base   = mb.taxa_entrega if mb else 5.0
        ad_chuva    = float(request.form.get('adicional_chuva', 0))
        ad_pico     = float(request.form.get('adicional_pico', 0))
        ad_noturno  = float(request.form.get('adicional_noturno', 0))
        ad_feriado  = float(request.form.get('adicional_feriado', 0))
        total_taxa  = taxa_base + ad_chuva + ad_pico + ad_noturno + ad_feriado
        perc_frota  = (mb.percentual_frota / 100) if mb else 0.20
        ganho_frota = round(total_taxa * perc_frota, 2)
        ganho_mb    = round(total_taxa - ganho_frota, 2)

        e = EntregaFrota(
            motoboy_id        = mb_id,
            restaurante_nome  = request.form.get('restaurante_nome',''),
            cliente_nome      = request.form.get('cliente_nome',''),
            cliente_endereco  = request.form.get('cliente_endereco',''),
            codigo_ifood      = request.form.get('codigo_ifood',''),
            origem            = request.form.get('origem','direto'),
            valor_pedido      = float(request.form.get('valor_pedido', 0)),
            taxa_base         = taxa_base,
            adicional_chuva   = ad_chuva,
            adicional_pico    = ad_pico,
            adicional_noturno = ad_noturno,
            adicional_feriado = ad_feriado,
            valor_total_taxa  = total_taxa,
            ganho_motoboy     = ganho_mb,
            ganho_frota       = ganho_frota,
            distancia_km      = float(request.form.get('distancia_km', 0) or 0),
            observacao        = request.form.get('observacao',''),
        )
        db.session.add(e)
        db.session.commit()
        flash(f'Entrega criada! Taxa: R$ {total_taxa:.2f} (motoboy R$ {ganho_mb:.2f} / frota R$ {ganho_frota:.2f})', 'success')
        return redirect(url_for('listar_entregas'))

    return render_template('nova_entrega.html',
        motoboys=motoboys_ativos,
        sugestao_chuva=chuva, sugestao_pico=pico,
        sugestao_noturno=noturno, sugestao_feriado=feriado,
        ADICIONAL_CHUVA=ADICIONAL_CHUVA, ADICIONAL_PICO=ADICIONAL_PICO,
        ADICIONAL_NOTURNO=ADICIONAL_NOTURNO, ADICIONAL_FERIADO=ADICIONAL_FERIADO
    )

@app.route('/entregas')
@login_required
def listar_entregas():
    page   = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    q      = EntregaFrota.query
    if status: q = q.filter_by(status=status)
    entregas = q.order_by(EntregaFrota.criado_em.desc()).paginate(page=page, per_page=25)
    return render_template('entregas.html', entregas=entregas, status=status)

@app.route('/entregas/<int:eid>/status', methods=['POST'])
@login_required
def mudar_status_entrega(eid):
    e = EntregaFrota.query.get_or_404(eid)
    novo = request.form.get('status')
    e.status = novo
    if novo == 'entregue' and not e.entregue_em:
        e.entregue_em = datetime.utcnow()
    db.session.commit()
    flash(f'Status atualizado: {novo}', 'success')
    return redirect(url_for('listar_entregas'))

# ─── FINANCEIRO ──────────────────────────────────────────────────────────────

@app.route('/financeiro')
@login_required
@requer_nivel('super','financeiro')
def financeiro():
    hoje          = date.today()
    inicio_mes    = hoje.replace(day=1)

    receita_mes   = db.session.query(db.func.sum(EntregaFrota.ganho_frota)).filter(
        EntregaFrota.status == 'entregue',
        db.func.date(EntregaFrota.entregue_em) >= inicio_mes
    ).scalar() or 0.0

    pago_mes      = db.session.query(db.func.sum(PagamentoMotoboy.valor)).filter(
        PagamentoMotoboy.status == 'pago',
        db.func.date(PagamentoMotoboy.pago_em) >= inicio_mes
    ).scalar() or 0.0

    lucro_mes     = receita_mes - pago_mes

    pagamentos_pendentes = PagamentoMotoboy.query.filter_by(status='pendente').all()

    # Saldo a pagar por motoboy (entregas entregues, ganho_motoboy, sem pagamento)
    motoboys_saldo = []
    for mb in MotoboyFrota.query.filter_by(ativo=True).all():
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
        motoboys_saldo.append({'motoboy': mb, 'saldo': saldo, 'pago': pago, 'a_pagar': max(0, saldo - pago)})

    return render_template('financeiro.html',
        receita_mes=receita_mes, pago_mes=pago_mes, lucro_mes=lucro_mes,
        pagamentos_pendentes=pagamentos_pendentes,
        motoboys_saldo=motoboys_saldo, hoje=hoje, inicio_mes=inicio_mes
    )

@app.route('/financeiro/pagar/<int:mid>', methods=['POST'])
@login_required
@requer_nivel('super','financeiro')
def pagar_motoboy(mid):
    mb   = MotoboyFrota.query.get_or_404(mid)
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
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
    a_pagar = max(0, saldo - pago)
    if a_pagar > 0:
        pag = PagamentoMotoboy(
            motoboy_id     = mb.id,
            valor          = a_pagar,
            tipo           = 'pix',
            referencia     = f'PIX automático {hoje.strftime("%d/%m/%Y")}',
            periodo_inicio = inicio_mes,
            periodo_fim    = hoje,
            status         = 'pago',
            pago_em        = datetime.utcnow(),
        )
        db.session.add(pag)
        db.session.commit()
        flash(f'Pagamento de R$ {a_pagar:.2f} para {mb.nome} registrado!', 'success')
    else:
        flash('Nenhum valor a pagar.', 'info')
    return redirect(url_for('financeiro'))

# ─── ADMs ────────────────────────────────────────────────────────────────────

@app.route('/adms')
@login_required
@requer_nivel('super')
def adms():
    lista = AdminFrota.query.order_by(AdminFrota.nome).all()
    return render_template('adms.html', adms=lista, NIVEIS_ADM=NIVEIS_ADM)

@app.route('/adms/novo', methods=['GET','POST'])
@login_required
@requer_nivel('super')
def novo_adm():
    if request.method == 'POST':
        adm = AdminFrota(
            nome     = request.form['nome'],
            username = request.form['username'],
            nivel    = request.form.get('nivel','visualizador'),
        )
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

# ─── GPS / MOTOBOYS ONLINE ───────────────────────────────────────────────────

@app.route('/mapa')
@login_required
def mapa():
    try:
        r = requests.get(f'{MOTOBOY_API}/api/motoboys_disponiveis', timeout=2)
        motoboys_online = r.json()
    except Exception:
        motoboys_online = []
    return render_template('mapa.html', motoboys_online=motoboys_online)

# ─── RELATÓRIOS ──────────────────────────────────────────────────────────────

@app.route('/relatorios')
@login_required
@requer_nivel('super','financeiro')
def relatorios():
    hoje       = date.today()
    inicio_mes = hoje.replace(day=1)
    inicio_sem = hoje - timedelta(days=hoje.weekday())

    def stats(desde):
        total_tx = db.session.query(db.func.sum(EntregaFrota.valor_total_taxa)).filter(
            EntregaFrota.status=='entregue', db.func.date(EntregaFrota.entregue_em)>=desde).scalar() or 0
        frota_tx = db.session.query(db.func.sum(EntregaFrota.ganho_frota)).filter(
            EntregaFrota.status=='entregue', db.func.date(EntregaFrota.entregue_em)>=desde).scalar() or 0
        qtd = EntregaFrota.query.filter(
            EntregaFrota.status=='entregue', db.func.date(EntregaFrota.entregue_em)>=desde).count()
        return {'total': total_tx, 'frota': frota_tx, 'qtd': qtd}

    semana = stats(inicio_sem)
    mes    = stats(inicio_mes)
    return render_template('relatorios.html', semana=semana, mes=mes, hoje=hoje)

# ─── TURNOS E ESCALA ─────────────────────────────────────────────────────────

@app.route('/turnos')
@login_required
def turnos():
    hoje  = date.today()
    ativos = TurnoFrota.query.filter_by(ativo=True).all()
    mb_ativos_ids = {t.motoboy_id for t in ativos}
    motoboys = MotoboyFrota.query.filter_by(ativo=True).all()
    return render_template('turnos.html',
        motoboys=motoboys, mb_ativos_ids=mb_ativos_ids,
        ativos=ativos, hoje=hoje, NIVEIS_ADM=NIVEIS_ADM)


@app.route('/turnos/<int:mid>/iniciar', methods=['POST'])
@login_required
@requer_nivel('super','operacional')
def iniciar_turno(mid):
    ativo = TurnoFrota.query.filter_by(motoboy_id=mid, ativo=True).first()
    if not ativo:
        t = TurnoFrota(motoboy_id=mid, dia=date.today())
        db.session.add(t)
        db.session.commit()
        flash('Turno iniciado!', 'success')
    else:
        flash('Motoboy já tem turno ativo.', 'warning')
    return redirect(url_for('turnos'))


@app.route('/turnos/<int:mid>/encerrar', methods=['POST'])
@login_required
@requer_nivel('super','operacional')
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
    hoje   = date.today()
    semana = [hoje - timedelta(days=i) for i in range(6, -1, -1)]
    motoboys = MotoboyFrota.query.filter_by(ativo=True).all()
    # Monta grade: {motoboy_id: {dia: horas_trabalhadas}}
    grade = {}
    for mb in motoboys:
        grade[mb.id] = {}
        for dia in semana:
            ts = TurnoFrota.query.filter_by(motoboy_id=mb.id, dia=dia).all()
            horas = sum(t.fim and round((t.fim - t.inicio).total_seconds()/3600,1) or 0 for t in ts)
            grade[mb.id][dia] = round(horas, 1)
    return render_template('escala.html',
        motoboys=motoboys, semana=semana, grade=grade,
        hoje=hoje, NIVEIS_ADM=NIVEIS_ADM)


# ─── INICIALIZAÇÃO ────────────────────────────────────────────────────────────

def migrate_db():
    with app.app_context():
        db.create_all()
        if not AdminFrota.query.filter_by(username='admin').first():
            a = AdminFrota(nome='Super Admin Frota', username='admin', nivel='super')
            a.set_senha('admin123')
            db.session.add(a)
            db.session.commit()

if __name__ == '__main__':
    migrate_db()
    app.run(port=5004, debug=True)
