with open("modules/telegram_bot.py", "r", encoding="utf-8") as f:
    content = f.read()

# Encontra a linha do gerenciador_chaves
idx = content.find("from modules.gerenciador_chaves import")
fim = content.find("\n", idx)
linha_atual = content[idx:fim]
print("Linha atual:", linha_atual)

# Substitui pela linha correta com listar_todas_chaves
nova_linha = "from modules.gerenciador_chaves import get_status_chaves, salvar_chave, get_chave_pendente, remover_chave_pendente, salvar_chave_pendente, get_info_chave, adicionar_chave_livre, listar_todas_chaves, CHAVES_CONHECIDAS"

content = content[:idx] + nova_linha + content[fim:]

with open("modules/telegram_bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Corrigido!")