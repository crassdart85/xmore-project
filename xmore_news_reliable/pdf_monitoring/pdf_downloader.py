"""
pdf_monitoring/pdf_downloader.py — Xmore Reliable News Acquisition Layer

Downloads PDF files from URLs to a local cache directory.
Features:
  - Content-length check (skip zero-byte files)
  - Filename derived from URL + MD5 suffix (avoids collisions)
  - Already-downloaded check (skip re-download)
  - Streaming download (memory-efficient for large PDFs)
  - Enforces 50 MB max file size
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import requests

from config import DOWNLOAD_DIR, PDF_DOWNLOAD_TIMEOUT

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*;q=0.8",
}

MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB hard cap


# ---------------------------------------------------------------------------
# Filename helpers
# ---------------------------------------------------------------------------

def _safe_filename(url: str) -> str:
    """
    Derive a filesystem-safe filename from a URL.
    Format: <original_stem>_<hash8>.pdf
    """
    parsed = urlparse(url)
    path_part = unquote(parsed.path).rstrip("/")
    original_name = Path(path_part).name or "document"
    stem = Path(original_name).stem[:80]          # cap length
    stem = "".join(c if c.isalnum() or c in "-_." else "_" for c in stem)
    suffix = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{stem}_{suffix}.pdf"


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

class PDFDownloader:
    """
    Downloads PDFs to DOWNLOAD_DIR.  Idempotent: already-cached files are
    returned immediately without a network request.
    """

    def __init__(self, timeout: int = PDF_DOWNLOAD_TIMEOUT) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(_HEADERS)

    def download(self, url: str) -> Optional[Path]:
        """
        Download *url* to the local cache.

        Returns:
            Path to the downloaded PDF file, or None on failure.
        """
        filename = _safe_filename(url)
        dest = DOWNLOAD_DIR / filename

        # Cache hit
        if dest.exists() and dest.stat().st_size > 0:
            logger.debug("Cache hit: %s", filename)
            return dest

        logger.info("Downloading: %s", url)

        try:
            resp = self.session.get(url, timeout=self.timeout, stream=True)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "html" in content_type and "pdf" not in content_type:
                logger.warning(
                    "Skipping non-PDF response (content-type: %s) for %s",
                    content_type,
                    url,
                )
                return None

            bytes_written = 0
            with open(dest, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=65_536):
                    if chunk:
                        bytes_written += len(chunk)
                        if bytes_written > MAX_PDF_BYTES:
                            logger.warning(
                                "PDF too large (>%d MB), aborting: %s",
                                MAX_PDF_BYTES // (1024 * 1024),
                                url,
                            )
                            dest.unlink(missing_ok=True)
                            return None
                        fh.write(chunk)

            if bytes_written == 0:
                logger.warning("Zero-byte PDF downloaded from %s — discarding", url)
                dest.unlink(missing_ok=True)
                return None

            logger.info(
                "Downloaded %s (%.1f KB)",
                filename,
                bytes_written / 1024,
            )
            return dest

        except requests.exceptions.Timeout:
            logger.error("Timeout downloading PDF: %s", url)
        except requests.exceptions.HTTPError as exc:
            logger.error("HTTP %s downloading PDF: %s", exc.response.status_code, url)
        except OSError as exc:
            logger.error("Filesystem error saving PDF: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error downloading %s: %s", url, exc)

        # Clean up partial file
        if dest.exists():
            dest.unlink(missing_ok=True)
        return None
