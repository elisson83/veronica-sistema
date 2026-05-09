#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica se o pen drive com a chave autorizada está conectado.
Suporta modo de emergência (--emergencia) caso o pen drive seja perdido.

Uso direto:
    python verificador_chave.py                  # verifica pen drive
    python verificador_chave.py --emergencia     # acesso via senha de emergência

Uso em app.py:
    from pendrive.verificador_chave import exigir_pendrive
    exigir_pendrive()   # interrompe o processo se nenhum acesso for válido
"""
import getpass
import hashlib
import json
import sys
import time
from pathlib import Path


CHAVE_FILENAME    = ".veronica_key"
EMERGENCIA_FILE   = Path(__file__).parent / "emergencia.key"
_PBKDF2_ITERACOES = 600_000
_MAX_TENTATIVAS   = 3       # tentativas antes de bloquear por _COOLDOWN_SEG
_COOLDOWN_SEG     = 5.0     # espera entre ciclos de tentativas

# Diretórios padrão onde pen drives são montados por SO
_CAMINHOS_PENDRIVE = [
    # Linux/Ubuntu
    "/media",
    "/mnt",
    # Windows — todas as letras de unidade D: a Z:
    *[f"{chr(c)}:\\" for c in range(ord('D'), ord('Z') + 1)],
]


# ── Pen drive ─────────────────────────────────────────────────────────────────

def _validar_dados(dados: dict) -> bool:
    token     = dados.get("token", "")
    criado_em = dados.get("criado_em", "")
    esperado  = hashlib.sha256((token + criado_em).encode()).hexdigest()
    return dados.get("checksum") == esperado and len(token) == 128


def encontrar_chave() -> Path | None:
    """Procura o arquivo .veronica_key em todos os pen drives montados."""
    for base in _CAMINHOS_PENDRIVE:
        raiz = Path(base)
        if not raiz.exists():
            continue
        candidatos = (
            list(raiz.glob(f"**/{CHAVE_FILENAME}"))
            if str(raiz).startswith("/")
            else [raiz / CHAVE_FILENAME]
        )
        for candidato in candidatos:
            if candidato.exists():
                return candidato
    return None


def verificar() -> bool:
    """Retorna True se um pen drive com chave válida estiver conectado."""
    chave_path = encontrar_chave()
    if not chave_path:
        return False
    try:
        dados = json.loads(chave_path.read_text(encoding="utf-8"))
        return _validar_dados(dados)
    except Exception:
        return False


# ── Emergência ────────────────────────────────────────────────────────────────

def emergencia_configurada() -> bool:
    """Retorna True se o arquivo emergencia.key existir e for válido."""
    if not EMERGENCIA_FILE.exists():
        return False
    try:
        dados = json.loads(EMERGENCIA_FILE.read_text(encoding="utf-8"))
        return bool(dados.get("hash") and dados.get("salt"))
    except Exception:
        return False


def verificar_emergencia(senha: str) -> bool:
    """
    Verifica a senha de emergência contra o hash salvo em emergencia.key.
    Retorna True se a senha estiver correta.
    """
    if not EMERGENCIA_FILE.exists():
        return False
    try:
        dados  = json.loads(EMERGENCIA_FILE.read_text(encoding="utf-8"))
        salt   = bytes.fromhex(dados["salt"])
        iters  = int(dados.get("iteracoes", _PBKDF2_ITERACOES))
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt,
            iters,
        ).hex()
        return hashed == dados["hash"]
    except Exception:
        return False


def acesso_via_emergencia() -> bool:
    """
    Modo interativo: pede a senha de emergência até _MAX_TENTATIVAS vezes.
    Retorna True se a senha for correta, False após esgotar as tentativas.
    """
    if not emergencia_configurada():
        print("[ERRO] Arquivo 'emergencia.key' não encontrado.")
        print("       Execute 'python gerador_chave.py' para configurar a senha de emergência.")
        return False

    print("\n  === ACESSO DE EMERGÊNCIA ===")
    print(f"  Arquivo: {EMERGENCIA_FILE.resolve()}\n")

    for tentativa in range(1, _MAX_TENTATIVAS + 1):
        try:
            senha = getpass.getpass(f"  Senha de emergência ({tentativa}/{_MAX_TENTATIVAS}): ")
        except (KeyboardInterrupt, EOFError):
            print("\n  [AV] Cancelado.")
            return False

        if verificar_emergencia(senha):
            print("\n  [OK] Senha de emergência aceita. Acesso liberado.")
            return True

        restantes = _MAX_TENTATIVAS - tentativa
        if restantes > 0:
            print(f"  [AV] Senha incorreta. {restantes} tentativa(s) restante(s).")
            time.sleep(_COOLDOWN_SEG)
        else:
            print("  [ERRO] Tentativas esgotadas.")

    return False


# ── API pública ───────────────────────────────────────────────────────────────

def exigir_pendrive(
    mensagem: str = "Pen drive de segurança não encontrado. Conecte e tente novamente.",
    permitir_emergencia: bool = False,
):
    """
    Interrompe a execução se nenhum acesso válido for encontrado.
    Se permitir_emergencia=True, oferece o modo interativo de senha caso o pen drive falhe.
    """
    if verificar():
        print("[OK] Pen drive de segurança verificado.")
        return

    if permitir_emergencia and emergencia_configurada():
        print(f"[AV] {mensagem}")
        if acesso_via_emergencia():
            return

    print(f"[ERRO] {mensagem}")
    sys.exit(1)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    modo_emergencia = "--emergencia" in sys.argv

    if modo_emergencia:
        ok = acesso_via_emergencia()
        sys.exit(0 if ok else 1)

    # Modo normal: verifica pen drive
    if verificar():
        print("[OK] Chave de segurança válida encontrada.")
        sys.exit(0)

    print("[ERRO] Nenhum pen drive com chave válida encontrado.")

    if emergencia_configurada():
        print("      Use  python verificador_chave.py --emergencia  para acesso de backup.")

    sys.exit(1)
