"""
rss/rss_registry.py — Xmore News Ingestion Layer

Registry of official RSS feeds and per-source Google News fallback queries.

Sources without a public RSS feed (S&P, Moody's, Fitch, OPEC) are marked
rss_url=None and handled exclusively via Google News in the router.

Also includes CBE page-monitor sources added per requirements:
  - https://www.cbe.org.eg/en/news-publications/publications
  - https://www.cbe.org.eg/en/news-publications/news
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class RSSSourceDef:
    name: str                           # display label used in Article.source
    rss_url: Optional[str]              # None = Google News only
    google_news_queries: List[str]      # fallback / supplementary queries
    description: str = ""


RSS_SOURCES: dict[str, RSSSourceDef] = {
    # ------------------------------------------------------------------
    # Sources WITH verified public RSS feeds
    # ------------------------------------------------------------------
    "imf": RSSSourceDef(
        name="IMF",
        rss_url="https://www.imf.org/en/News/rss?language=eng",
        google_news_queries=[
            "IMF Egypt loan program review 2025",
            "IMF Egypt Article IV consultation",
        ],
        description="IMF press releases and economic outlooks",
    ),
    "federal_reserve": RSSSourceDef(
        name="Federal Reserve",
        rss_url="https://www.federalreserve.gov/feeds/press_all.xml",
        google_news_queries=[
            "Federal Reserve interest rate decision impact Egypt",
            "Fed rate emerging markets Egypt 2025",
        ],
        description="US Federal Reserve press releases",
    ),
    "world_bank": RSSSourceDef(
        name="World Bank",
        rss_url="https://www.worldbank.org/en/news/rss.xml",
        google_news_queries=[
            "World Bank Egypt loan project financing",
            "World Bank MENA Egypt 2025",
        ],
        description="World Bank news and project updates",
    ),
    "daily_news_egypt": RSSSourceDef(
        name="Daily News Egypt",
        rss_url="https://dailynewsegypt.com/feed/",
        google_news_queries=[
            "Egypt economy business Daily News Egypt",
            "EGX Egypt stock market earnings",
        ],
        description="Egyptian English-language business newspaper",
    ),
    # ------------------------------------------------------------------
    # Sources WITHOUT public RSS (Google News primary)
    # ------------------------------------------------------------------
    "sp_ratings": RSSSourceDef(
        name="S&P Global Ratings",
        rss_url=None,
        google_news_queries=[
            "S&P Global Ratings Egypt sovereign",
            "S&P Egypt credit rating outlook 2025",
        ],
        description="S&P credit rating actions on Egypt",
    ),
    "moodys": RSSSourceDef(
        name="Moodys",
        rss_url=None,
        google_news_queries=[
            "Moodys Egypt rating sovereign debt",
            "Moodys Egypt credit outlook downgrade upgrade",
        ],
        description="Moody's rating actions on Egypt",
    ),
    "fitch": RSSSourceDef(
        name="Fitch Ratings",
        rss_url=None,
        google_news_queries=[
            "Fitch Ratings Egypt sovereign credit",
            "Fitch Egypt outlook stable positive negative",
        ],
        description="Fitch rating actions on Egypt",
    ),
    "opec": RSSSourceDef(
        name="OPEC",
        rss_url=None,
        google_news_queries=[
            "OPEC oil production cut Egypt impact",
            "OPEC+ decision emerging markets Egypt",
        ],
        description="OPEC oil market decisions and their Egypt impact",
    ),
    # ------------------------------------------------------------------
    # CBE (page-monitored + supplementary Google News)
    # ------------------------------------------------------------------
    "cbe": RSSSourceDef(
        name="CBE",
        rss_url=None,
        google_news_queries=[
            "Central Bank Egypt monetary policy interest rate",
            "CBE Egypt inflation currency pound 2025",
        ],
        description="Central Bank of Egypt — monetary policy and publications",
    ),
}
