import os
import subprocess
import platform
from datetime import datetime
from pathlib import Path

try:
    import psutil
    PSUTIL_DISPONIVEL = True
except:
    PSUTIL_DISPONIVEL = False

try:
    import pyautogui
    PYAUTOGUI_DISPONIVEL = True
except:
    PYAUTOGUI_DISPONIVEL = False

def get_info_pc() -> str:
    try:
        if not PSUTIL_DISPONIVEL:
            return "❌ psutil não disponível neste ambiente"
        cpu = psutil.cpu_percent(interval=1)
        memoria = psutil.virtual_memory()
        disco = psutil.disk_usage('/')
        bateria = psutil.sensors_battery()
        info = (
            f"💻 *Informações do PC:*\n\n"
            f"• Sistema: {platform.system()} {platform.release()}\n"
            f"• CPU: {cpu}%\n"
            f"• Memória: {memoria.percent}% usado ({memoria.used // (1024**3)}GB / {memoria.total // (1024**3)}GB)\n"
            f"• Disco: {disco.percent}% usado\n"
        )
        if bateria:
            info += f"• Bateria: {bateria.percent:.0f}% {'🔌 Carregando' if bateria.power_plugged else '🔋'}\n"
        info += f"\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        return info
    except Exception as e:
        return f"❌ Erro ao obter informações: {e}"

def listar_processos() -> str:
    try:
        if not PSUTIL_DISPONIVEL:
            return "❌ psutil não disponível neste ambiente"
        processos = []
        for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['cpu_percent'] > 0.1:
                    processos.append(proc.info)
            except:
                pass
        processos = sorted(processos, key=lambda x: x['cpu_percent'], reverse=True)[:10]
        texto = "📋 *Processos em execução (top 10):*\n\n"
        for p in processos:
            texto += f"• {p['name']}: CPU {p['cpu_percent']:.1f}% | RAM {p['memory_percent']:.1f}%\n"
        return texto
    except Exception as e:
        return f"❌ Erro ao listar processos: {e}"

def abrir_programa(programa: str) -> str:
    try:
        programas = {
            "chrome": "chrome",
            "firefox": "firefox",
            "notepad": "notepad",
            "bloco de notas": "notepad",
            "calculadora": "calc",
            "calc": "calc",
            "explorer": "explorer",
            "arquivos": "explorer",
            "cmd": "cmd",
            "terminal": "cmd",
            "word": "winword",
            "excel": "excel",
            "vscode": "code",
            "vs code": "code",
            "whatsapp": "whatsapp",
            "telegram": "telegram",
        }
        programa_lower = programa.lower()
        comando = programas.get(programa_lower, programa)
        subprocess.Popen(comando, shell=True)
        return f"✅ Abrindo *{programa}*..."
    except Exception as e:
        return f"❌ Erro ao abrir {programa}: {e}"

def fechar_programa(programa: str) -> str:
    try:
        subprocess.run(f"taskkill /f /im {programa}.exe", shell=True)
        return f"✅ *{programa}* fechado!"
    except Exception as e:
        return f"❌ Erro ao fechar {programa}: {e}"

def desligar_pc(minutos: int = 0) -> str:
    try:
        segundos = minutos * 60 if minutos > 0 else 30
        resultado = subprocess.run(
            ["shutdown", "/s", "/t", str(segundos)],
            capture_output=True,
            text=True
        )
        if resultado.returncode == 0:
            return f"⚠️ PC será desligado em *{segundos} segundos*!\nDigite /cancelardesligamento para cancelar."
        else:
            # Tenta via powershell como fallback
            subprocess.Popen(
                ["powershell", "-Command", f"Stop-Computer -Force"],
                shell=False
            )
            return "⚠️ Comando de desligamento enviado via PowerShell!"
    except Exception as e:
        return f"❌ Erro ao desligar: {e}"

def cancelar_desligamento() -> str:
    try:
        resultado = subprocess.run(
            ["shutdown", "/a"],
            capture_output=True,
            text=True
        )
        if resultado.returncode == 0:
            return "✅ Desligamento cancelado!"
        return "⚠️ Nenhum desligamento agendado ou já cancelado!"
    except Exception as e:
        return f"❌ Erro: {e}"

def reiniciar_pc() -> str:
    try:
        resultado = subprocess.run(
            ["shutdown", "/r", "/t", "30"],
            capture_output=True,
            text=True
        )
        if resultado.returncode == 0:
            return "⚠️ PC será reiniciado em *30 segundos*!\nDigite /cancelardesligamento para cancelar."
        else:
            subprocess.Popen(
                ["powershell", "-Command", "Restart-Computer -Force"],
                shell=False
            )
            return "⚠️ Comando de reinicialização enviado via PowerShell!"
    except Exception as e:
        return f"❌ Erro: {e}"

def tirar_screenshot() -> str:
    try:
        if not PYAUTOGUI_DISPONIVEL:
            return "❌ Screenshot só funciona localmente!"
        screenshot_path = Path.home() / "Desktop" / "veronica" / "assets" / "screenshot.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot = pyautogui.screenshot()
        screenshot.save(str(screenshot_path))
        return str(screenshot_path)
    except Exception as e:
        return f"❌ Erro ao tirar screenshot: {e}"

def digitar_texto(texto: str) -> str:
    try:
        if not PYAUTOGUI_DISPONIVEL:
            return "❌ Controle de teclado só funciona localmente!"
        import time
        time.sleep(2)
        pyautogui.typewrite(texto, interval=0.05)
        return f"✅ Texto digitado: *{texto[:50]}*"
    except Exception as e:
        return f"❌ Erro ao digitar: {e}"

def executar_comando(comando: str) -> str:
    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        saida = resultado.stdout or resultado.stderr
        if saida:
            return f"✅ *Resultado:*\n```\n{saida[:500]}\n```"
        return f"✅ Comando executado: `{comando}`"
    except subprocess.TimeoutExpired:
        return f"⏱️ Comando demorou muito para executar"
    except Exception as e:
        return f"❌ Erro: {e}"