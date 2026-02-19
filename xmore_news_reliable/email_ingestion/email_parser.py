"""
email_ingestion/email_parser.py — Xmore Reliable News Acquisition Layer

Parses raw Gmail message objects into the unified article schema:

  {
    title, content, published_at, source,
    ingestion_method, detected_symbols, language, url, sender, message_id
  }

Responsibilities:
  - Strip HTML boilerplate via BeautifulSoup
  - Remove email signature blocks
  - Normalise whitespace and encoding
  - Detect Arabic vs English
  - Tag EGX ticker symbols
  - Parse RFC 2822 / ISO 8601 timestamps
"""

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from config import EGX_TICKERS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
_ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]"
)


def detect_language(text: str) -> str:
    """Return 'ar' if >15 % of non-whitespace chars are Arabic, else 'en'."""
    stripped = text.replace(" ", "").replace("\n", "")
    if not stripped:
        return "en"
    arabic_count = len(_ARABIC_RE.findall(stripped))
    return "ar" if arabic_count / len(stripped) > 0.15 else "en"


# ---------------------------------------------------------------------------
# Ticker detection
# ---------------------------------------------------------------------------
def detect_symbols(text: str) -> List[str]:
    """Return EGX tickers mentioned as whole words (case-insensitive)."""
    upper = text.upper()
    found = [sym for sym in EGX_TICKERS if re.search(rf"\b{re.escape(sym)}\b", upper)]
    return sorted(set(found))


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------
_BOILERPLATE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "img"]


def strip_html(html: str) -> str:
    """Convert HTML email body to clean plain text."""
    try:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(_BOILERPLATE_TAGS):
            tag.decompose()
        lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
        return "\n".join(line for line in lines if line)
    except Exception as exc:
        logger.warning("HTML stripping failed: %s", exc)
        # Fallback: crude regex strip
        return re.sub(r"<[^>]+>", " ", html).strip()


# ---------------------------------------------------------------------------
# Signature removal
# ---------------------------------------------------------------------------
_SIGNATURE_ANCHORS = re.compile(
    r"(?im)^[\-_]{2,}\s*$"                                  # -- or ___
    r"|^(best regards|sincerely|regards|thanks|thank you"
    r"|sent from|get outlook|disclaimer|confidentiality"
    r"|unsubscribe|manage preferences"
    r"|إخلاء مسؤولية|تحذير|مرسل من)"
)


def remove_signature(text: str) -> str:
    """Truncate text at the first line that looks like a signature anchor."""
    lines = text.splitlines()
    cutoff = len(lines)
    for i, line in enumerate(lines):
        if _SIGNATURE_ANCHORS.search(line):
            cutoff = i
            break
    return "\n".join(lines[:cutoff]).strip()


# ---------------------------------------------------------------------------
# Whitespace normalisation
# ---------------------------------------------------------------------------
def normalise_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------
def parse_email_date(message: Dict[str, Any]) -> str:
    """
    Try to parse a UTC ISO 8601 timestamp from the message.
    Priority: Date header → internalDate → now().
    """
    # 1. Date header (RFC 2822)
    for h in message.get("payload", {}).get("headers", []):
        if h["name"].lower() == "date":
            try:
                dt = parsedate_to_datetime(h["value"])
                return dt.astimezone(timezone.utc).isoformat()
            except Exception:
                pass

    # 2. Gmail internalDate (milliseconds epoch)
    ts_ms = message.get("internalDate")
    if ts_ms:
        try:
            ts = int(ts_ms) / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except Exception:
            pass

    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Public parser
# ---------------------------------------------------------------------------

class EmailParser:
    """
    Converts a raw Gmail message dict (from GmailClient) into the unified
    article schema.  Requires text_body / html_body pre-extracted by GmailClient.
    """

    def parse(
        self,
        message: Dict[str, Any],
        source: str,
        text_body: str,
        html_body: str,
    ) -> Dict[str, Any]:
        # --- Subject → title
        subject = self._get_header(message, "subject") or "(no subject)"
        title = re.sub(r"\s+", " ", subject).strip()

        # --- Body selection: prefer plain text, fall back to HTML
        if text_body.strip():
            raw_content = text_body
        elif html_body.strip():
            raw_content = strip_html(html_body)
        else:
            raw_content = ""

        content = remove_signature(raw_content)
        content = normalise_whitespace(content)

        # Truncate very long emails (keep first 30 000 chars)
        if len(content) > 30_000:
            content = content[:30_000] + "\n[... truncated]"

        # --- Metadata
        published_at = parse_email_date(message)
        sender = self._get_header(message, "from")
        full_text = f"{title} {content}"
        language = detect_language(full_text)
        symbols = detect_symbols(full_text)

        return {
            "title": title,
            "content": content,
            "published_at": published_at,
            "source": source,
            "ingestion_method": "email",
            "detected_symbols": symbols,
            "language": language,
            "url": None,
            "sender": sender,
            "message_id": message.get("id"),
        }

    @staticmethod
    def _get_header(message: Dict[str, Any], name: str) -> str:
        for h in message.get("payload", {}).get("headers", []):
            if h["name"].lower() == name.lower():
                return h["value"]
        return ""
