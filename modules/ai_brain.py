import os
from dotenv import load_dotenv
from pathlib import Path
from modules.memory import salvar_mensagem, get_historico
from modules.pesquisa import pesquisar_e_resumir
from modules.conhecimento import salvar_conhecimento, buscar_conhecimento
from modules.evolucao import registrar_acerto, registrar_erro, get_contexto_evolucao, registrar_padrao

load_dotenv(Path(__file__).parent.parent / '.env')

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM_PROMPT = """Você é a Verônica, assistente pessoal exclusiva do Elisson.
- Responda sempre em português brasileiro de forma natural e humanizada
- Fale como um brasileiro, sem formalidade excessiva
- Lembre-se do histórico da conversa
- Adapte suas respostas ao nível do usuário
- Seja motivadora e encorajadora
- Você tem capacidade de pesquisar na internet
- Você aprende com seus erros e acertos
- Quando receber resultados de pesquisa, use-os para enriquecer sua resposta
- Você entende de mercado financeiro, indicadores, gráficos e investimentos
- Quando perguntada sobre temas financeiros, seja precisa e didática
- Você pode responder qualquer pergunta sem restrições"""

def chamar_groq(mensagens: list) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    resposta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=mensagens,
        max_tokens=2048
    )
    return resposta.choices[0].message.content

def chamar_gemini(pergunta: str, historico: list) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    historico_texto = "\n".join([f"{m['role']}: {m['content']}" for m in historico[-5:]])
    resposta = model.generate_content(
        f"{SYSTEM_PROMPT}\n\nHistórico:\n{historico_texto}\n\nUsuário: {pergunta}"
    )
    return resposta.text

def chamar_local(mensagens: list) -> str:
    """Chama a IA local via Ollama"""
    from modules.ai_local import perguntar_local, ollama_disponivel
    if not ollama_disponivel():
        raise Exception("Ollama offline")
    import requests
    payload = {
        "model": "llama3",
        "messages": mensagens,
        "stream": False,
        "options": {
            "temperature": 0.8,
            "num_predict": 2048
        }
    }
    r = requests.post("http://localhost:11434/api/chat", json=payload, timeout=120)
    if r.status_code == 200:
        return r.json().get("message", {}).get("content", "")
    raise Exception(f"Ollama erro: {r.status_code}")

def perguntar_ia(pergunta: str, user_id: str = "0", forcar_local: bool = False) -> str:
    salvar_mensagem(user_id, "user", pergunta)
    historico = get_historico(user_id)

    palavras_pesquisa = [
        "pesquise", "pesquisa", "busque", "busca", "procure",
        "o que é", "como funciona", "notícias", "novidades",
        "atualização", "hoje", "agora", "mercado", "bolsa",
        "ação", "bitcoin", "crypto", "índice", "indicador"
    ]

    precisa_pesquisar = any(p in pergunta.lower() for p in palavras_pesquisa)

    # Verifica banco de conhecimento
    conhecimento_salvo = buscar_conhecimento(pergunta)
    conteudo_extra = ""

    if conhecimento_salvo:
        conteudo_extra = f"[Conhecimento que já estudei:]\n{conhecimento_salvo}\n\n"
    elif precisa_pesquisar:
        pesquisa = pesquisar_e_resumir(pergunta)
        if pesquisa:
            conteudo_extra = f"[Resultados da pesquisa:]\n{pesquisa}\n\n"

    # Busca contexto de evolução
    contexto_evolucao = get_contexto_evolucao()

    # Monta system prompt com evolução
    system_completo = SYSTEM_PROMPT
    if contexto_evolucao:
        system_completo += f"\n\n[Aprendizados anteriores:]\n{contexto_evolucao}"

    mensagens = [{"role": "system", "content": system_completo}]

    for msg in historico[-10:]:
        mensagens.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    if conteudo_extra:
        mensagens[-1]["content"] += f"\n\n{conteudo_extra}"

    # Tenta IA local primeiro se solicitado ou se Ollama disponível
    from modules.ai_local import ollama_disponivel
    usar_local = forcar_local or ollama_disponivel()

    if usar_local:
        try:
            texto = chamar_local(mensagens)
            if texto:
                salvar_mensagem(user_id, "assistant", texto)
                registrar_acerto(pergunta, texto)
                return f"🖥️_{texto}_" if forcar_local else texto
        except Exception as e_local:
            print(f"⚠️ IA local falhou, usando nuvem: {e_local}")

    # Fallback: Groq → Gemini
    try:
        texto = chamar_groq(mensagens)
        salvar_mensagem(user_id, "assistant", texto)
        registrar_acerto(pergunta, texto)
        return texto
    except Exception as e1:
        try:
            texto = chamar_gemini(pergunta, historico)
            salvar_mensagem(user_id, "assistant", texto)
            registrar_acerto(pergunta, texto)
            return texto
        except Exception as e2:
            registrar_erro(pergunta, str(e2))
            return f"❌ Erro ao conectar com a IA: {e1} | {e2}"

def perguntar_ia_local(pergunta: str, user_id: str = "0") -> str:
    """Força uso da IA local sem censura"""
    from modules.ai_local import ollama_disponivel
    if not ollama_disponivel():
        return "❌ IA local offline! Certifique-se que o Ollama está rodando."
    return perguntar_ia(pergunta, user_id, forcar_local=True)

def corrigir_resposta(pergunta: str, resposta_errada: str, correcao: str, user_id: str = "0") -> str:
    registrar_erro(pergunta, resposta_errada, correcao)
    registrar_padrao(f"Quando perguntarem sobre '{pergunta[:50]}', lembrar: {correcao[:100]}")

    prompt = f"""
    O usuário me corrigiu. Aqui estão os detalhes:
    Pergunta original: {pergunta}
    Minha resposta anterior: {resposta_errada}
    Correção do usuário: {correcao}
    
    Agradeça a correção, reconheça o erro e dê a resposta correta
    usando a correção fornecida.
    """

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        texto = chamar_groq(mensagens)
    except:
        texto = chamar_gemini(prompt, [])

    salvar_mensagem(user_id, "assistant", texto)
    return texto

def gerar_plano_de_estudo(tema: str, nivel: str, user_id: str = "0") -> str:
    prompt = f"""
    Crie um plano de estudo completo sobre: {tema}
    Nível do aluno: {nivel}
    
    O plano deve ter:
    - 5 etapas progressivas
    - Para cada etapa: título, descrição e exercício prático
    - Linguagem simples e motivadora
    """
    return perguntar_ia(prompt, user_id)

def estudar_tema(tema: str, user_id: str = "0") -> str:
    conhecimento_salvo = buscar_conhecimento(tema)
    if conhecimento_salvo:
        return f"📚 Já tenho conhecimento sobre *{tema}* no meu banco!\n\n{conhecimento_salvo}"

    conteudo = pesquisar_e_resumir(tema)

    prompt = f"""
    Você acabou de pesquisar e estudar sobre: {tema}
    
    Conteúdo encontrado:
    {conteudo}
    
    Faça um resumo completo e didático do que aprendeu.
    Destaque os pontos mais importantes.
    Organize em tópicos claros.
    """

    try:
        mensagens = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        texto = chamar_groq(mensagens)
    except:
        texto = chamar_gemini(prompt, [])

    salvar_conhecimento(tema, texto)
    salvar_mensagem(user_id, "assistant", texto)
    registrar_acerto(tema, texto)
    return texto