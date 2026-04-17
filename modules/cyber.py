import subprocess
import os
from pathlib import Path
from datetime import datetime

# Configurações do Kali Linux no VirtualBox
KALI_VM_NAME = "kali-linux-2026.1-virtualbox-amd64"
VBOXMANAGE = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"

def get_status_kali() -> str:
    """Verifica o status do Kali Linux"""
    try:
        resultado = subprocess.run(
            [VBOXMANAGE, "showvminfo", KALI_VM_NAME, "--machinereadable"],
            capture_output=True, text=True, timeout=10
        )
        if "VMState=\"running\"" in resultado.stdout:
            return "🟢 *Kali Linux está RODANDO*"
        elif "VMState=\"saved\"" in resultado.stdout:
            return "🟡 *Kali Linux está SALVO (pausado)*"
        elif "VMState=\"poweroff\"" in resultado.stdout:
            return "🔴 *Kali Linux está DESLIGADO*"
        else:
            return "⚪ *Status do Kali Linux desconhecido*"
    except Exception as e:
        return f"❌ Erro ao verificar Kali: {e}"

def ligar_kali() -> str:
    """Liga o Kali Linux"""
    try:
        subprocess.Popen([VBOXMANAGE, "startvm", KALI_VM_NAME])
        return "✅ *Kali Linux iniciando...* Aguarde 30 segundos!"
    except Exception as e:
        return f"❌ Erro ao ligar Kali: {e}"

def desligar_kali() -> str:
    """Desliga o Kali Linux"""
    try:
        subprocess.run([VBOXMANAGE, "controlvm", KALI_VM_NAME, "poweroff"])
        return "✅ *Kali Linux desligado!*"
    except Exception as e:
        return f"❌ Erro ao desligar Kali: {e}"

def pausar_kali() -> str:
    """Pausa o Kali Linux"""
    try:
        subprocess.run([VBOXMANAGE, "controlvm", KALI_VM_NAME, "savestate"])
        return "✅ *Kali Linux pausado!*"
    except Exception as e:
        return f"❌ Erro ao pausar Kali: {e}"

def executar_comando_kali(comando: str, usuario: str = "kali", senha: str = "kali") -> str:
    """Executa um comando no Kali Linux via SSH"""
    try:
        import paramiko
        
        # Conecta via SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('127.0.0.1', port=2222, username=usuario, password=senha, timeout=10)
        
        stdin, stdout, stderr = ssh.exec_command(comando)
        saida = stdout.read().decode('utf-8', errors='ignore')
        erro = stderr.read().decode('utf-8', errors='ignore')
        ssh.close()
        
        if saida:
            return f"✅ *Resultado:*\n```\n{saida[:500]}\n```"
        elif erro:
            return f"⚠️ *Aviso:*\n```\n{erro[:300]}\n```"
        return "✅ Comando executado!"
    except Exception as e:
        return f"❌ Erro SSH: {e}\n\n💡 Certifique-se que o Kali está rodando e o SSH está ativo!"

def scan_rede(alvo: str) -> str:
    """Faz um scan de rede com nmap"""
    try:
        resultado = subprocess.run(
            ["nmap", "-sV", "--open", "-T4", alvo],
            capture_output=True, text=True, timeout=60
        )
        if resultado.stdout:
            return f"🔍 *Scan de rede: {alvo}*\n\n```\n{resultado.stdout[:800]}\n```"
        return f"❌ Nmap não encontrou resultados para {alvo}"
    except FileNotFoundError:
        # Tenta via Kali SSH
        return executar_comando_kali(f"nmap -sV --open -T4 {alvo}")
    except Exception as e:
        return f"❌ Erro no scan: {e}"

def scan_vulnerabilidades(alvo: str) -> str:
    """Faz um scan de vulnerabilidades"""
    try:
        return executar_comando_kali(f"nmap -sV --script vuln {alvo}")
    except Exception as e:
        return f"❌ Erro: {e}"

def info_rede_local() -> str:
    """Mostra informações da rede local"""
    try:
        resultado = subprocess.run(
            ["ipconfig", "/all"],
            capture_output=True, text=True, timeout=10
        )
        linhas = resultado.stdout.split('\n')
        info = []
        for linha in linhas:
            if any(x in linha for x in ['IPv4', 'IPv6', 'Gateway', 'DNS', 'Máscara', 'Adaptador']):
                info.append(linha.strip())
        return f"🌐 *Informações da Rede:*\n\n```\n{chr(10).join(info[:20])}\n```"
    except Exception as e:
        return f"❌ Erro: {e}"

def gerar_relatorio_seguranca(alvo: str) -> str:
    """Gera um relatório completo de segurança"""
    from modules.ai_brain import perguntar_ia
    
    scan = scan_rede(alvo)
    
    prompt = f"""
    Analise os resultados deste scan de segurança e gere um relatório profissional:
    
    Alvo: {alvo}
    Resultados: {scan}
    
    O relatório deve incluir:
    1. Resumo executivo
    2. Vulnerabilidades encontradas
    3. Nível de risco (Alto/Médio/Baixo)
    4. Recomendações de segurança
    5. Próximos passos
    """
    
    return perguntar_ia(prompt)