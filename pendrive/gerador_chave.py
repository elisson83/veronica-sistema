#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera uma chave criptográfica única para o pen drive.
Execute APENAS UMA VEZ para cada pen drive autorizado.
A chave gerada deve ser copiada para o pen drive como '.veronica_key'.
"""
import secrets
import hashlib
import json
from datetime import datetime
from pathlib import Path


CHAVE_FILENAME = ".veronica_key"


def gerar():
    token      = secrets.token_hex(64)         # 128 chars hex
    criado_em  = datetime.now().isoformat()
    checksum   = hashlib.sha256((token + criado_em).encode()).hexdigest()

    dados = {
        "token":     token,
        "criado_em": criado_em,
        "checksum":  checksum,
        "versao":    "1.0",
    }

    saida = Path(CHAVE_FILENAME)
    saida.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    print(f"[OK] Chave gerada: {saida.resolve()}")
    print(f"     Copie o arquivo '{CHAVE_FILENAME}' para a raiz do pen drive.")
    print(f"     Token (primeiros 16): {token[:16]}...")
    return dados


if __name__ == "__main__":
    import sys
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    destino_arquivo = destino / CHAVE_FILENAME
    if destino_arquivo.exists():
        print(f"[AV] Chave já existe em {destino_arquivo}. Exclua antes de gerar nova.")
        sys.exit(1)

    dados = gerar()
    if destino != Path("."):
        destino_arquivo.write_text(json.dumps(dados, indent=2), encoding="utf-8")
        Path(CHAVE_FILENAME).unlink(missing_ok=True)
        print(f"[OK] Chave salva diretamente em: {destino_arquivo}")
