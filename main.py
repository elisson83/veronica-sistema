import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from config import TELEGRAM_TOKEN, USUARIOS_AUTORIZADOS
from modules.telegram_bot import iniciar_bot
from modules.licenca import registrar_instalacao, verificar_licenca

def main():
    print("🤖 Iniciando Verônica IA...")
    print("=" * 40)

    # Registra instalação e notifica pelo Telegram
    try:
        admin_id = USUARIOS_AUTORIZADOS[0]
        codigo = registrar_instalacao(TELEGRAM_TOKEN, admin_id)
        if not codigo.startswith("❌"):
            print(f"✅ Licença: {codigo}")
        else:
            print(f"⚠️ {codigo}")
    except Exception as e:
        print(f"⚠️ Aviso licença: {e}")

    print("=" * 40)
    print("✅ Verônica está online!")
    print("📱 Aguardando mensagens no Telegram...")
    print("=" * 40)

    # Inicia o bot
    iniciar_bot()

if __name__ == "__main__":
    main()