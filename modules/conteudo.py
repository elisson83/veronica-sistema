import os
from pathlib import Path
from datetime import datetime
from modules.ai_brain import perguntar_ia
from modules.pesquisa import pesquisar_e_resumir

ASSETS_DIR = Path(__file__).parent.parent / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

def criar_ebook(tema: str, user_id: str = "0") -> str:
    """Cria um e-book completo em PDF sobre um tema"""
    try:
        from fpdf import FPDF

        # Gera o conteúdo com IA
        prompt = f"""
        Crie um e-book completo e profissional sobre: {tema}
        
        O e-book deve ter:
        1. Título atrativo
        2. Introdução envolvente
        3. 5 capítulos com conteúdo rico
        4. Cada capítulo com subtítulos e exemplos práticos
        5. Conclusão motivadora
        6. Dicas bônus
        
        Formate assim:
        TITULO: [título do ebook]
        INTRODUCAO: [texto da introdução]
        CAPITULO 1: [título]
        CONTEUDO 1: [conteúdo detalhado]
        CAPITULO 2: [título]
        CONTEUDO 2: [conteúdo detalhado]
        CAPITULO 3: [título]
        CONTEUDO 3: [conteúdo detalhado]
        CAPITULO 4: [título]
        CONTEUDO 4: [conteúdo detalhado]
        CAPITULO 5: [título]
        CONTEUDO 5: [conteúdo detalhado]
        CONCLUSAO: [texto da conclusão]
        BONUS: [dicas bônus]
        """

        conteudo = perguntar_ia(prompt, user_id)

        # Cria o PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Título
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_fill_color(41, 128, 185)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 20, tema[:50], ln=True, align='C', fill=True)
        pdf.ln(10)

        # Data
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 10, f"Criado por Verônica IA em {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
        pdf.ln(10)

        # Conteúdo
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(0, 0, 0)

        linhas = conteudo.split('\n')
        for linha in linhas:
            linha = linha.strip()
            if not linha:
                pdf.ln(5)
                continue

            if any(linha.startswith(p) for p in ["TITULO:", "CAPITULO", "INTRODUCAO:", "CONCLUSAO:", "BONUS:"]):
                pdf.set_font("Helvetica", "B", 14)
                pdf.set_text_color(41, 128, 185)
                texto = linha.split(":", 1)[-1].strip() if ":" in linha else linha
                pdf.cell(0, 10, texto[:80], ln=True)
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)
            elif any(linha.startswith(p) for p in ["CONTEUDO"]):
                texto = linha.split(":", 1)[-1].strip() if ":" in linha else linha
                pdf.multi_cell(0, 8, texto[:500])
                pdf.ln(3)
            else:
                try:
                    pdf.multi_cell(0, 8, linha[:200])
                except:
                    pass

        # Salva o PDF
        nome_arquivo = f"ebook_{tema[:30].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        caminho = str(ASSETS_DIR / nome_arquivo)
        pdf.output(caminho)

        return caminho

    except Exception as e:
        return f"❌ Erro ao criar e-book: {e}"

def analisar_video_youtube(url: str, user_id: str = "0") -> str:
    """Analisa um vídeo do YouTube e sugere formas de monetização"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        import re

        # Extrai o ID do vídeo
        padrao = r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})'
        match = re.search(padrao, url)
        if not match:
            return "❌ URL do YouTube inválida! Use o formato: https://www.youtube.com/watch?v=XXXXX"

        video_id = match.group(1)

        # Tenta obter a transcrição
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'pt-BR', 'en'])
            texto_video = ' '.join([t['text'] for t in transcript[:50]])
        except:
            texto_video = "Transcrição não disponível para este vídeo."

        # Analisa com IA
        prompt = f"""
        Analise este vídeo do YouTube e crie um relatório completo:
        
        URL: {url}
        Transcrição parcial: {texto_video[:1000]}
        
        Por favor forneça:
        1. 📊 RESUMO DO CONTEÚDO - O que o vídeo aborda
        2. 💰 FORMAS DE MONETIZAÇÃO - Como ganhar dinheiro com este tema
        3. 📝 CONTEÚDO SIMILAR - Ideias para criar conteúdo parecido
        4. 🎯 PÚBLICO-ALVO - Quem se interessa por este tema
        5. 📱 ESTRATÉGIA DE MARKETING - Como divulgar
        6. 🚀 PRÓXIMOS PASSOS - O que fazer para começar
        """

        analise = perguntar_ia(prompt, user_id)
        return analise

    except Exception as e:
        return f"❌ Erro ao analisar vídeo: {e}"

def criar_post_redes_sociais(tema: str, rede: str = "instagram", user_id: str = "0") -> str:
    """Cria posts otimizados para redes sociais"""
    try:
        prompt = f"""
        Crie 3 posts profissionais para {rede} sobre: {tema}
        
        Para cada post inclua:
        - Texto principal envolvente
        - Hashtags relevantes
        - Call to action
        - Emoji estratégicos
        
        Formato:
        POST 1:
        [texto]
        
        POST 2:
        [texto]
        
        POST 3:
        [texto]
        """

        return perguntar_ia(prompt, user_id)

    except Exception as e:
        return f"❌ Erro ao criar posts: {e}"

def criar_script_video(tema: str, duracao: int = 10, user_id: str = "0") -> str:
    """Cria um script completo para vídeo"""
    try:
        prompt = f"""
        Crie um script completo para um vídeo de {duracao} minutos sobre: {tema}
        
        O script deve ter:
        - GANCHO (primeiros 30 segundos) - prender atenção
        - INTRODUÇÃO (1 minuto) - apresentar o tema
        - DESENVOLVIMENTO (principais tópicos)
        - CONCLUSÃO - resumo e call to action
        - DESCRIÇÃO DO VÍDEO para YouTube
        - TAGS para YouTube
        
        Use linguagem natural e envolvente.
        """

        return perguntar_ia(prompt, user_id)

    except Exception as e:
        return f"❌ Erro ao criar script: {e}"