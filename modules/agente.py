import time
from modules.controle_pc import abrir_programa, executar_comando
from modules.ai_brain import perguntar_ia

try:
    import pyautogui
    PYAUTOGUI_DISPONIVEL = True
except:
    PYAUTOGUI_DISPONIVEL = False

def analisar_tarefa(descricao: str) -> list:
    prompt = f"""
    Você é um agente de automação. O usuário quer executar esta tarefa:
    "{descricao}"
    
    Quebre esta tarefa em passos simples e executáveis.
    Responda APENAS em formato JSON assim:
    {{
        "passos": [
            {{"acao": "abrir_programa", "parametro": "chrome"}},
            {{"acao": "aguardar", "parametro": "2"}},
            {{"acao": "digitar", "parametro": "texto aqui"}},
            {{"acao": "tecla", "parametro": "enter"}}
        ]
    }}
    """
    try:
        import json
        resposta = perguntar_ia(prompt)
        inicio = resposta.find('{')
        fim = resposta.rfind('}') + 1
        if inicio >= 0 and fim > inicio:
            json_str = resposta[inicio:fim]
            dados = json.loads(json_str)
            return dados.get("passos", [])
    except Exception as e:
        print(f"Erro ao analisar tarefa: {e}")
    return []

def executar_passo(passo: dict) -> str:
    acao = passo.get("acao", "")
    parametro = passo.get("parametro", "")

    try:
        if acao == "abrir_programa":
            abrir_programa(parametro)
            time.sleep(2)
            return f"✅ Abriu {parametro}"

        elif acao == "aguardar":
            segundos = float(parametro) if parametro else 2
            time.sleep(segundos)
            return f"✅ Aguardou {segundos}s"

        elif acao == "digitar":
            if not PYAUTOGUI_DISPONIVEL:
                return "❌ Digitar só funciona localmente!"
            time.sleep(1)
            pyautogui.write(parametro, interval=0.05)
            return f"✅ Digitou: {parametro[:30]}"

        elif acao == "tecla":
            if not PYAUTOGUI_DISPONIVEL:
                return "❌ Tecla só funciona localmente!"
            pyautogui.press(parametro)
            return f"✅ Tecla: {parametro}"

        elif acao == "atalho":
            if not PYAUTOGUI_DISPONIVEL:
                return "❌ Atalho só funciona localmente!"
            teclas = parametro.replace("+", " ").split()
            pyautogui.hotkey(*teclas)
            return f"✅ Atalho: {parametro}"

        elif acao == "clicar":
            if not PYAUTOGUI_DISPONIVEL:
                return "❌ Clicar só funciona localmente!"
            coords = parametro.split(",")
            if len(coords) >= 2:
                x, y = int(coords[0].strip()), int(coords[1].strip())
                pyautogui.click(x, y)
                return f"✅ Clicou em {x},{y}"

        elif acao == "executar":
            return executar_comando(parametro)

        elif acao == "scroll":
            if not PYAUTOGUI_DISPONIVEL:
                return "❌ Scroll só funciona localmente!"
            if parametro == "cima":
                pyautogui.scroll(3)
            else:
                pyautogui.scroll(-3)
            return f"✅ Scroll {parametro}"

        return f"⚠️ Ação desconhecida: {acao}"

    except Exception as e:
        return f"❌ Erro em {acao}: {e}"

def executar_tarefa_autonoma(descricao: str, callback=None) -> list:
    resultados = []

    if callback:
        callback(f"🤖 Analisando tarefa: {descricao}")

    passos = analisar_tarefa(descricao)

    if not passos:
        return ["❌ Não consegui entender a tarefa. Tente ser mais específico."]

    if callback:
        callback(f"📋 Encontrei {len(passos)} passos para executar...")

    for i, passo in enumerate(passos, 1):
        if callback:
            callback(f"⚡ Passo {i}/{len(passos)}: {passo.get('acao')} - {passo.get('parametro', '')}")
        resultado = executar_passo(passo)
        resultados.append(f"Passo {i}: {resultado}")
        time.sleep(0.5)

    if callback:
        callback("✅ Tarefa concluída!")

    return resultados