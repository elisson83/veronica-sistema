#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifica se o pen drive com a chave autorizada está conectado.
Pode ser importado pelos apps Flask para exigir o pen drive na inicialização.

Uso em app.py:
    from pendrive.verificador_chave import exigir_pendrive
    exigir_pendrive()   # interrompe o processo se a chave não for encontrada
"""
import hashlib
import json
import sys
from pathlib import Path


CHAVE_FILENAME = ".veronica_key"

# Diretórios padrão onde pen drives são montados por SO
_CAMINHOS_PENDRIVE = [
    # Linux/Ubuntu
    "/media",
    "/mnt",
    # Windows — todas as letras de unidade D: a Z:
    *[f"{chr(c)}:\\" for c in range(ord('D'), ord('Z') + 1)],
]


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
        # Em Linux, monta em /media/<usuario>/<pendrive>/
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


def exigir_pendrive(mensagem: str = "Pen drive de segurança não encontrado. Conecte e tente novamente."):
    """Interrompe a execução se o pen drive não estiver conectado."""
    if not verificar():
        print(f"[ERRO] {mensagem}")
        sys.exit(1)
    print("[OK] Pen drive de segurança verificado.")


if __name__ == "__main__":
    if verificar():
        print("[OK] Chave de segurança válida encontrada.")
        sys.exit(0)
    else:
        print("[ERRO] Nenhum pen drive com chave válida encontrado.")
        sys.exit(1)
