"""
rss_ingestion/rss_parser.py — Xmore Reliable News Acquisition Layer

Converts raw RSS entry dicts (from GoogleNewsClient) into the unified
article schema shared across all ingestion paths:

  {
    title, content, published_at, source,
    ingestion_method, detected_symbols, language, url
  }
"""

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List

from email_ingestion.email_parser import detect_language, detect_symbols

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Date normalisation
# ---------------------------------------------------------------------------

def _parse_rss_date(raw: str) -> str:
    """
    Try RFC 2822 → ISO 8601 → now() in UTC.
    Always returns a UTC ISO 8601 string.
    """
    if not raw:
        return datetime.now(tz=timezone.utc).isoformat()

    # RFC 2822 (standard RSS/Atom)
    try:
        dt = parsedate_to_datetime(raw)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass

    # ISO 8601 / partial variants
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw[:19], fmt[:len(raw)])
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass

    logger.debug("Could not parse RSS date '%s', using now()", raw)
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Inline HTML cleaning (Google News often injects <a> / <b> in summaries)
# ---------------------------------------------------------------------------

def _strip_inline_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class RSSParser:
    """
    Stateless transformer: list of raw RSS entry dicts → list of article dicts.
    """

    def parse(self, entries: List[Dict[str, str]], source: str) -> List[Dict[str, Any]]:
        """
        Convert a list of raw feed entries (from GoogleNewsClient.fetch) into
        normalised article dicts ready for storage.save_article().
        """
        articles: List[Dict[str, Any]] = []

        for entry in entries:
            title = entry.get("title", "").strip()
            if not title:
                logger.debug("Skipping RSS entry with empty title")
                continue

            summary = _strip_inline_html(entry.get("summary", ""))
            link = entry.get("link", "")
            published_at = _parse_rss_date(entry.get("published", ""))
            source_tag = entry.get("source_tag", "Google News")

            # Content = summary if available, else fall back to title alone
            content = summary if summary else title

            # Truncate excessively long summaries
            if len(content) > 5_000:
                content = content[:5_000] + " [...]"

            full_text = f"{title} {content}"
            language = detect_language(full_text)
            symbols = detect_symbols(full_text)

            articles.append({
                "title": title,
                "content": content,
                "published_at": published_at,
                "source": source,
                "ingestion_method": "rss",
                "detected_symbols": symbols,
                "language": language,
                "url": link,
                "source_tag": source_tag,
            })

        logger.debug("RSSParser: %d → %d articles for source '%s'",
                     len(entries), len(articles), source)
        return articles
