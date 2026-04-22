from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'painelgest2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///painelgest.db'
db = SQLAlchemy(app)

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
    status = db.Column(db.String(10), nullable=False)

    def __init__(self, nome, login, senha, status):
        self.nome = nome
        self.login = login
        self.senha = senha
        self.status = status

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

@app.route('/')
def index():
    if 'administrador' in session:
        return redirect(url_for('dashboard'))
    else:
        return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        administrador = Administrador.query.filter_by(username=username).first()
        if administrador and check_password_hash(administrador.password, password):
            session['administrador'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('Login ou senha inválidos')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'administrador' in session:
        from datetime import date, timedelta
        clientes_total = Cliente.query.count()
        instagram_total = PerfilInstagram.query.count()
        hoje = date.today()
        em7dias = hoje + timedelta(days=7)
        vencimentos_proximos = Vencimento.query.filter(
            Vencimento.data_vencimento <= em7dias,
            Vencimento.status != 'pago'
        ).count()
        receita = sum([v.valor for v in Vencimento.query.filter_by(status='pago').all()])
        return render_template('dashboard.html',
            clientes_total=clientes_total,
            instagram_total=instagram_total,
            vencimentos_proximos=vencimentos_proximos,
            receita=f"{receita:,.0f}".replace(",",".")
        )
    else:
        return redirect(url_for('login'))

@app.route('/clientes')
def clientes():
    if 'administrador' in session:
        clientes = Cliente.query.all()
        return render_template('clientes.html', clientes=clientes)
    else:
        return redirect(url_for('login'))

@app.route('/cadastrar_cliente', methods=['GET', 'POST'])
def cadastrar_cliente():
    if 'administrador' in session:
        if request.method == 'POST':
            nome = request.form['nome']
            login = request.form['login']
            senha = request.form['senha']
            status = request.form['status']
            cliente = Cliente(nome, login, senha, status)
            db.session.add(cliente)
            db.session.commit()
            return redirect(url_for('clientes'))
        return render_template('cadastrar_cliente.html')
    else:
        return redirect(url_for('login'))

@app.route('/perfis_instagram')
def perfis_instagram():
    if 'administrador' in session:
        perfis = PerfilInstagram.query.all()
        return render_template('perfis_instagram.html', perfis=perfis)
    else:
        return redirect(url_for('login'))

@app.route('/cadastrar_perfil_instagram', methods=['GET', 'POST'])
def cadastrar_perfil_instagram():
    if 'administrador' in session:
        if request.method == 'POST':
            nome = request.form['nome']
            login = request.form['login']
            senha = request.form['senha']
            postagem = request.form['postagem']
            data_postagem = datetime.strptime(request.form['data_postagem'], '%Y-%m-%d %H:%M')
            perfil = PerfilInstagram(nome, login, senha, postagem, data_postagem)
            db.session.add(perfil)
            db.session.commit()
            return redirect(url_for('perfis_instagram'))
        return render_template('cadastrar_perfil_instagram.html')
    else:
        return redirect(url_for('login'))

@app.route('/vencimentos')
def vencimentos():
    if 'administrador' in session:
        vencimentos = Vencimento.query.all()
        return render_template('vencimentos.html', vencimentos=vencimentos)
    else:
        return redirect(url_for('login'))

@app.route('/cadastrar_vencimento', methods=['GET', 'POST'])
def cadastrar_vencimento():
    if 'administrador' in session:
        if request.method == 'POST':
            descricao = request.form['descricao']
            valor = float(request.form['valor'])
            data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')
            status = request.form['status']
            vencimento = Vencimento(descricao, valor, data_vencimento, status)
            db.session.add(vencimento)
            db.session.commit()
            return redirect(url_for('vencimentos'))
        return render_template('cadastrar_vencimento.html')
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('administrador', None)
    return redirect(url_for('index'))



class Restaurante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"))
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
    perfil_id = db.Column(db.Integer, db.ForeignKey("perfil_instagram.id"))
    imagem_path = db.Column(db.String(200), nullable=True)
    legenda = db.Column(db.Text, nullable=True)
    data_postagem = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="agendado")
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

@app.route("/restaurante/login", methods=["GET", "POST"])
def restaurante_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        restaurante = Restaurante.query.filter_by(username=username).first()
        if restaurante and check_password_hash(restaurante.password, password):
            session["restaurante"] = username
            session["restaurante_id"] = restaurante.id
            return redirect(url_for("restaurante_dashboard"))
        else:
            flash("Login ou senha invalidos")
    return render_template("login_restaurante.html")

@app.route("/restaurante/dashboard")
def restaurante_dashboard():
    if "restaurante" not in session:
        return redirect(url_for("restaurante_login"))
    restaurante = Restaurante.query.filter_by(username=session["restaurante"]).first()
    posts = PostAgendado.query.filter_by(status="agendado").all()
    return render_template("dashboard_restaurante.html",
        restaurante=restaurante,
        posts=posts
    )

@app.route("/restaurante/logout")
def restaurante_logout():
    session.pop("restaurante", None)
    session.pop("restaurante_id", None)
    return redirect(url_for("restaurante_login"))

@app.route("/restaurante/upload", methods=["POST"])
def restaurante_upload():
    if "restaurante" not in session:
        return redirect(url_for("restaurante_login"))
    if "imagem" not in request.files:
        flash("Nenhuma imagem enviada!")
        return redirect(url_for("restaurante_dashboard"))
    import os
    from pathlib import Path
    imagem = request.files["imagem"]
    upload_dir = Path("static/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    caminho = str(upload_dir / imagem.filename)
    imagem.save(caminho)
    flash("Imagem enviada com sucesso!")
    return redirect(url_for("restaurante_dashboard"))

@app.route("/admin/restaurantes")
def admin_restaurantes():
    if "administrador" not in session:
        return redirect(url_for("login"))
    restaurantes = Restaurante.query.all()
    return render_template("restaurantes.html", restaurantes=restaurantes)

@app.route("/admin/restaurantes/novo", methods=["GET", "POST"])
def novo_restaurante():
    if "administrador" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        nome = request.form["nome"]
        username = request.form["username"]
        password = request.form["password"]
        restaurante = Restaurante(nome, username, password)
        db.session.add(restaurante)
        db.session.commit()
        flash("Restaurante criado com sucesso!")
        return redirect(url_for("admin_restaurantes"))
    return render_template("novo_restaurante.html")

if __name__ == '__main__':
    app.run(debug=True, port=5002)
