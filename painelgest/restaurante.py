```python
from flask import Flask, render_template, request, redirect, url_for
from sqlite3 import connect
import os

app = Flask(__name__)

# Conexão com o banco de dados
def conectar_banco():
    try:
        conn = connect('painelgest.db')
        return conn
    except Exception as e:
        print(e)

# Tela de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = conectar_banco()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes WHERE username = ? AND password = ?", (username, password))
        row = cursor.fetchone()
        if row:
            return redirect(url_for('painel'))
        else:
            return render_template('login.html', mensagem='Usuário ou senha inválidos')
    return render_template('login.html')

# Painel do cliente
@app.route('/painel')
def painel():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE publicado = 0")
    posts_agendados = cursor.fetchall()
    cursor.execute("SELECT * FROM posts WHERE publicado = 1")
    posts_publicados = cursor.fetchall()
    cursor.execute("SELECT data_vencimento FROM clientes WHERE id = 1")
    data_vencimento = cursor.fetchone()
    cursor.execute("SELECT link_pagamento FROM clientes WHERE id = 1")
    link_pagamento = cursor.fetchone()
    return render_template('painel.html', posts_agendados=posts_agendados, posts_publicados=posts_publicados, data_vencimento=data_vencimento, link_pagamento=link_pagamento)

# Enviar imagem para o gestor
@app.route('/enviar_imagem', methods=['POST'])
def enviar_imagem():
    imagem = request.files['imagem']
    descricao = request.form['descricao']
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts (descricao, imagem) VALUES (?, ?)", (descricao, imagem.filename))
    conn.commit()
    conn.close()
    return redirect(url_for('painel'))

# Ver histórico de posts
@app.route('/historico')
def historico():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE publicado = 1")
    posts_publicados = cursor.fetchall()
    return render_template('historico.html', posts_publicados=posts_publicados)

if __name__ == '__main__':
    app.run(debug=True)
```