with open("painelgest/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Adiciona modelo Restaurante e rotas
adicionar = '''

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
'''

# Adiciona antes do if __name__
content = content.replace(
    "if __name__ == '__main__':",
    adicionar + "\nif __name__ == '__main__':"
)

with open("painelgest/app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("app.py atualizado com restaurantes e posts!")