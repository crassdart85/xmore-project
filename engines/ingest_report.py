#!/usr/bin/env python3
"""
Extract text from a PDF report and return normalized JSON for the admin ingestion API.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pdfplumber


ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-z]")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\u061f])\s+")


def extract_text_from_pdf(file_path: Path) -> str:
    chunks = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text:
                chunks.append(page_text)
    return "\n\n".join(chunks).strip()


def detect_language(text: str) -> str:
    if not text:
        return "EN"
    ar_count = len(ARABIC_RE.findall(text))
    en_count = len(LATIN_RE.findall(text))
    return "AR" if ar_count > en_count else "EN"


def summarize_text(text: str, max_sentences: int = 3, max_chars: int = 600) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return ""
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(cleaned) if s.strip()]
    if not sentences:
        return cleaned[:max_chars]
    summary = " ".join(sentences[:max_sentences]).strip()
    return summary[:max_chars]


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: ingest_report.py <pdf_path>", file=sys.stderr)
        return 1

    pdf_path = Path(sys.argv[1]).resolve()
    if not pdf_path.exists() or not pdf_path.is_file():
        print(f"File not found: {pdf_path}", file=sys.stderr)
        return 1

    try:
        extracted_text = extract_text_from_pdf(pdf_path)
        language = detect_language(extracted_text)
        summary = summarize_text(extracted_text)

        payload = {
            "success": True,
            "file_path": str(pdf_path),
            "language": language,
            "extracted_text": extracted_text,
            "summary": summary,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except Exception as exc:  # pragma: no cover - defensive runtime path
        print(f"PDF extraction failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
