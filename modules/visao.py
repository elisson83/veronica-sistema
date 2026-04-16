import mss
import mss.tools
import pyautogui
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from datetime import datetime
import pytesseract

# Caminho padrão do Tesseract no Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

ASSETS_DIR = Path(__file__).parent.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def capturar_tela(regiao=None) -> str:
    """Captura a tela inteira ou uma região específica"""
    try:
        with mss.mss() as sct:
            if regiao:
                monitor = {"top": regiao[1], "left": regiao[0], "width": regiao[2], "height": regiao[3]}
            else:
                monitor = sct.monitors[1]
            
            screenshot = sct.grab(monitor)
            caminho = str(ASSETS_DIR / "screenshot.png")
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=caminho)
            return caminho
    except Exception as e:
        # Fallback para pyautogui
        try:
            caminho = str(ASSETS_DIR / "screenshot.png")
            pyautogui.screenshot(caminho)
            return caminho
        except Exception as e2:
            return f"❌ Erro ao capturar tela: {e2}"

def ler_texto_tela() -> str:
    """Lê o texto visível na tela usando OCR"""
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

def encontrar_cor(cor_rgb: tuple, tolerancia: int = 30) -> list:
    """Encontra pixels de uma cor específica na tela"""
    try:
        caminho = capturar_tela()
        imagem = cv2.imread(caminho)
        imagem_rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)
        
        lower = np.array([max(0, c - tolerancia) for c in cor_rgb])
        upper = np.array([min(255, c + tolerancia) for c in cor_rgb])
        
        mask = cv2.inRange(imagem_rgb, lower, upper)
        locais = np.where(mask > 0)
        
        if len(locais[0]) > 0:
            pontos = list(zip(locais[1].tolist(), locais[0].tolist()))
            return pontos[:10]
        return []
    except Exception as e:
        return []

def analisar_tela_com_ia(pergunta: str = "") -> dict:
    """Captura a tela e retorna informações para análise"""
    try:
        caminho = capturar_tela()
        if caminho.startswith("❌"):
            return {"erro": caminho}
        
        # Pega informações básicas da imagem
        imagem = Image.open(caminho)
        largura, altura = imagem.size
        
        # Tenta ler texto
        try:
            texto = pytesseract.image_to_string(imagem, lang='por+eng')
        except:
            texto = ""
        
        return {
            "caminho": caminho,
            "largura": largura,
            "altura": altura,
            "texto_visivel": texto[:500] if texto else "",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"erro": str(e)}

def get_posicao_mouse() -> str:
    """Retorna a posição atual do mouse"""
    x, y = pyautogui.position()
    return f"🖱️ Mouse em: X={x}, Y={y}"

def mover_mouse(x: int, y: int) -> str:
    """Move o mouse para uma posição"""
    try:
        pyautogui.moveTo(x, y, duration=0.5)
        return f"✅ Mouse movido para X={x}, Y={y}"
    except Exception as e:
        return f"❌ Erro: {e}"

def clicar(x: int, y: int, botao: str = "left") -> str:
    """Clica em uma posição específica"""
    try:
        pyautogui.click(x, y, button=botao)
        return f"✅ Clicou em X={x}, Y={y}"
    except Exception as e:
        return f"❌ Erro: {e}"

def duplo_clicar(x: int, y: int) -> str:
    """Duplo clique em uma posição"""
    try:
        pyautogui.doubleClick(x, y)
        return f"✅ Duplo clique em X={x}, Y={y}"
    except Exception as e:
        return f"❌ Erro: {e}"

def digitar(texto: str) -> str:
    """Digita um texto"""
    try:
        import time
        time.sleep(1)
        pyautogui.write(texto, interval=0.05)
        return f"✅ Digitado: {texto[:50]}"
    except Exception as e:
        return f"❌ Erro: {e}"

def pressionar_tecla(tecla: str) -> str:
    """Pressiona uma tecla"""
    try:
        pyautogui.press(tecla)
        return f"✅ Tecla pressionada: {tecla}"
    except Exception as e:
        return f"❌ Erro: {e}"

def atalho_teclado(*teclas) -> str:
    """Executa um atalho de teclado"""
    try:
        pyautogui.hotkey(*teclas)
        return f"✅ Atalho executado: {' + '.join(teclas)}"
    except Exception as e:
        return f"❌ Erro: {e}"

def scroll(direcao: str, quantidade: int = 3) -> str:
    """Faz scroll na tela"""
    try:
        if direcao == "cima":
            pyautogui.scroll(quantidade)
        else:
            pyautogui.scroll(-quantidade)
        return f"✅ Scroll {direcao} executado"
    except Exception as e:
        return f"❌ Erro: {e}"