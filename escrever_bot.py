with open("modules/telegram_bot.py", "r", encoding="utf-8") as f:
    codigo = f.read()

# Adiciona import do twitter
codigo = codigo.replace(
    "from modules.marketing import criar_post_otimizado",
    "from modules.twitter_bot import postar_tweet, get_meu_perfil, get_meus_tweets, testar_conexao\nfrom modules.marketing import criar_post_otimizado"
)

# Adiciona comandos do twitter
novo_cmd = '''
async def twitter_status_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text("Verificando conexao com Twitter...")
    loop = asyncio.get_event_loop()
    resultado = await loop.run_in_executor(None, testar_conexao)
    await update.message.reply_text(resultado)

async def twitter_perfil_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    loop = asyncio.get_event_loop()
    resultado = await loop.run_in_executor(None, get_meu_perfil)
    await update.message.reply_text(resultado)

async def twitter_tweets_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    loop = asyncio.get_event_loop()
    resultado = await loop.run_in_executor(None, lambda: get_meus_tweets(5))
    await update.message.reply_text(resultado)

async def twitter_postar_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text(
            "Use: /tweetar Seu texto aqui\\n\\n"
            "Maximo 280 caracteres!"
        )
        return
    texto = " ".join(context.args)
    await update.message.reply_text(f"Postando tweet...")
    loop = asyncio.get_event_loop()
    resultado = await loop.run_in_executor(None, lambda: postar_tweet(texto))
    await update.message.reply_text(resultado)

async def twitter_mkpost_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text(
            "Cria post com IA e posta no Twitter!\\n\\n"
            "Use: /mktweet Marketing Digital com IA"
        )
        return
    tema = " ".join(context.args)
    await update.message.reply_text(f"Criando tweet sobre {tema}...")
    loop = asyncio.get_event_loop()
    post = await loop.run_in_executor(None, lambda: criar_post_otimizado(tema, "twitter"))
    await update.message.reply_text(f"Tweet criado:\\n\\n{post[:280]}\\n\\nPostando...")
    resultado = await loop.run_in_executor(None, lambda: postar_tweet(post[:280]))
    await update.message.reply_text(resultado)

'''

codigo = codigo.replace("def iniciar_bot():", novo_cmd + "def iniciar_bot():")

# Adiciona handlers
codigo = codigo.replace(
    'app.add_handler(CommandHandler("licenca", licenca_cmd))',
    'app.add_handler(CommandHandler("licenca", licenca_cmd))\n    app.add_handler(CommandHandler("twitterstatus", twitter_status_cmd))\n    app.add_handler(CommandHandler("twitterperfil", twitter_perfil_cmd))\n    app.add_handler(CommandHandler("meustveets", twitter_tweets_cmd))\n    app.add_handler(CommandHandler("tweetar", twitter_postar_cmd))\n    app.add_handler(CommandHandler("mktweet", twitter_mkpost_cmd))'
)

with open("modules/telegram_bot.py", "w", encoding="utf-8") as f:
    f.write(codigo)
print("Comandos Twitter adicionados!")