"""Deterministic Arabic financial lexicon scorer."""

from __future__ import annotations

from dataclasses import dataclass

from xmore_event_intel.arabic_sentiment.arabic_preprocessor import normalize_arabic

POSITIVE_KEYWORDS = {
    "نمو",
    "ارتفاع",
    "ارباح",
    "تحسن",
    "زياده",
    "توسع",
    "مكاسب",
    "تفوق",
    "مفاجاه ايجابيه",
}

NEGATIVE_KEYWORDS = {
    "خسائر",
    "تراجع",
    "انخفاض",
    "هبوط",
    "انكماش",
    "مخاطر",
    "ضغوط",
    "مفاجاه سلبيه",
}


@dataclass(frozen=True)
class LexiconScore:
    polarity: float
    positive_hits: int
    negative_hits: int
    positive_terms: list[str]
    negative_terms: list[str]


def score_arabic_lexicon(text: str) -> LexiconScore:
    normalized = normalize_arabic(text).lower()
    pos = sorted({k for k in POSITIVE_KEYWORDS if k in normalized})
    neg = sorted({k for k in NEGATIVE_KEYWORDS if k in normalized})
    pos_hits = len(pos)
    neg_hits = len(neg)
    total = pos_hits + neg_hits
    if total == 0:
        polarity = 0.0
    else:
        polarity = (pos_hits - neg_hits) / total
    return LexiconScore(
        polarity=max(-1.0, min(1.0, polarity)),
        positive_hits=pos_hits,
        negative_hits=neg_hits,
        positive_terms=pos,
        negative_terms=neg,
    )

