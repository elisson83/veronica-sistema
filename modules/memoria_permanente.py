import json
import re
from pathlib import Path
from datetime import datetime

MEMORIA_FILE = Path(__file__).parent.parent / "data" / "memoria_permanente.json"

# ── Estrutura da memória ──────────────────────────────────────────────────────

ESTRUTURA_PADRAO = {
    "fatos": [],           # Informações gerais sobre o Elisson
    "preferencias": {},    # Chave → valor (gostos, configurações)
    "pessoas": {},         # Pessoas mencionadas pelo Elisson
    "lembretes": [],       # Lembretes com data
    "objetivos": [],       # Metas e objetivos de longo prazo
    "negocios": [],        # Contexto de negócios e projetos
    "contexto_atual": {},  # O que está acontecendo agora na vida do Elisson
    "aprendizados": [],    # Insights e aprendizados compartilhados
}


# ── Persistência ──────────────────────────────────────────────────────────────

def inicializar():
    MEMORIA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORIA_FILE.exists():
        salvar(ESTRUTURA_PADRAO.copy())


def carregar() -> dict:
    inicializar()
    try:
        with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        # Garante que todos os campos existem (compatibilidade com versão antiga)
        for chave, valor in ESTRUTURA_PADRAO.items():
            if chave not in dados:
                dados[chave] = valor.copy() if isinstance(valor, (dict, list)) else valor
        return dados
    except Exception:
        return ESTRUTURA_PADRAO.copy()


def salvar(dados: dict):
    MEMORIA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _agora() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


# ── Funções de memorização ────────────────────────────────────────────────────

def lembrar_fato(fato: str, categoria: str = "geral") -> str:
    """Memoriza um fato sobre o Elisson."""
    dados = carregar()
    fato_limpo = fato.strip()

    # Evita duplicatas exatas
    for f in dados["fatos"]:
        if f["fato"].lower() == fato_limpo.lower():
            return f"✅ Já lembro disso."

    entrada = {
        "fato": fato_limpo,
        "categoria": categoria,
        "data": _agora(),
        "relevancia": _calcular_relevancia(categoria),
    }

    dados["fatos"].append(entrada)

    # Mantém os 200 fatos mais recentes/relevantes
    if len(dados["fatos"]) > 200:
        dados["fatos"] = sorted(dados["fatos"], key=lambda x: x.get("relevancia", 1), reverse=True)[:200]

    # Atualiza contexto atual para categorias relevantes
    if categoria in ("negócio", "objetivo", "situação", "localização"):
        dados["contexto_atual"][categoria] = {"valor": fato_limpo, "data": _agora()}

    salvar(dados)
    return f"✅ Memorizado: {fato_limpo}"


def lembrar_preferencia(chave: str, valor: str) -> str:
    """Memoriza uma preferência ou configuração do Elisson."""
    dados = carregar()
    dados["preferencias"][chave.lower().strip()] = {
        "valor": valor.strip(),
        "data": _agora()
    }
    salvar(dados)
    return f"✅ Preferência salva: {chave} = {valor}"


def lembrar_objetivo(objetivo: str, prazo: str = "") -> str:
    """Memoriza um objetivo ou meta do Elisson."""
    dados = carregar()
    entrada = {
        "objetivo": objetivo.strip(),
        "prazo": prazo,
        "data": _agora(),
        "status": "ativo"
    }
    # Evita duplicata
    for obj in dados["objetivos"]:
        if obj["objetivo"].lower() == objetivo.lower():
            obj.update(entrada)
            salvar(dados)
            return f"✅ Objetivo atualizado: {objetivo}"

    dados["objetivos"].append(entrada)
    salvar(dados)
    return f"✅ Objetivo memorizado: {objetivo}"


def lembrar_negocio(info: str, tipo: str = "geral") -> str:
    """Memoriza informações sobre os negócios do Elisson."""
    dados = carregar()
    entrada = {"info": info.strip(), "tipo": tipo, "data": _agora()}
    dados["negocios"].append(entrada)
    if len(dados["negocios"]) > 50:
        dados["negocios"] = dados["negocios"][-50:]
    salvar(dados)
    return f"✅ Info de negócio salva."


def adicionar_lembrete(texto: str, data_hora: str = "") -> str:
    """Adiciona um lembrete com data/hora opcional."""
    dados = carregar()
    lembrete = {
        "texto": texto.strip(),
        "data_criacao": _agora(),
        "data_lembrete": data_hora,
        "concluido": False
    }
    dados["lembretes"].append(lembrete)
    salvar(dados)
    return f"✅ Lembrete adicionado: {texto}"


def lembrar_pessoa(nome: str, contexto: str) -> str:
    """Memoriza uma pessoa mencionada pelo Elisson."""
    dados = carregar()
    nome_key = nome.lower().strip()
    dados["pessoas"][nome_key] = {
        "nome": nome,
        "contexto": contexto,
        "atualizado_em": _agora()
    }
    salvar(dados)
    return f"✅ Lembrei quem é {nome}."


# ── Busca e recuperação ───────────────────────────────────────────────────────

def _calcular_relevancia(categoria: str) -> int:
    """Relevância por categoria — quanto maior, mais importante."""
    relevancia = {
        "nome": 10, "negócio": 9, "objetivo": 9, "profissão": 8,
        "família": 8, "cidade": 7, "tecnologia": 7, "dificuldade": 7,
        "preferência": 6, "ferramenta": 6, "experiência": 6,
        "desgosto": 5, "geral": 4,
    }
    return relevancia.get(categoria, 4)


def buscar_memorias(termo: str = "") -> str:
    """Retorna memórias formatadas para o usuário."""
    dados = carregar()
    fatos = dados.get("fatos", [])
    prefs = dados.get("preferencias", {})
    objetivos = dados.get("objetivos", [])
    negocios = dados.get("negocios", [])

    if not fatos and not prefs and not objetivos:
        return "🧠 Ainda não tenho memórias permanentes sobre você. Pode me contar mais!"

    resultado = "🧠 *O que eu sei sobre você:*\n\n"

    # Preferências
    if prefs:
        resultado += "⚙️ *Preferências:*\n"
        for chave, info in list(prefs.items())[:10]:
            resultado += f"• {chave.capitalize()}: {info['valor']}\n"
        resultado += "\n"

    # Objetivos ativos
    objetivos_ativos = [o for o in objetivos if o.get("status") == "ativo"]
    if objetivos_ativos:
        resultado += "🎯 *Objetivos:*\n"
        for obj in objetivos_ativos[-5:]:
            prazo = f" (até {obj['prazo']})" if obj.get("prazo") else ""
            resultado += f"• {obj['objetivo']}{prazo}\n"
        resultado += "\n"

    # Negócios
    if negocios:
        resultado += "💼 *Negócios e projetos:*\n"
        for n in negocios[-3:]:
            resultado += f"• {n['info']}\n"
        resultado += "\n"

    # Fatos
    if fatos:
        resultado += "📝 *Fatos importantes:*\n"
        if termo:
            fatos_filtrados = [f for f in fatos if termo.lower() in f["fato"].lower() or termo.lower() in f.get("categoria", "").lower()]
        else:
            # Ordena por relevância e pega os mais importantes
            fatos_filtrados = sorted(fatos, key=lambda x: x.get("relevancia", 1), reverse=True)[:20]

        for f in fatos_filtrados:
            resultado += f"• [{f['categoria']}] {f['fato']} ({f['data']})\n"

    return resultado.strip()


def get_contexto_memoria() -> str:
    """Monta o contexto da memória para incluir no system prompt da IA."""
    dados = carregar()
    fatos = dados.get("fatos", [])
    prefs = dados.get("preferencias", {})
    objetivos = dados.get("objetivos", [])
    negocios = dados.get("negocios", [])
    contexto_atual = dados.get("contexto_atual", {})
    pessoas = dados.get("pessoas", {})

    partes = []

    # Contexto atual (mais importante)
    if contexto_atual:
        partes.append("Contexto atual do Elisson:")
        for k, v in contexto_atual.items():
            partes.append(f"  - {k}: {v['valor']}")

    # Preferências
    if prefs:
        partes.append("Preferências e configurações:")
        for chave, info in list(prefs.items())[:8]:
            partes.append(f"  - {chave}: {info['valor']}")

    # Objetivos ativos
    objetivos_ativos = [o for o in objetivos if o.get("status") == "ativo"]
    if objetivos_ativos:
        partes.append("Objetivos e metas:")
        for obj in objetivos_ativos[-5:]:
            prazo = f" (prazo: {obj['prazo']})" if obj.get("prazo") else ""
            partes.append(f"  - {obj['objetivo']}{prazo}")

    # Negócios recentes
    if negocios:
        partes.append("Projetos e negócios:")
        for n in negocios[-4:]:
            partes.append(f"  - {n['info']}")

    # Pessoas conhecidas
    if pessoas:
        partes.append("Pessoas mencionadas:")
        for nome, info in list(pessoas.items())[:5]:
            partes.append(f"  - {info['nome']}: {info['contexto']}")

    # Fatos por relevância (os mais importantes primeiro)
    fatos_relevantes = sorted(fatos, key=lambda x: x.get("relevancia", 1), reverse=True)[:12]
    if fatos_relevantes:
        partes.append("O que você sabe sobre o Elisson:")
        for f in fatos_relevantes:
            partes.append(f"  - [{f['categoria']}] {f['fato']}")

    if not partes:
        return ""

    return "\n".join(partes)


def buscar_por_categoria(categoria: str) -> list:
    """Retorna fatos de uma categoria específica."""
    dados = carregar()
    return [f for f in dados.get("fatos", []) if f.get("categoria") == categoria]


def atualizar_objetivo_status(objetivo_texto: str, novo_status: str) -> str:
    """Atualiza o status de um objetivo (ativo, concluído, pausado)."""
    dados = carregar()
    for obj in dados["objetivos"]:
        if objetivo_texto.lower() in obj["objetivo"].lower():
            obj["status"] = novo_status
            obj["atualizado_em"] = _agora()
            salvar(dados)
            return f"✅ Objetivo atualizado para '{novo_status}'."
    return "❌ Objetivo não encontrado."


def apagar_memorias() -> str:
    """Apaga toda a memória permanente."""
    salvar(ESTRUTURA_PADRAO.copy())
    return "🗑️ Memória permanente apagada completamente."


def get_lembretes_pendentes() -> list:
    """Retorna lembretes não concluídos."""
    dados = carregar()
    return [l for l in dados.get("lembretes", []) if not l.get("concluido")]


def concluir_lembrete(index: int) -> str:
    """Marca um lembrete como concluído."""
    dados = carregar()
    lembretes = dados.get("lembretes", [])
    if 0 <= index < len(lembretes):
        lembretes[index]["concluido"] = True
        salvar(dados)
        return f"✅ Lembrete concluído: {lembretes[index]['texto']}"
    return "❌ Lembrete não encontrado."
