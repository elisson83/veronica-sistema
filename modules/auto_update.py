import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def verificar_atualizacao() -> dict:
    try:
        # Busca atualizacoes do GitHub
        resultado = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )

        # Verifica se tem commits novos
        status = subprocess.run(
            ["git", "status", "-uno"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )

        tem_atualizacao = "Your branch is behind" in status.stdout

        # Pega o log de mudancas
        log = subprocess.run(
            ["git", "log", "HEAD..origin/main", "--oneline"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )

        mudancas = log.stdout.strip() if log.stdout.strip() else "Nenhuma mudanca"

        return {
            "tem_atualizacao": tem_atualizacao,
            "mudancas": mudancas,
            "hora": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
    except Exception as e:
        return {
            "tem_atualizacao": False,
            "mudancas": "",
            "erro": str(e)
        }

def aplicar_atualizacao() -> str:
    try:
        resultado = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        if resultado.returncode == 0:
            return f"✅ Atualizado com sucesso!\n\n{resultado.stdout}"
        return f"❌ Erro ao atualizar:\n{resultado.stderr}"
    except Exception as e:
        return f"❌ Erro: {e}"

def instalar_dependencias() -> str:
    try:
        resultado = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--break-system-packages"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        if resultado.returncode == 0:
            return "✅ Dependências instaladas!"
        return f"❌ Erro: {resultado.stderr}"
    except Exception as e:
        return f"❌ Erro: {e}"

def reiniciar_veronica() -> str:
    try:
        python = sys.executable
        os.execv(python, [python] + sys.argv)
        return "✅ Reiniciando..."
    except Exception as e:
        return f"❌ Erro ao reiniciar: {e}"

def get_versao_atual() -> str:
    try:
        resultado = subprocess.run(
            ["git", "log", "-1", "--format=%h %s %cr"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent.parent)
        )
        return resultado.stdout.strip()
    except:
        return "Versão desconhecida"

def get_status_sistema() -> str:
    versao = get_versao_atual()
    update = verificar_atualizacao()

    status = (
        f"🔄 *Status do Sistema:*\n\n"
        f"• Versão atual: `{versao}`\n"
        f"• Atualização disponível: {'✅ Sim' if update['tem_atualizacao'] else '❌ Não'}\n"
        f"• Verificado em: {update['hora']}\n"
    )

    if update.get("tem_atualizacao") and update.get("mudancas"):
        status += f"\n📝 *Mudanças:*\n{update['mudancas']}"

    return status