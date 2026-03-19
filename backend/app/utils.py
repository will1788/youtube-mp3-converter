# backend/app/utils.py
"""
Utilitários para validação e sanitização
"""
import re
from urllib.parse import urlparse, parse_qs
from typing import Optional


def validate_youtube_url(url: Optional[str]) -> bool:
    """
    Valida se a URL é uma URL válida do YouTube.

    Args:
        url: URL para validar

    Returns:
        True se válida, False caso contrário
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()
    if not url:
        return False

    # Padrões aceitos do YouTube
    youtube_patterns = [
        r"^https?://(www\.)?youtube\.com/watch\?.*v=[\w-]{11}",
        r"^https?://youtu\.be/[\w-]{11}",
        r"^https?://m\.youtube\.com/watch\?.*v=[\w-]{11}",
        r"^https?://(www\.)?youtube\.com/embed/[\w-]{11}",
        r"^https?://(www\.)?youtube\.com/v/[\w-]{11}",
    ]

    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True

    return False


def extract_video_id(url: str) -> Optional[str]:
    """
    Extrai o ID do vídeo de uma URL do YouTube.

    Args:
        url: URL do YouTube

    Returns:
        ID do vídeo ou None se não encontrado
    """
    if not url:
        return None

    # URL curta (youtu.be)
    short_match = re.match(r"https?://youtu\.be/([\w-]{11})", url)
    if short_match:
        return short_match.group(1)

    # URL padrão
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc or "youtube" in parsed.netloc:
        # Query parameter v=
        query_params = parse_qs(parsed.query)
        if "v" in query_params:
            return query_params["v"][0][:11]

        # Embed ou v URLs
        path_match = re.match(r"/(embed|v)/([\w-]{11})", parsed.path)
        if path_match:
            return path_match.group(2)

    return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza nome de arquivo removendo caracteres inválidos.

    Args:
        filename: Nome do arquivo original

    Returns:
        Nome sanitizado
    """
    if not filename or not filename.strip():
        return "audio"

    # Remove caracteres inválidos para sistemas de arquivo
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(invalid_chars, "", filename)

    # Remove espaços extras
    sanitized = " ".join(sanitized.split())

    # Trunca se muito longo
    if len(sanitized) > 200:
        sanitized = sanitized[:200]

    # Se ficou vazio, usa nome padrão
    if not sanitized.strip():
        return "audio"

    return sanitized.strip()


def format_duration(seconds: int) -> str:
    """
    Formata duração em segundos para MM:SS ou HH:MM:SS.

    Args:
        seconds: Duração em segundos

    Returns:
        String formatada
    """
    if seconds < 0:
        return "00:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
