import json
from pathlib import Path
from datetime import datetime

MEMORIA_FILE = Path(__file__).parent.parent / "data" / "memoria_permanente.json"

def inicializar():
    MEMORIA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORIA_FILE.exists():
        with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "fatos": [],
                "preferencias": {},
                "pessoas": {},
                "lembretes": []
            }, f, ensure_ascii=False, indent=2)

def carregar() -> dict:
    inicializar()
    try:
        with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"fatos": [], "preferencias": {}, "pessoas": {}, "lembretes": []}

def salvar(dados: dict):
    inicializar()
    with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def lembrar_fato(fato: str, categoria: str = "geral") -> str:
    dados = carregar()
    entrada = {
        "fato": fato,
        "categoria": categoria,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    dados["fatos"].append(entrada)
    salvar(dados)
    return f"✅ Memorizado: {fato}"

def lembrar_preferencia(chave: str, valor: str) -> str:
    dados = carregar()
    dados["preferencias"][chave] = {
        "valor": valor,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    salvar(dados)
    return f"✅ Preferência salva: {chave} = {valor}"

def buscar_memorias(termo: str = "") -> str:
    dados = carregar()
    fatos = dados.get("fatos", [])
    prefs = dados.get("preferencias", {})

    if not fatos and not prefs:
        return "🧠 Nenhuma memória permanente ainda."

    resultado = "🧠 *Minhas memórias sobre você:*\n\n"

    if prefs:
        resultado += "⚙️ *Preferências:*\n"
        for chave, info in prefs.items():
            resultado += f"• {chave}: {info['valor']}\n"
        resultado += "\n"

    if fatos:
        resultado += "📝 *Fatos importantes:*\n"
        if termo:
            fatos_filtrados = [f for f in fatos if termo.lower() in f["fato"].lower()]
        else:
            fatos_filtrados = fatos[-20:]
        for f in reversed(fatos_filtrados):
            resultado += f"• [{f['categoria']}] {f['fato']} ({f['data']})\n"

    return resultado

def get_contexto_memoria() -> str:
    dados = carregar()
    fatos = dados.get("fatos", [])[-10:]
    prefs = dados.get("preferencias", {})

    if not fatos and not prefs:
        return ""

    contexto = "[Memória permanente sobre o usuário:]\n"

    if prefs:
        for chave, info in prefs.items():
            contexto += f"- {chave}: {info['valor']}\n"

    if fatos:
        for f in fatos:
            contexto += f"- {f['fato']}\n"

    return contexto

def apagar_memorias() -> str:
    salvar({"fatos": [], "preferencias": {}, "pessoas": {}, "lembretes": []})
    return "🗑️ Memória permanente apagada!"