"""
pdf_engine/pdf_parser.py — Xmore News Ingestion Layer

Extracts plain text from downloaded PDF files.

Strategy:
  1. Try pdfplumber (best for structured financial PDFs)
  2. Fall back to PyMuPDF (fitz) if pdfplumber fails or returns empty text
  3. Return empty string if both fail (never raises)

Also derives metadata: title (from filename), page count, language.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from utils import clean_text, detect_language

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Text extraction backends
# ---------------------------------------------------------------------------

def _extract_pdfplumber(path: Path) -> str:
    """Primary extractor — excellent for columnar/financial PDFs."""
    import pdfplumber  # type: ignore

    pages_text: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text.strip())
    return "\n\n".join(pages_text)


def _extract_pymupdf(path: Path) -> str:
    """Fallback extractor — handles more corrupt / image-heavy PDFs."""
    import fitz  # PyMuPDF  # type: ignore

    doc = fitz.open(str(path))
    pages_text: list[str] = []
    for page in doc:
        text = page.get_text("text") or ""
        if text.strip():
            pages_text.append(text.strip())
    doc.close()
    return "\n\n".join(pages_text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_text(path: Path) -> str:
    """
    Extract all text from a PDF file.
    Returns cleaned text string (may be empty if PDF is image-only).
    Never raises.
    """
    if not path.exists():
        logger.error("[PDFParser] File not found: %s", path)
        return ""

    raw = ""
    try:
        raw = _extract_pdfplumber(path)
        if raw.strip():
            logger.debug("[PDFParser] pdfplumber OK: %s (%d chars)", path.name, len(raw))
        else:
            raise ValueError("pdfplumber returned empty text")
    except Exception as exc:
        logger.warning("[PDFParser] pdfplumber failed for %s: %s — trying PyMuPDF", path.name, exc)
        try:
            raw = _extract_pymupdf(path)
            if raw.strip():
                logger.debug("[PDFParser] PyMuPDF OK: %s (%d chars)", path.name, len(raw))
        except Exception as exc2:
            logger.error("[PDFParser] Both extractors failed for %s: %s", path.name, exc2)
            return ""

    text = clean_text(raw)
    if len(text) > 50_000:
        text = text[:50_000] + " [...]"
    return text


def extract_title(path: Path) -> str:
    """
    Derive a human-readable title from the PDF path.
    Tries to use first non-empty line of text; falls back to filename stem.
    """
    # Try to pull the first meaningful line as a title
    try:
        raw = _extract_pdfplumber(path)
    except Exception:
        raw = ""

    if raw:
        for line in raw.splitlines():
            line = line.strip()
            # A reasonable title: 5–120 chars, not all digits/punctuation
            if 5 <= len(line) <= 120 and re.search(r"[A-Za-z\u0600-\u06FF]", line):
                return line

    # Fallback: prettify filename
    stem = path.stem
    title = re.sub(r"[_\-]+", " ", stem).strip()
    return title[:120]


def parse_pdf(path: Path, source_name: str, url: str) -> Optional[dict]:
    """
    Parse a downloaded PDF and return a dict compatible with Article fields.
    Returns None if no text could be extracted.
    """
    text = extract_text(path)
    if not text:
        logger.warning("[PDFParser] No text extracted from %s", path.name)
        return None

    title = extract_title(path)
    language = detect_language(f"{title} {text[:500]}")

    return {
        "title": title,
        "content": text,
        "source": source_name,
        "ingestion_method": "pdf",
        "url": url,
        "language": language,
    }
