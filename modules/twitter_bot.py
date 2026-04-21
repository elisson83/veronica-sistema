import os
import tweepy
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

def get_cliente():
    try:
        client = tweepy.Client(
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_CONSUMER_KEY"),
            consumer_secret=os.getenv("TWITTER_CONSUMER_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )
        return client
    except Exception as e:
        return None

def postar_tweet(texto: str) -> str:
    try:
        client = get_cliente()
        if not client:
            return "❌ Twitter não configurado!"
        if len(texto) > 280:
            texto = texto[:277] + "..."
        response = client.create_tweet(text=texto)
        tweet_id = response.data["id"]
        return f"✅ Tweet postado!\n🔗 https://x.com/i/web/status/{tweet_id}"
    except Exception as e:
        return f"❌ Erro ao postar: {e}"

def get_meu_perfil() -> str:
    try:
        client = get_cliente()
        if not client:
            return "❌ Twitter não configurado!"
        me = client.get_me(user_fields=["public_metrics", "description"])
        user = me.data
        metrics = user.public_metrics
        return (
            f"🐦 *Perfil Twitter:*\n\n"
            f"• Nome: {user.name}\n"
            f"• @{user.username}\n"
            f"• Seguidores: {metrics['followers_count']}\n"
            f"• Seguindo: {metrics['following_count']}\n"
            f"• Tweets: {metrics['tweet_count']}\n"
        )
    except Exception as e:
        return f"❌ Erro: {e}"

def get_meus_tweets(quantidade: int = 5) -> str:
    try:
        client = get_cliente()
        if not client:
            return "❌ Twitter não configurado!"
        me = client.get_me()
        tweets = client.get_users_tweets(
            me.data.id,
            max_results=quantidade,
            tweet_fields=["public_metrics", "created_at"]
        )
        if not tweets.data:
            return "📭 Nenhum tweet encontrado."
        resultado = f"🐦 *Seus últimos {quantidade} tweets:*\n\n"
        for tweet in tweets.data:
            metrics = tweet.public_metrics
            resultado += f"📝 {tweet.text[:80]}...\n"
            resultado += f"❤️ {metrics['like_count']} | 🔁 {metrics['retweet_count']}\n\n"
        return resultado
    except Exception as e:
        return f"❌ Erro: {e}"

def deletar_tweet(tweet_id: str) -> str:
    try:
        client = get_cliente()
        if not client:
            return "❌ Twitter não configurado!"
        client.delete_tweet(tweet_id)
        return f"✅ Tweet {tweet_id} deletado!"
    except Exception as e:
        return f"❌ Erro ao deletar: {e}"

def testar_conexao() -> str:
    try:
        client = get_cliente()
        if not client:
            return "❌ Chaves não configuradas!"
        me = client.get_me()
        return f"✅ Twitter conectado! Conta: @{me.data.username}"
    except Exception as e:
        return f"❌ Erro de conexão: {e}"