import os
import base64
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ASSETS_DIR = Path(__file__).parent.parent / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

# ── System prompt para análise visual ────────────────────────────────────────

VISAO_SYSTEM = """Você é a Verônica, assistente visual inteligente do Elisson.
Ao analisar imagens e screenshots:
- Seja detalhista e precisa — descreva o que realmente está visível
- Use linguagem natural e direta em português brasileiro
- Organize a análise de forma clara (use tópicos quando necessário)
- Destaque o que é mais relevante para o contexto ou objetivo
- Sugira ações práticas quando houver um objetivo definido
- Se houver texto na imagem, transcreva os trechos mais importantes
- Se for um gráfico ou dados, interprete o que eles significam"""


# ── Utilitários ───────────────────────────────────────────────────────────────

def imagem_para_base64(caminho: str) -> str:
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def detectar_tipo_imagem(caminho: str) -> str:
    ext = Path(caminho).suffix.lower()
    tipos = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".gif": "gif", ".webp": "webp"}
    return tipos.get(ext, "png")


def salvar_screenshot(sufixo: str = "") -> str:
    """Tira screenshot e salva com timestamp."""
    try:
        import pyautogui
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome = f"screenshot_{timestamp}{sufixo}.png"
        caminho = str(ASSETS_DIR / nome)
        pyautogui.screenshot(caminho)
        return caminho
    except Exception as e:
        raise Exception(f"Erro ao tirar screenshot: {e}")


# ── Provedores de visão ───────────────────────────────────────────────────────

def descrever_com_groq(caminho: str, pergunta: str) -> str:
    """Usa Groq com modelo multimodal (llama-4-scout)."""
    try:
        imagem_b64 = imagem_para_base64(caminho)
        tipo = detectar_tipo_imagem(caminho)

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": VISAO_SYSTEM
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": pergunta},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/{tipo};base64,{imagem_b64}"}
                        }
                    ]
                }
            ],
            "max_tokens": 2048,
            "temperature": 0.5,
        }
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=45
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"__groq_erro_{r.status_code}__"
    except Exception as e:
        return f"__groq_erro_{e}__"


def descrever_com_gemini(caminho: str, pergunta: str) -> str:
    """Usa Google Gemini Vision como fallback."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        with open(caminho, "rb") as f:
            dados_imagem = f.read()

        tipo = detectar_tipo_imagem(caminho)
        image_part = {"mime_type": f"image/{tipo}", "data": dados_imagem}

        prompt_completo = f"{VISAO_SYSTEM}\n\n{pergunta}"
        resposta = model.generate_content([prompt_completo, image_part])
        return resposta.text
    except Exception as e:
        return f"__gemini_erro_{e}__"


def descrever_com_openai(caminho: str, pergunta: str) -> str:
    """Usa OpenAI GPT-4o Vision como último recurso."""
    try:
        imagem_b64 = imagem_para_base64(caminho)
        tipo = detectar_tipo_imagem(caminho)

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": VISAO_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": pergunta},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/{tipo};base64,{imagem_b64}"}
                        }
                    ]
                }
            ],
            "max_tokens": 2048,
        }
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers, json=payload, timeout=45
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"__openai_erro_{r.status_code}__"
    except Exception as e:
        return f"__openai_erro_{e}__"


def descrever_imagem(caminho: str, pergunta: str) -> str:
    """Cadeia de fallback: Groq → Gemini → OpenAI."""
    # Tenta Groq primeiro (gratuito e rápido)
    resultado = descrever_com_groq(caminho, pergunta)
    if not resultado.startswith("__groq_erro"):
        return resultado

    # Fallback: Gemini
    resultado = descrever_com_gemini(caminho, pergunta)
    if not resultado.startswith("__gemini_erro"):
        return resultado

    # Último recurso: OpenAI
    resultado = descrever_com_openai(caminho, pergunta)
    if not resultado.startswith("__openai_erro"):
        return resultado

    return "❌ Nenhum provedor de visão disponível. Verifique as chaves de API."


# ── Funções de alto nível ─────────────────────────────────────────────────────

def tirar_e_descrever(pergunta: str = "O que você vê nessa tela? Descreva tudo em detalhes.") -> tuple:
    """Tira screenshot e descreve o conteúdo."""
    try:
        caminho = salvar_screenshot()
        descricao = descrever_imagem(caminho, pergunta)
        return caminho, descricao
    except Exception as e:
        return "", f"❌ Erro ao capturar tela: {e}"


def analisar_imagem_enviada(caminho: str, pergunta: str = "O que você vê nessa imagem?") -> str:
    """Analisa uma imagem enviada pelo usuário."""
    if not Path(caminho).exists():
        return "❌ Arquivo de imagem não encontrado."
    return descrever_imagem(caminho, pergunta)


def ver_e_agir(objetivo: str) -> str:
    """Vê a tela atual e sugere ações para atingir um objetivo."""
    pergunta = f"""Analise essa tela com foco no objetivo: {objetivo}

Por favor, responda:
1. **O que está visível na tela** (descreva os elementos principais)
2. **O que está relevante para o objetivo** (filtre o que importa)
3. **Próxima ação recomendada** (seja específico: onde clicar, o que digitar, etc.)
4. **Possíveis obstáculos** (se houver algo que possa atrapalhar)

Seja direto e prático. O Elisson vai executar a ação baseado na sua análise."""

    caminho, descricao = tirar_e_descrever(pergunta)
    if not caminho:
        return descricao

    return f"👁️ *Análise da tela:*\n\n{descricao}\n\n🎯 *Objetivo:* {objetivo}"


def analisar_codigo_na_tela() -> str:
    """Especializada em analisar código/terminal visível na tela."""
    pergunta = """Analise o código ou terminal visível na tela:

1. **O que esse código faz** (resumo em linguagem simples)
2. **Linguagem/tecnologia** identificada
3. **Erros ou problemas** visíveis (destaque em vermelho mental)
4. **Sugestões de melhoria** (se aplicável)
5. **Transcrição dos trechos mais importantes** (copie o texto crítico)

Seja técnico e preciso. Foco em ser útil para o desenvolvedor."""

    caminho, descricao = tirar_e_descrever(pergunta)
    if not caminho:
        return descricao
    return f"💻 *Análise do código na tela:*\n\n{descricao}"


def analisar_grafico_na_tela() -> str:
    """Especializada em analisar gráficos e dados financeiros na tela."""
    pergunta = """Analise o gráfico ou dados visíveis na tela:

1. **Tipo de gráfico/visualização** (candlestick, linha, barra, etc.)
2. **Ativo ou dado sendo mostrado** (nome, ticker, período)
3. **Tendência atual** (alta, baixa, lateralização)
4. **Níveis importantes** (suporte, resistência, médias visíveis)
5. **Sinais técnicos** visíveis (padrões, cruzamentos, divergências)
6. **Interpretação geral** (o que esse gráfico está dizendo)

Se não for um gráfico financeiro, adapte a análise para o tipo de dado visível.
Seja analítico e objetivo."""

    caminho, descricao = tirar_e_descrever(pergunta)
    if not caminho:
        return descricao
    return f"📊 *Análise do gráfico:*\n\n{descricao}"


def ler_texto_na_tela() -> str:
    """Extrai e transcreve todo texto visível na tela."""
    pergunta = """Extraia TODO o texto visível nessa imagem/tela:

- Transcreva fielmente, mantendo a formatação original quando possível
- Se houver múltiplas seções, separe-as claramente
- Destaque títulos, botões e elementos de interface
- Se houver texto em imagem, transcreva também
- Ignore elementos decorativos sem texto

Retorne apenas o texto extraído, organizado e limpo."""

    caminho, texto = tirar_e_descrever(pergunta)
    if not caminho:
        return texto
    return f"📝 *Texto extraído da tela:*\n\n{texto}"


def comparar_imagens(caminho1: str, caminho2: str, foco: str = "diferenças") -> str:
    """Compara duas imagens e descreve as diferenças."""
    if not Path(caminho1).exists() or not Path(caminho2).exists():
        return "❌ Uma ou ambas as imagens não foram encontradas."

    # Analisa as duas separadamente e compara
    desc1 = descrever_imagem(caminho1, "Descreva essa imagem em detalhes para comparação.")
    desc2 = descrever_imagem(caminho2, "Descreva essa imagem em detalhes para comparação.")

    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT
    prompt = f"""Compare essas duas descrições de imagens e foque em: {foco}

IMAGEM 1:
{desc1}

IMAGEM 2:
{desc2}

Analise:
1. Principais diferenças
2. O que mudou entre as duas
3. O que permaneceu igual
4. Qual das duas é melhor (se aplicável) e por quê

Seja específico e organize por seções."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return chamar_groq(mensagens, temperatura=0.5)
    except Exception:
        from modules.ai_brain import chamar_gemini
        return chamar_gemini(prompt, [])


# Aliases para compatibilidade
descrever_imagem_openai = descrever_com_openai
descrever_imagem_groq = descrever_com_groq
