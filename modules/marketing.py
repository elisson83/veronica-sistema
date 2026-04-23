import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

DATA_DIR = Path(__file__).parent.parent / "data"
MARKETING_FILE = DATA_DIR / "marketing.json"
DATA_DIR.mkdir(exist_ok=True)


# ── Persistência ──────────────────────────────────────────────────────────────

def carregar_dados() -> dict:
    try:
        if MARKETING_FILE.exists():
            with open(MARKETING_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"posts": [], "calendario": [], "estrategias": [], "copies": [], "analises": []}


def salvar_dados(dados: dict):
    with open(MARKETING_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


# ── Configuração das redes ────────────────────────────────────────────────────

REDES_CONFIG = {
    "instagram": {
        "limite": 2200,
        "hashtags": 30,
        "formato": "visual, emocional e com storytelling. Use emojis estrategicamente. Stories primeiro, feed depois.",
        "melhores_horarios": "12h, 18h e 21h",
        "dicas": "Use os primeiros 2 segundos para prender. Quebre em parágrafos curtos. CTA no final.",
        "viral_hooks": ["POV:", "Ninguém te conta isso:", "Errei muito até descobrir:", "Fiz X em Y dias:"]
    },
    "facebook": {
        "limite": 63206,
        "hashtags": 5,
        "formato": "conversacional, informativo e que gera debate. Faça perguntas para engajar.",
        "melhores_horarios": "13h e 16h",
        "dicas": "Posts com perguntas geram 2x mais comentários. Use vídeos curtos.",
        "viral_hooks": ["Vou ser honesto:", "Opinião impopular:", "Aprendi isso da pior forma:"]
    },
    "twitter": {
        "limite": 280,
        "hashtags": 3,
        "formato": "direto, impactante e com opinião forte. Uma ideia clara por tweet.",
        "melhores_horarios": "8h, 12h e 17h",
        "dicas": "Threads performam melhor. Seja polêmico (com respeito). Responda mentions.",
        "viral_hooks": ["Hot take:", "Ninguém fala mas:", "Depois de X anos aprendi:"]
    },
    "linkedin": {
        "limite": 3000,
        "hashtags": 5,
        "formato": "profissional com storytelling pessoal. Mostre vulnerabilidade estratégica.",
        "melhores_horarios": "8h, 12h e 17h (dias úteis)",
        "dicas": "Primeiras 3 linhas são cruciais (ver mais). Use listas. Case pessoal > teoria.",
        "viral_hooks": ["Fui demitido e aprendi:", "Erro que me custou R$X:", "O que mudou minha carreira:"]
    },
    "tiktok": {
        "limite": 2200,
        "hashtags": 20,
        "formato": "rápido, autêntico e com gancho nos primeiros 3 segundos. Tendências e sons virais.",
        "melhores_horarios": "7h, 14h e 21h",
        "dicas": "Gancho fortíssimo no início. Mostre o resultado antes do processo. POV funciona.",
        "viral_hooks": ["Se eu soubesse disso antes:", "Testei por 30 dias:", "Vai mudar sua vida:"]
    },
    "youtube": {
        "limite": 5000,
        "hashtags": 15,
        "formato": "título + descrição otimizada para SEO. Destaque timestamps. Link nos primeiros.",
        "melhores_horarios": "14h a 16h (sexta e sábado)",
        "dicas": "Thumbnail é 80% do sucesso. Primeiros 30 segundos definem retenção. Pede like cedo.",
        "viral_hooks": ["Como eu fiz X sem Y:", "O método que ninguém ensina:", "Resultado honesto de:"]
    },
    "whatsapp": {
        "limite": 1000,
        "hashtags": 0,
        "formato": "pessoal, direto e conversacional. Listas e emojis moderados.",
        "melhores_horarios": "8h, 12h e 20h",
        "dicas": "Listas de transmissão > grupos. Áudio converte mais que texto. Seja consistente.",
        "viral_hooks": ["Oi! Preciso te contar algo:", "Só quem tem lista vip vê isso:", "Aviso exclusivo:"]
    }
}

TONS = {
    "profissional": "sério, confiante, baseado em dados e autoridade",
    "descontraído": "amigável, próximo, com humor leve e linguagem casual",
    "motivacional": "energético, inspirador, focado em transformação e conquista",
    "educativo": "didático, claro, com exemplos e passo a passo",
    "urgente": "senso de urgência sem parecer spam — escassez real e honesta",
    "storytelling": "narrativa pessoal envolvente, começa com conflito e termina com transformação",
    "vendas": "persuasivo com gatilhos mentais: prova social, escassez, autoridade, reciprocidade",
    "viral": "polêmico (com respeito), opinion piece, contraintuitivo, inesperado",
}


# ── Funções principais ────────────────────────────────────────────────────────

def criar_post_otimizado(tema: str, rede: str, tom: str = "profissional", contexto: str = "") -> str:
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    config = REDES_CONFIG.get(rede.lower(), REDES_CONFIG["instagram"])
    descricao_tom = TONS.get(tom.lower(), TONS["profissional"])
    hooks = config.get("viral_hooks", [])
    hooks_texto = "\n".join([f"  • {h}" for h in hooks])

    prompt = f"""Crie um post COMPLETO, ORIGINAL e de ALTA PERFORMANCE para {rede.upper()}.

TEMA: {tema}
{f'CONTEXTO ADICIONAL: {contexto}' if contexto else ''}

PARÂMETROS:
- Tom: {tom} ({descricao_tom})
- Formato ideal: {config['formato']}
- Limite: {config['limite']} caracteres
- Hashtags: até {config['hashtags']}
- Melhor horário para postar: {config['melhores_horarios']}

GANCHOS QUE FUNCIONAM PARA {rede.upper()}:
{hooks_texto}

DICAS DA PLATAFORMA:
{config['dicas']}

ESTRUTURA DO POST:
1. **GANCHO** (primeiras palavras — deve parar o scroll imediatamente)
2. **DESENVOLVIMENTO** (conteúdo de valor — eduque, inspire ou entretenha)
3. **VIRADA OU INSIGHT** (o momento "nossa" que fica na cabeça)
4. **CTA** (uma ação clara: comentar, salvar, compartilhar, clicar no link)
5. **HASHTAGS** (se aplicável — misture grandes e de nicho)

REGRAS:
- Escreva em português brasileiro autêntico (não traduzido)
- Seja específico, não genérico — exemplos reais convertem mais
- Evite clichês como "No mundo de hoje" e "Em um mercado cada vez mais"
- O post deve fazer a pessoa sentir algo (curiosidade, esperança, identificação)

Retorne APENAS o post pronto, sem explicações. Pronto para copiar e colar."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        resposta = chamar_groq(mensagens, temperatura=0.88, max_tokens=2048)
    except Exception:
        from modules.ai_brain import chamar_gemini
        resposta = chamar_gemini(prompt, [])

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


def criar_post_variações(tema: str, rede: str, qtd: int = 3) -> str:
    """Cria múltiplas variações de um mesmo post para teste A/B."""
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    config = REDES_CONFIG.get(rede.lower(), REDES_CONFIG["instagram"])

    prompt = f"""Crie {qtd} variações DIFERENTES de post para {rede.upper()} sobre: {tema}

Cada variação deve ter:
- Um gancho diferente (abordagem distinta do mesmo tema)
- Estrutura e tom diferente entre si
- Todas otimizadas para {config['formato']}
- Máximo de {config['hashtags']} hashtags cada

Separe as variações claramente com:
---VARIAÇÃO 1---
[post]
---VARIAÇÃO 2---
[post]
(e assim por diante)

Objetivo: ajudar a fazer teste A/B e descobrir o que performa melhor.
Escreva em português brasileiro. Retorne APENAS as variações."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return chamar_groq(mensagens, temperatura=0.92, max_tokens=3000)
    except Exception:
        from modules.ai_brain import chamar_gemini
        return chamar_gemini(prompt, [])


def criar_calendario_editorial(nicho: str, dias: int = 30, redes: list = None) -> str:
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    if redes is None:
        redes = ["Instagram", "LinkedIn"]
    redes_texto = ", ".join(redes)

    prompt = f"""Crie um calendário editorial detalhado para {dias} dias no nicho: {nicho}
Redes: {redes_texto}

SEMANAS (repita o padrão para cobrir {dias} dias):

Para cada dia com post, inclua:
- 📅 Dia da semana e data relativa (Semana 1 - Segunda, etc.)
- 📱 Rede social
- 🎯 Tipo: [Educativo / Motivacional / Produto / Bastidores / Dica / Pergunta / Case / Meme]
- 💡 Tema específico (não genérico — seja preciso)
- 🎣 Sugestão de gancho de abertura
- #️⃣ 3 hashtags principais

FREQUÊNCIA RECOMENDADA:
- Instagram: 4-5x/semana
- LinkedIn: 3x/semana
- Twitter: 1-2x/dia

PILARES DE CONTEÚDO (distribua equilibradamente):
- 40% Educativo (ensine algo do nicho)
- 25% Inspiracional (mostre transformações, bastidores)
- 20% Engajamento (perguntas, desafios, polls)
- 15% Promocional (produto/serviço)

Seja específico nos temas — "Como precificar serviços de design em 2026" é melhor que "Dicas de precificação".
Formate de forma limpa e fácil de seguir."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        resposta = chamar_groq(mensagens, temperatura=0.75, max_tokens=4096)
    except Exception:
        from modules.ai_brain import chamar_gemini
        resposta = chamar_gemini(prompt, [])

    dados = carregar_dados()
    dados["calendario"].append({
        "nicho": nicho,
        "dias": dias,
        "redes": redes,
        "conteudo": resposta,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    salvar_dados(dados)
    return resposta


def criar_estrategia_completa(negocio: str, objetivo: str, orcamento: str = "baixo") -> str:
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    prompt = f"""Crie uma estratégia completa e ACIONÁVEL de marketing digital:

NEGÓCIO: {negocio}
OBJETIVO PRINCIPAL: {objetivo}
ORÇAMENTO: {orcamento}

---

## 1. DIAGNÓSTICO RÁPIDO
- O que está funcionando no mercado para esse nicho agora
- Principal oportunidade identificada
- Maior erro que empreendedores desse nicho cometem

## 2. AVATAR DO CLIENTE IDEAL
- Quem é (dados demográficos E comportamentais)
- Onde passa o tempo online
- Dores que te tiram o sono
- Desejos e sonhos reais
- O que pesquisa antes de comprar

## 3. POSICIONAMENTO E DIFERENCIAÇÃO
- Como se diferenciar dos concorrentes
- Proposta de valor única (UVP)
- Tom de voz e identidade da marca

## 4. CANAIS PRIORITÁRIOS
Para cada canal escolhido: por quê, frequência, formato principal e KPI

## 5. FUNIL DE AQUISIÇÃO
- Topo (descoberta): como atrair desconhecidos
- Meio (consideração): como educar e engajar
- Fundo (decisão): como converter e fechar
- Pós-venda: como fidelizar e gerar indicações

## 6. PLANO DE CONTEÚDO
- Pilares de conteúdo (4-5 temas principais)
- Tipos de conteúdo por pilar
- Frequência semanal por rede

## 7. TÁTICA DE CRESCIMENTO RÁPIDO (Quick Wins)
3 ações que podem gerar resultado em 30 dias ou menos

## 8. CRONOGRAMA 90 DIAS
- Mês 1: foco em [o quê] — meta: [X]
- Mês 2: foco em [o quê] — meta: [X]
- Mês 3: foco em [o quê] — meta: [X]

## 9. MÉTRICAS E KPIs
- 5 métricas principais para acompanhar semanalmente
- Metas realistas para cada uma

## 10. FERRAMENTAS RECOMENDADAS
Por categoria: gratuitas e pagas (com preço aproximado)

Contexto: empreendedor brasileiro, realidade do mercado nacional. Seja prático e direto."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        resposta = chamar_groq(mensagens, temperatura=0.72, max_tokens=4096)
    except Exception:
        from modules.ai_brain import chamar_gemini
        resposta = chamar_gemini(prompt, [])

    dados = carregar_dados()
    dados["estrategias"].append({
        "negocio": negocio,
        "objetivo": objetivo,
        "conteudo": resposta,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    salvar_dados(dados)
    return resposta


def criar_copy_vendas(produto: str, publico: str, preco: str = "", beneficio_principal: str = "") -> str:
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    prompt = f"""Crie uma copy de vendas PODEROSA e COMPLETA:

PRODUTO/SERVIÇO: {produto}
PÚBLICO-ALVO: {publico}
{'PREÇO: ' + preco if preco else ''}
{'BENEFÍCIO PRINCIPAL: ' + beneficio_principal if beneficio_principal else ''}

---

# HEADLINES (5 opções — do mais direto ao mais criativo)
[Cada headline em uma linha, numerada]

# SUBHEADLINE
[Uma frase que complementa o headline escolhido]

# ABERTURA (o gancho)
[2-3 parágrafos que identificam a dor e criam identificação]

# O PROBLEMA
[Aprofunda a dor sem ser pessimista — faz a pessoa se sentir compreendida]

# A SOLUÇÃO
[Apresenta o produto/serviço como a resposta natural — não força]

# COMO FUNCIONA
[Passo a passo simples — remove objeções de complexidade]

# BENEFÍCIOS (lista com bullets)
[10 benefícios — combine racionais e emocionais]
•

# PARA QUEM É (e para quem NÃO é)
[Qualifica o lead — aumenta percepção de exclusividade]

# PROVA SOCIAL
[3 depoimentos sugeridos que cobrem diferentes perfis de clientes]

# OFERTA E GARANTIA
[O que está incluído + garantia com prazo definido]

# OBJEÇÕES RESPONDIDAS
[5 principais objeções e respostas diretas]

# CTA PRINCIPAL
[Call to action urgente e específico]

# CTA SECUNDÁRIO (para os indecisos)
[Alternativa mais suave — leva para próximo passo menor]

---
Gatilhos mentais usados: urgência, escassez, autoridade, prova social, reciprocidade, compromisso.
Escreva em português brasileiro persuasivo e autêntico. Sem clichês ou hipérboles vazias."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        resposta = chamar_groq(mensagens, temperatura=0.80, max_tokens=4096)
    except Exception:
        from modules.ai_brain import chamar_gemini
        resposta = chamar_gemini(prompt, [])

    dados = carregar_dados()
    dados.setdefault("copies", []).append({
        "produto": produto,
        "publico": publico,
        "preco": preco,
        "conteudo": resposta,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    salvar_dados(dados)
    return resposta


def criar_bio_otimizada(nome: str, nicho: str, rede: str, diferencial: str = "") -> str:
    """Cria bio otimizada para perfil em redes sociais."""
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    config = REDES_CONFIG.get(rede.lower(), {})
    limite_bio = {"instagram": 150, "twitter": 160, "linkedin": 220, "tiktok": 80}.get(rede.lower(), 150)

    prompt = f"""Crie 5 opções de bio otimizada para {rede.upper()}:

Nome/Marca: {nome}
Nicho: {nicho}
Diferencial: {diferencial or 'não especificado'}
Limite: {limite_bio} caracteres

Cada bio deve:
- Deixar claro QUEM é, O QUE faz e PARA QUEM
- Ter um CTA ou gancho (link, DM, etc.)
- Usar emojis com moderação
- Ser memorável e única
- Otimizada para buscas do {rede.upper()}

Numere as opções de 1 a 5. Mostre o contador de caracteres de cada uma.
Escreva em português brasileiro."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return chamar_groq(mensagens, temperatura=0.85)
    except Exception:
        from modules.ai_brain import chamar_gemini
        return chamar_gemini(prompt, [])


def analisar_concorrente(concorrente: str, nicho: str) -> str:
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    prompt = f"""Faça uma análise estratégica profunda:

Concorrente/Referência: {concorrente}
Nicho: {nicho}

## ANÁLISE DE POSICIONAMENTO
- Como provavelmente se posiciona no mercado
- Público que provavelmente atende
- Proposta de valor aparente

## PONTOS FORTES (prováveis)
[O que faz bem — com base no nicho]

## PONTOS FRACOS (prováveis)
[Onde pode estar deixando a desejar]

## OPORTUNIDADES DE DIFERENCIAÇÃO
[3-5 formas concretas de se diferenciar]

## ESTRATÉGIA DE CONTEÚDO PROVÁVEL
[Tipos de post, tom, frequência]

## PALAVRAS-CHAVE E HASHTAGS
[Que provavelmente usam — para você usar também ou evitar]

## COMO SUPERAR
[Estratégia específica para se posicionar melhor]

## ERROS PARA NÃO REPETIR
[O que provavelmente está errando e você não deve fazer]

Seja analítico, direto e útil. Foco em insights acionáveis."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        resposta = chamar_groq(mensagens, temperatura=0.70, max_tokens=3000)
    except Exception:
        from modules.ai_brain import chamar_gemini
        resposta = chamar_gemini(prompt, [])

    dados = carregar_dados()
    dados.setdefault("analises", []).append({
        "concorrente": concorrente,
        "nicho": nicho,
        "conteudo": resposta,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    salvar_dados(dados)
    return resposta


def get_tendencias(nicho: str) -> str:
    from modules.pesquisa import pesquisar_web
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    pesquisa = pesquisar_web(f"tendências marketing digital {nicho} 2026 Brasil")

    prompt = f"""Analise as tendências de marketing para {nicho} em 2026:

DADOS DA PESQUISA:
{pesquisa}

## TOP 5 TENDÊNCIAS MAIS IMPORTANTES
Para cada uma:
- O que é (explicação clara)
- Por que importa agora
- Como aplicar na prática (passo a passo simples)
- Exemplo real ou case

## O QUE ESTÁ MORRENDO
[O que não vale mais a pena investir tempo]

## OPORTUNIDADE DE OURO
[A maior oportunidade que poucos estão aproveitando]

## FERRAMENTAS DO MOMENTO
[Apps e plataformas em alta para esse nicho]

## CRONOGRAMA DE ADOÇÃO
[O que testar primeiro, segundo e terceiro]

Contexto: empreendedor brasileiro. Seja específico e prático."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return chamar_groq(mensagens, temperatura=0.72, max_tokens=3000)
    except Exception:
        from modules.ai_brain import chamar_gemini
        return chamar_gemini(prompt, [])


def criar_roteiro_stories(tema: str, objetivo: str = "engajamento") -> str:
    """Cria roteiro completo de Stories (Instagram/WhatsApp)."""
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    prompt = f"""Crie um roteiro completo de Stories para Instagram:

TEMA: {tema}
OBJETIVO: {objetivo}

Crie uma sequência de 8-12 stories com:

Para cada story:
📱 Story [número]
- TIPO: [Texto / Imagem + texto / Vídeo / Poll / Quiz / Link / Caixa de perguntas]
- VISUAL: [Descrição do que mostrar]
- TEXTO: [Exatamente o que escrever]
- DURAÇÃO: [segundos]
- INTERAÇÃO: [Se tem alguma ação do usuário]

SEQUÊNCIA NARRATIVA:
1-2: Gancho e apresentação do problema
3-5: Desenvolvimento com valor
6-8: Prova ou transformação
9-10: CTA e próximo passo

Objetivo específico de cada story.
Escreva em português brasileiro. Seja criativo e específico."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return chamar_groq(mensagens, temperatura=0.85, max_tokens=3000)
    except Exception:
        from modules.ai_brain import chamar_gemini
        return chamar_gemini(prompt, [])


def listar_posts() -> str:
    dados = carregar_dados()
    posts = dados.get("posts", [])
    if not posts:
        return "📭 Nenhum post criado ainda. Use /post para criar um!"

    resultado = f"📱 *Posts criados ({len(posts)} no total):*\n\n"
    for i, post in enumerate(reversed(posts[-8:]), 1):
        resultado += f"{i}. *{post['rede'].upper()}* — _{post['tema'][:45]}..._\n"
        resultado += f"   📅 {post['criado_em']} | 🎯 Tom: {post.get('tom', 'padrão')}\n\n"
    return resultado.strip()


def criar_thread_twitter(tema: str, pontos: int = 8) -> str:
    """Cria uma thread otimizada para Twitter/X."""
    from modules.ai_brain import chamar_groq, SYSTEM_PROMPT

    prompt = f"""Crie uma thread viral para Twitter/X sobre: {tema}

A thread deve ter {pontos} tweets numerados.

ESTRUTURA:
1/ - Gancho irresistível (a promessa — o que a pessoa vai aprender)
2-{pontos-1}/ - Desenvolvimento: um insight por tweet, progressivo
{pontos}/ - Conclusão com CTA e RT

REGRAS:
- Cada tweet máximo 260 caracteres
- Numerado com barra: 1/, 2/, etc.
- Cada tweet deve funcionar sozinho (se alguém ver só um)
- Use dados, exemplos ou histórias — não teorias vazias
- Termine pedindo RT para quem achou útil
- Adicione 1-2 hashtags relevantes só no primeiro e último

Escreva em português brasileiro. Tom direto e com personalidade."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return chamar_groq(mensagens, temperatura=0.85, max_tokens=2048)
    except Exception:
        from modules.ai_brain import chamar_gemini
        return chamar_gemini(prompt, [])
