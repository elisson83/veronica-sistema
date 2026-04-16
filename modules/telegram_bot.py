import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN
from modules.ai_brain import perguntar_ia, gerar_plano_de_estudo, estudar_tema, corrigir_resposta
from modules.memory import get_usuario, atualizar_nivel, atualizar_nome, carregar_usuarios, salvar_usuarios
from modules.pesquisa import pesquisar_web, pesquisar_noticias
from modules.conhecimento import listar_conhecimentos
from modules.evolucao import get_estatisticas
from modules.financeiro import get_cotacao, get_indicadores, get_mercado_geral

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Dicionário para controlar quem está aguardando digitar o nome
aguardando_nome = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    usuario = get_usuario(user_id)
    nome_salvo = usuario.get("nome", "")

    if nome_salvo and nome_salvo != "":
        await update.message.reply_text(
            f"👋 Olá, *{nome_salvo}*! Bem-vindo de volta!\n\n"
            "Serei sua assistente pessoal. Como posso te ajudar hoje? 😊",
            parse_mode='Markdown'
        )
        return

    aguardando_nome[user_id] = True
    await update.message.reply_text(
        "👋 Olá! Eu sou a *Verônica*!\n\n"
        "Qual é o seu nome? 😊",
        parse_mode='Markdown'
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Comandos da Verônica:*\n\n"
        "📚 *Estudo e Pesquisa:*\n"
        "/plano - Criar plano de estudo\n"
        "/estudar - Estudar um tema\n"
        "/conhecimentos - Ver temas estudados\n"
        "/pesquisar - Pesquisar na internet\n"
        "/noticias - Ver notícias\n\n"
        "💻 *Programação:*\n"
        "/codigo - Me pedir para programar algo\n\n"
        "📈 *Financeiro:*\n"
        "/mercado - Ver mercado geral\n"
        "/cotacao - Ver cotação de um ativo\n"
        "/indicadores - Ver indicadores técnicos\n\n"
        "🧠 *Evolução:*\n"
        "/corrigir - Me corrigir quando errar\n"
        "/evolucao - Ver estatísticas\n\n"
        "⚙️ *Configurações:*\n"
        "/nivel - Mudar nível\n"
        "/perfil - Ver perfil\n"
        "/limpar - Limpar histórico\n"
        "/ajuda - Ver esta mensagem\n\n"
        "Ou simplesmente me faça qualquer pergunta! 😊",
        parse_mode='Markdown'
    )

async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    usuario = get_usuario(user_id)
    total_mensagens = len(usuario.get("historico", []))

    await update.message.reply_text(
        f"👤 *Seu Perfil:*\n\n"
        f"• Nome: {usuario.get('nome', 'Não definido')}\n"
        f"• Nível: {usuario.get('nivel', 'iniciante')}\n"
        f"• Mensagens trocadas: {total_mensagens}\n"
        f"• Membro desde: {usuario.get('criado_em', '?')[:10]}\n",
        parse_mode='Markdown'
    )

async def nivel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "📊 *Escolha seu nível:*\n\n"
            "/nivel iniciante\n"
            "/nivel intermediario\n"
            "/nivel avancado",
            parse_mode='Markdown'
        )
        return

    novo_nivel = context.args[0].lower()
    if novo_nivel not in ["iniciante", "intermediario", "avancado"]:
        await update.message.reply_text("❌ Nível inválido! Use: iniciante, intermediario ou avancado")
        return

    user_id = str(update.message.from_user.id)
    atualizar_nivel(user_id, novo_nivel)
    await update.message.reply_text(f"✅ Nível atualizado para *{novo_nivel}*!", parse_mode='Markdown')

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    usuarios = carregar_usuarios()
    if user_id in usuarios:
        usuarios[user_id]["historico"] = []
        usuarios[user_id]["nome"] = ""
        salvar_usuarios(usuarios)
    aguardando_nome.pop(user_id, None)
    await update.message.reply_text(
        "🧹 Histórico e nome limpos com sucesso!\n\n"
        "Digite /start para se apresentar novamente! 😊"
    )

async def plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    usuario = get_usuario(user_id)

    if not context.args:
        await update.message.reply_text(
            "📚 Para criar um plano de estudo, escreva assim:\n"
            "/plano Python\n"
            "/plano Matemática\n"
            "/plano Inglês"
        )
        return

    tema = ' '.join(context.args)
    nivel_usuario = usuario.get("nivel", "iniciante")

    await update.message.reply_text(
        f"⏳ Gerando seu plano de estudo sobre *{tema}* "
        f"para nível *{nivel_usuario}*...",
        parse_mode='Markdown'
    )
    resposta = gerar_plano_de_estudo(tema, nivel_usuario, user_id)
    await update.message.reply_text(resposta)

async def estudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if not context.args:
        await update.message.reply_text(
            "📖 Para me pedir para estudar um tema, escreva assim:\n"
            "/estudar Mercado Financeiro\n"
            "/estudar Bitcoin\n"
            "/estudar Indicadores Técnicos"
        )
        return

    tema = ' '.join(context.args)
    await update.message.reply_text(
        f"📚 Estou pesquisando e estudando sobre *{tema}*...\n"
        f"Aguarde um momento! 🔍",
        parse_mode='Markdown'
    )
    resposta = estudar_tema(tema, user_id)
    await update.message.reply_text(resposta)

async def conhecimentos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = listar_conhecimentos()
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def evolucao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = get_estatisticas()
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def corrigir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if not context.args:
        await update.message.reply_text(
            "✏️ Para me corrigir, escreva assim:\n"
            "/corrigir A resposta certa é...\n\n"
            "Exemplo:\n"
            "/corrigir Bitcoin foi criado em 2009, não 2010"
        )
        return

    correcao = ' '.join(context.args)
    historico = get_usuario(user_id).get("historico", [])

    ultima_pergunta = ""
    ultima_resp = ""
    for msg in reversed(historico):
        if msg["role"] == "assistant" and not ultima_resp:
            ultima_resp = msg["content"]
        if msg["role"] == "user" and not ultima_pergunta:
            ultima_pergunta = msg["content"]
        if ultima_pergunta and ultima_resp:
            break

    await update.message.reply_text("✏️ Obrigada pela correção! Aprendendo...")
    resposta = corrigir_resposta(ultima_pergunta, ultima_resp, correcao, user_id)
    await update.message.reply_text(resposta)

async def mercado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Buscando dados do mercado...")
    resposta = get_mercado_geral()
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def cotacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "💰 Para ver cotação, escreva assim:\n"
            "/cotacao PETR4.SA\n"
            "/cotacao BTC-USD\n"
            "/cotacao VALE3.SA"
        )
        return

    ticker = context.args[0].upper()
    await update.message.reply_text(f"💰 Buscando cotação de *{ticker}*...", parse_mode='Markdown')
    resposta = get_cotacao(ticker)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def indicadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "📊 Para ver indicadores técnicos, escreva assim:\n"
            "/indicadores PETR4.SA\n"
            "/indicadores BTC-USD\n"
            "/indicadores VALE3.SA"
        )
        return

    ticker = context.args[0].upper()
    await update.message.reply_text(f"📊 Calculando indicadores de *{ticker}*...", parse_mode='Markdown')
    resposta = get_indicadores(ticker)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def codigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if not context.args:
        await update.message.reply_text(
            "💻 Para me pedir para programar algo, escreva assim:\n"
            "/codigo Crie uma função em Python que calcula IMC\n"
            "/codigo Faça um script que lê um arquivo CSV\n"
            "/codigo Como criar uma API com Flask"
        )
        return

    pedido = ' '.join(context.args)
    await update.message.reply_text(
        f"💻 Programando: *{pedido[:50]}*...",
        parse_mode='Markdown'
    )

    prompt = f"""
    O usuário precisa de ajuda com programação:
    {pedido}
    
    Por favor:
    1. Explique o que vai fazer
    2. Forneça o código completo e funcional
    3. Explique cada parte importante do código
    4. Dê dicas de como usar e melhorar
    """
    resposta = perguntar_ia(prompt, user_id)
    await update.message.reply_text(resposta)

async def pesquisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔍 Para pesquisar na internet, escreva assim:\n"
            "/pesquisar Bitcoin hoje\n"
            "/pesquisar Ibovespa\n"
            "/pesquisar Python tutorial"
        )
        return

    query = ' '.join(context.args)
    await update.message.reply_text(f"🔍 Pesquisando: *{query}*...", parse_mode='Markdown')
    resposta = pesquisar_web(query)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "📰 Para ver notícias, escreva assim:\n"
            "/noticias Mercado Financeiro\n"
            "/noticias Bitcoin\n"
            "/noticias Economia Brasil"
        )
        return

    query = ' '.join(context.args)
    await update.message.reply_text(f"📰 Buscando notícias sobre: *{query}*...", parse_mode='Markdown')
    resposta = pesquisar_noticias(query)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def responder_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    texto = update.message.text

    # Verifica se está aguardando nome
    if user_id in aguardando_nome and aguardando_nome[user_id]:
        nome = texto.strip()
        atualizar_nome(user_id, nome)
        aguardando_nome.pop(user_id, None)
        await update.message.reply_text(
            f"Olá, *{nome}*! 🎉\n\n"
            "Serei sua assistente pessoal. Estou aqui para te ajudar a aprender, programar e investir!\n\n"
            "💡 Digite /ajuda para ver todos os comandos!\n\n"
            "O que deseja fazer hoje? 😊",
            parse_mode='Markdown'
        )
        return

    # Responde normalmente
    await update.message.reply_text("🤔 Pensando...")
    resposta = perguntar_ia(texto, user_id)
    await update.message.reply_text(resposta)

def iniciar_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("plano", plano))
    app.add_handler(CommandHandler("estudar", estudar))
    app.add_handler(CommandHandler("conhecimentos", conhecimentos))
    app.add_handler(CommandHandler("evolucao", evolucao))
    app.add_handler(CommandHandler("corrigir", corrigir))
    app.add_handler(CommandHandler("mercado", mercado))
    app.add_handler(CommandHandler("cotacao", cotacao))
    app.add_handler(CommandHandler("indicadores", indicadores))
    app.add_handler(CommandHandler("codigo", codigo))
    app.add_handler(CommandHandler("pesquisar", pesquisar))
    app.add_handler(CommandHandler("noticias", noticias))
    app.add_handler(CommandHandler("nivel", nivel))
    app.add_handler(CommandHandler("perfil", perfil))
    app.add_handler(CommandHandler("limpar", limpar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensagem))

    print("🤖 Verônica está online!")
    app.run_polling()