with open("modules/telegram_bot.py", "r", encoding="utf-8") as f:
    codigo = f.read()

# Adiciona import listar_todas_chaves
codigo = codigo.replace(
    "from modules.gerenciador_chaves import get_status_chaves, salvar_chave, get_chave_pendente, remover_chave_pendente, salvar_chave_pendente, get_info_chave, adicionar_chave_livre, listar_todas_chaves, CHAVES_CONHECIDAS",
    "from modules.gerenciador_chaves import get_status_chaves, salvar_chave, get_chave_pendente, remover_chave_pendente, salvar_chave_pendente, get_info_chave, adicionar_chave_livre, listar_todas_chaves, CHAVES_CONHECIDAS"
)

# Adiciona funcao e handler diretamente antes de iniciar_bot
nova_funcao = '''
async def todas_chaves_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(listar_todas_chaves())

'''

codigo = codigo.replace("def iniciar_bot():", nova_funcao + "def iniciar_bot():")

# Adiciona handler
codigo = codigo.replace(
    'app.add_handler(CommandHandler("chaves", chaves_cmd))',
    'app.add_handler(CommandHandler("chaves", chaves_cmd))\n    app.add_handler(CommandHandler("todaschaves", todas_chaves_cmd))'
)

with open("modules/telegram_bot.py", "w", encoding="utf-8") as f:
    f.write(codigo)
print("Adicionado!")

# Verifica
with open("modules/telegram_bot.py", "r", encoding="utf-8") as f:
    content = f.read()
print("todaschaves handler:", "todaschaves" in content)
print("todas_chaves_cmd:", "todas_chaves_cmd" in content)