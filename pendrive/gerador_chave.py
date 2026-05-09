#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera uma chave criptográfica única para o pen drive.
Execute APENAS UMA VEZ para cada pen drive autorizado.
A chave gerada deve ser copiada para o pen drive como '.veronica_key'.
Um arquivo 'emergencia.key' é salvo localmente como backup caso o pen drive seja perdido.
"""
import secrets
import hashlib
import json
import getpass
import sys
from datetime import datetime
from pathlib import Path


CHAVE_FILENAME     = ".veronica_key"
EMERGENCIA_FILE    = Path(__file__).parent / "emergencia.key"
_PBKDF2_ITERACOES  = 600_000


def _hash_senha(senha: str, salt: bytes) -> str:
    """PBKDF2-HMAC-SHA256 com 600 000 iterações. Retorna hex."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt,
        _PBKDF2_ITERACOES,
    ).hex()


def _pedir_senha_emergencia() -> str:
    """Pede a senha de emergência duas vezes e valida a confirmação."""
    print("\n  === SENHA DE EMERGÊNCIA ===")
    print("  Essa senha permite acesso caso o pen drive seja perdido.")
    print("  Escolha uma senha forte (mínimo 12 caracteres).\n")
    while True:
        senha = getpass.getpass("  Senha de emergência: ")
        if len(senha) < 12:
            print("  [AV] Senha muito curta. Use no mínimo 12 caracteres.\n")
            continue
        confirmacao = getpass.getpass("  Confirme a senha:     ")
        if senha != confirmacao:
            print("  [AV] Senhas não conferem. Tente novamente.\n")
            continue
        return senha


def _salvar_emergencia(senha: str) -> None:
    """Cria o arquivo emergencia.key com o hash da senha."""
    salt       = secrets.token_bytes(32)
    hash_senha = _hash_senha(senha, salt)
    dados = {
        "salt":       salt.hex(),
        "hash":       hash_senha,
        "criado_em":  datetime.now().isoformat(),
        "iteracoes":  _PBKDF2_ITERACOES,
        "algoritmo":  "pbkdf2-hmac-sha256",
    }
    EMERGENCIA_FILE.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    print(f"\n  [OK] Senha de emergência salva em: {EMERGENCIA_FILE.resolve()}")
    print("       Guarde esse arquivo em local seguro (separado do pen drive).")
    print("       SEM esse arquivo, a senha de emergência não funcionará.")


def gerar(pedir_emergencia: bool = True) -> dict:
    """Gera o token do pen drive e opcionalmente registra a senha de emergência."""
    token      = secrets.token_hex(64)         # 128 chars hex
    criado_em  = datetime.now().isoformat()
    checksum   = hashlib.sha256((token + criado_em).encode()).hexdigest()

    dados = {
        "token":     token,
        "criado_em": criado_em,
        "checksum":  checksum,
        "versao":    "1.1",
    }

    saida = Path(CHAVE_FILENAME)
    saida.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    print(f"\n  [OK] Chave gerada: {saida.resolve()}")
    print(f"       Copie o arquivo '{CHAVE_FILENAME}' para a raiz do pen drive.")
    print(f"       Token (primeiros 16): {token[:16]}...")

    if pedir_emergencia:
        try:
            senha = _pedir_senha_emergencia()
            _salvar_emergencia(senha)
        except (KeyboardInterrupt, EOFError):
            print("\n  [AV] Senha de emergência não configurada.")

    return dados


if __name__ == "__main__":
    _args       = sys.argv[1:]
    _so_emerg   = "--emergencia" in _args
    _posicionais = [a for a in _args if not a.startswith("--")]

    # Modo --emergencia: apenas configura/reconfigura a senha, sem gerar nova chave
    if _so_emerg:
        print("=" * 52)
        print("  CONFIGURAR SENHA DE EMERGÊNCIA")
        print("=" * 52)
        try:
            _senha = _pedir_senha_emergencia()
            _salvar_emergencia(_senha)
        except (KeyboardInterrupt, EOFError):
            print("\n  [AV] Cancelado.")
            sys.exit(1)
        sys.exit(0)

    # Modo normal: gera a chave do pen drive
    destino = Path(_posicionais[0]) if _posicionais else Path(".")
    destino_arquivo = destino / CHAVE_FILENAME

    if destino_arquivo.exists():
        print(f"[AV] Chave já existe em {destino_arquivo}. Exclua antes de gerar nova.")
        sys.exit(1)

    print("=" * 52)
    print("  GERADOR DE CHAVE — Ecossistema Verônica")
    print("=" * 52)

    dados = gerar(pedir_emergencia=True)

    if destino != Path("."):
        destino_arquivo.write_text(json.dumps(dados, indent=2), encoding="utf-8")
        Path(CHAVE_FILENAME).unlink(missing_ok=True)
        print(f"\n  [OK] Chave salva diretamente em: {destino_arquivo}")

    print("\n  Próximos passos:")
    print(f"  1. Copie '{CHAVE_FILENAME}' para a raiz do pen drive")
    print(f"  2. Guarde '{EMERGENCIA_FILE.name}' em local seguro (nuvem, e-mail, cofre)")
    print("  3. NUNCA compartilhe a senha de emergência")
    print("=" * 52)
