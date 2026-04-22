import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

AREA_TRABALHO = Path(os.environ["USERPROFILE"]) / "Desktop"
HD_BACKUP = Path("E:/backup_veronica")
PENDRIVE_BACKUP = Path("D:/backup_veronica")
PROJETOS_DIR = AREA_TRABALHO / "projetos_veronica"

def criar_estrutura():
    pastas = [
        PROJETOS_DIR,
        PROJETOS_DIR / "PainelGest",
        PROJETOS_DIR / "PainelPedidos",
        PROJETOS_DIR / "Site",
        PROJETOS_DIR / "Outros",
        HD_BACKUP,
        HD_BACKUP / "projetos",
        HD_BACKUP / "veronica_ia",
    ]
    for pasta in pastas:
        pasta.mkdir(parents=True, exist_ok=True)
    print("Estrutura de pastas criada!")

def copiar_projeto(nome_projeto, pasta_origem):
    origem = Path(pasta_origem)
    if not origem.exists():
        print(f"Pasta {pasta_origem} nao encontrada!")
        return
    destino_desktop = PROJETOS_DIR / nome_projeto
    if destino_desktop.exists():
        shutil.rmtree(destino_desktop)
    shutil.copytree(origem, destino_desktop)
    print(f"{nome_projeto} copiado para area de trabalho!")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino_hd = HD_BACKUP / "projetos" / f"{nome_projeto}_{timestamp}"
    try:
        shutil.copytree(origem, destino_hd)
        print(f"Backup no HD (E:) feito!")
    except Exception as e:
        print(f"Erro backup HD: {e}")
    destino_pendrive = PENDRIVE_BACKUP / "projetos" / nome_projeto
    try:
        PENDRIVE_BACKUP.mkdir(parents=True, exist_ok=True)
        (PENDRIVE_BACKUP / "projetos").mkdir(exist_ok=True)
        if destino_pendrive.exists():
            shutil.rmtree(destino_pendrive)
        shutil.copytree(origem, destino_pendrive)
        print(f"Backup no Pen Drive (D:) feito!")
    except Exception as e:
        print(f"Erro backup Pen Drive: {e}")

def backup_veronica():
    origem = AREA_TRABALHO / "veronica"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino_hd = HD_BACKUP / "veronica_ia" / f"veronica_{timestamp}"
    try:
        shutil.copytree(origem, destino_hd,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "*.db"))
        print(f"Backup Veronica no HD feito!")
    except Exception as e:
        print(f"Erro backup HD: {e}")
    destino_pendrive = PENDRIVE_BACKUP / "veronica_ia" / f"veronica_{timestamp}"
    try:
        PENDRIVE_BACKUP.mkdir(parents=True, exist_ok=True)
        (PENDRIVE_BACKUP / "veronica_ia").mkdir(exist_ok=True)
        shutil.copytree(origem, destino_pendrive,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "*.db"))
        print(f"Backup Veronica no Pen Drive feito!")
    except Exception as e:
        print(f"Erro backup Pen Drive: {e}")

def listar_projetos():
    print("\nProjetos na area de trabalho:")
    if PROJETOS_DIR.exists():
        for pasta in PROJETOS_DIR.iterdir():
            if pasta.is_dir():
                print(f"  {pasta.name}")
    print("\nBackups no HD (E:):")
    if (HD_BACKUP / "projetos").exists():
        for pasta in (HD_BACKUP / "projetos").iterdir():
            if pasta.is_dir():
                print(f"  {pasta.name}")
    print("\nBackups no Pen Drive (D:):")
    if (PENDRIVE_BACKUP / "projetos").exists():
        for pasta in (PENDRIVE_BACKUP / "projetos").iterdir():
            if pasta.is_dir():
                print(f"  {pasta.name}")

if len(sys.argv) > 1:
    opcao = sys.argv[1]
else:
    print("\nSistema de Organizacao Veronica\n")
    print("1 - Criar estrutura de pastas")
    print("2 - Copiar PainelGest para projetos")
    print("3 - Backup completo da Veronica")
    print("4 - Listar projetos")
    opcao = input("\nEscolha: ")

if opcao == "1":
    criar_estrutura()
elif opcao == "2":
    criar_estrutura()
    copiar_projeto("PainelGest", "painelgest")
    print("\nPainelGest organizado!")
elif opcao == "3":
    backup_veronica()
elif opcao == "4":
    listar_projetos()
else:
    print("Opcao invalida!")