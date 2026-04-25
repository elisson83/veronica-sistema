import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

AREA_TRABALHO = Path(os.environ["USERPROFILE"]) / "Desktop"
PROJETO_DIR   = AREA_TRABALHO / "veronica"

# Destinos de backup
HD_G = Path("G:/Backup_Veronica")   # arena x
HD_E = Path("E:/Backup_Veronica")   # Roberta

IGNORAR = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".git", "*.db-journal",
    "node_modules", ".env", "*.log"
)

def _copiar(origem: Path, destino: Path, nome: str):
    try:
        destino.mkdir(parents=True, exist_ok=True)
        destino_final = destino / nome
        if destino_final.exists():
            shutil.rmtree(destino_final)
        shutil.copytree(origem, destino_final, ignore=IGNORAR)
        print(f"  OK -> {destino_final}")
        return True
    except Exception as e:
        print(f"  ERRO -> {destino}: {e}")
        return False

def backup_completo():
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"veronica_{ts}"
    print(f"\n[BACKUP] {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"  Origem : {PROJETO_DIR}")
    print(f"  Pasta  : {nome}\n")
    ok_g = _copiar(PROJETO_DIR, HD_G, nome)
    ok_e = _copiar(PROJETO_DIR, HD_E, nome)
    return ok_g, ok_e

def listar_backups():
    for hd, label in [(HD_G, "G: arena x"), (HD_E, "E: Roberta")]:
        print(f"\nBackups em {label} ({hd}):")
        if hd.exists():
            pastas = sorted(hd.iterdir(), reverse=True)
            for p in pastas[:10]:
                if p.is_dir():
                    tam = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                    print(f"  {p.name}  ({tam//1024//1024} MB)")
        else:
            print("  HD nao encontrado")

if __name__ == "__main__":
    opcao = sys.argv[1] if len(sys.argv) > 1 else ""
    if opcao == "backup":
        ok_g, ok_e = backup_completo()
        print("\nResultado:")
        print(f"  HD G: (arena x)  -> {'OK' if ok_g else 'FALHOU'}")
        print(f"  HD E: (Roberta)  -> {'OK' if ok_e else 'FALHOU'}")
    elif opcao == "listar":
        listar_backups()
    else:
        ok_g, ok_e = backup_completo()
        print("\nResultado:")
        print(f"  HD G: (arena x)  -> {'OK' if ok_g else 'FALHOU'}")
        print(f"  HD E: (Roberta)  -> {'OK' if ok_e else 'FALHOU'}")
