with open("modules/telegram_bot.py", "r", encoding="utf-8") as f:
    linhas = f.readlines()

# Encontra inicio e fim da funcao responder_foto
inicio = None
fim = None
for i, linha in enumerate(linhas):
    if "async def responder_foto" in linha:
        inicio = i
    if inicio and i > inicio and "async def " in linha and "responder_foto" not in linha:
        fim = i
        break

print(f"Funcao encontrada: linhas {inicio} ate {fim}")
print("Conteudo atual:")
for i in range(inicio, min(inicio+20, len(linhas))):
    print(f"{i}: {linhas[i]}", end="")

# Substitui a funcao
nova_funcao = '''async def responder_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    if not is_autorizado(int_id) and not usuario_liberado(user_id):
        return
    if not update.message.photo:
        return
    legenda = update.message.caption or ""
    legenda_lower = legenda.lower().strip()
    estilos_validos = ["anime", "cartoon", "pixar", "sketch", "watercolor"]
    palavras_transformar = ["anime", "cartoon", "pixar", "sketch", "watercolor", "desenho", "transforma", "converte", "estilo"]
    if any(p in legenda_lower for p in palavras_transformar):
        estilo = "anime"
        for e in estilos_validos:
            if e in legenda_lower:
                estilo = e
                break
        if "desenho" in legenda_lower or "cartoon" in legenda_lower:
            estilo = "cartoon"
        await update.message.reply_text(f"Transformando foto em {estilo}... aguarde!")
        foto = update.message.photo[-1]
        arquivo = await foto.get_file()
        from pathlib import Path
        caminho = str(Path("assets") / f"original_{foto.file_id}.jpg")
        Path("assets").mkdir(exist_ok=True)
        await arquivo.download_to_drive(caminho)
        loop = asyncio.get_event_loop()
        caminho_result, ia_usada = await loop.run_in_executor(None, lambda: transformar_foto_anime(caminho, estilo))
        if str(caminho_result).startswith("ERRO"):
            await update.message.reply_text(caminho_result)
        else:
            await update.message.reply_photo(photo=open(caminho_result, "rb"), caption=f"Foto transformada em {estilo}!")
        return
    await update.message.reply_text("Analisando imagem...")
    foto = update.message.photo[-1]
    arquivo = await foto.get_file()
    from pathlib import Path
    caminho = str(Path("assets") / f"img_{foto.file_id}.jpg")
    Path("assets").mkdir(exist_ok=True)
    await arquivo.download_to_drive(caminho)
    pergunta = legenda or "O que voce ve nessa imagem? Descreva em detalhes em portugues."
    loop = asyncio.get_event_loop()
    descricao = await loop.run_in_executor(None, lambda: analisar_imagem_enviada(caminho, pergunta))
    await update.message.reply_text(f"Analise:\\n\\n{descricao}")

'''

novas_linhas = linhas[:inicio] + [nova_funcao] + linhas[fim:]

with open("modules/telegram_bot.py", "w", encoding="utf-8") as f:
    f.writelines(novas_linhas)

print("\\nFuncao substituida com sucesso!")