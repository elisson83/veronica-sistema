import os
import json
import uuid
import platform
import socket
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LICENCA_FILE = DATA_DIR / "licenca.json"

def get_info_computador() -> dict:
    """Coleta informações do computador"""
    try:
        return {
            "nome_pc": socket.gethostname(),
            "usuario": os.getenv("USERNAME") or os.getenv("USER") or "desconhecido",
            "sistema": platform.system(),
            "versao": platform.release(),
            "processador": platform.processor(),
            "data_instalacao": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "ip": socket.gethostbyname(socket.gethostname())
        }
    except Exception as e:
        return {"erro": str(e)}

def gerar_codigo_licenca() -> str:
    """Gera um código de licença único"""
    codigo = str(uuid.uuid4()).upper().replace("-", "")
    return f"VRC-{codigo[:6]}-{codigo[6:12]}-{codigo[12:18]}"

def salvar_licenca(codigo: str, info_pc: dict) -> bool:
    """Salva a licença no arquivo"""
    try:
        dados = {
            "codigo": codigo,
            "computador": info_pc,
            "ativa": True,
            "criada_em": datetime.now().isoformat()
        }
        with open(LICENCA_FILE, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Erro ao salvar licença: {e}")
        return False

def carregar_licenca() -> dict:
    """Carrega a licença salva"""
    try:
        if LICENCA_FILE.exists():
            with open(LICENCA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def verificar_licenca() -> bool:
    """Verifica se a licença é válida"""
    licenca = carregar_licenca()
    return licenca.get("ativa", False)

def registrar_instalacao(telegram_token: str, admin_id: int) -> str:
    """Registra nova instalação e notifica pelo Telegram"""
    try:
        import requests

        # Coleta informações do PC
        info_pc = get_info_computador()

        # Verifica se já tem licença
        licenca_atual = carregar_licenca()
        if licenca_atual.get("ativa"):
            codigo = licenca_atual.get("codigo")
        else:
            codigo = gerar_codigo_licenca()
            salvar_licenca(codigo, info_pc)

        # Monta mensagem de notificação
        mensagem = (
            f"🔔 *Nova instalação da Verônica!*\n\n"
            f"🔑 Licença: `{codigo}`\n\n"
            f"💻 *Informações do PC:*\n"
            f"• Nome: {info_pc.get('nome_pc', '?')}\n"
            f"• Usuário: {info_pc.get('usuario', '?')}\n"
            f"• Sistema: {info_pc.get('sistema', '?')} {info_pc.get('versao', '')}\n"
            f"• IP: {info_pc.get('ip', '?')}\n"
            f"• Data: {info_pc.get('data_instalacao', '?')}\n"
        )

        # Envia notificação pelo Telegram
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        requests.post(url, json={
            "chat_id": admin_id,
            "text": mensagem,
            "parse_mode": "Markdown"
        }, timeout=10)

        return codigo

    except Exception as e:
        return f"❌ Erro ao registrar instalação: {e}"

def get_info_licenca() -> str:
    """Retorna informações da licença atual"""
    licenca = carregar_licenca()
    if not licenca:
        return "❌ Nenhuma licença encontrada!"

    pc = licenca.get("computador", {})
    return (
        f"🔑 *Informações da Licença:*\n\n"
        f"• Código: `{licenca.get('codigo', '?')}`\n"
        f"• Status: {'✅ Ativa' if licenca.get('ativa') else '❌ Inativa'}\n"
        f"• PC: {pc.get('nome_pc', '?')}\n"
        f"• Usuário: {pc.get('usuario', '?')}\n"
        f"• Sistema: {pc.get('sistema', '?')}\n"
        f"• Instalada em: {pc.get('data_instalacao', '?')}\n"
    )