"""Normalization and entity mention extraction for news articles."""

from __future__ import annotations

import hashlib
import html
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from bs4 import BeautifulSoup

from xmore_news import config
from xmore_news.sources.common import fetch_url

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def normalize_article(raw_article: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize article shape and values.

    Returns:
        Dict with required schema:
        title, content, published_at, source, url, mentioned_symbols, region
    """
    title = _clean_text(raw_article.get("title", ""))
    url = str(raw_article.get("url", "")).strip()
    source = _clean_text(raw_article.get("source", "Unknown"))
    region = str(raw_article.get("region", "global")).strip().lower() or "global"

    content_raw = raw_article.get("content", "")
    content = _clean_text(content_raw)
    if not content and config.ENABLE_ARTICLE_BODY_FETCH and url:
        try:
            fetched = extract_article_body(url)
            content = _clean_text(fetched)
        except Exception as exc:
            logger.warning("Body extraction failed for %s: %s", url, exc)

    published_iso = normalize_datetime(raw_article.get("published_at"))

    text_for_mentions = f"{title}\n{content}"
    mentioned_symbols = extract_company_mentions(text_for_mentions, config.get_egx_symbols())
    sector_keywords = extract_sector_keywords(text_for_mentions)
    language = detect_language(text_for_mentions)

    return {
        "title": title,
        "content": content,
        "published_at": published_iso,
        "source": source,
        "url": url,
        "mentioned_symbols": mentioned_symbols,
        "region": region if region in {"global", "regional", "egypt"} else "global",
        "sector_keywords": sector_keywords,
        "language": language,
        "url_hash": hashlib.sha256(url.encode("utf-8")).hexdigest() if url else "",
    }


def extract_company_mentions(text: str, symbols: list[str]) -> list[str]:
    """Extract EGX symbol mentions from title/content text."""
    if not text:
        return []

    text_upper = text.upper()
    matches: set[str] = set()
    for symbol in symbols:
        clean_symbol = symbol.upper().strip()
        base = clean_symbol.replace(".CA", "")
        if not base:
            continue
        if re.search(rf"\b{re.escape(base)}\b", text_upper):
            matches.add(base)
            continue
        if clean_symbol.endswith(".CA") and re.search(rf"\b{re.escape(clean_symbol)}\b", text_upper):
            matches.add(base)

    if re.search(r"\bEGX\s*30\b|\bEGX30\b|البورصة المصرية", text, flags=re.IGNORECASE):
        matches.add("EGX30")

    return sorted(matches)


def extract_sector_keywords(text: str) -> list[str]:
    """Detect configured sector/macro keywords in text."""
    text_lower = text.lower()
    found = {kw for kw in (*config.SECTOR_KEYWORDS, *config.MACRO_KEYWORDS) if kw in text_lower}
    return sorted(found)


def normalize_datetime(value: Any) -> str:
    """Normalize article datetime to UTC ISO8601."""
    if value is None:
        return datetime.now(timezone.utc).isoformat()

    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()

    raw = str(value).strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()

    for attempt in (
        lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")),
        parsedate_to_datetime,
    ):
        try:
            dt = attempt(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            continue

    return datetime.now(timezone.utc).isoformat()


def detect_language(text: str) -> str:
    """Detect EN/AR language label."""
    if not text:
        return "EN"
    try:
        from langdetect import detect  # type: ignore

        lang = detect(text)
        return "AR" if lang == "ar" else "EN"
    except Exception:
        ar = len(_ARABIC_RE.findall(text))
        return "AR" if ar > max(10, len(text) // 10) else "EN"


def extract_article_body(url: str) -> str:
    """Try newspaper3k first, fallback to generic paragraph extraction."""
    # Optional rich extractor.
    try:
        from newspaper import Article  # type: ignore

        article = Article(url)
        article.download()
        article.parse()
        body = article.text.strip()
        if body:
            return body
    except Exception:
        pass

    html_text = fetch_url(url)
    soup = BeautifulSoup(html_text, "html.parser")
    paragraph_text = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    long_paragraphs = [p for p in paragraph_text if len(p) > 50]
    return "\n".join(long_paragraphs)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = html.unescape(text)
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(" ")
    text = _HTML_TAG_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

