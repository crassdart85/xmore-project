"""
models.py — Xmore News Ingestion Layer
Unified data models shared across all ingestion methods.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class Article:
    """
    Canonical article schema.  Every ingestion method must produce this.
    """
    title: str
    content: str
    source: str
    ingestion_method: str                   # rss | google_news | pdf_monitor
    published_at: Optional[str] = None
    url: Optional[str] = None
    language: str = "en"
    processed_flag: int = 0
    id: Optional[int] = None

    def content_hash(self) -> str:
        """
        Stable dedup key: SHA-256 over source + title + first 500 chars of content.
        Identical articles from different ingestion paths hash to the same value.
        """
        raw = f"{self.source}|{self.title}|{self.content[:500]}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["content_hash"] = self.content_hash()
        return d

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Article":
        return cls(
            id=row.get("id"),
            title=row.get("title", ""),
            content=row.get("content", ""),
            source=row.get("source", ""),
            ingestion_method=row.get("ingestion_method", ""),
            published_at=row.get("published_at"),
            url=row.get("url"),
            language=row.get("language", "en"),
            processed_flag=row.get("processed_flag", 0),
        )


@dataclass
class IngestionAttempt:
    """Records a single ingestion attempt for structured logging and health tracking."""
    source: str
    method: str
    success: bool
    articles_count: int = 0
    error: Optional[str] = None
    duration_ms: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )


@dataclass
class SourceHealth:
    """Aggregated health state for a single named source."""
    source_name: str
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_success: Optional[str] = None
    status: str = "active"          # active | degraded | offline
    success_rate: float = 0.0
    updated_at: Optional[str] = None
