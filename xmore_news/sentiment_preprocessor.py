"""Preprocessing layer for sentiment model consumption."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from xmore_news import config
from xmore_news.parser import detect_language

_BOILERPLATE_PATTERNS = (
    r"\bsubscribe\b",
    r"\bsign up\b",
    r"\bread more\b",
    r"\ball rights reserved\b",
    r"\bclick here\b",
)


def prepare_for_sentiment(article: dict[str, Any], *, translate_ar: bool | None = None) -> dict[str, Any]:
    """
    Prepare article content for sentiment analysis.

    Steps:
    - normalize unicode/encoding
    - remove boilerplate/noise
    - detect language
    - optional AR->EN translation
    - chunk long content
    """
    title = _normalize(article.get("title", ""))
    content = _normalize(article.get("content", ""))
    merged = _strip_boilerplate(f"{title}\n{content}".strip())
    language = detect_language(merged)

    should_translate = config.ENABLE_TRANSLATION if translate_ar is None else translate_ar
    translated_text = merged
    if should_translate and language == "AR":
        translated_text = _translate_ar_to_en(merged)

    chunks = chunk_text(translated_text, chunk_size=2000, overlap=200)

    payload = dict(article)
    payload.update(
        {
            "prepared_text": translated_text,
            "language": language,
            "chunks": chunks,
            "chunk_count": len(chunks),
        }
    )
    return payload


def chunk_text(text: str, *, chunk_size: int = 2000, overlap: int = 200) -> list[str]:
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _normalize(text: str) -> str:
    cleaned = unicodedata.normalize("NFKC", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _strip_boilerplate(text: str) -> str:
    out = text
    for pattern in _BOILERPLATE_PATTERNS:
        out = re.sub(pattern, " ", out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _translate_ar_to_en(text: str) -> str:
    try:
        from deep_translator import GoogleTranslator  # type: ignore

        return GoogleTranslator(source="ar", target="en").translate(text)
    except Exception:
        return text

