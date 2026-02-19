"""
utils.py — Xmore News Ingestion Layer
Shared utilities: retry decorator, language detection, HTML stripping,
date normalisation, text cleaning, EGX ticker detection.
"""

from __future__ import annotations

import functools
import logging
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Exponential-backoff retry decorator.

    Args:
        max_attempts : total attempts (not just retries)
        delay        : initial sleep between attempts in seconds
        backoff      : multiplier applied to delay after each failure
        exceptions   : exception types to catch and retry on
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempt(s): %s",
                            func.__name__, max_attempts, exc,
                        )
                        raise
                    logger.warning(
                        "%s attempt %d/%d failed: %s — retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper  # type: ignore
    return decorator


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]"
)


def detect_language(text: str) -> str:
    """
    Return 'ar' if more than 15 % of non-whitespace characters are Arabic,
    otherwise 'en'.
    """
    stripped = re.sub(r"\s", "", text)
    if not stripped:
        return "en"
    arabic = len(_ARABIC_RE.findall(stripped))
    return "ar" if arabic / len(stripped) > 0.15 else "en"


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "button"]


def strip_html(html: str) -> str:
    """
    Convert HTML to plain text, stripping navigation, scripts and layout tags.
    Falls back to a crude regex strip on BeautifulSoup parse failure.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(_NOISE_TAGS):
            tag.decompose()
        lines = [ln.strip() for ln in soup.get_text(separator="\n").splitlines()]
        return "\n".join(ln for ln in lines if ln)
    except Exception as exc:
        logger.debug("HTML strip fallback (%s)", exc)
        return re.sub(r"<[^>]+>", " ", html).strip()


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Normalise line endings, collapse whitespace runs."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

def parse_date(raw: str) -> str:
    """
    Parse any common date string to UTC ISO 8601.
    Tries RFC 2822 → ISO 8601 variants → falls back to now().
    """
    if not raw:
        return _now_iso()

    # RFC 2822 (standard RSS / email)
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc).isoformat()
    except Exception:
        pass

    # ISO 8601 and common variants
    formats = (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%B %d, %Y",   # "January 15, 2025"
        "%d %B %Y",    # "15 January 2025"
    )
    clean = raw.strip()
    for fmt in formats:
        try:
            length = len(datetime.now().strftime(fmt))
            dt = datetime.strptime(clean[:length], fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass

    logger.debug("Could not parse date '%s' — using now()", raw)
    return _now_iso()


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# EGX ticker detection
# ---------------------------------------------------------------------------

_EGX_TICKERS = [
    "COMI", "EKHW", "EGTS", "HRHO", "OCDI", "PHDC", "CLHO", "GBCO", "FWRY",
    "SWDY", "TELE", "MFPC", "MNHD", "ORWE", "SPMD", "TMGH", "CIEB", "ADIB",
    "DCRC", "ISPH", "AMOC", "SOCO", "BICO", "DICE", "RAYA", "JUFO", "EKHO",
    "INCO", "AMER", "MCQE", "CIRA", "SUGR", "HELI", "LCSW", "EFIC",
]


def detect_tickers(text: str) -> List[str]:
    """Return EGX ticker symbols found as whole words in text."""
    upper = text.upper()
    return sorted({sym for sym in _EGX_TICKERS if re.search(rf"\b{re.escape(sym)}\b", upper)})
