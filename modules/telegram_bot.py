import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, is_autorizado
from modules.ai_brain import perguntar_ia, perguntar_ia_local, gerar_plano_de_estudo, estudar_tema, corrigir_resposta
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
from modules.licenca import get_info_licenca
from modules.ai_local import get_status_local, listar_modelos_locais
from modules.memoria_permanente import lembrar_fato, lembrar_preferencia, buscar_memorias, apagar_memorias
from modules.visao_ia import tirar_e_descrever, ver_e_agir, analisar_imagem_enviada
from modules.dual_brain import get_status_completo, get_status_resumido, get_melhor_ia
from modules.marketing import criar_post_otimizado, criar_calendario_editorial, criar_estrategia_completa, criar_copy_vendas, analisar_concorrente, get_tendencias, listar_posts
from modules.visao_geradora import gerar_imagem, gerar_logo, gerar_banner_post, gerar_capa_ebook, gerar_imagem_inteligente, transformar_foto_anime

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

aguardando_nome = {}
aguardando_senha = {}
aguardando_nova_senha = {}
aguardando_confirmacao = {}
aguardando_tarefa = {}

CONFIRMAR = ["CONFIRMAR", "SIM", "S", "OK", "YES", "Y", "1", "EXECUTAR", "PODE", "VAI", "EXECUTE"]
CANCELAR = ["CANCELAR", "NAO", "NAO", "N", "NO", "0", "PARA", "STOP", "CANCELA"]

async def verificar_acesso(update: Update) -> bool:
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    if is_autorizado(int_id):
        return True
    if usuario_liberado(user_id):
        return True
    aguardando_senha[user_id] = True
    await update.message.reply_text("Acesso Restrito! Digite a senha para continuar:")
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    if is_autorizado(int_id) or usuario_liberado(user_id):
        usuario = get_usuario(user_id)
        nome_salvo = usuario.get("nome", "")
        if nome_salvo and nome_salvo != "":
            ia_ativa = get_status_resumido()
            await update.message.reply_text(f"Ola, {nome_salvo}! Bem-vindo de volta!\n\n{ia_ativa}\n\nComo posso te ajudar hoje?")
            return
        aguardando_nome[user_id] = True
        await update.message.reply_text("Ola! Eu sou a Veronica! Qual e o seu nome?")
        return
    aguardando_senha[user_id] = True
    await update.message.reply_text("Acesso Restrito! Digite a senha para continuar:")

async def trocar_senha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    if not is_autorizado(int_id):
        await update.message.reply_text("Apenas o administrador pode trocar a senha!")
        return
    if not context.args:
        aguardando_nova_senha[user_id] = True
        await update.message.reply_text("Digite a nova senha:")
        return
    nova_senha = " ".join(context.args)
    trocar_senha(nova_senha)
    await update.message.reply_text(f"Senha alterada! Nova senha: {nova_senha}")

async def ver_senha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    int_id = update.message.from_user.id
    if not is_autorizado(int_id):
        await update.message.reply_text("Apenas o administrador pode ver a senha!")
        return
    senha = get_senha()
    usuarios = listar_usuarios_liberados()
    await update.message.reply_text(f"Senha atual: {senha}\nUsuarios liberados: {len(usuarios)}")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    int_id = update.message.from_user.id
    admin_cmds = ""
    if is_autorizado(int_id):
        admin_cmds = "\n/trocarsenha /versenha /licenca /status\n/ialocal /ialocalstatus /modelos\n/lembrar /memorias /esquecertudo\n/verdescrever /veragir /analisarimagem\n/mkpost /mkcalendario /mkestrategia /mkcopy /mkconcorrente /mktendencias /mkposts\n/infopc /processos /abrirprograma /fecharprograma /screenshot\n/desligarpc /reiniciarpc /executar\n/vertela /lertela /mouse /mover /clicar /digitar /tecla /atalho /scroll\n/tarefa /ebook /analisarvideo /post /script\n/kalistatus /kaliligar /kalidesligar /kalicomando /scanrede /inforede /relatorio"
    await update.message.reply_text(f"Comandos da Veronica:\n/plano /estudar /conhecimentos\n/pesquisar /noticias /codigo\n/mercado /cotacao /indicadores\n/corrigir /evolucao /nivel /perfil /limpar{admin_cmds}\n\nOu me faca qualquer pergunta!")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text("Verificando sistemas...")
    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, get_status_completo)
    await update.message.reply_text(status)

async def perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    usuario = get_usuario(user_id)
    total_mensagens = len(usuario.get("historico", []))
    await update.message.reply_text(f"Perfil:\nNome: {usuario.get('nome','?')}\nNivel: {usuario.get('nivel','iniciante')}\nMensagens: {total_mensagens}\nMembro desde: {usuario.get('criado_em','?')[:10]}")

async def nivel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /nivel iniciante ou /nivel intermediario ou /nivel avancado")
        return
    novo_nivel = context.args[0].lower()
    if novo_nivel not in ["iniciante", "intermediario", "avancado"]:
        await update.message.reply_text("Nivel invalido!")
        return
    user_id = str(update.message.from_user.id)
    atualizar_nivel(user_id, novo_nivel)
    await update.message.reply_text(f"Nivel atualizado para {novo_nivel}!")

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
    await update.message.reply_text("Historico limpo! Digite /start para recomecar!")

async def lembrar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /lembrar Elisson mora em Florianopolis")
        return
    fato = " ".join(context.args)
    await update.message.reply_text(lembrar_fato(fato, "manual"))

async def memorias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    termo = " ".join(context.args) if context.args else ""
    await update.message.reply_text(buscar_memorias(termo))

async def esquecertudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "apagar_memoria"
    await update.message.reply_text("Apagar TODA a memoria permanente? Digite SIM ou NAO")

async def verdescrever_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    pergunta = " ".join(context.args) if context.args else "O que voce ve nessa tela? Descreva tudo em detalhes."
    await update.message.reply_text("Analisando a tela com IA...")
    loop = asyncio.get_event_loop()
    caminho, descricao = await loop.run_in_executor(None, lambda: tirar_e_descrever(pergunta))
    if caminho:
        await update.message.reply_photo(photo=open(caminho, "rb"), caption=f"Analise da tela:\n\n{descricao[:1000]}")
    else:
        await update.message.reply_text(descricao)

async def veragir_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /veragir Abrir o chrome")
        return
    objetivo = " ".join(context.args)
    await update.message.reply_text(f"Analisando tela para: {objetivo}...")
    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, lambda: ver_e_agir(objetivo))
    await update.message.reply_text(resposta)

async def analisar_imagem_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not update.message.photo:
        await update.message.reply_text("Envie uma imagem com o comando /analisarimagem ou com legenda!")
        return
    await update.message.reply_text("Analisando imagem...")
    foto = update.message.photo[-1]
    arquivo = await foto.get_file()
    from pathlib import Path
    caminho = str(Path("assets") / f"img_{foto.file_id}.jpg")
    Path("assets").mkdir(exist_ok=True)
    await arquivo.download_to_drive(caminho)
    pergunta = update.message.caption or "O que voce ve nessa imagem? Descreva em detalhes."
    loop = asyncio.get_event_loop()
    descricao = await loop.run_in_executor(None, lambda: analisar_imagem_enviada(caminho, pergunta))
    await update.message.reply_text(f"Analise:\n\n{descricao}")

async def mkpost_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Use: /mkpost instagram Marketing Digital")
        return
    rede = context.args[0].lower()
    tema = " ".join(context.args[1:])
    await update.message.reply_text(f"Criando post para {rede.upper()}...")
    loop = asyncio.get_event_loop()
    post = await loop.run_in_executor(None, lambda: criar_post_otimizado(tema, rede))
    await update.message.reply_text(post)

async def mkcalendario_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /mkcalendario Marketing Digital")
        return
    nicho = " ".join(context.args)
    await update.message.reply_text(f"Criando calendario para {nicho}...")
    loop = asyncio.get_event_loop()
    calendario = await loop.run_in_executor(None, lambda: criar_calendario_editorial(nicho))
    await update.message.reply_text(calendario[:4000])

async def mkestrategia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /mkestrategia Loja de roupas|Aumentar vendas")
        return
    texto = " ".join(context.args)
    if "|" in texto:
        partes = texto.split("|")
        negocio = partes[0].strip()
        objetivo = partes[1].strip()
    else:
        negocio = texto
        objetivo = "aumentar vendas e visibilidade"
    await update.message.reply_text(f"Criando estrategia para {negocio}...")
    loop = asyncio.get_event_loop()
    estrategia = await loop.run_in_executor(None, lambda: criar_estrategia_completa(negocio, objetivo))
    await update.message.reply_text(estrategia[:4000])

async def mkcopy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /mkcopy Curso de Python|Iniciantes")
        return
    texto = " ".join(context.args)
    if "|" in texto:
        partes = texto.split("|")
        produto = partes[0].strip()
        publico = partes[1].strip()
    else:
        produto = texto
        publico = "publico geral"
    await update.message.reply_text(f"Criando copy para {produto}...")
    loop = asyncio.get_event_loop()
    copy = await loop.run_in_executor(None, lambda: criar_copy_vendas(produto, publico))
    await update.message.reply_text(copy[:4000])

async def mkconcorrente_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /mkconcorrente Hotmart|Produtos digitais")
        return
    texto = " ".join(context.args)
    if "|" in texto:
        partes = texto.split("|")
        concorrente = partes[0].strip()
        nicho = partes[1].strip()
    else:
        concorrente = texto
        nicho = "mercado geral"
    await update.message.reply_text(f"Analisando {concorrente}...")
    loop = asyncio.get_event_loop()
    analise = await loop.run_in_executor(None, lambda: analisar_concorrente(concorrente, nicho))
    await update.message.reply_text(analise[:4000])

async def mktendencias_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /mktendencias Marketing Digital")
        return
    nicho = " ".join(context.args)
    await update.message.reply_text(f"Buscando tendencias de {nicho}...")
    loop = asyncio.get_event_loop()
    tendencias = await loop.run_in_executor(None, lambda: get_tendencias(nicho))
    await update.message.reply_text(tendencias[:4000])

async def mkposts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    await update.message.reply_text(listar_posts())

async def plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    usuario = get_usuario(user_id)
    if not context.args:
        await update.message.reply_text("Use: /plano Python")
        return
    tema = " ".join(context.args)
    nivel_usuario = usuario.get("nivel", "iniciante")
    await update.message.reply_text(f"Gerando plano sobre {tema}...")
    await update.message.reply_text(gerar_plano_de_estudo(tema, nivel_usuario, user_id))

async def estudar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("Use: /estudar Mercado Financeiro")
        return
    tema = " ".join(context.args)
    await update.message.reply_text(f"Estudando {tema}...")
    await update.message.reply_text(estudar_tema(tema, user_id))

async def conhecimentos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    await update.message.reply_text(listar_conhecimentos())

async def evolucao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    await update.message.reply_text(get_estatisticas())

async def corrigir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("Use: /corrigir A resposta certa e...")
        return
    correcao = " ".join(context.args)
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
    await update.message.reply_text("Obrigada! Aprendendo...")
    await update.message.reply_text(corrigir_resposta(ultima_pergunta, ultima_resp, correcao, user_id))

async def mercado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    await update.message.reply_text("Buscando mercado...")
    await update.message.reply_text(get_mercado_geral())

async def cotacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /cotacao PETR4.SA")
        return
    ticker = context.args[0].upper()
    await update.message.reply_text(f"Buscando {ticker}...")
    await update.message.reply_text(get_cotacao(ticker))

async def indicadores(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /indicadores PETR4.SA")
        return
    ticker = context.args[0].upper()
    await update.message.reply_text(f"Calculando {ticker}...")
    await update.message.reply_text(get_indicadores(ticker))

async def codigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("Use: /codigo Crie uma funcao Python que calcula IMC")
        return
    pedido = " ".join(context.args)
    await update.message.reply_text(f"Programando: {pedido[:50]}...")
    prompt = f"O usuario precisa de ajuda com programacao: {pedido}"
    await update.message.reply_text(perguntar_ia(prompt, user_id))

async def pesquisar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /pesquisar Bitcoin hoje")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"Pesquisando: {query}...")
    await update.message.reply_text(pesquisar_web(query))

async def noticias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    if not context.args:
        await update.message.reply_text("Use: /noticias Mercado Financeiro")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"Buscando: {query}...")
    await update.message.reply_text(pesquisar_noticias(query))

async def ialocal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /ialocal sua pergunta aqui")
        return
    user_id = str(update.message.from_user.id)
    pergunta = " ".join(context.args)
    await update.message.reply_text("Consultando IA local...")
    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, lambda: perguntar_ia_local(pergunta, user_id))
    await update.message.reply_text(resposta)

async def ialocal_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(get_status_local())

async def modelos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(listar_modelos_locais())

async def infopc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text("Coletando informacoes...")
    await update.message.reply_text(get_info_pc())

async def processos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(listar_processos())

async def abrirprograma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /abrirprograma chrome")
        return
    await update.message.reply_text(abrir_programa(" ".join(context.args)))

async def fecharprograma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /fecharprograma chrome")
        return
    await update.message.reply_text(fechar_programa(context.args[0]))

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text("Tirando screenshot...")
    caminho = tirar_screenshot()
    if caminho.startswith("X"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, "rb"), caption="Screenshot!")

async def desligarpc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "desligar"
    await update.message.reply_text("Confirmar desligamento? Digite SIM ou NAO")

async def reiniciarpc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "reiniciar"
    await update.message.reply_text("Confirmar reinicializacao? Digite SIM ou NAO")

async def cancelardesligamento_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(cancelar_desligamento())

async def executar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /executar dir")
        return
    await update.message.reply_text(executar_comando(" ".join(context.args)))

async def vertela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text("Capturando tela...")
    caminho = capturar_tela()
    if caminho.startswith("X"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, "rb"), caption="Tela atual!")

async def lertela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text("Lendo texto...")
    await update.message.reply_text(ler_texto_tela())

async def mouse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(get_posicao_mouse())

async def mover_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Use: /mover 500 300")
        return
    x, y = int(context.args[0]), int(context.args[1])
    await update.message.reply_text(mover_mouse(x, y))

async def clicar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Use: /clicar 500 300")
        return
    x, y = int(context.args[0]), int(context.args[1])
    await update.message.reply_text(clicar(x, y))

async def digitar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /digitar Ola mundo")
        return
    await update.message.reply_text(digitar(" ".join(context.args)))

async def tecla_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /tecla enter")
        return
    await update.message.reply_text(pressionar_tecla(context.args[0]))

async def atalho_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /atalho ctrl c")
        return
    await update.message.reply_text(atalho_teclado(*context.args))

async def scroll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /scroll cima ou /scroll baixo")
        return
    await update.message.reply_text(scroll(context.args[0]))

async def tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /tarefa Abrir o notepad e digitar Ola mundo")
        return
    descricao = " ".join(context.args)
    user_id = str(update.message.from_user.id)
    aguardando_tarefa[user_id] = descricao
    await update.message.reply_text(f"Tarefa recebida: {descricao}\n\nDigite SIM para executar ou NAO para cancelar.")

async def ebook_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("Use: /ebook Como Ganhar Dinheiro Online")
        return
    tema = " ".join(context.args)
    await update.message.reply_text(f"Criando e-book sobre {tema}...")
    loop = asyncio.get_event_loop()
    caminho = await loop.run_in_executor(None, lambda: criar_ebook(tema, user_id))
    if caminho.startswith("X"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_document(document=open(caminho, "rb"), caption=f"E-book criado: {tema}")

async def analisarvideo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("Use: /analisarvideo https://youtube.com/watch?v=XXXXX")
        return
    url = context.args[0]
    await update.message.reply_text("Analisando video...")
    loop = asyncio.get_event_loop()
    analise = await loop.run_in_executor(None, lambda: analisar_video_youtube(url, user_id))
    await update.message.reply_text(analise)

async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("Use: /post instagram Marketing Digital")
        return
    rede = context.args[0].lower()
    tema = " ".join(context.args[1:]) if len(context.args) > 1 else context.args[0]
    await update.message.reply_text(f"Criando posts para {rede}...")
    loop = asyncio.get_event_loop()
    posts = await loop.run_in_executor(None, lambda: criar_post_redes_sociais(tema, rede, user_id))
    await update.message.reply_text(posts)

async def script_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acesso(update):
        return
    user_id = str(update.message.from_user.id)
    if not context.args:
        await update.message.reply_text("Use: /script Como Ganhar Dinheiro Online")
        return
    tema = " ".join(context.args)
    await update.message.reply_text(f"Criando script sobre {tema}...")
    loop = asyncio.get_event_loop()
    script = await loop.run_in_executor(None, lambda: criar_script_video(tema, 10, user_id))
    await update.message.reply_text(script)

async def kali_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(get_status_kali())

async def kali_ligar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(ligar_kali())

async def kali_desligar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    user_id = str(update.message.from_user.id)
    aguardando_confirmacao[user_id] = "kali_desligar"
    await update.message.reply_text("Confirmar desligamento do Kali? Digite SIM ou NAO")

async def kali_comando_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /kalicomando ifconfig")
        return
    comando = " ".join(context.args)
    await update.message.reply_text(f"Executando no Kali: {comando}...")
    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, lambda: executar_comando_kali(comando))
    await update.message.reply_text(resposta)

async def scan_rede_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /scanrede 192.168.1.1")
        return
    alvo = context.args[0]
    await update.message.reply_text(f"Escaneando: {alvo}...")
    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, lambda: scan_rede(alvo))
    await update.message.reply_text(resposta)

async def info_rede_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(info_rede_local())

async def relatorio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /relatorio 192.168.1.1")
        return
    alvo = context.args[0]
    await update.message.reply_text(f"Gerando relatorio para {alvo}...")
    loop = asyncio.get_event_loop()
    resposta = await loop.run_in_executor(None, lambda: gerar_relatorio_seguranca(alvo))
    await update.message.reply_text(resposta)

async def licenca_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    await update.message.reply_text(get_info_licenca())

async def responder_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    int_id = update.message.from_user.id
    texto = update.message.text
    texto_upper = texto.upper().strip()

    if user_id in aguardando_nova_senha and aguardando_nova_senha[user_id]:
        nova_senha = texto.strip()
        trocar_senha(nova_senha)
        aguardando_nova_senha.pop(user_id, None)
        await update.message.reply_text(f"Senha alterada! Nova senha: {nova_senha}")
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
            elif acao == "apagar_memoria":
                resposta = apagar_memorias()
            else:
                resposta = "Confirmado!"
            await update.message.reply_text(resposta)
        else:
            await update.message.reply_text("Operacao cancelada!")
        return

    if user_id in aguardando_tarefa:
        if texto_upper in CONFIRMAR:
            descricao = aguardando_tarefa.pop(user_id)
            await update.message.reply_text("Executando tarefa autonomamente...")
            mensagens = []
            def callback(msg):
                mensagens.append(msg)
            loop = asyncio.get_event_loop()
            resultados = await loop.run_in_executor(None, lambda: executar_tarefa_autonoma(descricao, callback))
            for msg in mensagens:
                await update.message.reply_text(msg)
            await update.message.reply_text(f"Tarefa concluida!\n\n{chr(10).join(resultados)[:1000]}")
        else:
            aguardando_tarefa.pop(user_id, None)
            await update.message.reply_text("Tarefa cancelada!")
        return

    if user_id in aguardando_senha and aguardando_senha[user_id]:
        if texto.strip() == get_senha():
            liberar_usuario(user_id)
            aguardando_senha.pop(user_id, None)
            aguardando_nome[user_id] = True
            await update.message.reply_text("Acesso liberado! Ola! Eu sou a Veronica! Qual e o seu nome?")
        else:
            await update.message.reply_text("Senha incorreta! Tente novamente:")
        return

    if not is_autorizado(int_id) and not usuario_liberado(user_id):
        aguardando_senha[user_id] = True
        await update.message.reply_text("Acesso Restrito! Digite a senha:")
        return

    if user_id in aguardando_nome and aguardando_nome[user_id]:
        nome = texto.strip()
        atualizar_nome(user_id, nome)
        aguardando_nome.pop(user_id, None)
        await update.message.reply_text(f"Ola, {nome}! Serei sua assistente pessoal! Digite /ajuda para ver todos os comandos!")
        return

    await update.message.reply_text("Pensando...")
    await update.message.reply_text(perguntar_ia(texto, user_id))

async def responder_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(f"Analise:\n\n{descricao}")

async def gerarimg_cmd(update, context):
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
        await update.message.reply_photo(photo=open(caminho, "rb"), caption=f"Imagem gerada com {ia_usada}!")

async def gerarlogo_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /gerarlogo MinhaEmpresa|tecnologia|azul e branco")
        return
    texto = " ".join(context.args)
    partes = texto.split("|")
    nome = partes[0].strip()
    nicho = partes[1].strip() if len(partes) > 1 else "empresa"
    cores = partes[2].strip() if len(partes) > 2 else "azul e branco"
    await update.message.reply_text(f"Gerando logo para {nome}... aguarde!")
    loop = asyncio.get_event_loop()
    caminho, prompt = await loop.run_in_executor(None, lambda: gerar_logo(nome, nicho, cores))
    if caminho.startswith("X") or caminho.startswith("E"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, "rb"), caption=f"Logo gerado para: {nome}")

async def gerarbanner_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /gerarbanner instagram|Marketing Digital")
        return
    texto = " ".join(context.args)
    partes = texto.split("|")
    rede = partes[0].strip() if len(partes) > 1 else "instagram"
    tema = partes[1].strip() if len(partes) > 1 else texto
    await update.message.reply_text(f"Gerando banner para {rede}... aguarde!")
    loop = asyncio.get_event_loop()
    caminho, prompt = await loop.run_in_executor(None, lambda: gerar_banner_post(tema, rede))
    if caminho.startswith("X") or caminho.startswith("E"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, "rb"), caption=f"Banner {rede}: {tema[:100]}")

async def gerarcapa_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not context.args:
        await update.message.reply_text("Use: /gerarcapa Como Ganhar Dinheiro Online")
        return
    titulo = " ".join(context.args)
    await update.message.reply_text(f"Gerando capa para: {titulo}... aguarde!")
    loop = asyncio.get_event_loop()
    caminho, prompt = await loop.run_in_executor(None, lambda: gerar_capa_ebook(titulo))
    if caminho.startswith("X") or caminho.startswith("E"):
        await update.message.reply_text(caminho)
    else:
        await update.message.reply_photo(photo=open(caminho, "rb"), caption=f"Capa ebook: {titulo[:100]}")


async def animefoto_cmd(update, context):
    if not is_autorizado(update.message.from_user.id):
        await update.message.reply_text("Apenas o administrador!")
        return
    if not update.message.photo and not update.message.reply_to_message:
        await update.message.reply_text(
            "Envie uma foto com o comando /animefoto na legenda!\n\n"
            "Ou responda uma foto com /animefoto\n\n"
            "Estilos disponiveis:\n"
            "anime, cartoon, pixar, sketch, watercolor"
        )
        return
    estilo = context.args[0].lower() if context.args else "anime"
    await update.message.reply_text(f"Transformando foto em {estilo}... aguarde!")
    from pathlib import Path
    foto = None
    if update.message.photo:
        foto = update.message.photo[-1]
    elif update.message.reply_to_message and update.message.reply_to_message.photo:
        foto = update.message.reply_to_message.photo[-1]
    if not foto:
        await update.message.reply_text("Nenhuma foto encontrada!")
        return
    arquivo = await foto.get_file()
    caminho_original = str(Path("assets") / f"original_{foto.file_id}.jpg")
    Path("assets").mkdir(exist_ok=True)
    await arquivo.download_to_drive(caminho_original)
    loop = asyncio.get_event_loop()
    caminho_result, ia_usada = await loop.run_in_executor(None, lambda: transformar_foto_anime(caminho_original, estilo))
    if str(caminho_result).startswith("ERRO"):
        await update.message.reply_text(caminho_result)
    else:
        await update.message.reply_photo(
            photo=open(caminho_result, "rb"),
            caption=f"Foto transformada em {estilo} usando {ia_usada}!"
        )

def iniciar_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("status", status_cmd))
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
    app.add_handler(CommandHandler("ialocal", ialocal_cmd))
    app.add_handler(CommandHandler("ialocalstatus", ialocal_status_cmd))
    app.add_handler(CommandHandler("modelos", modelos_cmd))
    app.add_handler(CommandHandler("lembrar", lembrar_cmd))
    app.add_handler(CommandHandler("memorias", memorias_cmd))
    app.add_handler(CommandHandler("esquecertudo", esquecertudo_cmd))
    app.add_handler(CommandHandler("verdescrever", verdescrever_cmd))
    app.add_handler(CommandHandler("veragir", veragir_cmd))
    app.add_handler(CommandHandler("analisarimagem", analisar_imagem_cmd))
    app.add_handler(CommandHandler("mkpost", mkpost_cmd))
    app.add_handler(CommandHandler("mkcalendario", mkcalendario_cmd))
    app.add_handler(CommandHandler("mkestrategia", mkestrategia_cmd))
    app.add_handler(CommandHandler("mkcopy", mkcopy_cmd))
    app.add_handler(CommandHandler("mkconcorrente", mkconcorrente_cmd))
    app.add_handler(CommandHandler("mktendencias", mktendencias_cmd))
    app.add_handler(CommandHandler("mkposts", mkposts_cmd))
    app.add_handler(CommandHandler("gerarimg", gerarimg_cmd))
    app.add_handler(CommandHandler("gerarlogo", gerarlogo_cmd))
    app.add_handler(CommandHandler("gerarbanner", gerarbanner_cmd))
    app.add_handler(CommandHandler("gerarcapa", gerarcapa_cmd))
    app.add_handler(CommandHandler("animefoto", animefoto_cmd))
    app.add_handler(CommandHandler("anime", animefoto_cmd))
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
    app.add_handler(CommandHandler("licenca", licenca_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, responder_foto))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_mensagem))
    print("Veronica esta online!")
    app.run_polling()
