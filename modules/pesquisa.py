from duckduckgo_search import DDGS

def pesquisar_web(query: str, max_resultados: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(
                query,
                max_results=max_resultados,
                region="br-pt"
            ))

        if not resultados:
            # Tenta sem região
            with DDGS() as ddgs:
                resultados = list(ddgs.text(query, max_results=max_resultados))

        if not resultados:
            return "Não encontrei resultados para essa pesquisa."

        texto = f"🔍 *Resultados: {query}*\n\n"
        for i, r in enumerate(resultados, 1):
            texto += f"*{i}. {r['title']}*\n"
            texto += f"{r['body'][:200]}...\n"
            texto += f"🔗 {r['href']}\n\n"

        return texto
    except Exception as e:
        return f"Erro ao pesquisar: {e}"

def pesquisar_e_resumir(query: str) -> str:
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(
                query,
                max_results=5,
                region="br-pt"
            ))

        if not resultados:
            with DDGS() as ddgs:
                resultados = list(ddgs.text(query, max_results=5))

        if not resultados:
            return ""

        conteudo = ""
        for r in resultados:
            conteudo += f"Título: {r['title']}\n"
            conteudo += f"Conteúdo: {r['body']}\n\n"

        return conteudo
    except Exception as e:
        return ""

def pesquisar_noticias(query: str, max_resultados: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.news(
                query,
                max_results=max_resultados,
                region="br-pt"
            ))

        if not resultados:
            with DDGS() as ddgs:
                resultados = list(ddgs.news(query, max_results=max_resultados))

        if not resultados:
            return "Não encontrei notícias recentes sobre esse tema."

        texto = f"📰 *Notícias recentes: {query}*\n\n"
        for i, r in enumerate(resultados, 1):
            texto += f"*{i}. {r['title']}*\n"
            texto += f"{r['body'][:200]}...\n"
            texto += f"🔗 {r['url']}\n\n"

        return texto
    except Exception as e:
        return f"Erro ao buscar notícias: {e}"