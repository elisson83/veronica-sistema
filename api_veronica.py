import os
import json
import secrets
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Chave de acesso da API
API_KEY = os.getenv("VERONICA_API_KEY", secrets.token_hex(16))

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

def verificar_api_key():
    key = request.headers.get("X-API-Key") or request.args.get("api_key")
    return key == API_KEY

@app.route("/")
def index():
    return jsonify({
        "nome": "Veronica IA API",
        "versao": "1.0",
        "status": "online",
        "hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "endpoints": [
            "POST /api/perguntar",
            "POST /api/imagem",
            "POST /api/marketing",
            "GET /api/status",
            "GET /api/memorias",
            "POST /api/lembrar"
        ]
    })

@app.route("/api/status")
def status():
    try:
        from modules.dual_brain import get_status_completo, ollama_online
        return jsonify({
            "status": "online",
            "ollama": ollama_online(),
            "groq": True,
            "gemini": True,
            "hora": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
    except Exception as e:
        return jsonify({"status": "online", "erro": str(e)})

@app.route("/api/perguntar", methods=["POST"])
def perguntar():
    if not verificar_api_key():
        return jsonify({"erro": "API Key invalida!"}), 401
    dados = request.json
    if not dados or "pergunta" not in dados:
        return jsonify({"erro": "Campo 'pergunta' obrigatorio!"}), 400
    try:
        from modules.ai_brain import perguntar_ia
        pergunta = dados["pergunta"]
        user_id = dados.get("user_id", "api_user")
        resposta = perguntar_ia(pergunta, user_id)
        return jsonify({
            "resposta": resposta,
            "pergunta": pergunta,
            "hora": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/imagem", methods=["POST"])
def gerar_imagem():
    if not verificar_api_key():
        return jsonify({"erro": "API Key invalida!"}), 401
    dados = request.json
    if not dados or "descricao" not in dados:
        return jsonify({"erro": "Campo 'descricao' obrigatorio!"}), 400
    try:
        from modules.visao_geradora import gerar_imagem_inteligente
        descricao = dados["descricao"]
        caminho, ia_usada = gerar_imagem_inteligente(descricao)
        if caminho.startswith("ERRO"):
            return jsonify({"erro": caminho}), 500
        nome_arquivo = Path(caminho).name
        return jsonify({
            "sucesso": True,
            "arquivo": nome_arquivo,
            "caminho": caminho,
            "ia_usada": ia_usada,
            "descricao": descricao
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/marketing", methods=["POST"])
def criar_post():
    if not verificar_api_key():
        return jsonify({"erro": "API Key invalida!"}), 401
    dados = request.json
    if not dados or "tema" not in dados:
        return jsonify({"erro": "Campos 'tema' e 'rede' obrigatorios!"}), 400
    try:
        from modules.marketing import criar_post_otimizado
        tema = dados["tema"]
        rede = dados.get("rede", "instagram")
        tom = dados.get("tom", "profissional")
        post = criar_post_otimizado(tema, rede, tom)
        return jsonify({
            "post": post,
            "tema": tema,
            "rede": rede,
            "hora": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/memorias")
def get_memorias():
    if not verificar_api_key():
        return jsonify({"erro": "API Key invalida!"}), 401
    try:
        from modules.memoria_permanente import buscar_memorias
        memorias = buscar_memorias()
        return jsonify({"memorias": memorias})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/lembrar", methods=["POST"])
def lembrar():
    if not verificar_api_key():
        return jsonify({"erro": "API Key invalida!"}), 401
    dados = request.json
    if not dados or "fato" not in dados:
        return jsonify({"erro": "Campo 'fato' obrigatorio!"}), 400
    try:
        from modules.memoria_permanente import lembrar_fato
        fato = dados["fato"]
        categoria = dados.get("categoria", "api")
        resultado = lembrar_fato(fato, categoria)
        return jsonify({"sucesso": True, "resultado": resultado})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/api/zeus", methods=["POST"])
def zeus_endpoint():
    """Endpoint especial para o Zeus se comunicar com a Veronica"""
    dados = request.json
    zeus_key = dados.get("zeus_key", "")
    if zeus_key != os.getenv("ZEUS_KEY", "zeus_veronica_2026"):
        return jsonify({"erro": "Zeus key invalida!"}), 401
    tipo = dados.get("tipo", "")
    if tipo == "alerta":
        mensagem = dados.get("mensagem", "")
        return jsonify({"recebido": True, "acao": "alerta_registrado"})
    elif tipo == "status":
        return jsonify({"veronica": "online", "hora": datetime.now().strftime("%d/%m/%Y %H:%M")})
    return jsonify({"erro": "Tipo desconhecido"}), 400

if __name__ == "__main__":
    print("🌐 API Verônica iniciando...")
    print(f"🔑 API Key: {API_KEY}")
    print("📡 Acesse: http://localhost:5001")
    print("📖 Docs: http://localhost:5001/")

    # Salva a API key no .env
    env_file = Path(".env")
    if env_file.exists():
        content = env_file.read_text()
        if "VERONICA_API_KEY" not in content:
            with open(env_file, "a") as f:
                f.write(f"\nVERONICA_API_KEY={API_KEY}")
            print(f"✅ API Key salva no .env!")

    app.run(host="0.0.0.0", port=5001, debug=False)