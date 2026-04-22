```python
import sqlite3
from sqlite3 import Error
from apscheduler.schedulers.blocking import BlockingScheduler
from instagrapi import Client

# Conexão com o banco de dados
def conectar_banco():
    try:
        conn = sqlite3.connect('painelgest.db')
        return conn
    except Error as e:
        print(e)

# Verificar posts agendados
def verificar_posts():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE publicado = 0 AND data_hora <= datetime('now')")
    rows = cursor.fetchall()
    for row in rows:
        postar_instagram(row)
        marcar_publicado(row[0])
    conn.close()

# Postar no Instagram
def postar_instagram(row):
    cl = Client()
    cl.login("seu_usuario", "sua_senha")
    media = cl.photo_upload(row[2], row[1])
    cl.media_create(media, caption=row[1])
    cl.logout()

# Marcar post como publicado
def marcar_publicado(id_post):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET publicado = 1 WHERE id = ?", (id_post,))
    conn.commit()
    conn.close()

# Agendar tarefa
def agendar_tarefa():
    scheduler = BlockingScheduler()
    scheduler.add_job(verificar_posts, 'interval', minutes=5)
    scheduler.start()

agendar_tarefa()
```