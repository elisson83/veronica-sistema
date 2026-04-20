import os
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

def transformar_foto_anime(caminho_imagem: str, estilo: str = "anime") -> tuple:
    """Transforma uma foto em estilo anime/cartoon usando IA"""
    try:
        import base64
        
        # Le a imagem e converte para base64
        with open(caminho_imagem, "rb") as f:
            imagem_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        estilos = {
            "anime": "anime style, japanese animation, detailed anime art, Studio Ghibli style",
            "cartoon": "cartoon style, Disney animation, colorful cartoon, fun animated style",
            "pixar": "Pixar 3D animation style, detailed 3D cartoon, Pixar movie style",
            "sketch": "pencil sketch, black and white drawing, artistic sketch style",
            "watercolor": "watercolor painting, artistic, soft colors, painting style"
        }
        
        descricao_estilo = estilos.get(estilo.lower(), estilos["anime"])
        
        # Tenta usar DALL-E para transformacao
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                client = openai.OpenAI(api_key=api_key)
                
                # Primeiro analisa a imagem
                response_analise = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Descreva detalhadamente esta imagem em ingles para eu recriar em estilo anime. Inclua: genero, cabelo, olhos, roupas, expressao, fundo. Seja muito detalhado."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagem_b64}"}}
                        ]
                    }],
                    max_tokens=300
                )
                
                descricao = response_analise.choices[0].message.content
                prompt_final = f"{descricao}, converted to {descricao_estilo}, high quality, detailed"
                
                # Gera a imagem no estilo solicitado
                response_img = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt_final,
                    size="1024x1024",
                    quality="standard",
                    n=1
                )
                
                image_url = response_img.data[0].url
                r = requests.get(image_url, timeout=30)
                if r.status_code == 200:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    caminho = str(ASSETS_DIR / f"anime_{timestamp}.png")
                    with open(caminho, "wb") as f:
                        f.write(r.content)
                    return caminho, f"DALL-E 3 ({estilo})"
        except Exception as e:
            print(f"DALL-E falhou: {e}")
        
        # Fallback: Pollinations com descricao generica
        prompt = f"portrait photo transformed into {descricao_estilo}, high quality, detailed"
        caminho = gerar_imagem_pollinations(prompt)
        return caminho, f"Pollinations ({estilo})"
        
    except Exception as e:
        return f"ERRO: {e}", "erro"
