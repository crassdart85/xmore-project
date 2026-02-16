"""News source fetchers."""

from .alarabiya_scraper import fetch_alarabiya_news
from .egypt_local_scraper import fetch_egypt_news
from .reuters_scraper import fetch_reuters_news

__all__ = ["fetch_reuters_news", "fetch_alarabiya_news", "fetch_egypt_news"]

