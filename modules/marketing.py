import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

DATA_DIR = Path(__file__).parent.parent / "data"
MARKETING_FILE = DATA_DIR / "marketing.json"
DATA_DIR.mkdir(exist_ok=True)

def carregar_dados() -> dict:
    try:
        if MARKETING_FILE.exists():
            with open(MARKETING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {"posts": [], "calendario": [], "estrategias": []}

def salvar_dados(dados: dict):
    with open(MARKETING_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def criar_post_otimizado(tema: str, rede: str, tom: str = "profissional") -> str:
    from modules.ai_brain import perguntar_ia
    redes_config = {
        "instagram": {
            "limite": 2200,
            "hashtags": 30,
            "formato": "visual e emocional com emojis"
        },
        "facebook": {
            "limite": 63206,
            "hashtags": 10,
            "formato": "conversacional e informativo"
        },
        "twitter": {
            "limite": 280,
            "hashtags": 3,
            "formato": "direto e impactante"
        },
        "linkedin": {
            "limite": 3000,
            "hashtags": 5,
            "formato": "profissional e educativo"
        },
        "tiktok": {
            "limite": 2200,
            "hashtags": 20,
            "formato": "jovem, divertido e viral"
        }
    }

    config = redes_config.get(rede.lower(), redes_config["instagram"])

    prompt = f"""
    Crie um post COMPLETO e OTIMIZADO para {rede.upper()} sobre: {tema}
    
    Configurações:
    - Tom: {tom}
    - Formato: {config['formato']}
    - Limite de caracteres: {config['limite']}
    - Máximo de hashtags: {config['hashtags']}
    
    O post deve ter:
    1. Texto principal envolvente
    2. Call to action (CTA) forte
    3. Hashtags otimizadas para alcance
    4. Emojis relevantes (se adequado para a rede)
    
    Crie em português brasileiro.
    Retorne APENAS o post pronto para copiar e colar.
    """

    resposta = perguntar_ia(prompt, "marketing")

    # Salva no histórico
    dados = carregar_dados()
    dados["posts"].append({
        "tema": tema,
        "rede": rede,
        "tom": tom,
        "conteudo": resposta,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    salvar_dados(dados)

    return resposta

def criar_calendario_editorial(nicho: str, dias: int = 30) -> str:
    from modules.ai_brain import perguntar_ia

    prompt = f"""
    Crie um calendário editorial completo para {dias} dias para o nicho: {nicho}
    
    Para cada semana inclua:
    - Segunda: tipo de post e tema
    - Quarta: tipo de post e tema  
    - Sexta: tipo de post e tema
    - Domingo: tipo de post e tema
    
    Tipos de post: Educativo, Motivacional, Produto/Serviço, Bastidores, Dica, Pergunta, Meme/Humor
    
    Organize por semanas e seja específico nos temas.
    Formato limpo e fácil de seguir.
    """

    resposta = perguntar_ia(prompt, "marketing")

    dados = carregar_dados()
    dados["calendario"].append({
        "nicho": nicho,
        "dias": dias,
        "conteudo": resposta,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    salvar_dados(dados)

    return resposta

def criar_estrategia_completa(negocio: str, objetivo: str) -> str:
    from modules.ai_brain import perguntar_ia

    prompt = f"""
    Crie uma estratégia completa de marketing digital para:
    Negócio: {negocio}
    Objetivo: {objetivo}
    
    A estratégia deve incluir:
    
    1. ANÁLISE DO PÚBLICO-ALVO
    - Perfil demográfico
    - Dores e desejos
    - Onde está online
    
    2. REDES SOCIAIS PRIORITÁRIAS
    - Quais usar e por quê
    - Frequência de posts
    - Melhor horário para postar
    
    3. TIPOS DE CONTEÚDO
    - Formatos que funcionam
    - Proporção (80% valor / 20% venda)
    
    4. FUNIL DE VENDAS
    - Topo: como atrair
    - Meio: como engajar
    - Fundo: como converter
    
    5. MÉTRICAS PARA ACOMPANHAR
    - KPIs principais
    - Metas mensais
    
    6. CRONOGRAMA 90 DIAS
    - Mês 1: o que fazer
    - Mês 2: o que fazer
    - Mês 3: o que fazer
    
    Seja específico e prático para o negócio descrito.
    """

    resposta = perguntar_ia(prompt, "marketing")

    dados = carregar_dados()
    dados["estrategias"].append({
        "negocio": negocio,
        "objetivo": objetivo,
        "conteudo": resposta,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    salvar_dados(dados)

    return resposta

def criar_copy_vendas(produto: str, publico: str, preco: str = "") -> str:
    from modules.ai_brain import perguntar_ia

    prompt = f"""
    Crie uma copy de vendas PERSUASIVA e COMPLETA para:
    Produto/Serviço: {produto}
    Público-alvo: {publico}
    {'Preço: ' + preco if preco else ''}
    
    A copy deve ter:
    1. HEADLINE impactante (3 opções)
    2. SUBHEADLINE
    3. PROBLEMA que resolve
    4. SOLUÇÃO oferecida
    5. BENEFÍCIOS (lista com bullets)
    6. PROVA SOCIAL (sugestão de depoimentos)
    7. OFERTA e GARANTIA
    8. CTA (Call to Action) forte
    
    Use gatilhos mentais: urgência, escassez, autoridade, prova social.
    Escreva em português brasileiro persuasivo.
    """

    return perguntar_ia(prompt, "marketing")

def analisar_concorrente(concorrente: str, nicho: str) -> str:
    from modules.ai_brain import perguntar_ia

    prompt = f"""
    Faça uma análise estratégica do concorrente/nicho:
    Concorrente/Referência: {concorrente}
    Nicho: {nicho}
    
    Analise:
    1. PONTOS FORTES prováveis
    2. PONTOS FRACOS prováveis  
    3. OPORTUNIDADES para se diferenciar
    4. ESTRATÉGIAS que provavelmente usam
    5. COMO SE DIFERENCIAR
    6. PALAVRAS-CHAVE que provavelmente usam
    
    Dê sugestões práticas de como superar ou se diferenciar.
    """

    return perguntar_ia(prompt, "marketing")

def get_tendencias(nicho: str) -> str:
    from modules.pesquisa import pesquisar_web
    from modules.ai_brain import perguntar_ia

    pesquisa = pesquisar_web(f"tendências marketing {nicho} 2026")

    prompt = f"""
    Com base nas tendências de marketing para {nicho} em 2026:
    {pesquisa}
    
    Resuma:
    1. TOP 5 tendências mais importantes
    2. Como aplicar cada uma
    3. Ferramentas recomendadas
    4. O que evitar
    
    Seja prático e objetivo.
    """

    return perguntar_ia(prompt, "marketing")

def listar_posts() -> str:
    dados = carregar_dados()
    posts = dados.get("posts", [])
    if not posts:
        return "📭 Nenhum post criado ainda."
    
    resultado = f"📱 *Posts criados ({len(posts)} total):*\n\n"
    for i, post in enumerate(posts[-5:], 1):
        resultado += f"{i}. *{post['rede'].upper()}* — {post['tema'][:50]}\n"
        resultado += f"   📅 {post['criado_em']}\n\n"
    return resultado