import os
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def imagem_para_base64(caminho: str) -> str:
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def descrever_imagem_openai(caminho: str, pergunta: str = "O que você vê nessa tela?") -> str:
    try:
        imagem_b64 = imagem_para_base64(caminho)
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Você é a Verônica, assistente do Elisson. {pergunta} Responda em português brasileiro de forma clara e objetiva."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{imagem_b64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1024
        }
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"❌ Erro OpenAI: {r.status_code} - {r.text}"
    except Exception as e:
        return f"❌ Erro ao descrever imagem: {e}"

def descrever_imagem_groq(caminho: str, pergunta: str = "O que você vê nessa tela?") -> str:
    try:
        imagem_b64 = imagem_para_base64(caminho)
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Você é a Verônica, assistente do Elisson. {pergunta} Responda em português brasileiro de forma clara e objetiva."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{imagem_b64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1024
        }
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"❌ Erro Groq Vision: {r.status_code} - {r.text}"
    except Exception as e:
        return f"❌ Erro ao descrever imagem: {e}"

def tirar_e_descrever(pergunta: str = "O que você vê nessa tela? Descreva tudo em detalhes.") -> tuple:
    try:
        import pyautogui
        from datetime import datetime
        assets_dir = Path(__file__).parent.parent / "assets"
        assets_dir.mkdir(exist_ok=True)
        caminho = str(assets_dir / f"screenshot_{datetime.now().strftime('%H%M%S')}.png")
        pyautogui.screenshot(caminho)

        # Tenta Groq primeiro (gratuito), depois OpenAI
        descricao = descrever_imagem_groq(caminho, pergunta)
        if descricao.startswith("❌"):
            descricao = descrever_imagem_openai(caminho, pergunta)

        return caminho, descricao
    except Exception as e:
        return "", f"❌ Erro: {e}"

def ver_e_agir(objetivo: str) -> str:
    try:
        caminho, descricao = tirar_e_descrever(
            f"Analise essa tela. O objetivo é: {objetivo}. "
            f"Descreva o que você vê e sugira qual ação tomar para atingir o objetivo. "
            f"Seja específico sobre onde clicar, o que digitar, etc."
        )
        if not caminho:
            return descricao

        return (
            f"👁️ *Análise da tela:*\n\n"
            f"{descricao}\n\n"
            f"🎯 *Objetivo:* {objetivo}"
        )
    except Exception as e:
        return f"❌ Erro: {e}"

def analisar_imagem_enviada(caminho: str, pergunta: str = "O que você vê nessa imagem?") -> str:
    descricao = descrever_imagem_groq(caminho, pergunta)
    if descricao.startswith("❌"):
        descricao = descrever_imagem_openai(caminho, pergunta)
    return descricao