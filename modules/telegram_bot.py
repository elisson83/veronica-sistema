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
from modules.visao import capturar_tela, ler_texto_tela, get_posicao_mouse, mover_mouse, clicar, duplo_clicar, digitar, pressionar_tecla, atalho_teclado, scroll

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
        "🔒 *Acesso Restrito!*\n\nDigite a senha para continuar:",
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
                f"👋 Olá, *{nome_salvo}*! Bem-vindo de volta!\n\nSerei sua assistente pessoal. Como posso te ajudar hoje? 😊",
                parse_mode='Markdown'
            )
            return
        aguardando_nome[user_id] = True
        await update.message.reply_text("👋 Olá! Eu sou a *Verônica*!\n\nQual é o seu nome? 😊", parse_mode='Markdown')
        return
    aguardando_senha[user_id] = True
    await update.message.reply_text("🔒 *Acesso Restrito!*\n\nDigite a senha para continuar:", parse_mode='Markdown')

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
        f"🔑 *Configurações de Acesso:*\n\n• Senha atual: `{senha}`\n• Usuários liberados: {len(usuarios)}\n",
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
            "/infopc - Informações do PC\n"
            "/processos - Ver processos\n"
            "/abrirprograma - Abrir programa\n"
            "/fecharprograma - Fechar programa\n"
            "/screenshot - Tirar screenshot\n"
            "/desligarpc - Desligar PC\n"
            "/reiniciarpc - Reiniciar PC\n"
            "/executar - Executar comando\n\n"
            "👁️ *Visão e Mouse:*\n"
            "/vertela - Ver a tela atual\n"
            "/lertela - Ler texto da tela\n"
            "/mouse - Ver posição do mouse\n"
            "/mover - Mover mouse\n"
            "/clicar - Clicar na tela\n"
            "/digitar - Digitar texto\n"
            "/tecla - Pressionar tecla\n"
            "/atalho - Atalho de teclado\n"
            "/scroll - Rolar a tela\n"
        )
    await update.message.reply_text(
        "🆘 *Comandos da Verônica:*\n\n"
        "📚 *Estudo:* /plano /estudar /conhecimentos\n"
        "🔍 *Pesquisa:* /pesquisar /noticias\n"
        "💻 *Código:* /codigo\n"
        "📈 *Financeiro:* /mercado /cotacao /indicadores\n"
        "🧠 *Evolução:* /corrigir /evolucao\n"
        "⚙️ *Config:* /nivel /perfil /limpar\n"
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
        f"• Mensagens: {total_mensagens}\n"
        f"• Membro desde: {usuario.get('criado_em', '?')[:10]}\n",
        parse_mode='Markdown'
    )

async def nivel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("📊 Use:\n/nivel iniciante\n/nivel intermediario\n/nivel avancado")
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
        await update.message.reply_text("📚 Use:\n/plano Python\n/plano Matemática")
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
        await update.message.reply_text("📖 Use:\n/estudar Mercado Financeiro")
        return
    tema = ' '.join(context.args)
    await update.message.reply_text(f"📚 Estudando *{tema}*... 🔍", parse_mode='Markdown')
    resposta = estudar_tema(tema, user_id)
    await update.message.reply_text(resposta)

async def conhecimentos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    await update.message.reply_text(listar_conhecimentos(), parse_mode='Markdown')

async def evolucao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    await update.message.reply_text(get_estatisticas(), parse_mode='Markdown')

async def corrigir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("✏️ Use:\n/corrigir A resposta certa é...")
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
    await update.message.reply_text("✏️ Obrigada! Aprendendo...")
    resposta = corrigir_resposta(ultima_pergunta, ultima_resp, correcao, user_id)
    await update.message.reply_text(resposta)

async def mercado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    await update.message.reply_text("📊 Buscando mercado...")
    await update.message.reply_text(get_mercado_geral(), parse_mode='Markdown')

async def cotacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("💰 Use:\n/cotacao PETR4.SA\n/cotacao BTC-USD")
        return
    ticker = context.args[0].upper()
    await update.message.reply_text(f"💰 Buscando *{ticker}*...", parse_mode='Markdown')
    await update.message.reply_text(get_cotacao(ticker), parse_mode='Markdown')

async def indicadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("📊 Use:\n/indicadores PETR4.SA")
        return
    ticker = context.args[0].upper()
    await update.message.reply_text(f"📊 Calculando *{ticker}*...", parse_mode='Markdown')
    await update.message.reply_text(get_indicadores(ticker), parse_mode='Markdown')

async def codigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("💻 Use:\n/codigo Crie uma função Python que calcula IMC")
        return
    pedido = ' '.join(context.args)
    await update.message.reply_text(f"💻 Programando: *{pedido[:50]}*...", parse_mode='Markdown')
    prompt = f"O usuário precisa de ajuda com programação: {pedido}\n1. Explique 2. Código completo 3. Explique partes 4. Dicas"
    await update.message.reply_text(perguntar_ia(prompt, user_id))

async def pesquisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("🔍 Use:\n/pesquisar Bitcoin hoje")
        return
    query = ' '.join(context.args)
    await update.message.reply_text(f"🔍 Pesquisando: *{query}*...", parse_mode='Markdown')
    await update.message.reply_text(pesquisar_web(query), parse_mode='Markdown')

async def noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("📰 Use:\n/noticias Mercado Financeiro")
        return
    query = ' '.join(context.args)
    await update.message.reply_text(f"📰 Buscando: *{query}*...", parse_mode='Markdown')
    await update.message.reply_text(pesquisar_noticias(query), parse_mode='Markdown')

# ─── Controle do PC ─────────────────────────────────────────

async def infopc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text("💻 Coletando informações...")
    await update.message.reply_text(get_info_pc(), parse_mode='Markdown')

async def processos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text(listar_processos(), parse_mode='Markdown')

async def abrirprograma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("💻 Use:\n/abrirprograma chrome\n/abrirprograma notepad")
        return
    resposta = abrir_programa(' '.join(context.args))
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def fecharprograma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("💻 Use:\n/fecharprograma chrome")
        return
    await update.message.reply_text(fechar_programa(context.args[0]), parse_mode='Markdown')

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text("📸 Tirando screenshot...")
    caminho = tirar_screenshot()
    if caminho.startswith("❌"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, 'rb'), caption="📸 Screenshot!")

async def desligarpc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "desligar"
    await update.message.reply_text("⚠️ *Confirmar desligamento?*\n\nDigite *SIM* ou *NÃO*", parse_mode='Markdown')

async def reiniciarpc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "reiniciar"
    await update.message.reply_text("⚠️ *Confirmar reinicialização?*\n\nDigite *SIM* ou *NÃO*", parse_mode='Markdown')

async def cancelardesligamento_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text(cancelar_desligamento(), parse_mode='Markdown')

async def executar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("💻 Use:\n/executar dir\n/executar ipconfig")
        return
    await update.message.reply_text(f"⚡ Executando...", parse_mode='Markdown')
    await update.message.reply_text(executar_comando(' '.join(context.args)), parse_mode='Markdown')

# ─── Visão e Mouse ──────────────────────────────────────────

async def vertela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text("👁️ Capturando tela...")
    caminho = capturar_tela()
    if caminho.startswith("❌"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, 'rb'), caption="👁️ Tela atual!")

async def lertela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text("👁️ Lendo texto da tela...")
    await update.message.reply_text(ler_texto_tela(), parse_mode='Markdown')

async def mouse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text(get_posicao_mouse())

async def mover_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("🖱️ Use:\n/mover 500 300")
        return
    x, y = int(context.args[0]), int(context.args[1])
    await update.message.reply_text(mover_mouse(x, y))

async def clicar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("🖱️ Use:\n/clicar 500 300")
        return
    x, y = int(context.args[0]), int(context.args[1])
    await update.message.reply_text(clicar(x, y))

async def digitar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("⌨️ Use:\n/digitar Olá mundo")
        return
    texto = ' '.join(context.args)
    await update.message.reply_text(digitar(texto))

async def tecla_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("⌨️ Use:\n/tecla enter\n/tecla esc\n/tecla f5")
        return
    await update.message.reply_text(pressionar_tecla(context.args[0]))

async def atalho_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("⌨️ Use:\n/atalho ctrl c\n/atalho alt f4\n/atalho win d")
        return
    await update.message.reply_text(atalho_teclado(*context.args))

async def scroll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("🖱️ Use:\n/scroll cima\n/scroll baixo")
        return
    await update.message.reply_text(scroll(context.args[0]))

async def responder_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    texto = update.message.text

    if user_id in aguardando_nova_senha and aguardando_nova_senha[user_id]:
        nova_senha = texto.strip()
        trocar_senha(nova_senha)
        aguardando_nova_senha.pop(user_id, None)
        await update.message.reply_text(f"✅ Senha alterada!\n\nNova senha: `{nova_senha}`", parse_mode='Markdown')
        return

    if user_id in aguardando_confirmacao:
        acao = aguardando_confirmacao.pop(user_id)
        if texto.upper() == "SIM":
            resposta = desligar_pc() if acao == "desligar" else reiniciar_pc()
            await update.message.reply_text(resposta, parse_mode='Markdown')
        else:
            await update.message.reply_text("✅ Operação cancelada!")
        return

    if user_id in aguardando_senha and aguardando_senha[user_id]:
        senha_digitada = texto.strip()
        if senha_digitada == get_senha():
            liberar_usuario(user_id)
            aguardando_senha.pop(user_id, None)
            aguardando_nome[user_id] = True
            await update.message.reply_text("✅ *Acesso liberado!*\n\n👋 Olá! Eu sou a *Verônica*!\n\nQual é o seu nome? 😊", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Senha incorreta! Tente novamente:")
        return

    if not is_autorizado(int_id) and not usuario_liberado(user_id):
        aguardando_senha[user_id] = True
        await update.message.reply_text("🔒 *Acesso Restrito!*\n\nDigite a senha:", parse_mode='Markdown')
        return

    if user_id in aguardando_nome and aguardando_nome[user_id]:
        nome = texto.strip()
        atualizar_nome(user_id, nome)
        aguardando_nome.pop(user_id, None)
        await update.message.reply_text(
            f"Olá, *{nome}*! 🎉\n\nSerei sua assistente pessoal!\n\n💡 Digite /ajuda para ver todos os comandos!\n\nO que deseja fazer hoje? 😊",
            parse_mode='Markdown'
        )
        return

    await update.message.reply_text("🤔 Pensando...")
    await update.message.reply_text(perguntar_ia(texto, user_id))

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
    app.add_handler(CommandHandler("vertela", vertela))
    app.add_handler(CommandHandler("lertela", lertela))
    app.add_handler(CommandHandler("mouse", mouse_cmd))
    app.add_handler(CommandHandler("mover", mover_cmd))
    app.add_handler(CommandHandler("clicar", clicar_cmd))
    app.add_handler(CommandHandler("digitar", digitar_cmd))
    app.add_handler(CommandHandler("tecla", tecla_cmd))
    app.add_handler(CommandHandler("atalho", atalho_cmd))
    app.add_handler(CommandHandler("scroll", scroll_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensagem))
    print("🤖 Verônica está online!")
    app.run_polling()