"""Configuration for Xmore Event Intelligence pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from egx_symbols import EGX_SYMBOL_DATABASE

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


@dataclass(frozen=True)
class SourceConfig:
    name: str
    rss_urls: tuple[str, ...]
    listing_urls: tuple[str, ...]
    region: str = "egypt"


USER_AGENT: Final[str] = os.getenv(
    "XMORE_EVENT_INTEL_USER_AGENT",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 XmoreEventIntel/1.0"
    ),
)
REQUEST_TIMEOUT_SECONDS: Final[float] = float(os.getenv("XMORE_EVENT_TIMEOUT_SECONDS", "20"))
REQUEST_DELAY_SECONDS: Final[float] = float(os.getenv("XMORE_EVENT_DELAY_SECONDS", "1.2"))
MAX_RETRIES: Final[int] = int(os.getenv("XMORE_EVENT_MAX_RETRIES", "3"))
MAX_ARTICLES_PER_SOURCE: Final[int] = int(os.getenv("XMORE_EVENT_MAX_ARTICLES_PER_SOURCE", "80"))
DEFAULT_SQLITE_DB_PATH: Final[str] = os.getenv("XMORE_EVENT_DB_PATH", "xmore_event_intel.db")
PRICE_DB_PATH: Final[str] = os.getenv("XMORE_EVENT_PRICE_DB_PATH", "stocks.db")

OPENAI_API_ENDPOINT: Final[str] = os.getenv("OPENAI_API_ENDPOINT", "https://api.openai.com/v1/chat/completions")
OPENAI_MODEL: Final[str] = os.getenv("XMORE_EVENT_LLM_MODEL", "gpt-4o-mini")
OPENAI_API_KEY: Final[str | None] = os.getenv("OPENAI_API_KEY")

ENTERPRISE_SOURCE = SourceConfig(
    name="Enterprise",
    rss_urls=("https://enterprise.press/feed/",),
    listing_urls=("https://enterprise.press/",),
)

DAILYNEWS_SOURCE = SourceConfig(
    name="Daily News Egypt",
    rss_urls=("https://dailynewsegypt.com/feed/",),
    listing_urls=("https://dailynewsegypt.com/category/business/",),
)

EGYPTTODAY_SOURCE = SourceConfig(
    name="Egypt Today",
    rss_urls=("https://www.egypttoday.com/RSS/15",),
    listing_urls=("https://www.egypttoday.com/Section/3/Business",),
)

MUBASHER_SOURCE = SourceConfig(
    name="Mubasher Info",
    rss_urls=(
        "http://feeds.mubasher.info/en/EGX/news",
        "http://feeds.mubasher.info/ar/EGX/news",
    ),
    listing_urls=("https://www.mubasher.info/countries/eg/news",),
)

EGX_DISCLOSURES_SOURCE = SourceConfig(
    name="Egyptian Exchange",
    rss_urls=(),
    listing_urls=(
        "https://www.egx.com.eg/ar/DisclosureNews.aspx",
        "https://www.egx.com.eg/en/DisclosureNews.aspx",
    ),
)


def build_symbol_aliases() -> dict[str, str]:
    """Build alias-to-ticker map for deterministic symbol detection."""
    aliases: dict[str, str] = {}
    for ticker, stock in EGX_SYMBOL_DATABASE.items():
        aliases[ticker.upper()] = ticker.upper()
        aliases[stock.yahoo.upper()] = ticker.upper()
        aliases[stock.name_en.upper()] = ticker.upper()
        if stock.name_ar:
            aliases[stock.name_ar.strip().upper()] = ticker.upper()
    return aliases


SYMBOL_ALIASES: Final[dict[str, str]] = build_symbol_aliases()

