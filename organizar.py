import os
import shutil
from pathlib import Path
from datetime import datetime

# Configuracoes
AREA_TRABALHO = Path(os.environ["USERPROFILE"]) / "Desktop"
HD_BACKUP = Path("E:/backup_veronica")
PENDRIVE_BACKUP = Path("D:/backup_veronica")
PROJETOS_DIR = AREA_TRABALHO / "projetos_veronica"

def criar_estrutura():
    """Cria estrutura de pastas organizada"""
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
    print("✅ Estrutura de pastas criada!")

def copiar_projeto(nome_projeto: str, pasta_origem: str):
    """Copia projeto para pasta organizada e faz backup"""
    origem = Path(pasta_origem)
    if not origem.exists():
        print(f"❌ Pasta {pasta_origem} nao encontrada!")
        return

    # Copia para projetos_veronica na area de trabalho
    destino_desktop = PROJETOS_DIR / nome_projeto
    if destino_desktop.exists():
        shutil.rmtree(destino_desktop)
    shutil.copytree(origem, destino_desktop)
    print(f"✅ {nome_projeto} copiado para area de trabalho!")

    # Backup no HD
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino_hd = HD_BACKUP / "projetos" / f"{nome_projeto}_{timestamp}"
    try:
        shutil.copytree(origem, destino_hd)
        print(f"✅ Backup no HD (E:) feito!")
    except Exception as e:
        print(f"❌ Erro backup HD: {e}")

    # Backup no Pen Drive
    destino_pendrive = PENDRIVE_BACKUP / "projetos" / nome_projeto
    try:
        PENDRIVE_BACKUP.mkdir(parents=True, exist_ok=True)
        (PENDRIVE_BACKUP / "projetos").mkdir(exist_ok=True)
        if destino_pendrive.exists():
            shutil.rmtree(destino_pendrive)
        shutil.copytree(origem, destino_pendrive)
        print(f"✅ Backup no Pen Drive (D:) feito!")
    except Exception as e:
        print(f"❌ Erro backup Pen Drive: {e}")

def backup_veronica():
    """Faz backup completo da Verônica"""
    origem = AREA_TRABALHO / "veronica"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Backup HD
    destino_hd = HD_BACKUP / "veronica_ia" / f"veronica_{timestamp}"
    try:
        shutil.copytree(origem, destino_hd, 
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".git", 
                "assets/geradas/*", "*.db"
            )
        )
        print(f"✅ Backup Verônica no HD feito!")
    except Exception as e:
        print(f"❌ Erro backup HD: {e}")

    # Backup Pen Drive
    destino_pendrive = PENDRIVE_BACKUP / "veronica_ia" / f"veronica_{timestamp}"
    try:
        PENDRIVE_BACKUP.mkdir(parents=True, exist_ok=True)
        (PENDRIVE_BACKUP / "veronica_ia").mkdir(exist_ok=True)
        shutil.copytree(origem, destino_pendrive,
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".git",
                "assets/geradas/*", "*.db"
            )
        )
        print(f"✅ Backup Verônica no Pen Drive feito!")
    except Exception as e:
        print(f"❌ Erro backup Pen Drive: {e}")

def listar_projetos():
    """Lista todos os projetos organizados"""
    print("\n📁 Projetos na área de trabalho:")
    if PROJETOS_DIR.exists():
        for pasta in PROJETOS_DIR.iterdir():
            if pasta.is_dir():
                print(f"  📂 {pasta.name}")
    else:
        print("  Nenhum projeto ainda!")

    print("\n💾 Backups no HD (E:):")
    if HD_BACKUP.exists():
        for pasta in HD_BACKUP.iterdir():
            if pasta.is_dir():
                print(f"  📂 {pasta.name}")
    else:
        print("  HD não encontrado!")

    print("\n🔌 Backups no Pen Drive (D:):")
    if PENDRIVE_BACKUP.exists():
        for pasta in PENDRIVE_BACKUP.iterdir():
            if pasta.is_dir():
                print(f"  📂 {pasta.name}")
    else:
        print("  Pen Drive não encontrado!")

if __name__ == "__main__":
    print("🗂️ Sistema de Organização Verônica\n")
    print("1 - Criar estrutura de pastas")
    print("2 - Copiar PainelGest para projetos")
    print("3 - Backup completo da Verônica")
    print("4 - Listar projetos")
    opcao = input("\nEscolha: ")

    if opcao == "1":
        criar_estrutura()
    elif opcao == "2":
        criar_estrutura()
        copiar_projeto("PainelGest", "painelgest")
        print("\n✅ PainelGest organizado!")
    elif opcao == "3":
        backup_veronica()
    elif opcao == "4":
        listar_projetos()
    else:
        print("Opcao invalida!")