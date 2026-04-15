"""
╔══════════════════════════════════════════════════════════╗
║           VERÔNICA IA - Arquivo Principal                ║
╚══════════════════════════════════════════════════════════╝
"""

from config import TELEGRAM_TOKEN
from modules.telegram_bot import iniciar_bot

def main():
    print("\n🤖 Iniciando Verônica IA...\n")
    
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "seu_token_aqui":
        print("❌ Token do Telegram não configurado no arquivo .env!")
        return
    
    print("✅ Configurações OK!")
    print("🚀 Iniciando bot do Telegram...")
    print("⏹  Para parar, aperte Ctrl+C\n")
    
    iniciar_bot()

if __name__ == "__main__":
    main()