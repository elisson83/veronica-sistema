codigo = '''import os
import requests
import base64
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "geradas"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

def gerar_imagem_pollinations(prompt: str, largura: int = 1024, altura: int = 1024) -> str:
    try:
        import urllib.parse
        prompt_encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width={largura}&height={altura}&nologo=true"
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = str(ASSETS_DIR / f"img_{timestamp}.png")
            with open(caminho, "wb") as f:
                f.write(r.content)
            return caminho
        return f"ERRO ao gerar imagem: {r.status_code}"
    except Exception as e:
        return f"ERRO: {e}"

def gerar_imagem_dalle(descricao: str, tamanho: str = "1024x1024") -> str:
    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "ERRO: OPENAI_API_KEY nao configurada!"
        client = openai.OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=descricao,
            size=tamanho,
            quality="standard",
            n=1
        )
        image_url = response.data[0].url
        r = requests.get(image_url, timeout=30)
        if r.status_code == 200:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = str(ASSETS_DIR / f"dalle_{timestamp}.png")
            with open(caminho, "wb") as f:
                f.write(r.content)
            return caminho
        return f"ERRO ao baixar imagem: {r.status_code}"
    except Exception as e:
        return f"ERRO DALL-E: {e}"

def gerar_imagem_inteligente(descricao: str) -> tuple:
    try:
        import openai
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            client = openai.OpenAI(api_key=api_key)
            response = client.images.generate(
                model="dall-e-3",
                prompt=descricao,
                size="1024x1024",
                quality="standard",
                n=1
            )
            image_url = response.data[0].url
            r = requests.get(image_url, timeout=30)
            if r.status_code == 200:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                caminho = str(ASSETS_DIR / f"dalle_{timestamp}.png")
                with open(caminho, "wb") as f:
                    f.write(r.content)
                return caminho, "DALL-E 3"
    except Exception as e:
        print(f"DALL-E falhou: {e} usando Pollinations...")
    caminho = gerar_imagem_pollinations(descricao)
    return caminho, "Pollinations (gratuito)"

def gerar_imagem(descricao: str, estilo: str = "realista") -> tuple:
    estilos = {
        "realista": "photorealistic, high quality, detailed, 8k",
        "arte": "digital art, artistic, colorful, detailed illustration",
        "logo": "logo design, professional, clean, vector style, white background",
        "banner": "banner design, professional, marketing, wide format",
        "cartoon": "cartoon style, colorful, fun, animated",
        "minimalista": "minimalist design, clean, simple, modern"
    }
    sufixo = estilos.get(estilo.lower(), estilos["realista"])
    prompt_completo = f"{descricao}, {sufixo}"
    caminho = gerar_imagem_pollinations(prompt_completo)
    return caminho, prompt_completo

def gerar_logo(nome_empresa: str, nicho: str, cores: str = "azul e branco") -> tuple:
    prompt = f"Professional logo for {nome_empresa}, {nicho} company, colors: {cores}, minimalist, clean, vector style, white background, professional business logo design"
    return gerar_imagem_inteligente(prompt)

def gerar_banner_post(tema: str, rede: str = "instagram") -> tuple:
    prompt = f"Social media {rede} post design about {tema}, professional, modern, eye-catching, marketing design, vibrant colors"
    return gerar_imagem_inteligente(prompt)

def gerar_capa_ebook(titulo: str, subtitulo: str = "") -> tuple:
    prompt = f"Professional ebook cover design titled {titulo}, modern design, professional, book cover, attractive, high quality"
    return gerar_imagem_inteligente(prompt)

def gerar_avatar_ia(nome: str, personalidade: str = "profissional e amigavel") -> tuple:
    prompt = f"AI assistant avatar named {nome}, personality: {personalidade}, digital art style, futuristic, friendly face, professional"
    return gerar_imagem_inteligente(prompt)
'''

with open("modules/visao_geradora.py", "w", encoding="utf-8") as f:
    f.write(codigo)
print("visao_geradora.py recriado com sucesso!")