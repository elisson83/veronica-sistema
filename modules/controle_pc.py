import os
import subprocess
import psutil
import pyautogui
import platform
from datetime import datetime
from pathlib import Path

# Segurança - desativa o failsafe do pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

def get_info_pc() -> str:
    """Retorna informações do PC"""
    try:
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
    """Lista os processos em execução"""
    try:
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
    """Abre um programa no PC"""
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
    """Fecha um programa pelo nome"""
    try:
        os.system(f"taskkill /f /im {programa}.exe")
        return f"✅ *{programa}* fechado!"
    except Exception as e:
        return f"❌ Erro ao fechar {programa}: {e}"

def desligar_pc(minutos: int = 0) -> str:
    """Desliga o PC"""
    try:
        if minutos > 0:
            os.system(f"shutdown /s /t {minutos * 60}")
            return f"⚠️ PC será desligado em *{minutos} minutos*!"
        else:
            os.system("shutdown /s /t 30")
            return "⚠️ PC será desligado em *30 segundos*!\nDigite /cancelardesligamento para cancelar."
    except Exception as e:
        return f"❌ Erro: {e}"

def cancelar_desligamento() -> str:
    """Cancela o desligamento agendado"""
    try:
        os.system("shutdown /a")
        return "✅ Desligamento cancelado!"
    except Exception as e:
        return f"❌ Erro: {e}"

def reiniciar_pc() -> str:
    """Reinicia o PC"""
    try:
        os.system("shutdown /r /t 30")
        return "⚠️ PC será reiniciado em *30 segundos*!\nDigite /cancelardesligamento para cancelar."
    except Exception as e:
        return f"❌ Erro: {e}"

def tirar_screenshot() -> str:
    """Tira um screenshot da tela"""
    try:
        screenshot_path = Path.home() / "Desktop" / "veronica" / "assets" / "screenshot.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot = pyautogui.screenshot()
        screenshot.save(str(screenshot_path))
        return str(screenshot_path)
    except Exception as e:
        return f"❌ Erro ao tirar screenshot: {e}"

def digitar_texto(texto: str) -> str:
    """Digita um texto usando o teclado"""
    try:
        import time
        time.sleep(2)
        pyautogui.typewrite(texto, interval=0.05)
        return f"✅ Texto digitado: *{texto[:50]}*"
    except Exception as e:
        return f"❌ Erro ao digitar: {e}"

def executar_comando(comando: str) -> str:
    """Executa um comando no terminal"""
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

def get_volume(nivel: int) -> str:
    """Ajusta o volume do PC"""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(nivel / 100, None)
        return f"✅ Volume ajustado para *{nivel}%*"
    except:
        os.system(f"nircmd.exe setsysvolume {nivel * 655}")
        return f"✅ Volume ajustado para *{nivel}%*"