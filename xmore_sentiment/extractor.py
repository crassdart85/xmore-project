"""LLM structured fact extractor (JSON schema constrained)."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import requests

from xmore_sentiment.schemas import ArticleInput, ExtractedFacts

logger = logging.getLogger(__name__)


EXTRACTION_JSON_SCHEMA: dict[str, Any] = {
    "name": "xmore_fact_extraction",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "company_mentioned": {"type": "boolean"},
            "company_names": {"type": "array", "items": {"type": "string"}},
            "primary_subject": {"type": "boolean"},
            "financial_event_type": {
                "type": "string",
                "enum": ["earnings", "guidance", "debt", "macro", "regulatory", "none"],
            },
            "revenue_change_percent": {"type": ["number", "null"]},
            "profit_change_percent": {"type": ["number", "null"]},
            "debt_change_percent": {"type": ["number", "null"]},
            "guidance_direction": {
                "type": "string",
                "enum": ["raised", "lowered", "unchanged", "null"],
            },
            "macro_related": {"type": "boolean"},
            "tone_keywords_detected": {"type": "array", "items": {"type": "string"}},
            "certainty": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": [
            "company_mentioned",
            "company_names",
            "primary_subject",
            "financial_event_type",
            "revenue_change_percent",
            "profit_change_percent",
            "debt_change_percent",
            "guidance_direction",
            "macro_related",
            "tone_keywords_detected",
            "certainty",
        ],
    },
    "strict": True,
}


@dataclass
class ExtractorConfig:
    model: str = os.getenv("XMORE_SENTIMENT_MODEL", "gpt-4o-mini")
    endpoint: str = os.getenv("OPENAI_API_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    api_key: str | None = os.getenv("OPENAI_API_KEY")
    timeout_seconds: float = float(os.getenv("XMORE_SENTIMENT_LLM_TIMEOUT", "25"))
    max_retries: int = int(os.getenv("XMORE_SENTIMENT_LLM_RETRIES", "3"))
    min_request_interval_sec: float = float(os.getenv("XMORE_SENTIMENT_LLM_MIN_INTERVAL", "0.6"))


class LLMFactExtractor:
    """Strictly extracts structured financial facts via JSON schema output."""

    def __init__(self, config: ExtractorConfig | None = None) -> None:
        self.config = config or ExtractorConfig()
        self._last_request_ts = 0.0

    def extract(self, article: ArticleInput) -> ExtractedFacts | None:
        """
        Extract structured facts from article content.

        Returns None if extraction fails or JSON is invalid.
        """
        if not self.config.api_key:
            logger.error("OPENAI_API_KEY not configured; extraction skipped for URL hash=%s", article.url_hash)
            return None

        prompt = self._build_prompt(article)
        payload = {
            "model": self.config.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a financial fact extraction engine. "
                        "Return JSON only. Do not classify sentiment. "
                        "Do not provide explanations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_schema", "json_schema": EXTRACTION_JSON_SCHEMA},
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        backoff = 1.0
        for attempt in range(1, self.config.max_retries + 1):
            self._rate_limit_wait()
            try:
                response = requests.post(
                    self.config.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout_seconds,
                )
                self._last_request_ts = time.time()
                response.raise_for_status()
                raw_json = self._extract_content_json(response.json())
                return ExtractedFacts.model_validate(raw_json)
            except Exception as exc:
                logger.warning("LLM extraction failed attempt=%s article=%s: %s", attempt, article.url_hash, exc)
                if attempt < self.config.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error("Discarding extraction after retries article=%s", article.url_hash)
        return None

    def _rate_limit_wait(self) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < self.config.min_request_interval_sec:
            time.sleep(self.config.min_request_interval_sec - elapsed)

    @staticmethod
    def _build_prompt(article: ArticleInput) -> str:
        text = f"Title: {article.title}\n\nContent: {article.content}"
        return (
            "Extract structured facts from the financial article below.\n"
            "Rules:\n"
            "- company_names must contain ticker-like symbols when identifiable.\n"
            "- If no evidence for a field, return null or conservative defaults.\n"
            "- certainty should reflect extraction confidence only.\n\n"
            f"{text[:12000]}"
        )

    @staticmethod
    def _extract_content_json(response_payload: dict[str, Any]) -> dict[str, Any]:
        choices = response_payload.get("choices", [])
        if not choices:
            raise ValueError("No choices in LLM response")

        message = choices[0].get("message", {})
        content = message.get("content")

        if isinstance(content, list):
            text_chunks = [item.get("text", "") for item in content if isinstance(item, dict)]
            content_str = "".join(text_chunks).strip()
        else:
            content_str = str(content or "").strip()

        if not content_str:
            raise ValueError("Empty JSON content from LLM")

        try:
            return json.loads(content_str)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON from LLM: %s", content_str[:500])
            raise ValueError("LLM returned invalid JSON") from exc

