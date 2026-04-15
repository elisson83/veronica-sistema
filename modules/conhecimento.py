import json
from pathlib import Path
from datetime import datetime

CONHECIMENTO_FILE = Path(__file__).parent.parent / "data" / "conhecimento.json"

def inicializar_conhecimento():
    if not CONHECIMENTO_FILE.exists():
        with open(CONHECIMENTO_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "_info": "Banco de conhecimento permanente da Verônica IA",
                "_version": "0.1.0",
                "_temas": {}
            }, f, ensure_ascii=False, indent=2)

def salvar_conhecimento(tema: str, conteudo: str):
    inicializar_conhecimento()
    with open(CONHECIMENTO_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)
    
    tema_key = tema.lower().strip()
    dados["_temas"][tema_key] = {
        "tema": tema,
        "conteudo": conteudo,
        "atualizado_em": datetime.now().isoformat(),
        "vezes_consultado": dados["_temas"].get(tema_key, {}).get("vezes_consultado", 0)
    }
    
    with open(CONHECIMENTO_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Conhecimento sobre '{tema}' salvo!")

def buscar_conhecimento(tema: str) -> str:
    inicializar_conhecimento()
    try:
        with open(CONHECIMENTO_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        tema_key = tema.lower().strip()
        
        # Busca exata
        if tema_key in dados["_temas"]:
            item = dados["_temas"][tema_key]
            item["vezes_consultado"] += 1
            with open(CONHECIMENTO_FILE, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            return item["conteudo"]
        
        # Busca parcial
        for key, item in dados["_temas"].items():
            if tema_key in key or key in tema_key:
                item["vezes_consultado"] += 1
                with open(CONHECIMENTO_FILE, "w", encoding="utf-8") as f:
                    json.dump(dados, f, ensure_ascii=False, indent=2)
                return item["conteudo"]
        
        return ""
    except:
        return ""

def listar_conhecimentos() -> str:
    inicializar_conhecimento()
    try:
        with open(CONHECIMENTO_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        temas = dados["_temas"]
        if not temas:
            return "📚 Ainda não estudei nenhum tema. Use /estudar para começar!"
        
        texto = "📚 *Temas que já estudei:*\n\n"
        for key, item in sorted(temas.items()):
            texto += f"• {item['tema']} _(consultado {item['vezes_consultado']}x)_\n"
        
        return texto
    except:
        return "Erro ao listar conhecimentos."

def deletar_conhecimento(tema: str) -> bool:
    inicializar_conhecimento()
    try:
        with open(CONHECIMENTO_FILE, "r", encoding="utf-8") as f:
            dados = json.load(f)
        
        tema_key = tema.lower().strip()
        if tema_key in dados["_temas"]:
            del dados["_temas"][tema_key]
            with open(CONHECIMENTO_FILE, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False, indent=2)
            return True
        return False
    except:
        return False