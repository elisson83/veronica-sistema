import os
import json
import base64
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

DATA_DIR = Path(__file__).parent / "data"
COFRE_FILE = DATA_DIR / "cofre.json"
PROJETOS_FILE = DATA_DIR / "projetos.json"
DATA_DIR.mkdir(exist_ok=True)

def carregar_cofre() -> dict:
    try:
        if COFRE_FILE.exists():
            with open(COFRE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def salvar_cofre(dados: dict):
    with open(COFRE_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_projetos() -> list:
    try:
        if PROJETOS_FILE.exists():
            with open(PROJETOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

def salvar_projetos(projetos: list):
    with open(PROJETOS_FILE, "w", encoding="utf-8") as f:
        json.dump(projetos, f, ensure_ascii=False, indent=2)

@app.route("/")
def index():
    return render_template("status.html")

@app.route("/dashboard")
def dashboard_old():
    return render_template("dashboard.html")

@app.route("/status")
def status_page():
    return render_template("status.html")

@app.route("/api/status")
def api_status():
    try:
        from modules.dual_brain import get_status_completo, ollama_online
        ollama = ollama_online()
        return jsonify({
            "ollama": ollama,
            "groq": True,
            "gemini": True,
            "ia_ativa": "LLaMA 3 Local" if ollama else "Groq Nuvem",
            "hora": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
    except Exception as e:
        return jsonify({"erro": str(e)})

@app.route("/api/cofre", methods=["GET"])
def get_cofre():
    cofre = carregar_cofre()
    # Não retorna as senhas, só os nomes dos serviços
    servicos = []
    for nome, dados in cofre.items():
        servicos.append({
            "nome": nome,
            "tipo": dados.get("tipo", ""),
            "email": dados.get("email", ""),
            "criado_em": dados.get("criado_em", "")
        })
    return jsonify(servicos)

@app.route("/api/cofre", methods=["POST"])
def add_cofre():
    dados = request.json
    cofre = carregar_cofre()
    nome = dados.get("nome", "").strip()
    if not nome:
        return jsonify({"erro": "Nome obrigatório"}), 400
    cofre[nome] = {
        "tipo": dados.get("tipo", ""),
        "email": dados.get("email", ""),
        "senha": dados.get("senha", ""),
        "api_key": dados.get("api_key", ""),
        "extra": dados.get("extra", ""),
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    salvar_cofre(cofre)
    return jsonify({"sucesso": f"✅ {nome} adicionado ao cofre!"})

@app.route("/api/cofre/<nome>", methods=["DELETE"])
def del_cofre(nome):
    cofre = carregar_cofre()
    if nome in cofre:
        del cofre[nome]
        salvar_cofre(cofre)
        return jsonify({"sucesso": f"✅ {nome} removido!"})
    return jsonify({"erro": "Serviço não encontrado"}), 404

@app.route("/api/projetos", methods=["GET"])
def get_projetos():
    return jsonify(carregar_projetos())

@app.route("/api/projetos", methods=["POST"])
def add_projeto():
    dados = request.json
    projetos = carregar_projetos()
    projeto = {
        "id": len(projetos) + 1,
        "titulo": dados.get("titulo", ""),
        "descricao": dados.get("descricao", ""),
        "status": "pendente",
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "resultado": ""
    }
    projetos.append(projeto)
    salvar_projetos(projetos)
    return jsonify({"sucesso": "✅ Projeto adicionado!", "id": projeto["id"]})

@app.route("/api/executar", methods=["POST"])
def executar_projeto():
    dados = request.json
    descricao = dados.get("descricao", "")
    user_id = "dashboard"
    try:
        from modules.ai_brain import perguntar_ia
        prompt = f"""
        O usuário pediu via dashboard:
        {descricao}
        
        Responda de forma completa e detalhada.
        Se for código, gere o código completo.
        Se for uma tarefa, explique passo a passo.
        """
        resposta = perguntar_ia(prompt, user_id)
        return jsonify({"resposta": resposta})
    except Exception as e:
        return jsonify({"erro": str(e)})

@app.route("/api/memorias")
def get_memorias():
    try:
        from modules.memoria_permanente import buscar_memorias
        return jsonify({"memorias": buscar_memorias()})
    except Exception as e:
        return jsonify({"erro": str(e)})

if __name__ == "__main__":
    print("🌐 Dashboard Verônica iniciando...")
    print("📊 Acesse: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)