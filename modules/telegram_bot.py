import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, is_autorizado
from modules.ai_brain import perguntar_ia, gerar_plano_de_estudo, estudar_tema, corrigir_resposta
from modules.memory import get_usuario, atualizar_nivel, atualizar_nome, carregar_usuarios, salvar_usuarios
from modules.pesquisa import pesquisar_web, pesquisar_noticias
from modules.conhecimento import listar_conhecimentos
from modules.evolucao import get_estatisticas
from modules.financeiro import get_cotacao, get_indicadores, get_mercado_geral
from modules.seguranca import get_senha, trocar_senha, liberar_usuario, usuario_liberado, listar_usuarios_liberados
from modules.controle_pc import get_info_pc, listar_processos, abrir_programa, fechar_programa, desligar_pc, cancelar_desligamento, reiniciar_pc, tirar_screenshot, executar_comando

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

aguardando_nome = {}
aguardando_senha = {}
aguardando_nova_senha = {}
aguardando_confirmacao = {}

async def verificar_acesso(update: Update) -> bool:
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    if is_autorizado(int_id):
        return True
    if usuario_liberado(user_id):
        return True
    aguardando_senha[user_id] = True
    await update.message.reply_text(
        "🔒 *Acesso Restrito!*\n\n"
        "Este bot é privado. Digite a senha para continuar:",
        parse_mode='Markdown'
    )
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    if is_autorizado(int_id) or usuario_liberado(user_id):
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
        return
    aguardando_senha[user_id] = True
    await update.message.reply_text(
        "🔒 *Acesso Restrito!*\n\n"
        "Este bot é privado. Digite a senha para continuar:",
        parse_mode='Markdown'
    )

async def trocar_senha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    if not is_autorizado(int_id):
        await update.message.reply_text("⛔ Apenas o administrador pode trocar a senha!")
        return
    if not context.args:
        aguardando_nova_senha[user_id] = True
        await update.message.reply_text("🔑 *Trocar Senha*\n\nDigite a nova senha:", parse_mode='Markdown')
        return
    nova_senha = ' '.join(context.args)
    trocar_senha(nova_senha)
    await update.message.reply_text(f"✅ Senha alterada!\n\nNova senha: `{nova_senha}`", parse_mode='Markdown')

async def ver_senha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    int_id = update.message.from_user.id
    if not is_autorizado(int_id):
        await update.message.reply_text("⛔ Apenas o administrador pode ver a senha!")
        return
    senha = get_senha()
    usuarios = listar_usuarios_liberados()
    await update.message.reply_text(
        f"🔑 *Configurações de Acesso:*\n\n"
        f"• Senha atual: `{senha}`\n"
        f"• Usuários liberados: {len(usuarios)}\n",
        parse_mode='Markdown'
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    int_id = update.message.from_user.id
    admin_cmds = ""
    if is_autorizado(int_id):
        admin_cmds = (
            "\n👑 *Admin:*\n"
            "/trocarsenha - Trocar senha\n"
            "/versenha - Ver senha atual\n\n"
            "💻 *Controle do PC:*\n"
            "/infopc - Ver informações do PC\n"
            "/processos - Ver processos em execução\n"
            "/abrirprograma - Abrir um programa\n"
            "/fecharprograma - Fechar um programa\n"
            "/screenshot - Tirar screenshot\n"
            "/desligarpc - Desligar o PC\n"
            "/reiniciarpc - Reiniciar o PC\n"
            "/cancelardesligamento - Cancelar desligamento\n"
            "/executar - Executar comando no terminal\n"
        )
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
        "/ajuda - Ver esta mensagem\n"
        f"{admin_cmds}\n"
        "Ou simplesmente me faça qualquer pergunta! 😊",
        parse_mode='Markdown'
    )

async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
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
    if not await verificar_acesso(update):
        return
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
        await update.message.reply_text("❌ Nível inválido!")
        return
    user_id = str(update.message.from_user.id)
    atualizar_nivel(user_id, novo_nivel)
    await update.message.reply_text(f"✅ Nível atualizado para *{novo_nivel}*!", parse_mode='Markdown')

async def limpar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    usuarios = carregar_usuarios()
    if user_id in usuarios:
        usuarios[user_id]["historico"] = []
        usuarios[user_id]["nome"] = ""
        salvar_usuarios(usuarios)
    aguardando_nome.pop(user_id, None)
    await update.message.reply_text("🧹 Histórico e nome limpos!\n\nDigite /start para recomeçar! 😊")

async def plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    usuario = get_usuario(user_id)
    if not context.args:
        await update.message.reply_text("📚 Use assim:\n/plano Python\n/plano Matemática")
        return
    tema = ' '.join(context.args)
    nivel_usuario = usuario.get("nivel", "iniciante")
    await update.message.reply_text(f"⏳ Gerando plano sobre *{tema}*...", parse_mode='Markdown')
    resposta = gerar_plano_de_estudo(tema, nivel_usuario, user_id)
    await update.message.reply_text(resposta)

async def estudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("📖 Use assim:\n/estudar Mercado Financeiro\n/estudar Bitcoin")
        return
    tema = ' '.join(context.args)
    await update.message.reply_text(f"📚 Estudando sobre *{tema}*... 🔍", parse_mode='Markdown')
    resposta = estudar_tema(tema, user_id)
    await update.message.reply_text(resposta)

async def conhecimentos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    resposta = listar_conhecimentos()
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def evolucao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    resposta = get_estatisticas()
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def corrigir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("✏️ Use assim:\n/corrigir A resposta certa é...")
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
    if not await verificar_acesso(update):
        return
    await update.message.reply_text("📊 Buscando dados do mercado...")
    resposta = get_mercado_geral()
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def cotacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("💰 Use assim:\n/cotacao PETR4.SA\n/cotacao BTC-USD")
        return
    ticker = context.args[0].upper()
    await update.message.reply_text(f"💰 Buscando *{ticker}*...", parse_mode='Markdown')
    resposta = get_cotacao(ticker)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def indicadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("📊 Use assim:\n/indicadores PETR4.SA\n/indicadores BTC-USD")
        return
    ticker = context.args[0].upper()
    await update.message.reply_text(f"📊 Calculando *{ticker}*...", parse_mode='Markdown')
    resposta = get_indicadores(ticker)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def codigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("💻 Use assim:\n/codigo Crie uma função Python que calcula IMC")
        return
    pedido = ' '.join(context.args)
    await update.message.reply_text(f"💻 Programando: *{pedido[:50]}*...", parse_mode='Markdown')
    prompt = f"""O usuário precisa de ajuda com programação: {pedido}
    Por favor: 1. Explique o que vai fazer 2. Forneça o código completo 3. Explique cada parte 4. Dê dicas"""
    resposta = perguntar_ia(prompt, user_id)
    await update.message.reply_text(resposta)

async def pesquisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("🔍 Use assim:\n/pesquisar Bitcoin hoje")
        return
    query = ' '.join(context.args)
    await update.message.reply_text(f"🔍 Pesquisando: *{query}*...", parse_mode='Markdown')
    resposta = pesquisar_web(query)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("📰 Use assim:\n/noticias Mercado Financeiro")
        return
    query = ' '.join(context.args)
    await update.message.reply_text(f"📰 Buscando notícias: *{query}*...", parse_mode='Markdown')
    resposta = pesquisar_noticias(query)
    await update.message.reply_text(resposta, parse_mode='Markdown')

# ─── Controle do PC ─────────────────────────────────────────

async def infopc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador pode usar este comando!")
        return
    await update.message.reply_text("💻 Coletando informações do PC...")
    resposta = get_info_pc()
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def processos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador pode usar este comando!")
        return
    resposta = listar_processos()
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def abrirprograma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador pode usar este comando!")
        return
    if not context.args:
        await update.message.reply_text(
            "💻 Use assim:\n"
            "/abrirprograma chrome\n"
            "/abrirprograma notepad\n"
            "/abrirprograma calculadora"
        )
        return
    programa = ' '.join(context.args)
    resposta = abrir_programa(programa)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def fecharprograma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador pode usar este comando!")
        return
    if not context.args:
        await update.message.reply_text("💻 Use assim:\n/fecharprograma chrome\n/fecharprograma notepad")
        return
    programa = context.args[0]
    resposta = fechar_programa(programa)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador pode usar este comando!")
        return
    await update.message.reply_text("📸 Tirando screenshot...")
    caminho = tirar_screenshot()
    if caminho.startswith("❌"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, 'rb'), caption="📸 Screenshot capturado!")

async def desligarpc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador pode usar este comando!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "desligar"
    await update.message.reply_text(
        "⚠️ *Confirmar desligamento?*\n\n"
        "Digite *SIM* para confirmar ou *NÃO* para cancelar.",
        parse_mode='Markdown'
    )

async def reiniciarpc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador pode usar este comando!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "reiniciar"
    await update.message.reply_text(
        "⚠️ *Confirmar reinicialização?*\n\n"
        "Digite *SIM* para confirmar ou *NÃO* para cancelar.",
        parse_mode='Markdown'
    )

async def cancelardesligamento_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador pode usar este comando!")
        return
    resposta = cancelar_desligamento()
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def executar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador pode usar este comando!")
        return
    if not context.args:
        await update.message.reply_text("💻 Use assim:\n/executar dir\n/executar ipconfig")
        return
    comando = ' '.join(context.args)
    await update.message.reply_text(f"⚡ Executando: `{comando}`...", parse_mode='Markdown')
    resposta = executar_comando(comando)
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def responder_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    texto = update.message.text

    # Aguardando nova senha
    if user_id in aguardando_nova_senha and aguardando_nova_senha[user_id]:
        nova_senha = texto.strip()
        trocar_senha(nova_senha)
        aguardando_nova_senha.pop(user_id, None)
        await update.message.reply_text(f"✅ Senha alterada!\n\nNova senha: `{nova_senha}`", parse_mode='Markdown')
        return

    # Aguardando confirmação de desligamento/reiniciar
    if user_id in aguardando_confirmacao:
        acao = aguardando_confirmacao.pop(user_id)
        if texto.upper() == "SIM":
            if acao == "desligar":
                resposta = desligar_pc()
            else:
                resposta = reiniciar_pc()
            await update.message.reply_text(resposta, parse_mode='Markdown')
        else:
            await update.message.reply_text("✅ Operação cancelada!")
        return

    # Aguardando senha
    if user_id in aguardando_senha and aguardando_senha[user_id]:
        senha_digitada = texto.strip()
        senha_correta = get_senha()
        if senha_digitada == senha_correta:
            liberar_usuario(user_id)
            aguardando_senha.pop(user_id, None)
            aguardando_nome[user_id] = True
            await update.message.reply_text(
                "✅ *Acesso liberado!*\n\n"
                "👋 Olá! Eu sou a *Verônica*!\n\nQual é o seu nome? 😊",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Senha incorreta! Tente novamente:")
        return

    # Verifica acesso
    if not is_autorizado(int_id) and not usuario_liberado(user_id):
        aguardando_senha[user_id] = True
        await update.message.reply_text("🔒 *Acesso Restrito!*\n\nDigite a senha:", parse_mode='Markdown')
        return

    # Aguardando nome
    if user_id in aguardando_nome and aguardando_nome[user_id]:
        nome = texto.strip()
        atualizar_nome(user_id, nome)
        aguardando_nome.pop(user_id, None)
        await update.message.reply_text(
            f"Olá, *{nome}*! 🎉\n\n"
            "Serei sua assistente pessoal!\n\n"
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
    app.add_handler(CommandHandler("trocarsenha", trocar_senha_cmd))
    app.add_handler(CommandHandler("versenha", ver_senha_cmd))
    app.add_handler(CommandHandler("infopc", infopc))
    app.add_handler(CommandHandler("processos", processos))
    app.add_handler(CommandHandler("abrirprograma", abrirprograma))
    app.add_handler(CommandHandler("fecharprograma", fecharprograma))
    app.add_handler(CommandHandler("screenshot", screenshot))
    app.add_handler(CommandHandler("desligarpc", desligarpc_cmd))
    app.add_handler(CommandHandler("reiniciarpc", reiniciarpc_cmd))
    app.add_handler(CommandHandler("cancelardesligamento", cancelardesligamento_cmd))
    app.add_handler(CommandHandler("executar", executar_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensagem))
    print("🤖 Verônica está online!")
    app.run_polling()