"""Arabic text normalization utilities."""

from __future__ import annotations

import re

_ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652]")
_TATWEEL = "\u0640"
_NON_TEXT = re.compile(r"[^\w\s%.\-+]")


def normalize_arabic(text: str) -> str:
    value = str(text or "")
    value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    value = value.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    value = value.replace(_TATWEEL, "")
    value = _ARABIC_DIACRITICS.sub("", value)
    value = _NON_TEXT.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def build_sentiment_text(title: str, content: str) -> str:
    return normalize_arabic(f"{title}\n{content}")

