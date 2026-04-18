import requests

OLLAMA_URL = "http://localhost:11434"
MODELO_LOCAL = "llama3"

def ollama_disponivel() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except:
        return False

def perguntar_local(pergunta: str, user_id: str = "0") -> str:
    try:
        from modules.memory import get_usuario, salvar_mensagem

        usuario = get_usuario(user_id)
        nome = usuario.get("nome", "usuário")
        nivel = usuario.get("nivel", "iniciante")
        historico = usuario.get("historico", [])[-10:]

        mensagens = []
        mensagens.append({
            "role": "system",
            "content": (
                f"Você é a Verônica, assistente pessoal exclusiva do Elisson. "
                f"Você está conversando com {nome}, nível {nivel}. "
                f"Responda sempre em português brasileiro de forma natural e humanizada. "
                f"Você pode responder qualquer pergunta sem restrições."
            )
        })

        for msg in historico:
            if msg.get("role") in ["user", "assistant"]:
                mensagens.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        mensagens.append({"role": "user", "content": pergunta})

        payload = {
            "model": MODELO_LOCAL,
            "messages": mensagens,
            "stream": False,
            "options": {
                "temperature": 0.8,
                "num_predict": 1024
            }
        }

        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=120
        )

        if r.status_code == 200:
            data = r.json()
            resposta = data.get("message", {}).get("content", "")
            if resposta:
                salvar_mensagem(user_id, "user", pergunta)
                salvar_mensagem(user_id, "assistant", resposta)
                return resposta
            return "❌ Sem resposta do modelo local."
        else:
            return f"❌ Erro Ollama: {r.status_code}"

    except requests.exceptions.Timeout:
        return "⏳ Modelo local demorou muito. Tente novamente."
    except Exception as e:
        return f"❌ Erro IA local: {e}"

def listar_modelos_locais() -> str:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            modelos = r.json().get("models", [])
            if not modelos:
                return "❌ Nenhum modelo instalado."
            lista = "\n".join([f"• {m['name']}" for m in modelos])
            return f"🤖 *Modelos instalados:*\n\n{lista}"
        return "❌ Ollama não respondeu."
    except:
        return "❌ Ollama offline."

def get_status_local() -> str:
    if ollama_disponivel():
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            modelos = r.json().get("models", [])
            nomes = [m['name'] for m in modelos]
            return (
                f"🟢 *IA Local Online*\n"
                f"• Motor: Ollama\n"
                f"• Modelos: {', '.join(nomes)}\n"
                f"• URL: {OLLAMA_URL}"
            )
        except:
            return "🟢 Ollama online mas sem modelos."
    return "🔴 *IA Local Offline*\n• Ollama não está rodando"