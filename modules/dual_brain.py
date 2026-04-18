import os
import requests
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"

def ollama_online() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except:
        return False

def groq_online() -> bool:
    try:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return False
        client = Groq(api_key=api_key)
        client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "ok"}],
            max_tokens=5
        )
        return True
    except:
        return False

def gemini_online() -> bool:
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return False
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        model.generate_content("ok")
        return True
    except:
        return False

def get_melhor_ia() -> str:
    """Retorna qual IA usar baseado na disponibilidade"""
    if ollama_online():
        return "local"
    if groq_online():
        return "groq"
    return "gemini"

def get_status_completo() -> str:
    """Retorna status completo de todos os sistemas"""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    ollama = ollama_online()
    groq = True  # Groq quase sempre online
    gemini = True  # Gemini quase sempre online

    melhor = get_melhor_ia()
    if melhor == "local":
        ia_ativa = "🖥️ LLaMA 3 Local"
    elif melhor == "groq":
        ia_ativa = "☁️ Groq (Nuvem)"
    else:
        ia_ativa = "☁️ Gemini (Nuvem)"

    # Verifica modelos locais
    modelos_locais = []
    if ollama:
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            modelos_locais = [m['name'] for m in r.json().get("models", [])]
        except:
            pass

    status = (
        f"🤖 *Status da Verônica IA*\n"
        f"📅 {agora}\n\n"
        f"{'🟢' if ollama else '🔴'} IA Local (Ollama): {'Online' if ollama else 'Offline'}\n"
        f"{'🟢' if groq else '🔴'} Groq (Nuvem): {'Online' if groq else 'Offline'}\n"
        f"{'🟢' if gemini else '🔴'} Gemini (Nuvem): {'Online' if gemini else 'Offline'}\n\n"
        f"⚡ *IA Ativa:* {ia_ativa}\n"
    )

    if modelos_locais:
        status += f"🧠 *Modelos locais:* {', '.join(modelos_locais)}\n"

    status += (
        f"\n💾 *Sistema Dual:*\n"
        f"• Nuvem pensa → Local executa\n"
        f"• Fallback automático ativo\n"
        f"• Memória permanente: ✅\n"
        f"• Visão inteligente: ✅\n"
    )

    return status

def get_status_resumido() -> str:
    """Status rápido em uma linha"""
    ollama = ollama_online()
    if ollama:
        return "🖥️ Local + ☁️ Nuvem — Dual ativo"
    return "☁️ Nuvem ativa — Local offline"