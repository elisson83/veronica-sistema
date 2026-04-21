with open("modules/telegram_bot.py", "r", encoding="utf-8") as f:
    codigo = f.read()

# Adiciona imports
codigo = codigo.replace(
    "from modules.twitter_bot import postar_tweet, get_meu_perfil, get_meus_tweets, testar_conexao",
    "from modules.twitter_bot import postar_tweet, get_meu_perfil, get_meus_tweets, testar_conexao\nfrom modules.gerenciador_chaves import get_status_chaves, salvar_chave, get_chave_pendente, remover_chave_pendente, salvar_chave_pendente, get_info_chave, CHAVES_CONHECIDAS\nfrom modules.auto_update import get_status_sistema, verificar_atualizacao, aplicar_atualizacao, reiniciar_veronica, instalar_dependencias"
)

# Adiciona novos comandos
novo_cmd = '''
async def chaves_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(get_status_chaves())

async def adicionarchave_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        chaves_disponiveis = "\\n".join([f"• {k}" for k in CHAVES_CONHECIDAS.keys()])
        await update.message.reply_text(
            f"Use: /adicionarchave NOME_DA_CHAVE\\n\\n"
            f"Chaves disponiveis:\\n{chaves_disponiveis}"
        )
        return
    nome_chave = context.args[0].upper()
    if nome_chave not in CHAVES_CONHECIDAS:
        await update.message.reply_text(f"Chave {nome_chave} nao reconhecida!")
        return
    user_id = str(update.message.from_user.id)
    salvar_chave_pendente(nome_chave, user_id)
    info = get_info_chave(nome_chave)
    await update.message.reply_text(
        f"Digite agora o valor da chave {info.get('nome', nome_chave)}:\\n\\n"
        f"Onde obter: {info.get('onde_obter', '')}\\n\\n"
        f"(Digite apenas a chave, sem mais nada)"
    )

async def atualizar_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text("Verificando atualizacoes...")
    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, get_status_sistema)
    await update.message.reply_text(status)

async def aplicaratualizar_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "aplicar_atualizacao"
    await update.message.reply_text(
        "Aplicar atualizacao do GitHub?\\n\\n"
        "Isso vai baixar as ultimas mudancas e reiniciar a Veronica.\\n\\n"
        "Digite SIM ou NAO"
    )

async def reiniciar_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "reiniciar_veronica"
    await update.message.reply_text("Reiniciar a Veronica? Digite SIM ou NAO")

'''

codigo = codigo.replace("def iniciar_bot():", novo_cmd + "def iniciar_bot():")

# Adiciona handlers
codigo = codigo.replace(
    'app.add_handler(CommandHandler("licenca", licenca_cmd))',
    'app.add_handler(CommandHandler("licenca", licenca_cmd))\n    app.add_handler(CommandHandler("chaves", chaves_cmd))\n    app.add_handler(CommandHandler("adicionarchave", adicionarchave_cmd))\n    app.add_handler(CommandHandler("atualizar", atualizar_cmd))\n    app.add_handler(CommandHandler("aplicaratualizar", aplicaratualizar_cmd))\n    app.add_handler(CommandHandler("reiniciar", reiniciar_cmd))'
)

# Adiciona tratamento de chaves pendentes e confirmacoes no responder_mensagem
codigo = codigo.replace(
    "    if user_id in aguardando_nova_senha and aguardando_nova_senha[user_id]:",
    '''    # Verifica se esta aguardando uma chave API
    chave_pendente = get_chave_pendente(user_id)
    if chave_pendente:
        valor = texto.strip()
        if salvar_chave(chave_pendente, valor):
            remover_chave_pendente(user_id)
            await update.message.reply_text(f"Chave {chave_pendente} salva com sucesso!")
        else:
            await update.message.reply_text("Erro ao salvar chave. Tente novamente.")
        return

    if user_id in aguardando_nova_senha and aguardando_nova_senha[user_id]:'''
)

# Adiciona confirmacoes de atualizacao
codigo = codigo.replace(
    '            elif acao == "apagar_memoria":\n                resposta = apagar_memorias()',
    '            elif acao == "apagar_memoria":\n                resposta = apagar_memorias()\n            elif acao == "aplicar_atualizacao":\n                await update.message.reply_text("Aplicando atualizacao...")\n                loop = asyncio.get_event_loop()\n                res1 = await loop.run_in_executor(None, aplicar_atualizacao)\n                await update.message.reply_text(res1)\n                res2 = await loop.run_in_executor(None, instalar_dependencias)\n                await update.message.reply_text(res2)\n                resposta = "Reinicie manualmente com /reiniciar"\n            elif acao == "reiniciar_veronica":\n                await update.message.reply_text("Reiniciando Veronica...")\n                reiniciar_veronica()\n                resposta = "Reiniciando..."'
)

with open("modules/telegram_bot.py", "w", encoding="utf-8") as f:
    f.write(codigo)
print("Sessao 14 adicionada com sucesso!")