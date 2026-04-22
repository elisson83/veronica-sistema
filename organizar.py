import sys
if len(sys.argv) > 1:
    opcao = sys.argv[1]
    if opcao == "1":
        criar_estrutura()
    elif opcao == "2":
        criar_estrutura()
        copiar_projeto("PainelGest", "painelgest")
        print("✅ PainelGest organizado!")
    elif opcao == "3":
        backup_veronica()
    elif opcao == "4":
        listar_projetos()