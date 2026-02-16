"""Pydantic schemas for Xmore Sentiment Intelligence Layer."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class FinancialEventType(str, Enum):
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    DEBT = "debt"
    MACRO = "macro"
    REGULATORY = "regulatory"
    NONE = "none"


class GuidanceDirection(str, Enum):
    RAISED = "raised"
    LOWERED = "lowered"
    UNCHANGED = "unchanged"
    NONE = "null"


class ExtractedFacts(BaseModel):
    """Structured fact extraction output from LLM (no free-text sentiment)."""

    model_config = ConfigDict(extra="forbid")

    company_mentioned: bool
    company_names: list[str] = Field(default_factory=list)
    primary_subject: bool
    financial_event_type: FinancialEventType
    revenue_change_percent: float | None = None
    profit_change_percent: float | None = None
    debt_change_percent: float | None = None
    guidance_direction: GuidanceDirection = GuidanceDirection.NONE
    macro_related: bool
    tone_keywords_detected: list[str] = Field(default_factory=list)
    certainty: float = Field(ge=0.0, le=1.0)

    @field_validator("company_names", mode="after")
    @classmethod
    def _normalize_company_names(cls, value: list[str]) -> list[str]:
        return sorted({v.strip().upper() for v in value if v and v.strip()})

    @field_validator("tone_keywords_detected", mode="after")
    @classmethod
    def _normalize_keywords(cls, value: list[str]) -> list[str]:
        return sorted({v.strip().lower() for v in value if v and v.strip()})


class ArticleInput(BaseModel):
    """Source article representation for sentiment pipeline."""

    model_config = ConfigDict(extra="allow")

    id: int | None = None
    title: str
    content: str
    published_at: datetime
    source: str
    url: HttpUrl | str
    url_hash: str
    region: Literal["global", "regional", "egypt"] = "global"
    mentioned_symbols: list[str] = Field(default_factory=list)
    processed_flag: bool = False

    @field_validator("title", "content", "source", "url_hash", mode="before")
    @classmethod
    def _strip_text(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("mentioned_symbols", mode="after")
    @classmethod
    def _normalize_symbols(cls, value: list[str]) -> list[str]:
        return sorted({s.strip().upper().replace(".CA", "") for s in value if s and s.strip()})


class RuleScore(BaseModel):
    """Deterministic score output from rule engine."""

    raw_score: float = Field(ge=-1.0, le=1.0)
    components: dict[str, float] = Field(default_factory=dict)
    normalized: float = Field(ge=-1.0, le=1.0)
    company_specific_weight_applied: float = Field(ge=0.0, le=1.0, default=1.0)


class ConfidenceBreakdown(BaseModel):
    """Confidence model output."""

    llm_certainty: float = Field(ge=0.0, le=1.0)
    entity_strength: float = Field(ge=0.0, le=1.0)
    quantitative_data_presence: float = Field(ge=0.0, le=1.0)
    agreement_strength: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class SentimentResult(BaseModel):
    """Final sentiment scoring record."""

    article_id: int
    symbol: str
    raw_score: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    final_sentiment: float = Field(ge=-1.0, le=1.0)
    keyword_polarity: float = Field(ge=-1.0, le=1.0)
    disagreement: float = Field(ge=0.0)
    uncertain: bool
    publish_date: datetime
    price_at_publish: float | None = None
    price_1d: float | None = None
    price_3d: float | None = None
    price_5d: float | None = None
    return_1d: float | None = None
    return_3d: float | None = None
    return_5d: float | None = None


class ValidationMetrics(BaseModel):
    """Historical validation metrics snapshot."""

    sample_size: int
    corr_1d: float | None = None
    corr_3d: float | None = None
    corr_5d: float | None = None
    accuracy_1d: float | None = None
    accuracy_3d: float | None = None
    accuracy_5d: float | None = None
    weight_multiplier: float = Field(ge=0.1, le=2.0, default=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

