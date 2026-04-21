import os
import asyncio
import requests
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ZEUS_TOKEN = os.getenv("ZEUS_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "8106101043"))
VERONICA_API = "http://localhost:5001"
ZEUS_KEY = os.getenv("ZEUS_KEY", "zeus_veronica_2026")

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ *Zeus — Guardião do Ecossistema Verônica*\n\n"
        "🛡️ Estou online e monitorando!\n\n"
        "Comandos:\n"
        "/status — Status de todos os sistemas\n"
        "/rede — Informações da rede\n"
        "/processos — Processos suspeitos\n"
        "/varredura — Varredura de segurança\n"
        "/veronica — Status da Verônica\n"
        "/relatorio — Relatório completo",
        parse_mode="Markdown"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Acesso negado!")
        return
    await update.message.reply_text("🔍 Verificando sistemas...")

    status = "⚡ *Status Zeus:*\n\n"

    # Verifica Verônica
    try:
        r = requests.get(f"{VERONICA_API}/api/status", timeout=5)
        if r.status_code == 200:
            dados = r.json()
            status += "✅ Verônica: Online\n"
            status += f"  • Groq: {'✅' if dados.get('groq') else '❌'}\n"
            status += f"  • Ollama: {'✅' if dados.get('ollama') else '❌'}\n"
        else:
            status += "❌ Verônica: Offline\n"
    except:
        status += "❌ Verônica API: Offline\n"

    # Info do sistema
    status += f"\n💻 *Sistema:*\n"
    status += f"• OS: {platform.system()} {platform.release()}\n"
    status += f"• Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"

    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        status += f"• CPU: {cpu}%\n"
        status += f"• RAM: {mem.percent}%\n"
    except:
        pass

    await update.message.reply_text(status, parse_mode="Markdown")

async def rede_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Acesso negado!")
        return
    await update.message.reply_text("🌐 Verificando rede...")
    try:
        resultado = subprocess.run(["ipconfig"], capture_output=True, text=True, shell=True)
        saida = resultado.stdout[:1000] if resultado.stdout else "Sem informações"
        await update.message.reply_text(f"🌐 *Rede:*\n```\n{saida}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

async def processos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Acesso negado!")
        return
    try:
        import psutil
        processos_suspeitos = []
        for proc in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
            try:
                if proc.info["cpu_percent"] > 50:
                    processos_suspeitos.append(proc.info)
            except:
                pass

        if processos_suspeitos:
            texto = "⚠️ *Processos com alto uso:*\n\n"
            for p in processos_suspeitos[:5]:
                texto += f"• {p['name']}: CPU {p['cpu_percent']}%\n"
        else:
            texto = "✅ *Nenhum processo suspeito!*\n\nSistema operando normalmente."

        await update.message.reply_text(texto, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}")

async def varredura_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Acesso negado!")
        return
    await update.message.reply_text("🔍 Iniciando varredura de segurança...")

    resultado = "🛡️ *Relatório de Segurança Zeus:*\n\n"

    # Verifica portas abertas
    portas_importantes = [5000, 5001, 11434, 8080]
    resultado += "🔌 *Portas monitoradas:*\n"
    for porta in portas_importantes:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            r = s.connect_ex(("localhost", porta))
            s.close()
            status = "🟢 Aberta" if r == 0 else "🔴 Fechada"
            nomes = {5000: "Dashboard", 5001: "API Verônica", 11434: "Ollama", 8080: "Web"}
            resultado += f"• {nomes.get(porta, porta)}: {status}\n"
        except:
            pass

    resultado += f"\n✅ Varredura concluída!\n"
    resultado += f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    await update.message.reply_text(resultado, parse_mode="Markdown")

async def veronica_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Acesso negado!")
        return
    try:
        r = requests.get(f"{VERONICA_API}/api/status", timeout=5)
        if r.status_code == 200:
            dados = r.json()
            texto = (
                f"🤖 *Verônica Status:*\n\n"
                f"• Status: ✅ Online\n"
                f"• Groq: {'✅' if dados.get('groq') else '❌'}\n"
                f"• Gemini: {'✅' if dados.get('gemini') else '❌'}\n"
                f"• Ollama: {'✅' if dados.get('ollama') else '❌'}\n"
                f"• Hora: {dados.get('hora', '?')}\n"
            )
        else:
            texto = "❌ Verônica offline!"
        await update.message.reply_text(texto, parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Verônica API não responde!\nCertifique que api_veronica.py está rodando.")

async def relatorio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Acesso negado!")
        return
    await update.message.reply_text("📊 Gerando relatório completo...")

    relatorio = (
        f"📊 *Relatório Completo Zeus*\n"
        f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        f"🖥️ *Sistema:*\n"
        f"• OS: {platform.system()} {platform.release()}\n"
    )

    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disco = psutil.disk_usage("/")
        relatorio += f"• CPU: {cpu}%\n"
        relatorio += f"• RAM: {mem.percent}% ({mem.used // (1024**3)}GB/{mem.total // (1024**3)}GB)\n"
        relatorio += f"• Disco: {disco.percent}%\n"
    except:
        pass

    try:
        r = requests.get(f"{VERONICA_API}/api/status", timeout=5)
        if r.status_code == 200:
            relatorio += f"\n🤖 *Verônica:* ✅ Online\n"
        else:
            relatorio += f"\n🤖 *Verônica:* ❌ Offline\n"
    except:
        relatorio += f"\n🤖 *Verônica:* ❌ Offline\n"

    relatorio += f"\n⚡ *Zeus:* ✅ Ativo e protegendo!"

    await update.message.reply_text(relatorio, parse_mode="Markdown")

async def notificar_admin(app, mensagem: str):
    try:
        await app.bot.send_message(chat_id=ADMIN_ID, text=mensagem, parse_mode="Markdown")
    except Exception as e:
        print(f"Erro ao notificar: {e}")

def iniciar_zeus():
    print("⚡ Zeus iniciando...")
    app = ApplicationBuilder().token(ZEUS_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("rede", rede_cmd))
    app.add_handler(CommandHandler("processos", processos_cmd))
    app.add_handler(CommandHandler("varredura", varredura_cmd))
    app.add_handler(CommandHandler("veronica", veronica_cmd))
    app.add_handler(CommandHandler("relatorio", relatorio_cmd))
    print("⚡ Zeus online! Guardião ativo!")
    app.run_polling()

if __name__ == "__main__":
    iniciar_zeus()