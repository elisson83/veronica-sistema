import yfinance as yf
from datetime import datetime

def get_cotacao(ticker: str) -> str:
    try:
        ativo = yf.Ticker(ticker)
        hist = ativo.history(period="5d")

        if hist.empty:
            return f"❌ Não encontrei dados para {ticker}. Verifique o código do ativo."

        preco_atual = hist['Close'].iloc[-1]
        preco_anterior = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Open'].iloc[-1]
        maxima = hist['High'].iloc[-1]
        minima = hist['Low'].iloc[-1]
        volume = hist['Volume'].iloc[-1]

        # Corrige zeros
        if maxima == 0:
            maxima = preco_atual
        if minima == 0:
            minima = preco_atual
        if volume == 0:
            volume = hist['Volume'].iloc[-2] if len(hist) > 1 else 0

        variacao = ((preco_atual - preco_anterior) / preco_anterior) * 100
        emoji = "📈" if variacao >= 0 else "📉"

        info = ativo.info
        nome = info.get('longName', ticker)

        return (
            f"{emoji} *{nome} ({ticker.upper()})*\n\n"
            f"• Preço atual: R$ {preco_atual:.2f}\n"
            f"• Variação: {variacao:+.2f}%\n"
            f"• Máxima: R$ {maxima:.2f}\n"
            f"• Mínima: R$ {minima:.2f}\n"
            f"• Volume: {volume:,.0f}\n"
            f"• Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        )
    except Exception as e:
        return f"❌ Erro ao buscar cotação de {ticker}: {e}"

def get_indicadores(ticker: str) -> str:
    try:
        ativo = yf.Ticker(ticker)
        hist = ativo.history(period="3mo")

        if hist.empty:
            return f"❌ Não encontrei dados para {ticker}."

        hist['MM9'] = hist['Close'].rolling(window=9).mean()
        hist['MM21'] = hist['Close'].rolling(window=21).mean()
        hist['MM50'] = hist['Close'].rolling(window=50).mean()

        delta = hist['Close'].diff()
        ganho = delta.where(delta > 0, 0).rolling(window=14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = ganho / perda
        hist['RSI'] = 100 - (100 / (1 + rs))

        preco = hist['Close'].iloc[-1]
        mm9 = hist['MM9'].iloc[-1]
        mm21 = hist['MM21'].iloc[-1]
        mm50 = hist['MM50'].iloc[-1]
        rsi = hist['RSI'].iloc[-1]

        sinal_mm = "🟢 COMPRA" if mm9 > mm21 else "🔴 VENDA"
        sinal_rsi = "🔴 Sobrecomprado" if rsi > 70 else "🟢 Sobrevendido" if rsi < 30 else "🟡 Neutro"

        return (
            f"📊 *Indicadores Técnicos: {ticker.upper()}*\n\n"
            f"💰 Preço atual: R$ {preco:.2f}\n\n"
            f"📈 *Médias Móveis:*\n"
            f"• MM9: R$ {mm9:.2f}\n"
            f"• MM21: R$ {mm21:.2f}\n"
            f"• MM50: R$ {mm50:.2f}\n"
            f"• Sinal MM: {sinal_mm}\n\n"
            f"⚡ *RSI (14):*\n"
            f"• Valor: {rsi:.1f}\n"
            f"• Sinal: {sinal_rsi}\n\n"
            f"⏰ Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        )
    except Exception as e:
        return f"❌ Erro ao calcular indicadores de {ticker}: {e}"

def get_carteira(tickers: list) -> str:
    try:
        texto = "💼 *Sua Carteira:*\n\n"
        for ticker in tickers:
            ativo = yf.Ticker(ticker)
            hist = ativo.history(period="5d")
            if not hist.empty:
                preco = hist['Close'].iloc[-1]
                preco_anterior = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[0]
                variacao = ((preco - preco_anterior) / preco_anterior) * 100
                emoji = "📈" if variacao >= 0 else "📉"
                texto += f"{emoji} *{ticker.upper()}*: R$ {preco:.2f} ({variacao:+.2f}%)\n"
        return texto
    except Exception as e:
        return f"❌ Erro ao buscar carteira: {e}"

def get_mercado_geral() -> str:
    try:
        ativos = {
            "^BVSP": "Ibovespa",
            "BRL=X": "Dólar",
            "BTC-USD": "Bitcoin",
            "GC=F": "Ouro"
        }

        texto = "🌍 *Mercado Geral:*\n\n"
        for ticker, nome in ativos.items():
            ativo = yf.Ticker(ticker)
            hist = ativo.history(period="5d")
            if not hist.empty:
                preco = hist['Close'].iloc[-1]
                preco_anterior = hist['Close'].iloc[-2] if len(hist) > 1 else hist['Close'].iloc[0]
                variacao = ((preco - preco_anterior) / preco_anterior) * 100
                emoji = "📈" if variacao >= 0 else "📉"
                texto += f"{emoji} *{nome}*: {preco:,.2f} ({variacao:+.2f}%)\n"

        texto += f"\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        return texto
    except Exception as e:
        return f"❌ Erro ao buscar mercado: {e}"