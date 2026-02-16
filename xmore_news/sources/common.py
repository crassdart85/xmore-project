"""Shared HTTP/RSS scraping helpers with compliance controls."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import feedparser
import requests
from bs4 import BeautifulSoup

from xmore_news import config

logger = logging.getLogger(__name__)


@dataclass
class RawArticle:
    title: str
    content: str
    published_at: str
    source: str
    url: str
    region: str

    def as_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "content": self.content,
            "published_at": self.published_at,
            "source": self.source,
            "url": self.url,
            "region": self.region,
        }


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT, "Accept-Language": "en-US,en;q=0.9,ar;q=0.8"})
    return session


SESSION = _build_session()


@lru_cache(maxsize=128)
def _robot_parser_for(base_url: str) -> RobotFileParser:
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    try:
        parser.set_url(robots_url)
        parser.read()
    except Exception as exc:
        logger.warning("Failed reading robots.txt for %s: %s", base_url, exc)
    return parser


def can_fetch_url(url: str, user_agent: str | None = None) -> bool:
    """Return whether robots.txt allows this URL."""
    ua = user_agent or config.USER_AGENT
    parser = _robot_parser_for(url)
    try:
        return parser.can_fetch(ua, url)
    except Exception:
        return False


def fetch_url(url: str, *, allow_redirects: bool = True) -> str:
    """Fetch URL with retries and exponential backoff."""
    if not can_fetch_url(url):
        raise PermissionError(f"Blocked by robots.txt: {url}")

    delay = config.REQUEST_DELAY_SECONDS
    last_exc: Exception | None = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            response = SESSION.get(
                url,
                timeout=config.REQUEST_TIMEOUT_SECONDS,
                allow_redirects=allow_redirects,
            )
            response.raise_for_status()
            time.sleep(config.REQUEST_DELAY_SECONDS)
            return response.text
        except Exception as exc:
            last_exc = exc
            logger.warning("Request failed (%s/%s) for %s: %s", attempt, config.MAX_RETRIES, url, exc)
            if attempt < config.MAX_RETRIES:
                time.sleep(delay)
                delay *= 2

    raise RuntimeError(f"Failed fetching {url}") from last_exc


def parse_rss(url: str, source_name: str, region: str) -> list[dict[str, str]]:
    """Read RSS feed and return normalized raw article dictionaries."""
    if not can_fetch_url(url):
        logger.warning("Skipping RSS (robots.txt): %s", url)
        return []

    feed = feedparser.parse(url, request_headers={"User-Agent": config.USER_AGENT})
    raw: list[dict[str, str]] = []
    for entry in feed.entries[: config.MAX_ARTICLES_PER_SOURCE]:
        link = entry.get("link", "").strip()
        if not link:
            continue
        published = _entry_published_to_iso(entry)
        article = RawArticle(
            title=entry.get("title", "").strip(),
            content=(entry.get("summary") or entry.get("description") or "").strip(),
            published_at=published,
            source=source_name,
            url=link,
            region=region,
        )
        raw.append(article.as_dict())
    return raw


def scrape_listing_links(url: str, selectors: tuple[str, ...], max_links: int = 60) -> list[str]:
    """Extract candidate article links from listing pages."""
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()

    for selector in selectors:
        for tag in soup.select(selector):
            href = tag.get("href", "").strip()
            if not href:
                continue
            if href.startswith("/"):
                parsed = urlparse(url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            if not href.startswith("http"):
                continue
            if href in seen:
                continue
            seen.add(href)
            links.append(href)
            if len(links) >= max_links:
                return links
    return links


def parse_article_page(url: str, source_name: str, region: str) -> dict[str, str] | None:
    """Attempt generic extraction of article title/body/date from static HTML."""
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = str(og_title["content"]).strip()
    if not title and soup.title:
        title = soup.title.get_text(" ", strip=True)
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else ""
    if not title:
        return None

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    content = "\n".join([p for p in paragraphs if len(p) > 40])

    published = ""
    time_tag = soup.find("time")
    if time_tag:
        published = (time_tag.get("datetime") or time_tag.get_text(" ", strip=True) or "").strip()
    if not published:
        for key in ("article:published_time", "pubdate", "date", "og:updated_time"):
            meta = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
            if meta and meta.get("content"):
                published = str(meta["content"]).strip()
                break
    if not published:
        published = datetime.utcnow().isoformat()

    return RawArticle(
        title=title,
        content=content,
        published_at=published,
        source=source_name,
        url=url,
        region=region,
    ).as_dict()


def _entry_published_to_iso(entry: Any) -> str:
    if getattr(entry, "published_parsed", None):
        dt = datetime(*entry.published_parsed[:6])
        return dt.isoformat()
    if getattr(entry, "updated_parsed", None):
        dt = datetime(*entry.updated_parsed[:6])
        return dt.isoformat()

    for key in ("published", "updated", "pubDate"):
        val = entry.get(key)
        if not val:
            continue
        try:
            return parsedate_to_datetime(val).isoformat()
        except Exception:
            continue
    return datetime.utcnow().isoformat()

