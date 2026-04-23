import os
from dotenv import load_dotenv
from pathlib import Path
from modules.memory import salvar_mensagem, get_historico
from modules.pesquisa import pesquisar_e_resumir
from modules.conhecimento import salvar_conhecimento, buscar_conhecimento
from modules.evolucao import registrar_acerto, registrar_erro, get_contexto_evolucao, registrar_padrao
from modules.memoria_permanente import get_contexto_memoria, lembrar_fato, lembrar_preferencia

load_dotenv(Path(__file__).parent.parent / '.env')

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ── System Prompt Principal ───────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é a Verônica — assistente pessoal, inteligente e de confiança do Elisson.

## Quem você é
Você não é um robô nem um chatbot genérico. Você é a Verônica: uma parceira inteligente, carismática e genuinamente comprometida com o sucesso do Elisson. Pense em si como uma mistura de assistente pessoal de alto nível, consultora de negócios experiente e amiga de confiança — tudo em uma só pessoa.

Você foi criada especialmente para o Elisson e conhece bem o contexto dele: empreendedor, focado em tecnologia, marketing digital e automações. Você está sempre do lado dele, torcendo pelo crescimento dele.

## Como você fala
- **Tom:** Natural, caloroso e direto. Fale como uma pessoa inteligente falando com outra pessoa inteligente — sem robotismo, sem formalidade excessiva.
- **Idioma:** Português brasileiro autêntico. Use expressões brasileiras naturais quando fizer sentido ("cara", "exatamente", "olha", "bora"), mas sem exagerar.
- **Energia:** Animada e positiva sem ser irritante. Confiante sem ser arrogante. Honesta sem ser grossa.
- **Comprimento das respostas:** Adapte ao contexto. Perguntas simples → respostas diretas. Temas complexos → respostas completas e bem estruturadas. Nunca corte uma resposta no meio porque "ficou longa".
- **Emojis:** Use com moderação e naturalidade. Nunca abuse para não parecer um bot de marketing.

## Suas capacidades
- Responder perguntas sobre qualquer tema com profundidade e precisão
- Fazer pesquisas na internet e resumir o que encontrou
- Analisar dados, gráficos e situações de negócio
- Criar conteúdo: textos, posts, estratégias, planos
- Dar conselhos de marketing, negócios, tecnologia e finanças
- Lembrar tudo que o Elisson compartilha e usar esse contexto nas respostas
- Aprender com erros e aprimorar as próximas respostas

## Como você pensa e responde

**Antes de responder, você considera:**
1. O que o Elisson realmente quer saber ou resolver?
2. O que eu já sei sobre ele da memória permanente que é relevante aqui?
3. Preciso pesquisar algo para dar uma resposta melhor?
4. Qual é a melhor estrutura para essa resposta?

**Estruture respostas complexas assim:**
- Comece com o ponto principal (não enrole)
- Desenvolva com contexto e detalhes relevantes
- Use listas, tópicos e exemplos quando ajudar a entender
- Termine com uma conclusão prática ou próximo passo

## Memória e contexto
- USE SEMPRE as informações da memória permanente para personalizar suas respostas
- Se você sabe que o Elisson trabalha com algo específico, mencione isso naturalmente
- Quando ele compartilhar algo importante sobre si (preferência, objetivo, situação), memorize discretamente
- Conecte conversas anteriores quando for relevante: "Lembro que você me falou sobre isso antes..."

## Inteligência emocional
- Quando o Elisson estiver frustrado ou estressado, reconheça isso antes de dar a solução
- Quando ele conquistar algo, comemore genuinamente com ele
- Quando errar, assuma com honestidade e corrija com clareza
- Nunca seja condescendente ou trate perguntas como "óbvias"

## Finanças e mercado
- Seja precisa, didática e use dados reais quando disponíveis
- Explique conceitos técnicos em linguagem acessível
- Dê contexto histórico e comparações quando ajudar

## O que você NÃO faz
- Não começa respostas com "Claro!", "Certamente!" ou "Com prazer!" — é robótico
- Não inventa dados ou fatos — se não souber, diz que vai pesquisar
- Não repete a pergunta de volta antes de responder
- Não é excessivamente formal ou cheia de ressalvas desnecessárias
- Não trata o Elisson como se ele fosse iniciante em tudo

## Formato Telegram
- Use *negrito* para destacar pontos importantes
- Use _itálico_ para ênfase suave
- Use `código` para comandos, URLs ou termos técnicos
- Use listas com bullets (•) ou números quando organizar várias informações
- Emojis no início de seções grandes para facilitar a leitura"""

# ── Prompt especializado para análises de negócio ──────────────────────────
PROMPT_NEGOCIOS = """Ao analisar negócios, estratégias ou decisões:
- Considere o contexto do empreendedor brasileiro
- Seja específica sobre o que fazer, não apenas o que considerar
- Dê exemplos práticos e cases reais quando possível
- Aponte riscos sem criar paralisia por excesso de cuidado
- Priorize: o que dá resultado no curto prazo vs. o que constrói no longo prazo"""

# ── Chamadas de IA ────────────────────────────────────────────────────────────

def chamar_groq(mensagens: list, temperatura: float = 0.75, max_tokens: int = 4096) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    resposta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=mensagens,
        max_tokens=max_tokens,
        temperature=temperatura,
        top_p=0.9,
    )
    return resposta.choices[0].message.content


def chamar_gemini(pergunta: str, historico: list, temperatura: float = 0.75) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"temperature": temperatura, "max_output_tokens": 4096}
    )
    historico_texto = "\n".join([
        f"{'Elisson' if m['role'] == 'user' else 'Verônica'}: {m['content']}"
        for m in historico[-8:]
    ])
    prompt_completo = f"{SYSTEM_PROMPT}\n\nHistórico da conversa:\n{historico_texto}\n\nElisson: {pergunta}\nVerônica:"
    resposta = model.generate_content(prompt_completo)
    return resposta.text


def chamar_local(mensagens: list) -> str:
    import requests
    payload = {
        "model": "llama3",
        "messages": mensagens,
        "stream": False,
        "options": {
            "temperature": 0.75,
            "top_p": 0.9,
            "num_predict": 4096,
        }
    }
    r = requests.post("http://localhost:11434/api/chat", json=payload, timeout=120)
    if r.status_code == 200:
        return r.json().get("message", {}).get("content", "")
    raise Exception(f"Ollama erro: {r.status_code}")


# ── Detecção e memorização automática ────────────────────────────────────────

# Gatilhos expandidos — detecta muito mais contexto do usuário
GATILHOS_MEMORIA = {
    # Identidade
    "meu nome é": "nome",
    "me chamo": "nome",
    "pode me chamar de": "nome",
    # Localização
    "moro em": "cidade",
    "sou de": "cidade",
    "fico em": "cidade",
    "estou em": "localização",
    # Profissão
    "trabalho com": "profissão",
    "trabalho como": "profissão",
    "sou desenvolvedor": "profissão",
    "sou programador": "profissão",
    "sou designer": "profissão",
    "sou empresário": "profissão",
    "sou empreendedor": "profissão",
    "sou freelancer": "profissão",
    "minha profissão": "profissão",
    "meu trabalho é": "profissão",
    # Negócio
    "meu negócio": "negócio",
    "minha empresa": "negócio",
    "meu produto": "negócio",
    "meu serviço": "negócio",
    "vendo": "negócio",
    "meu nicho": "negócio",
    # Objetivos
    "meu objetivo": "objetivo",
    "quero aprender": "objetivo",
    "quero alcançar": "objetivo",
    "minha meta": "objetivo",
    "sonho em": "objetivo",
    "pretendo": "objetivo",
    # Gostos
    "gosto de": "preferência",
    "adoro": "preferência",
    "amo": "preferência",
    "curto muito": "preferência",
    # Desgostos
    "odeio": "desgosto",
    "não gosto de": "desgosto",
    "detesto": "desgosto",
    # Família / contexto pessoal
    "minha esposa": "família",
    "meu marido": "família",
    "minha filha": "família",
    "meu filho": "família",
    "meus filhos": "família",
    # Idade
    "tenho": "idade",  # "tenho X anos"
    "anos de idade": "idade",
    "anos de experiência": "experiência",
    # Ferramentas e tecnologia
    "uso o": "ferramenta",
    "trabalho com o": "ferramenta",
    "minha stack": "tecnologia",
    # Dificuldades
    "minha maior dificuldade": "dificuldade",
    "meu maior problema": "dificuldade",
    "não consigo": "dificuldade",
    "estou travado em": "dificuldade",
}


def detectar_e_memorizar(pergunta: str, user_id: str):
    """Detecta informações importantes na mensagem e memoriza automaticamente."""
    pergunta_lower = pergunta.lower()
    for gatilho, categoria in GATILHOS_MEMORIA.items():
        if gatilho in pergunta_lower:
            # Salva um trecho relevante, não a mensagem inteira
            inicio = pergunta_lower.find(gatilho)
            trecho = pergunta[max(0, inicio):min(len(pergunta), inicio + 200)].strip()
            lembrar_fato(trecho, categoria)
            break  # Uma memorização por mensagem para não poluir


def detectar_intencao(pergunta: str) -> dict:
    """Detecta a intenção da pergunta para adaptar a resposta."""
    p = pergunta.lower()
    return {
        "precisa_pesquisa": any(t in p for t in [
            "pesquise", "busque", "procure", "o que é", "como funciona",
            "notícias", "novidades", "atualização", "hoje", "agora",
            "mercado", "bolsa", "ação", "bitcoin", "crypto", "índice",
            "preço", "cotação", "valor atual", "última hora"
        ]),
        "e_negocio": any(t in p for t in [
            "negócio", "empresa", "estratégia", "marketing", "vendas",
            "cliente", "produto", "serviço", "concorrência", "mercado"
        ]),
        "e_tecnico": any(t in p for t in [
            "código", "programação", "python", "javascript", "api",
            "banco de dados", "servidor", "deploy", "bug", "erro", "função"
        ]),
        "e_emocional": any(t in p for t in [
            "estou triste", "estou frustrado", "não aguento", "cansado",
            "difícil", "complicado", "perdido", "ansioso", "preocupado"
        ]),
        "e_criativo": any(t in p for t in [
            "crie", "escreva", "faça um", "gere", "elabore", "monte",
            "post", "texto", "copy", "roteiro", "história"
        ]),
        "precisa_memoria": any(t in p for t in [
            "lembra", "falei antes", "mencionei", "contexto", "minha situação"
        ]),
    }


# ── Função principal ──────────────────────────────────────────────────────────

def perguntar_ia(pergunta: str, user_id: str = "0", forcar_local: bool = False) -> str:
    salvar_mensagem(user_id, "user", pergunta)
    historico = get_historico(user_id)

    # Detecta e memoriza informações importantes
    detectar_e_memorizar(pergunta, user_id)

    # Analisa a intenção para montar o contexto certo
    intencao = detectar_intencao(pergunta)

    # ── Busca de contexto ──
    conteudo_extra = ""
    conhecimento_salvo = buscar_conhecimento(pergunta)

    if conhecimento_salvo:
        conteudo_extra = f"[Conhecimento que já estudei sobre isso:]\n{conhecimento_salvo}\n\n"
    elif intencao["precisa_pesquisa"]:
        pesquisa = pesquisar_e_resumir(pergunta)
        if pesquisa:
            conteudo_extra = f"[Resultado da pesquisa que fiz agora:]\n{pesquisa}\n\n"

    # ── Monta o system prompt completo ──
    contexto_evolucao = get_contexto_evolucao()
    contexto_memoria = get_contexto_memoria()

    system_completo = SYSTEM_PROMPT

    if intencao["e_negocio"]:
        system_completo += f"\n\n{PROMPT_NEGOCIOS}"

    if contexto_memoria:
        system_completo += f"\n\n## O que você sabe sobre o Elisson (memória permanente)\n{contexto_memoria}"

    if contexto_evolucao:
        system_completo += f"\n\n## Aprendizados de conversas anteriores\n{contexto_evolucao}"

    # ── Monta as mensagens com histórico ──
    mensagens = [{"role": "system", "content": system_completo}]

    # Inclui mais histórico para contexto mais rico
    for msg in historico[-14:]:
        mensagens.append({"role": msg["role"], "content": msg["content"]})

    # Adiciona contexto extra na última mensagem do usuário
    if conteudo_extra and mensagens[-1]["role"] == "user":
        mensagens[-1]["content"] += f"\n\n{conteudo_extra}"

    # ── Chama a IA ──
    temperatura = 0.85 if intencao["e_criativo"] else 0.72

    if forcar_local:
        try:
            texto = chamar_local(mensagens)
            if texto:
                salvar_mensagem(user_id, "assistant", texto)
                registrar_acerto(pergunta, texto)
                return f"🖥️ _{texto}_"
        except Exception as e_local:
            print(f"⚠️ IA local falhou: {e_local}")
            return f"❌ IA local offline: {e_local}"

    # Padrão: Groq → Gemini
    try:
        texto = chamar_groq(mensagens, temperatura=temperatura)
        salvar_mensagem(user_id, "assistant", texto)
        registrar_acerto(pergunta, texto)
        return texto
    except Exception as e1:
        try:
            texto = chamar_gemini(pergunta, historico, temperatura=temperatura)
            salvar_mensagem(user_id, "assistant", texto)
            registrar_acerto(pergunta, texto)
            return texto
        except Exception as e2:
            registrar_erro(pergunta, str(e2))
            return f"❌ Erro ao conectar com a IA. Groq: {e1} | Gemini: {e2}"


def perguntar_ia_local(pergunta: str, user_id: str = "0") -> str:
    from modules.ai_local import ollama_disponivel
    if not ollama_disponivel():
        return "❌ IA local offline! Certifique-se que o Ollama está rodando com `ollama run llama3`."
    return perguntar_ia(pergunta, user_id, forcar_local=True)


def corrigir_resposta(pergunta: str, resposta_errada: str, correcao: str, user_id: str = "0") -> str:
    registrar_erro(pergunta, resposta_errada, correcao)
    registrar_padrao(f"Quando perguntarem sobre '{pergunta[:60]}', lembrar: {correcao[:120]}")

    prompt = f"""O Elisson me corrigiu e preciso responder bem isso:

Pergunta original: {pergunta}
Minha resposta anterior (errada): {resposta_errada}
Correção do Elisson: {correcao}

Agradeça a correção de forma natural e breve, reconheça o erro sem drama e dê a resposta correta usando a informação que ele forneceu. Seja direta e útil."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        texto = chamar_groq(mensagens)
    except Exception:
        texto = chamar_gemini(prompt, [])

    salvar_mensagem(user_id, "assistant", texto)
    return texto


def gerar_plano_de_estudo(tema: str, nivel: str, user_id: str = "0") -> str:
    prompt = f"""Crie um plano de estudo completo e prático sobre: {tema}
Nível atual: {nivel}

O plano deve ter:
- 5 etapas progressivas com títulos claros
- Para cada etapa: o que aprender, por que isso importa e um exercício prático concreto
- Recursos recomendados (livros, cursos, sites) — cite recursos brasileiros quando existirem
- Estimativa de tempo por etapa
- Como saber se avançou para a próxima etapa

Linguagem motivadora e direta. Foco no que realmente importa, não em teoria demais."""
    return perguntar_ia(prompt, user_id)


def estudar_tema(tema: str, user_id: str = "0") -> str:
    conhecimento_salvo = buscar_conhecimento(tema)
    if conhecimento_salvo:
        return f"📚 Já tenho isso no meu banco de conhecimento:\n\n{conhecimento_salvo}"

    conteudo = pesquisar_e_resumir(tema)
    prompt = f"""Você acabou de pesquisar sobre: {tema}

Informações encontradas:
{conteudo}

Faça um resumo completo, didático e bem organizado do que aprendeu.
Use tópicos com títulos claros.
Destaque os pontos mais importantes em negrito.
Inclua exemplos práticos quando possível.
Termine com 3 insights principais para o Elisson lembrar."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        texto = chamar_groq(mensagens, max_tokens=4096)
    except Exception:
        texto = chamar_gemini(prompt, [])

    salvar_conhecimento(tema, texto)
    salvar_mensagem(user_id, "assistant", texto)
    registrar_acerto(tema, texto)
    return texto


def analisar_situacao(contexto: str, user_id: str = "0") -> str:
    """Análise profunda de uma situação ou problema do Elisson."""
    contexto_memoria = get_contexto_memoria()

    prompt = f"""Analise essa situação com profundidade:

{contexto}

{f'Contexto do Elisson: {contexto_memoria}' if contexto_memoria else ''}

Faça uma análise estruturada:
1. **O que está acontecendo de fato** (sem julgamento)
2. **Causas raiz** (por que isso está acontecendo)
3. **Opções disponíveis** (pelo menos 3 caminhos possíveis)
4. **Recomendação** (o que eu faria no lugar dele e por quê)
5. **Próximos passos concretos** (o que fazer nos próximos 7 dias)

Seja honesta e direta. O Elisson precisa de clareza, não de suavidade excessiva."""

    return perguntar_ia(prompt, user_id)


def resumir_conversa(user_id: str = "0") -> str:
    """Resume os pontos principais da conversa atual."""
    historico = get_historico(user_id)
    if not historico:
        return "Ainda não temos conversa para resumir."

    conversa_texto = "\n".join([
        f"{'Elisson' if m['role'] == 'user' else 'Verônica'}: {m['content'][:300]}"
        for m in historico[-20:]
    ])

    prompt = f"""Resume essa conversa de forma clara e útil:

{conversa_texto}

Inclua:
- Tópicos principais discutidos
- Decisões ou conclusões tomadas
- Tarefas ou próximos passos mencionados
- Informações importantes que o Elisson compartilhou

Formato conciso, use bullets."""

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        return chamar_groq(mensagens)
    except Exception:
        return chamar_gemini(prompt, [])
