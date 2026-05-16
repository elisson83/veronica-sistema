import importlib.util
import os
import sqlite3
import subprocess
import sys

from cryptography.fernet import Fernet

from config import DATA_DIR

DB_PATH = DATA_DIR / "api_integrations.db"
FERNET_FILE = DATA_DIR / "api_integrations.key"

SUPPORTED_APIS = {
    "binance": {"package": "python-binance", "import_name": "binance", "label": "Binance"},
    "coingecko": {"package": "requests", "import_name": "requests", "label": "CoinGecko"},
    "openweather": {"package": "requests", "import_name": "requests", "label": "OpenWeather"},
    "newsapi": {"package": "requests", "import_name": "requests", "label": "NewsAPI"},
}


def normalize_api_name(name: str) -> str:
    return (name or "").strip().lower().replace("-", "").replace("_", "")


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_integrations (
            name TEXT PRIMARY KEY,
            encrypted_key BLOB NOT NULL,
            package_name TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


def _get_fernet() -> Fernet:
    env_key = os.getenv("VERONICA_FERNET_KEY")
    if env_key:
        return Fernet(env_key.encode())
    DATA_DIR.mkdir(exist_ok=True)
    if FERNET_FILE.exists():
        key = FERNET_FILE.read_bytes()
    else:
        key = Fernet.generate_key()
        FERNET_FILE.write_bytes(key)
    return Fernet(key)


def _is_import_available(import_name: str) -> bool:
    return importlib.util.find_spec(import_name) is not None


def install_dependency_for_api(name: str) -> str:
    api = SUPPORTED_APIS[name]
    if _is_import_available(api["import_name"]):
        return f"Biblioteca {api['package']} ja esta disponivel."
    cmd = [sys.executable, "-m", "pip", "install", api["package"]]
    if os.name != "nt":
        cmd.append("--break-system-packages")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"Falha ao instalar {api['package']}: {stderr[-1000:]}")
    return f"Biblioteca {api['package']} instalada."


def add_api(name: str, secret: str) -> str:
    name = normalize_api_name(name)
    if name not in SUPPORTED_APIS:
        supported = ", ".join(sorted(SUPPORTED_APIS))
        return f"API nao suportada. Suportadas: {supported}."
    if not secret:
        return "Informe a chave secreta da API."
    install_msg = install_dependency_for_api(name)
    encrypted = _get_fernet().encrypt(secret.encode("utf-8"))
    api = SUPPORTED_APIS[name]
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO api_integrations(name, encrypted_key, package_name, enabled)
            VALUES(?, ?, ?, 1)
            ON CONFLICT(name) DO UPDATE SET
                encrypted_key=excluded.encrypted_key,
                package_name=excluded.package_name,
                enabled=1,
                updated_at=CURRENT_TIMESTAMP
            """,
            (name, encrypted, api["package"]),
        )
    return f"{api['label']} integrada e ativa. {install_msg}"


def remove_api(name: str) -> str:
    name = normalize_api_name(name)
    with _connect() as conn:
        cur = conn.execute("DELETE FROM api_integrations WHERE name = ?", (name,))
    if cur.rowcount:
        return f"API {name} removida."
    return f"API {name} nao estava integrada."


def list_apis() -> str:
    with _connect() as conn:
        rows = conn.execute("SELECT name, package_name, enabled, updated_at FROM api_integrations ORDER BY name").fetchall()
    if not rows:
        supported = ", ".join(sorted(SUPPORTED_APIS))
        return f"Nenhuma API integrada ainda.\nSuportadas: {supported}."
    lines = ["APIs integradas:"]
    for name, package_name, enabled, updated_at in rows:
        status = "ativa" if enabled else "inativa"
        lines.append(f"- {name}: {status} ({package_name}) atualizada em {updated_at}")
    return "\n".join(lines)


def get_api_secret(name: str) -> str | None:
    name = normalize_api_name(name)
    with _connect() as conn:
        row = conn.execute("SELECT encrypted_key FROM api_integrations WHERE name = ? AND enabled = 1", (name,)).fetchone()
    if not row:
        return None
    return _get_fernet().decrypt(row[0]).decode("utf-8")
