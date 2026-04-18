import json
from pathlib import Path
from datetime import datetime

MEMORY_FILE = Path(__file__).parent.parent / "data" / "users.json"

def inicializar_arquivo():
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists():
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "_info": "Arquivo de memória dos usuários da Verônica IA",
                "_version": "0.1.0",
                "_usuarios": {}
            }, f, ensure_ascii=False, indent=2)

def carregar_usuarios():
    inicializar_arquivo()
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados.get("_usuarios", {})
    except:
        return {}

def salvar_usuarios(usuarios):
    inicializar_arquivo()
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "_info": "Arquivo de memória dos usuários da Verônica IA",
            "_version": "0.1.0",
            "_usuarios": usuarios
        }, f, ensure_ascii=False, indent=2)

def get_usuario(user_id: str):
    usuarios = carregar_usuarios()
    if user_id not in usuarios:
        usuarios[user_id] = {
            "id": user_id,
            "nome": "",
            "nivel": "iniciante",
            "historico": [],
            "criado_em": datetime.now().isoformat()
        }
        salvar_usuarios(usuarios)
    return usuarios[user_id]

def salvar_mensagem(user_id: str, role: str, conteudo: str):
    usuarios = carregar_usuarios()
    usuario = get_usuario(user_id)
    usuario["historico"].append({
        "role": role,
        "content": conteudo,
        "timestamp": datetime.now().isoformat()
    })
    if len(usuario["historico"]) > 20:
        usuario["historico"] = usuario["historico"][-20:]
    usuarios[user_id] = usuario
    salvar_usuarios(usuarios)

def get_historico(user_id: str) -> list:
    usuario = get_usuario(user_id)
    return usuario["historico"]

def atualizar_nivel(user_id: str, nivel: str):
    usuarios = carregar_usuarios()
    usuario = get_usuario(user_id)
    usuario["nivel"] = nivel
    usuarios[user_id] = usuario
    salvar_usuarios(usuarios)

def atualizar_nome(user_id: str, nome: str):
    usuarios = carregar_usuarios()
    usuario = get_usuario(user_id)
    usuario["nome"] = nome
    usuarios[user_id] = usuario
    salvar_usuarios(usuarios)