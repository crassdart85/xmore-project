"""
pdf_monitoring/pdf_parser.py — Xmore Reliable News Acquisition Layer

Extracts text from downloaded PDF files and converts them into the unified
article schema.

Library priority:
  1. pdfplumber  — best for structured/table-heavy financial PDFs
  2. PyMuPDF (fitz) — fallback, faster, handles more corrupt PDFs

Both libraries are optional at import time — the parser tries whichever is
installed and raises a clear error if neither is available.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from email_ingestion.email_parser import detect_language, detect_symbols

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Library availability detection
# ---------------------------------------------------------------------------
try:
    import pdfplumber
    _PDFPLUMBER = True
except ImportError:
    _PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    _PYMUPDF = True
except ImportError:
    _PYMUPDF = False

if not _PDFPLUMBER and not _PYMUPDF:
    logger.warning(
        "No PDF extraction library found. "
        "Install pdfplumber or PyMuPDF: pip install pdfplumber"
    )

MAX_CONTENT_CHARS = 60_000  # storage cap per article


# ---------------------------------------------------------------------------
# Text extraction backends
# ---------------------------------------------------------------------------

def _extract_pdfplumber(path: Path) -> str:
    pages: List[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def _extract_pymupdf(path: Path) -> str:
    pages: List[str] = []
    doc = fitz.open(str(path))
    try:
        for page in doc:
            pages.append(page.get_text("text"))
    finally:
        doc.close()
    return "\n\n".join(pages)


def extract_text_from_pdf(path: Path) -> str:
    """
    Extract full text from a PDF file.
    Tries pdfplumber first, then PyMuPDF.
    Raises RuntimeError if no library is available.
    """
    last_exc: Optional[Exception] = None

    if _PDFPLUMBER:
        try:
            text = _extract_pdfplumber(path)
            if text.strip():
                return text
            logger.debug("pdfplumber returned empty text for %s", path.name)
        except Exception as exc:
            last_exc = exc
            logger.warning("pdfplumber failed on %s: %s — trying fallback", path.name, exc)

    if _PYMUPDF:
        try:
            return _extract_pymupdf(path)
        except Exception as exc:
            last_exc = exc
            logger.error("PyMuPDF also failed on %s: %s", path.name, exc)

    if last_exc:
        raise RuntimeError(f"All PDF extraction backends failed for {path.name}") from last_exc
    raise RuntimeError(
        "No PDF extraction library available. Run: pip install pdfplumber"
    )


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------

def _infer_title(text: str, filename: str) -> str:
    """
    Attempt to extract a meaningful title from the first few non-empty lines.
    Falls back to the cleaned filename stem.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines[:8]:
        # Skip lines that look like page numbers, dates, or short codes
        if len(line) < 10:
            continue
        if re.match(r"^[\d\s/\-:\.]+$", line):
            continue
        # Cap at 200 chars
        return line[:200]

    # Filename fallback
    stem = Path(filename).stem
    stem = re.sub(r"[_\-]+", " ", stem)
    return stem[:200].strip()


# ---------------------------------------------------------------------------
# Whitespace normalisation
# ---------------------------------------------------------------------------

def _clean_pdf_text(raw: str) -> str:
    # Remove control characters (except newline/tab)
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw)
    # Collapse runs of blank lines
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    # Collapse runs of spaces/tabs
    raw = re.sub(r"[ \t]+", " ", raw)
    return raw.strip()


# ---------------------------------------------------------------------------
# Public parser
# ---------------------------------------------------------------------------

class PDFParser:
    """
    Converts a downloaded PDF file into a unified article dict.
    Returns None if text extraction fails or yields empty content.
    """

    def parse(
        self,
        path: Path,
        source: str,
        url: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Parameters
        ----------
        path   : local Path to the downloaded PDF
        source : logical source name (e.g. 'EGX_disclosure')
        url    : original download URL (stored for provenance)

        Returns
        -------
        Normalised article dict or None on failure.
        """
        try:
            raw_text = extract_text_from_pdf(path)
        except RuntimeError as exc:
            logger.error("PDF extraction failed for %s: %s", path.name, exc)
            return None

        if not raw_text.strip():
            logger.warning("Empty text extracted from %s — skipping", path.name)
            return None

        cleaned = _clean_pdf_text(raw_text)
        title = _infer_title(cleaned, path.name)

        # Cap content length
        content = cleaned if len(cleaned) <= MAX_CONTENT_CHARS else (
            cleaned[:MAX_CONTENT_CHARS] + "\n[... content truncated]"
        )

        language = detect_language(content)
        symbols = detect_symbols(content)

        return {
            "title": title,
            "content": content,
            "published_at": datetime.now(tz=timezone.utc).isoformat(),
            "source": source,
            "ingestion_method": "pdf_monitor",
            "detected_symbols": symbols,
            "language": language,
            "url": url,
            "pdf_path": str(path),
        }
