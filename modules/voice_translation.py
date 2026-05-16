import json
import os
import uuid
from pathlib import Path

from config import ASSETS_DIR, DATA_DIR

SESSIONS_FILE = DATA_DIR / "translation_sessions.json"
VOICE_DIR = ASSETS_DIR / "voice_replies"
DEFAULT_TARGET_LANG = os.getenv("DEFAULT_TRANSLATION_LANG", "pt").lower()
TRANSLATION_MODEL = os.getenv("TRANSLATION_MODEL", "llama-3.3-70b-versatile")

SUPPORTED_TTS_LANGS = {
    "pt": "pt",
    "en": "en",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "it": "it",
}


def _load_sessions() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if not SESSIONS_FILE.exists():
        return {}
    try:
        return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_sessions(sessions: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SESSIONS_FILE.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")


def get_translation_session(user_id: str) -> dict:
    sessions = _load_sessions()
    session = sessions.get(user_id, {})
    return {
        "enabled": bool(session.get("enabled", False)),
        "target_lang": session.get("target_lang", DEFAULT_TARGET_LANG).lower(),
    }


def set_translation_mode(user_id: str, enabled: bool) -> dict:
    sessions = _load_sessions()
    session = get_translation_session(user_id)
    session["enabled"] = enabled
    sessions[user_id] = session
    _save_sessions(sessions)
    return session


def set_target_language(user_id: str, language: str) -> dict:
    language = (language or DEFAULT_TARGET_LANG).lower().strip()
    if language not in SUPPORTED_TTS_LANGS:
        raise ValueError("Idioma nao suportado para audio. Use: pt, en, es, fr, de ou it.")
    sessions = _load_sessions()
    session = get_translation_session(user_id)
    session["target_lang"] = language
    sessions[user_id] = session
    _save_sessions(sessions)
    return session


def detect_language(text: str) -> str:
    if not text.strip():
        return "desconhecido"
    try:
        from langdetect import detect
        return detect(text)
    except Exception:
        return "desconhecido"


def transcribe_audio(audio_path: str) -> str:
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada para transcricao.")
    client = Groq(api_key=api_key)
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(Path(audio_path).name, audio_file),
            model="whisper-large-v3",
            response_format="json",
        )
    if isinstance(transcription, dict):
        return transcription.get("text", "")
    return getattr(transcription, "text", "")


def translate_text(text: str, target_lang: str = DEFAULT_TARGET_LANG) -> str:
    target_lang = (target_lang or DEFAULT_TARGET_LANG).lower()
    source_lang = detect_language(text)
    if source_lang == target_lang:
        return text
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada para traducao.")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=TRANSLATION_MODEL,
        messages=[
            {"role": "system", "content": "Voce e um tradutor profissional. Traduza fielmente para o idioma destino. Responda somente com a traducao, sem comentarios extras."},
            {"role": "user", "content": f"Idioma destino: {target_lang}\nTexto:\n{text}"},
        ],
        temperature=0.1,
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()


def text_to_speech(text: str, language: str = DEFAULT_TARGET_LANG) -> str:
    from gtts import gTTS
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    tts_lang = SUPPORTED_TTS_LANGS.get((language or DEFAULT_TARGET_LANG).lower(), "pt")
    output_path = VOICE_DIR / f"resposta_{uuid.uuid4().hex}.mp3"
    gTTS(text=text[:4500], lang=tts_lang).save(str(output_path))
    return str(output_path)


def translate_audio(audio_path: str, target_lang: str = DEFAULT_TARGET_LANG) -> dict:
    original = transcribe_audio(audio_path)
    detected = detect_language(original)
    translated = translate_text(original, target_lang)
    audio_reply = text_to_speech(translated, target_lang)
    return {
        "original": original,
        "detected_lang": detected,
        "target_lang": target_lang,
        "translated": translated,
        "audio_reply": audio_reply,
    }
