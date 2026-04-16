import json
from pathlib import Path

SENHA_FILE = Path(__file__).parent.parent / "data" / "seguranca.json"

def inicializar_seguranca():
    SENHA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SENHA_FILE.exists():
        with open(SENHA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "senha": "veronica2026",
                "usuarios_liberados": []
            }, f, ensure_ascii=False, indent=2)

def get_senha() -> str:
    inicializar_seguranca()
    with open(SENHA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    return dados.get("senha", "veronica2026")

def trocar_senha(nova_senha: str):
    inicializar_seguranca()
    with open(SENHA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    dados["senha"] = nova_senha
    with open(SENHA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def liberar_usuario(user_id: str):
    inicializar_seguranca()
    with open(SENHA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if user_id not in dados["usuarios_liberados"]:
        dados["usuarios_liberados"].append(user_id)
    with open(SENHA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def remover_usuario(user_id: str):
    inicializar_seguranca()
    with open(SENHA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    if user_id in dados["usuarios_liberados"]:
        dados["usuarios_liberados"].remove(user_id)
    with open(SENHA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def usuario_liberado(user_id: str) -> bool:
    inicializar_seguranca()
    with open(SENHA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    return user_id in dados["usuarios_liberados"]

def listar_usuarios_liberados() -> list:
    inicializar_seguranca()
    with open(SENHA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    return dados.get("usuarios_liberados", [])