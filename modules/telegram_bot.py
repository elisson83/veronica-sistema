import logging
import asyncio
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
from modules.agente import executar_tarefa_autonoma
from modules.conteudo import criar_ebook, analisar_video_youtube, criar_post_redes_sociais, criar_script_video
from modules.cyber import get_status_kali, ligar_kali, desligar_kali, pausar_kali, executar_comando_kali, scan_rede, info_rede_local, gerar_relatorio_seguranca

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

aguardando_nome = {}
aguardando_senha = {}
aguardando_nova_senha = {}
aguardando_confirmacao = {}
aguardando_tarefa = {}

CONFIRMAR = ["CONFIRMAR", "SIM", "S", "OK", "YES", "Y", "1", "EXECUTAR", "PODE", "VAI", "EXECUTE"]
CANCELAR = ["CANCELAR", "NAO", "NÃO", "N", "NO", "0", "PARA", "STOP", "CANCELA"]

async def verificar_acesso(update: Update) -> bool:
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    if is_autorizado(int_id):
        return True
    if usuario_liberado(user_id):
        return True
    aguardando_senha[user_id] = True
    await update.message.reply_text("🔒 *Acesso Restrito!*\n\nDigite a senha para continuar:", parse_mode='Markdown')
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
            "/trocarsenha /versenha\n\n"
            "💻 *Controle do PC:*\n"
            "/infopc /processos /abrirprograma\n"
            "/fecharprograma /screenshot\n"
            "/desligarpc /reiniciarpc /executar\n\n"
            "👁️ *Visão e Mouse:*\n"
            "/vertela /lertela /mouse\n"
            "/mover /clicar /digitar\n"
            "/tecla /atalho /scroll\n\n"
            "🤖 *Agente Autônomo:*\n"
            "/tarefa - Executar tarefa autonomamente\n\n"
            "📚 *Criação de Conteúdo:*\n"
            "/ebook /analisarvideo /post /script\n\n"
            "🔒 *Cyber Segurança:*\n"
            "/kalistatus /kaliligar /kalidesligar\n"
            "/kalicomando /scanrede /inforede /relatorio\n"
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
    await update.message.reply_text(gerar_plano_de_estudo(tema, nivel_usuario, user_id))

async def estudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("📖 Use:\n/estudar Mercado Financeiro")
        return
    tema = ' '.join(context.args)
    await update.message.reply_text(f"📚 Estudando *{tema}*... 🔍", parse_mode='Markdown')
    await update.message.reply_text(estudar_tema(tema, user_id))

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
    await update.message.reply_text(corrigir_resposta(ultima_pergunta, ultima_resp, correcao, user_id))

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
    await update.message.reply_text(abrir_programa(' '.join(context.args)), parse_mode='Markdown')

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
    await update.message.reply_text(executar_comando(' '.join(context.args)), parse_mode='Markdown')

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
    await update.message.reply_text("👁️ Lendo texto...")
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
    await update.message.reply_text(digitar(' '.join(context.args)))

async def tecla_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("⌨️ Use:\n/tecla enter\n/tecla esc")
        return
    await update.message.reply_text(pressionar_tecla(context.args[0]))

async def atalho_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("⌨️ Use:\n/atalho ctrl c\n/atalho alt f4")
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

async def tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text(
            "🤖 *Agente Autônomo*\n\n"
            "Exemplos:\n"
            "/tarefa Abrir o notepad e digitar Olá mundo\n"
            "/tarefa Abrir o chrome e ir para google.com"
        )
        return
    descricao = ' '.join(context.args)
    user_id = str(update.message.from_user.id)
    aguardando_tarefa[user_id] = descricao
    await update.message.reply_text(
        f"🤖 *Tarefa recebida:*\n_{descricao}_\n\n"
        "Digite *SIM* para executar ou *NÃO* para cancelar.",
        parse_mode='Markdown'
    )

async def ebook_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("📚 Use:\n/ebook Como Ganhar Dinheiro Online")
        return
    tema = ' '.join(context.args)
    await update.message.reply_text(f"📚 Criando e-book sobre *{tema}*... ⏳", parse_mode='Markdown')
    loop = asyncio.get_event_loop()
    caminho = await loop.run_in_executor(None, lambda: criar_ebook(tema, user_id))
    if caminho.startswith("❌"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_document(
            document=open(caminho, 'rb'),
            caption=f"📚 *E-book criado:* {tema}\n\n✅ Pronto para vender!",
            parse_mode='Markdown'
        )

async def analisarvideo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("🎥 Use:\n/analisarvideo https://youtube.com/watch?v=XXXXX")
        return
    url = context.args[0]
    await update.message.reply_text("🎥 Analisando vídeo... ⏳")
    loop = asyncio.get_event_loop()
    analise = await loop.run_in_executor(None, lambda: analisar_video_youtube(url, user_id))
    await update.message.reply_text(analise)

async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("📱 Use:\n/post instagram Marketing Digital")
        return
    rede = context.args[0].lower()
    tema = ' '.join(context.args[1:]) if len(context.args) > 1 else context.args[0]
    await update.message.reply_text(f"📱 Criando posts para *{rede}*... ⏳", parse_mode='Markdown')
    loop = asyncio.get_event_loop()
    posts = await loop.run_in_executor(None, lambda: criar_post_redes_sociais(tema, rede, user_id))
    await update.message.reply_text(posts)

async def script_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("🎬 Use:\n/script Como Ganhar Dinheiro Online")
        return
    tema = ' '.join(context.args)
    await update.message.reply_text(f"🎬 Criando script sobre *{tema}*... ⏳", parse_mode='Markdown')
    loop = asyncio.get_event_loop()
    script = await loop.run_in_executor(None, lambda: criar_script_video(tema, 10, user_id))
    await update.message.reply_text(script)

async def kali_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text(get_status_kali(), parse_mode='Markdown')

async def kali_ligar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text(ligar_kali(), parse_mode='Markdown')

async def kali_desligar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "kali_desligar"
    await update.message.reply_text("⚠️ *Confirmar desligamento do Kali?*\n\nDigite *SIM* ou *NÃO*", parse_mode='Markdown')

async def kali_comando_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("💻 Use:\n/kalicomando ifconfig\n/kalicomando whoami")
        return
    comando = ' '.join(context.args)
    await update.message.reply_text(f"⚡ Executando no Kali: `{comando}`...", parse_mode='Markdown')
    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, lambda: executar_comando_kali(comando))
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def scan_rede_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("🔍 Use:\n/scanrede 192.168.1.1\n/scanrede 192.168.1.0/24")
        return
    alvo = context.args[0]
    await update.message.reply_text(f"🔍 Escaneando: *{alvo}*... Aguarde!", parse_mode='Markdown')
    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, lambda: scan_rede(alvo))
    await update.message.reply_text(resposta, parse_mode='Markdown')

async def info_rede_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    await update.message.reply_text(info_rede_local(), parse_mode='Markdown')

async def relatorio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("⛔ Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("📊 Use:\n/relatorio 192.168.1.1")
        return
    alvo = context.args[0]
    await update.message.reply_text(f"📊 Gerando relatório para *{alvo}*... ⏳", parse_mode='Markdown')
    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, lambda: gerar_relatorio_seguranca(alvo))
    await update.message.reply_text(resposta)

async def responder_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    texto = update.message.text
    texto_upper = texto.upper().strip()

    if user_id in aguardando_nova_senha and aguardando_nova_senha[user_id]:
        nova_senha = texto.strip()
        trocar_senha(nova_senha)
        aguardando_nova_senha.pop(user_id, None)
        await update.message.reply_text(f"✅ Senha alterada!\n\nNova senha: `{nova_senha}`", parse_mode='Markdown')
        return

    if user_id in aguardando_confirmacao:
        acao = aguardando_confirmacao.pop(user_id)
        if texto_upper in CONFIRMAR:
            if acao == "desligar":
                resposta = desligar_pc()
            elif acao == "reiniciar":
                resposta = reiniciar_pc()
            elif acao == "kali_desligar":
                resposta = desligar_kali()
            else:
                resposta = "✅ Confirmado!"
            await update.message.reply_text(resposta, parse_mode='Markdown')
        else:
            await update.message.reply_text("✅ Operação cancelada!")
        return

    if user_id in aguardando_tarefa:
        if texto_upper in CONFIRMAR:
            descricao = aguardando_tarefa.pop(user_id)
            await update.message.reply_text("🤖 Executando tarefa autonomamente...")
            mensagens = []
            def callback(msg):
                mensagens.append(msg)
            loop = asyncio.get_event_loop()
            resultados = await loop.run_in_executor(
                None, lambda: executar_tarefa_autonoma(descricao, callback)
            )
            for msg in mensagens:
                await update.message.reply_text(msg)
            await update.message.reply_text(
                f"✅ *Tarefa concluída!*\n\n{chr(10).join(resultados)[:1000]}",
                parse_mode='Markdown'
            )
        else:
            aguardando_tarefa.pop(user_id, None)
            await update.message.reply_text("✅ Tarefa cancelada!")
        return

    if user_id in aguardando_senha and aguardando_senha[user_id]:
        if texto.strip() == get_senha():
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
    app.add_handler(CommandHandler("tarefa", tarefa))
    app.add_handler(CommandHandler("ebook", ebook_cmd))
    app.add_handler(CommandHandler("analisarvideo", analisarvideo_cmd))
    app.add_handler(CommandHandler("post", post_cmd))
    app.add_handler(CommandHandler("script", script_cmd))
    app.add_handler(CommandHandler("kalistatus", kali_status_cmd))
    app.add_handler(CommandHandler("kaliligar", kali_ligar_cmd))
    app.add_handler(CommandHandler("kalidesligar", kali_desligar_cmd))
    app.add_handler(CommandHandler("kalicomando", kali_comando_cmd))
    app.add_handler(CommandHandler("scanrede", scan_rede_cmd))
    app.add_handler(CommandHandler("inforede", info_rede_cmd))
    app.add_handler(CommandHandler("relatorio", relatorio_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensagem))
    print("🤖 Verônica está online!")
    app.run_polling()