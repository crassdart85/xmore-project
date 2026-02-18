"""Shared scraping helpers for xmore_event_intel sources."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from functools import lru_cache
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import feedparser
import requests
from bs4 import BeautifulSoup

from xmore_event_intel import config

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": config.USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    }
)


@lru_cache(maxsize=128)
def _robot_parser(url: str) -> RobotFileParser:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    try:
        parser.set_url(robots_url)
        parser.read()
    except Exception as exc:
        logger.warning("robots.txt read failure for %s: %s", robots_url, exc)
    return parser


def can_fetch(url: str) -> bool:
    parser = _robot_parser(url)
    try:
        return parser.can_fetch(config.USER_AGENT, url)
    except Exception:
        return False


def fetch_url(url: str) -> str:
    if not can_fetch(url):
        raise PermissionError(f"Blocked by robots.txt: {url}")
    delay = config.REQUEST_DELAY_SECONDS
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            response = _SESSION.get(url, timeout=config.REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            time.sleep(config.REQUEST_DELAY_SECONDS)
            return response.text
        except Exception:
            if attempt >= config.MAX_RETRIES:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"Fetch failed for {url}")


def parse_rss(rss_url: str, source_name: str) -> list[dict]:
    if not can_fetch(rss_url):
        logger.warning("RSS skipped by robots: %s", rss_url)
        return []
    feed = feedparser.parse(rss_url, request_headers={"User-Agent": config.USER_AGENT})
    out: list[dict] = []
    for entry in feed.entries[: config.MAX_ARTICLES_PER_SOURCE]:
        url = str(entry.get("link", "")).strip()
        if not url:
            continue
        published_at = _rss_ts_to_iso(entry)
        title = str(entry.get("title", "")).strip()
        content = str(entry.get("summary") or entry.get("description") or "").strip()
        out.append(
            {
                "title": title,
                "content": content,
                "published_at": published_at,
                "source": source_name,
                "url": url,
            }
        )
    return out


def enrich_article_from_url(article: dict) -> dict:
    url = str(article.get("url", "")).strip()
    if not url:
        return article
    try:
        html = fetch_url(url)
    except Exception:
        return article

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    body = "\n".join([p for p in paragraphs if len(p) > 40])
    if body and len(body) > len(str(article.get("content", ""))):
        article["content"] = body
    article["raw_html"] = html
    if not article.get("published_at"):
        article["published_at"] = _extract_page_datetime(soup) or datetime.utcnow().isoformat()
    return article


def scrape_listing(url: str, source_name: str) -> list[dict]:
    html = fetch_url(url)
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for selector in (
        "article a",
        "h1 a",
        "h2 a",
        "h3 a",
        "a[href*='/news/']",
        "a[href*='/business/']",
        "a[href*='/markets/']",
    ):
        for tag in soup.select(selector):
            href = str(tag.get("href", "")).strip()
            if not href:
                continue
            if href.startswith("/"):
                parsed = urlparse(url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"
            if not href.startswith("http") or href in seen:
                continue
            seen.add(href)
            links.append(href)
            if len(links) >= config.MAX_ARTICLES_PER_SOURCE:
                break
        if len(links) >= config.MAX_ARTICLES_PER_SOURCE:
            break

    out: list[dict] = []
    for link in links:
        if not can_fetch(link):
            continue
        try:
            page_html = fetch_url(link)
            page_soup = BeautifulSoup(page_html, "html.parser")
            title = _extract_title(page_soup)
            if not title:
                continue
            paragraphs = [p.get_text(" ", strip=True) for p in page_soup.find_all("p")]
            content = "\n".join([p for p in paragraphs if len(p) > 40])
            out.append(
                {
                    "title": title,
                    "content": content,
                    "published_at": _extract_page_datetime(page_soup) or datetime.utcnow().isoformat(),
                    "source": source_name,
                    "url": link,
                    "raw_html": page_html,
                }
            )
        except Exception as exc:
            logger.debug("Listing parse failed for %s: %s", link, exc)
    return out


def detect_symbols(text: str) -> list[str]:
    hay = re.sub(r"\s+", " ", text.upper()).strip()
    found: set[str] = set()
    for alias, ticker in config.SYMBOL_ALIASES.items():
        if alias and alias in hay:
            found.add(ticker)
    return sorted(found)


def normalize_article(item: dict, source: str) -> dict:
    title = str(item.get("title", "")).strip()
    content = str(item.get("content", "")).strip()
    published_at = str(item.get("published_at", "")).strip() or datetime.utcnow().isoformat()
    url = str(item.get("url", "")).strip()
    raw_html = str(item.get("raw_html", ""))
    symbols = detect_symbols(f"{title}\n{content}")
    return {
        "title": title,
        "content": content,
        "published_at": published_at,
        "source": source,
        "url": url,
        "detected_symbols": symbols,
        "raw_html": raw_html,
    }


def _rss_ts_to_iso(entry) -> str:
    if getattr(entry, "published_parsed", None):
        return datetime(*entry.published_parsed[:6]).isoformat()
    if getattr(entry, "updated_parsed", None):
        return datetime(*entry.updated_parsed[:6]).isoformat()
    for key in ("published", "updated", "pubDate"):
        val = entry.get(key)
        if not val:
            continue
        try:
            return parsedate_to_datetime(val).isoformat()
        except Exception:
            continue
    return datetime.utcnow().isoformat()


def _extract_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return str(og["content"]).strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    if soup.title:
        return soup.title.get_text(" ", strip=True)
    return ""


def _extract_page_datetime(soup: BeautifulSoup) -> str | None:
    time_tag = soup.find("time")
    if time_tag:
        dt = str(time_tag.get("datetime") or time_tag.get_text(" ", strip=True)).strip()
        if dt:
            return dt
    for key in ("article:published_time", "pubdate", "date", "og:updated_time"):
        meta = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if meta and meta.get("content"):
            return str(meta["content"]).strip()
    return None

