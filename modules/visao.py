from pathlib import Path
from datetime import datetime

try:
    import mss
    import mss.tools
    MSS_DISPONIVEL = True
except:
    MSS_DISPONIVEL = False

try:
    import pyautogui
    PYAUTOGUI_DISPONIVEL = True
except:
    PYAUTOGUI_DISPONIVEL = False

try:
    import cv2
    import numpy as np
    CV2_DISPONIVEL = True
except:
    CV2_DISPONIVEL = False

try:
    from PIL import Image
    PIL_DISPONIVEL = True
except:
    PIL_DISPONIVEL = False

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    TESSERACT_DISPONIVEL = True
except:
    TESSERACT_DISPONIVEL = False

ASSETS_DIR = Path(__file__).parent.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def capturar_tela(regiao=None) -> str:
    if not MSS_DISPONIVEL and not PYAUTOGUI_DISPONIVEL:
        return "❌ Captura de tela só funciona localmente!"
    try:
        if MSS_DISPONIVEL:
            with mss.mss() as sct:
                if regiao:
                    monitor = {"top": regiao[1], "left": regiao[0], "width": regiao[2], "height": regiao[3]}
                else:
                    monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                caminho = str(ASSETS_DIR / "screenshot.png")
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=caminho)
                return caminho
        elif PYAUTOGUI_DISPONIVEL:
            caminho = str(ASSETS_DIR / "screenshot.png")
            pyautogui.screenshot(caminho)
            return caminho
    except Exception as e:
        return f"❌ Erro ao capturar tela: {e}"

def ler_texto_tela() -> str:
    if not TESSERACT_DISPONIVEL:
        return "❌ OCR só funciona localmente com Tesseract instalado!"
    try:
        caminho = capturar_tela()
        if caminho.startswith("❌"):
            return caminho
        imagem = Image.open(caminho)
        texto = pytesseract.image_to_string(imagem, lang='por+eng')
        if texto.strip():
            return f"📖 *Texto encontrado na tela:*\n\n{texto[:1000]}"
        return "📖 Não encontrei texto legível na tela."
    except Exception as e:
        return f"❌ Erro ao ler texto: {e}"

def get_posicao_mouse() -> str:
    if not PYAUTOGUI_DISPONIVEL:
        return "❌ Controle de mouse só funciona localmente!"
    try:
        x, y = pyautogui.position()
        return f"🖱️ Mouse em: X={x}, Y={y}"
    except Exception as e:
        return f"❌ Erro: {e}"

def mover_mouse(x: int, y: int) -> str:
    if not PYAUTOGUI_DISPONIVEL:
        return "❌ Controle de mouse só funciona localmente!"
    try:
        pyautogui.moveTo(x, y, duration=0.5)
        return f"✅ Mouse movido para X={x}, Y={y}"
    except Exception as e:
        return f"❌ Erro: {e}"

def clicar(x: int, y: int, botao: str = "left") -> str:
    if not PYAUTOGUI_DISPONIVEL:
        return "❌ Controle de mouse só funciona localmente!"
    try:
        pyautogui.click(x, y, button=botao)
        return f"✅ Clicou em X={x}, Y={y}"
    except Exception as e:
        return f"❌ Erro: {e}"

def duplo_clicar(x: int, y: int) -> str:
    if not PYAUTOGUI_DISPONIVEL:
        return "❌ Controle de mouse só funciona localmente!"
    try:
        pyautogui.doubleClick(x, y)
        return f"✅ Duplo clique em X={x}, Y={y}"
    except Exception as e:
        return f"❌ Erro: {e}"

def digitar(texto: str) -> str:
    if not PYAUTOGUI_DISPONIVEL:
        return "❌ Controle de teclado só funciona localmente!"
    try:
        import time
        time.sleep(1)
        pyautogui.write(texto, interval=0.05)
        return f"✅ Digitado: {texto[:50]}"
    except Exception as e:
        return f"❌ Erro: {e}"

def pressionar_tecla(tecla: str) -> str:
    if not PYAUTOGUI_DISPONIVEL:
        return "❌ Controle de teclado só funciona localmente!"
    try:
        pyautogui.press(tecla)
        return f"✅ Tecla pressionada: {tecla}"
    except Exception as e:
        return f"❌ Erro: {e}"

def atalho_teclado(*teclas) -> str:
    if not PYAUTOGUI_DISPONIVEL:
        return "❌ Controle de teclado só funciona localmente!"
    try:
        pyautogui.hotkey(*teclas)
        return f"✅ Atalho executado: {' + '.join(teclas)}"
    except Exception as e:
        return f"❌ Erro: {e}"

def scroll(direcao: str, quantidade: int = 3) -> str:
    if not PYAUTOGUI_DISPONIVEL:
        return "❌ Controle de mouse só funciona localmente!"
    try:
        if direcao == "cima":
            pyautogui.scroll(quantidade)
        else:
            pyautogui.scroll(-quantidade)
        return f"✅ Scroll {direcao} executado"
    except Exception as e:
        return f"❌ Erro: {e}"