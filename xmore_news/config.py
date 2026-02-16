"""Configuration for Xmore news ingestion."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # dotenv is optional at runtime.
    pass

from egx_symbols import EGX_SYMBOL_DATABASE


@dataclass(frozen=True)
class SourceConfig:
    name: str
    region: str
    rss_urls: tuple[str, ...]
    listing_urls: tuple[str, ...]


USER_AGENT = os.getenv(
    "XMORE_NEWS_USER_AGENT",
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0 Safari/537.36 XmoreNewsBot/1.0"
    ),
)
REQUEST_TIMEOUT_SECONDS = float(os.getenv("XMORE_NEWS_TIMEOUT_SECONDS", "15"))
REQUEST_DELAY_SECONDS = float(os.getenv("XMORE_NEWS_DELAY_SECONDS", "1.2"))
MAX_RETRIES = int(os.getenv("XMORE_NEWS_MAX_RETRIES", "3"))
MAX_ARTICLES_PER_SOURCE = int(os.getenv("XMORE_NEWS_MAX_ARTICLES_PER_SOURCE", "80"))
SCHEDULER_INTERVAL_MINUTES = int(os.getenv("XMORE_NEWS_INTERVAL_MINUTES", "30"))
DB_PATH = os.getenv("XMORE_NEWS_DB_PATH", "xmore_news.db")

ENABLE_ARTICLE_BODY_FETCH = os.getenv("XMORE_NEWS_FETCH_FULL_TEXT", "1").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ENABLE_TRANSLATION = os.getenv("XMORE_NEWS_TRANSLATE_AR", "0").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

REUTERS_SOURCE = SourceConfig(
    name="Reuters",
    region="global",
    rss_urls=(
        # Legacy Reuters feeds can be unreliable in some regions.
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/worldNews",
        # Source-specific Google News RSS fallback for Reuters.
        "https://news.google.com/rss/search?q=site:reuters.com+business+OR+markets&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=site:reuters.com+egypt+market+OR+EGX&hl=en-US&gl=US&ceid=US:en",
    ),
    listing_urls=(
        "https://www.reuters.com/world/",
        "https://www.reuters.com/business/",
        "https://www.reuters.com/markets/",
    ),
)

ALARABIYA_SOURCE = SourceConfig(
    name="Al Arabiya Business",
    region="regional",
    rss_urls=(
        # Official endpoints can be blocked by robots in some environments.
        "https://english.alarabiya.net/rss",
        # Source-specific Google News RSS fallbacks for both EN + AR coverage.
        "https://news.google.com/rss/search?q=site:english.alarabiya.net+business&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=site:alarabiya.net+%D8%A3%D8%B3%D9%88%D8%A7%D9%82&hl=ar&gl=EG&ceid=EG:ar",
    ),
    listing_urls=(
        "https://english.alarabiya.net/business",
        "https://www.alarabiya.net/aswaq",
    ),
)

EGYPT_LOCAL_SOURCES: tuple[SourceConfig, ...] = (
    SourceConfig(
        name="Enterprise.press",
        region="egypt",
        rss_urls=("https://enterprise.press/feed/",),
        listing_urls=("https://enterprise.press/",),
    ),
    SourceConfig(
        name="Daily News Egypt",
        region="egypt",
        rss_urls=("https://dailynewsegypt.com/feed/",),
        listing_urls=("https://dailynewsegypt.com/category/business/",),
    ),
    SourceConfig(
        name="Egypt Today",
        region="egypt",
        rss_urls=("https://www.egypttoday.com/RSS/15",),
        listing_urls=("https://www.egypttoday.com/Section/3/Business",),
    ),
    SourceConfig(
        name="Mubasher",
        region="egypt",
        rss_urls=(
            "http://feeds.mubasher.info/en/EGX/news",
            "http://feeds.mubasher.info/ar/EGX/news",
        ),
        listing_urls=("https://www.mubasher.info/countries/eg/news",),
    ),
    SourceConfig(
        name="Zawya",
        region="egypt",
        rss_urls=(),
        listing_urls=("https://www.zawya.com/en/markets/equities",),
    ),
)

SECTOR_KEYWORDS: tuple[str, ...] = (
    "banking",
    "banks",
    "real estate",
    "construction",
    "cement",
    "energy",
    "oil",
    "gas",
    "petrochemicals",
    "telecom",
    "healthcare",
    "pharma",
    "industrial",
    "shipping",
    "logistics",
    "fertilizer",
    "tourism",
    "consumer",
    "financial services",
    "fintech",
    "equities",
    "bonds",
    "central bank",
    "interest rate",
    "inflation",
    "currency",
    "suez canal",
)

MACRO_KEYWORDS: tuple[str, ...] = (
    "inflation",
    "interest rates",
    "cbe",
    "central bank of egypt",
    "currency devaluation",
    "usd/egp",
    "fiscal deficit",
    "subsidy",
    "imf",
    "earnings",
    "dividend",
)


def get_egx_symbols() -> list[str]:
    """Return symbols in ticker and Yahoo-style formats."""
    symbols: list[str] = []
    for ticker, stock in EGX_SYMBOL_DATABASE.items():
        symbols.append(ticker.upper())
        symbols.append(stock.yahoo.upper())
    return sorted(set(symbols))


def iter_source_names() -> Iterable[str]:
    yield REUTERS_SOURCE.name
    yield ALARABIYA_SOURCE.name
    for source in EGYPT_LOCAL_SOURCES:
        yield source.name
