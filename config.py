import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
ASSETS_DIR = ROOT_DIR / "assets"

USERS_FILE = DATA_DIR / "users.json"

NIVEIS_DISPONIVEIS = ["iniciante", "intermediario", "avancado"]
NIVEL_PADRAO = "iniciante"
MAX_ETAPAS = 20
OVERLAY_TIMEOUT = 15