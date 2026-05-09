"""
Utilitarios de seguranca web compartilhados por todos os paineis Flask.
"""
import time
from functools import wraps
from collections import defaultdict
from flask import request, jsonify

# ── Rastreamento de tentativas de login ───────────────────────────────────────
_tentativas: dict = defaultdict(list)
MAX_TENTATIVAS   = 5
JANELA_SEGUNDOS  = 300   # 5 min — janela de contagem
BLOQUEIO_SEGUNDOS = 900  # 15 min — duração do bloqueio


def registrar_falha(ip: str) -> bool:
    """Registra tentativa falha. Retorna True se o IP deve ser bloqueado."""
    agora = time.time()
    _tentativas[ip] = [t for t in _tentativas[ip] if agora - t < BLOQUEIO_SEGUNDOS]
    _tentativas[ip].append(agora)
    return len([t for t in _tentativas[ip] if agora - t < JANELA_SEGUNDOS]) >= MAX_TENTATIVAS


def ip_bloqueado(ip: str) -> bool:
    agora = time.time()
    recentes = [t for t in _tentativas.get(ip, []) if agora - t < BLOQUEIO_SEGUNDOS]
    return len(recentes) >= MAX_TENTATIVAS


def limpar_falhas(ip: str):
    _tentativas.pop(ip, None)


def get_ip() -> str:
    return (request.headers.get('X-Forwarded-For', '') or request.remote_addr or '').split(',')[0].strip()


# ── Rate limiting simples (sem dependência externa) ───────────────────────────
_rate_cache: dict = defaultdict(list)


def checar_rate_limit(ip: str, max_req: int = 60, janela: int = 60) -> bool:
    """Retorna True se o IP excedeu o limite de requisições."""
    agora = time.time()
    _rate_cache[ip] = [t for t in _rate_cache[ip] if agora - t < janela]
    _rate_cache[ip].append(agora)
    return len(_rate_cache[ip]) > max_req


def rate_limit(max_req: int = 60, janela: int = 60):
    """Decorator de rate limiting para rotas Flask."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if checar_rate_limit(get_ip(), max_req, janela):
                return jsonify({'erro': 'Muitas requisicoes. Aguarde um momento.'}), 429
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── Headers de seguranca HTTP ─────────────────────────────────────────────────
def aplicar_headers(response):
    """Adiciona headers de segurança a qualquer resposta Flask."""
    h = response.headers
    h['X-Content-Type-Options']  = 'nosniff'
    h['X-Frame-Options']          = 'SAMEORIGIN'
    h['X-XSS-Protection']         = '1; mode=block'
    h['Referrer-Policy']          = 'strict-origin-when-cross-origin'
    h['Permissions-Policy']       = 'geolocation=(self), camera=(), microphone=()'
    h['Content-Security-Policy']  = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://maps.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
        "https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https:;"
    )
    h['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


def init_seguranca(app):
    """Registra o after_request de headers em qualquer app Flask."""
    app.after_request(aplicar_headers)


# ── Upload seguro ─────────────────────────────────────────────────────────────
from werkzeug.utils import secure_filename as _secure_filename

UPLOAD_TIPOS_IMAGEM = frozenset(['image/jpeg', 'image/png'])
UPLOAD_MAX_BYTES    = 5 * 1024 * 1024  # 5 MB

_MAGIC = {
    b'\xff\xd8\xff':           'image/jpeg',
    b'\x89PNG\r\n\x1a\n':     'image/png',
}


def validar_upload(file_storage, tipos=UPLOAD_TIPOS_IMAGEM, max_bytes=UPLOAD_MAX_BYTES):
    """
    Valida tipo MIME por magic bytes e tamanho máximo.
    Retorna (True, nome_seguro) ou (False, mensagem_erro).
    Nunca confia na extensão ou no Content-Type declarado pelo browser.
    """
    if not file_storage or not file_storage.filename:
        return False, 'Nenhum arquivo enviado.'
    header = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    mime = next((m for sig, m in _MAGIC.items() if header[:len(sig)] == sig), None)
    if mime not in tipos:
        return False, 'Tipo de arquivo não permitido. Envie apenas JPG ou PNG.'
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_bytes:
        return False, f'Arquivo muito grande. Máximo {max_bytes // 1024 // 1024} MB.'
    nome = _secure_filename(file_storage.filename) or 'upload.jpg'
    return True, nome
