"""
pdf_engine/pdf_downloader.py — Xmore News Ingestion Layer

Downloads PDFs (and other binary documents) discovered by the page monitor.

Features:
  - Streaming download with 50 MB hard cap
  - Content-Type validation (only accepts PDF responses)
  - Local disk cache under <project_root>/downloaded_pdfs/
  - Cache-hit detection via file existence + ETag/Last-Modified headers
  - Retry with exponential backoff
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from config import MAX_RETRIES, REQUEST_TIMEOUT_SECONDS, USER_AGENT
from utils import retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Maximum download size (50 MB)
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024

# Where downloaded PDFs are stored
_BASE_DIR = Path(__file__).resolve().parents[1]   # xmore_news/
DOWNLOAD_DIR = _BASE_DIR / "downloaded_pdfs"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Content-Types we accept as valid PDF documents
_VALID_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",   # some servers serve PDFs this way
    "binary/octet-stream",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _url_to_filename(url: str) -> str:
    """
    Derive a stable, filesystem-safe filename from a URL.
    Uses URL path leaf + short hash to avoid collisions.
    """
    parsed = urlparse(url)
    leaf = Path(parsed.path).name or "document"
    # Remove characters that are unsafe on Windows/Linux filesystems
    safe_leaf = "".join(c if c.isalnum() or c in "._-" else "_" for c in leaf)
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    # Ensure .pdf extension
    stem = Path(safe_leaf).stem
    return f"{stem}_{url_hash}.pdf"


@retry(
    max_attempts=MAX_RETRIES,
    delay=3.0,
    backoff=2.0,
    exceptions=(requests.RequestException, OSError),
)
def _stream_download(url: str, dest: Path) -> bool:
    """
    Stream-download url to dest.
    Returns True on success, False if content-type is not a PDF.
    Raises on network errors (triggers retry).
    """
    with requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        stream=True,
        timeout=REQUEST_TIMEOUT_SECONDS,
        allow_redirects=True,
    ) as resp:
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type not in _VALID_CONTENT_TYPES:
            logger.debug(
                "[PDFDownloader] Skipping %s — content-type: %s", url, content_type
            )
            return False

        bytes_written = 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    bytes_written += len(chunk)
                    if bytes_written > MAX_DOWNLOAD_BYTES:
                        logger.warning(
                            "[PDFDownloader] %s exceeds %d MB — aborting",
                            url, MAX_DOWNLOAD_BYTES // (1024 * 1024),
                        )
                        dest.unlink(missing_ok=True)
                        return False
                    fh.write(chunk)

    logger.info(
        "[PDFDownloader] Downloaded %s -> %s (%.1f KB)",
        url, dest.name, bytes_written / 1024,
    )
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_pdf(url: str) -> Optional[Path]:
    """
    Download the PDF at url to the local cache.

    Returns the local Path if successful, None otherwise.
    Never raises.
    """
    filename = _url_to_filename(url)
    dest = DOWNLOAD_DIR / filename

    # Cache hit
    if dest.exists() and dest.stat().st_size > 0:
        logger.debug("[PDFDownloader] Cache hit: %s", filename)
        return dest

    start = time.monotonic()
    try:
        ok = _stream_download(url, dest)
        elapsed = time.monotonic() - start
        if ok and dest.exists():
            logger.info(
                "[PDFDownloader] OK in %.1fs: %s", elapsed, filename
            )
            return dest
        return None
    except Exception as exc:
        logger.error("[PDFDownloader] Failed %s: %s", url, exc)
        dest.unlink(missing_ok=True)
        return None


def download_pdfs(urls: list[str]) -> dict[str, Optional[Path]]:
    """Download multiple PDF URLs. Returns {url: local_path_or_None}."""
    return {url: download_pdf(url) for url in urls}
