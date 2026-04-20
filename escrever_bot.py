codigo = open("modules/telegram_bot.py", "r", encoding="utf-8").read()

# Atualiza o comando gerarimg para usar a função inteligente
codigo = codigo.replace(
    "from modules.visao_geradora import gerar_imagem, gerar_logo, gerar_banner_post, gerar_capa_ebook",
    "from modules.visao_geradora import gerar_imagem, gerar_logo, gerar_banner_post, gerar_capa_ebook, gerar_imagem_inteligente"
)

codigo = codigo.replace(
    '''async def gerarimg_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /gerarimg um gato astronauta no espaco")
        return
    descricao = " ".join(context.args)
    await update.message.reply_text(f"Gerando imagem: {descricao[:50]}... aguarde!")
    loop = asyncio.get_event_loop()
    caminho, prompt = await loop.run_in_executor(None, lambda: gerar_imagem(descricao))
    if caminho.startswith("X") or caminho.startswith("E"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, "rb"), caption=f"Imagem gerada: {descricao[:100]}")''',
    '''async def gerarimg_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /gerarimg descricao da imagem que voce quer")
        return
    descricao = " ".join(context.args)
    await update.message.reply_text(f"Gerando imagem... aguarde alguns segundos!")
    loop = asyncio.get_event_loop()
    caminho, ia_usada = await loop.run_in_executor(None, lambda: gerar_imagem_inteligente(descricao))
    if caminho.startswith("X") or caminho.startswith("E") or caminho.startswith("?"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, "rb"), caption=f"Imagem gerada com {ia_usada}!")'''
)

with open("modules/telegram_bot.py", "w", encoding="utf-8") as f:
    f.write(codigo)
print("Atualizado com sucesso!")