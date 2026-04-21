import os
import json
from pathlib import Path
from dotenv import load_dotenv, set_key

ENV_FILE = Path(__file__).parent.parent / ".env"
CHAVES_FILE = Path(__file__).parent.parent / "data" / "chaves_pendentes.json"

load_dotenv(ENV_FILE)

CHAVES_CONHECIDAS = {
    "OPENAI_API_KEY": {
        "nome": "OpenAI (DALL-E, GPT-4)",
        "descricao": "Para gerar imagens com DALL-E 3 e usar GPT-4",
        "onde_obter": "https://platform.openai.com/api-keys",
        "obrigatorio": False
    },
    "HUGGINGFACE_TOKEN": {
        "nome": "HuggingFace",
        "descricao": "Para modelos de IA gratuitos e geração de imagens",
        "onde_obter": "https://huggingface.co/settings/tokens",
        "obrigatorio": False
    },
    "TWITTER_ACCESS_TOKEN": {
        "nome": "Twitter/X Access Token",
        "descricao": "Para postar no Twitter automaticamente",
        "onde_obter": "https://developer.x.com",
        "obrigatorio": False
    },
    "TWITTER_CONSUMER_KEY": {
        "nome": "Twitter/X Consumer Key",
        "descricao": "Chave do app Twitter",
        "onde_obter": "https://developer.x.com",
        "obrigatorio": False
    },
    "INSTAGRAM_TOKEN": {
        "nome": "Instagram Access Token",
        "descricao": "Para postar no Instagram automaticamente",
        "onde_obter": "https://developers.facebook.com",
        "obrigatorio": False
    },
    "REPLICATE_API_TOKEN": {
        "nome": "Replicate (IA Visual Midjourney)",
        "descricao": "Para gerar imagens estilo Midjourney barato",
        "onde_obter": "https://replicate.com/account/api-tokens",
        "obrigatorio": False
    },
    "YOUTUBE_API_KEY": {
        "nome": "YouTube Data API",
        "descricao": "Para publicar e gerenciar videos no YouTube",
        "onde_obter": "https://console.cloud.google.com",
        "obrigatorio": False
    },
    "LINKEDIN_TOKEN": {
        "nome": "LinkedIn Access Token",
        "descricao": "Para postar no LinkedIn automaticamente",
        "onde_obter": "https://www.linkedin.com/developers",
        "obrigatorio": False
    },
    "WHATSAPP_TOKEN": {
        "nome": "WhatsApp Business API",
        "descricao": "Para enviar mensagens pelo WhatsApp",
        "onde_obter": "https://developers.facebook.com/docs/whatsapp",
        "obrigatorio": False
    },
    "OPENROUTER_API_KEY": {
        "nome": "OpenRouter (Modelos alternativos)",
        "descricao": "Acesso a GPT-4, Claude, Gemini por um lugar só",
        "onde_obter": "https://openrouter.ai/keys",
        "obrigatorio": False
    },
    "ELEVENLABS_API_KEY": {
        "nome": "ElevenLabs (Voz IA)",
        "descricao": "Para gerar voz realista com IA",
        "onde_obter": "https://elevenlabs.io/profile",
        "obrigatorio": False
    },
    "STABILITY_API_KEY": {
        "nome": "Stability AI (Stable Diffusion)",
        "descricao": "Para gerar imagens de alta qualidade",
        "onde_obter": "https://platform.stability.ai/account/keys",
        "obrigatorio": False
    },
    "FIVERR_API_KEY": {
        "nome": "Fiverr API",
        "descricao": "Para gerenciar pedidos no Fiverr",
        "onde_obter": "https://developers.fiverr.com",
        "obrigatorio": False
    },
    "HOTMART_TOKEN": {
        "nome": "Hotmart API",
        "descricao": "Para gerenciar produtos e vendas na Hotmart",
        "onde_obter": "https://developers.hotmart.com",
        "obrigatorio": False
    },
    "ROBLOX_API_KEY": {
        "nome": "Roblox Open Cloud API",
        "descricao": "Para gerenciar jogos e publicar no Roblox",
        "onde_obter": "https://create.roblox.com/credentials",
        "obrigatorio": False
    }
}

def verificar_chave(nome_chave: str) -> bool:
    valor = os.getenv(nome_chave, "")
    return bool(valor and valor.strip())

def salvar_chave(nome_chave: str, valor: str) -> bool:
    try:
        set_key(str(ENV_FILE), nome_chave, valor)
        os.environ[nome_chave] = valor
        return True
    except Exception as e:
        print(f"Erro ao salvar chave: {e}")
        return False

def get_chaves_faltando() -> list:
    faltando = []
    for chave, info in CHAVES_CONHECIDAS.items():
        if not verificar_chave(chave):
            faltando.append({
                "chave": chave,
                "nome": info["nome"],
                "descricao": info["descricao"],
                "onde_obter": info["onde_obter"],
                "obrigatorio": info["obrigatorio"]
            })
    return faltando

def get_status_chaves() -> str:
    resultado = "🔑 *Status das APIs:*\n\n"
    for chave, info in CHAVES_CONHECIDAS.items():
        status = "✅" if verificar_chave(chave) else "❌"
        resultado += f"{status} {info['nome']}\n"
    return resultado

def salvar_chave_pendente(nome_chave: str, user_id: str):
    CHAVES_FILE.parent.mkdir(exist_ok=True)
    dados = {}
    if CHAVES_FILE.exists():
        with open(CHAVES_FILE, "r") as f:
            dados = json.load(f)
    dados[user_id] = nome_chave
    with open(CHAVES_FILE, "w") as f:
        json.dump(dados, f)

def get_chave_pendente(user_id: str) -> str:
    if not CHAVES_FILE.exists():
        return ""
    with open(CHAVES_FILE, "r") as f:
        dados = json.load(f)
    return dados.get(user_id, "")

def remover_chave_pendente(user_id: str):
    if not CHAVES_FILE.exists():
        return
    with open(CHAVES_FILE, "r") as f:
        dados = json.load(f)
    dados.pop(user_id, None)
    with open(CHAVES_FILE, "w") as f:
        json.dump(dados, f)

def get_info_chave(nome_chave: str) -> dict:
    return CHAVES_CONHECIDAS.get(nome_chave, {
        "nome": nome_chave,
        "descricao": "Chave personalizada",
        "onde_obter": "Fornecida pelo servico",
        "obrigatorio": False
    })

def adicionar_chave_livre(nome_chave: str, valor: str) -> str:
    """Adiciona qualquer chave mesmo que nao esteja pre-programada"""
    nome_chave = nome_chave.upper().replace(" ", "_")
    if salvar_chave(nome_chave, valor):
        return f"✅ Chave {nome_chave} salva com sucesso!"
    return f"❌ Erro ao salvar chave {nome_chave}"

def listar_todas_chaves() -> str:
    """Lista todas as chaves do .env"""
    try:
        resultado = "📋 *Todas as chaves no sistema:*\n\n"
        with open(ENV_FILE, "r") as f:
            linhas = f.readlines()
        for linha in linhas:
            if "=" in linha and not linha.startswith("#"):
                nome = linha.split("=")[0].strip()
                tem_valor = len(linha.split("=")[1].strip()) > 0
                status = "✅" if tem_valor else "❌"
                resultado += f"{status} {nome}\n"
        return resultado
    except Exception as e:
        return f"❌ Erro: {e}"