import json
from pathlib import Path
from datetime import datetime

EVOLUCAO_FILE = Path(__file__).parent.parent / "data" / "evolucao.json"

def inicializar_evolucao():
    if not EVOLUCAO_FILE.exists():
        with open(EVOLUCAO_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "_info": "Arquivo de auto-evolução da Verônica IA",
                "_version": "0.1.0",
                "acertos": [],
                "erros": [],
                "correcoes": [],
                "padroes_aprendidos": [],
                "total_acertos": 0,
                "total_erros": 0
            }, f, ensure_ascii=False, indent=2)

def registrar_acerto(pergunta: str, resposta: str, feedback: str = ""):
    inicializar_evolucao()
    with open(EVOLUCAO_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)

    dados["acertos"].append({
        "pergunta": pergunta,
        "resposta": resposta,
        "feedback": feedback,
        "data": datetime.now().isoformat()
    })
    dados["total_acertos"] += 1

    # Manter apenas os últimos 50 acertos
    if len(dados["acertos"]) > 50:
        dados["acertos"] = dados["acertos"][-50:]

    with open(EVOLUCAO_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def registrar_erro(pergunta: str, resposta_errada: str, correcao: str = ""):
    inicializar_evolucao()
    with open(EVOLUCAO_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)

    dados["erros"].append({
        "pergunta": pergunta,
        "resposta_errada": resposta_errada,
        "correcao": correcao,
        "data": datetime.now().isoformat()
    })
    dados["total_erros"] += 1

    if correcao:
        dados["correcoes"].append({
            "pergunta": pergunta,
            "correcao": correcao,
            "data": datetime.now().isoformat()
        })

    # Manter apenas os últimos 50 erros
    if len(dados["erros"]) > 50:
        dados["erros"] = dados["erros"][-50:]

    with open(EVOLUCAO_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def registrar_padrao(padrao: str):
    inicializar_evolucao()
    with open(EVOLUCAO_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)

    if padrao not in dados["padroes_aprendidos"]:
        dados["padroes_aprendidos"].append(padrao)

    with open(EVOLUCAO_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def get_contexto_evolucao() -> str:
    inicializar_evolucao()
    try:
        with open(EVOLUCAO_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)

        correcoes = dados.get("correcoes", [])[-5:]
        padroes = dados.get("padroes_aprendidos", [])[-10:]

        contexto = ""
        if correcoes:
            contexto += "Correções anteriores que aprendi:\n"
            for c in correcoes:
                contexto += f"- Pergunta: {c['pergunta'][:100]}\n"
                contexto += f"  Correção: {c['correcao'][:200]}\n"

        if padroes:
            contexto += "\nPadrões que aprendi:\n"
            for p in padroes:
                contexto += f"- {p}\n"

        return contexto
    except:
        return ""

def get_estatisticas() -> str:
    inicializar_evolucao()
    try:
        with open(EVOLUCAO_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)

        total = dados["total_acertos"] + dados["total_erros"]
        taxa = (dados["total_acertos"] / total * 100) if total > 0 else 0

        return (
            f"📈 *Estatísticas de Evolução:*\n\n"
            f"• Total de interações: {total}\n"
            f"• Acertos: {dados['total_acertos']}\n"
            f"• Erros corrigidos: {dados['total_erros']}\n"
            f"• Taxa de acerto: {taxa:.1f}%\n"
            f"• Padrões aprendidos: {len(dados['padroes_aprendidos'])}\n"
            f"• Correções aplicadas: {len(dados['correcoes'])}\n"
        )
    except:
        return "Erro ao buscar estatísticas."