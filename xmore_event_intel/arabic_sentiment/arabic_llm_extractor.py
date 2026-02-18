"""Structured Arabic-aware LLM extraction with strict JSON validation."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Literal

import requests
from pydantic import BaseModel, ConfigDict, Field

from xmore_event_intel import config

logger = logging.getLogger(__name__)


class ArabicLLMExtraction(BaseModel):
    """Strict schema output for structured event facts."""

    model_config = ConfigDict(extra="forbid")

    company_mentioned: bool
    financial_event_type: str
    revenue_change_percent: float | None = None
    profit_change_percent: float | None = None
    guidance_direction: Literal["raised", "lowered", "unchanged", "null"] = "null"
    certainty: float = Field(ge=0.0, le=1.0)


EXTRACTION_JSON_SCHEMA: dict[str, Any] = {
    "name": "xmore_arabic_event_extraction",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "company_mentioned": {"type": "boolean"},
            "financial_event_type": {"type": "string"},
            "revenue_change_percent": {"type": ["number", "null"]},
            "profit_change_percent": {"type": ["number", "null"]},
            "guidance_direction": {
                "type": "string",
                "enum": ["raised", "lowered", "unchanged", "null"],
            },
            "certainty": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": [
            "company_mentioned",
            "financial_event_type",
            "revenue_change_percent",
            "profit_change_percent",
            "guidance_direction",
            "certainty",
        ],
    },
    "strict": True,
}


@dataclass
class LLMConfig:
    endpoint: str = config.OPENAI_API_ENDPOINT
    model: str = config.OPENAI_MODEL
    api_key: str | None = config.OPENAI_API_KEY
    timeout_seconds: float = 25.0
    max_retries: int = 3
    min_request_interval_sec: float = 0.6


class ArabicLLMExtractor:
    """Strictly extracts structured fields only. No direct BUY/SELL output."""

    def __init__(self, cfg: LLMConfig | None = None) -> None:
        self.cfg = cfg or LLMConfig()
        self._last_request_ts = 0.0

    def extract(self, title: str, content: str) -> ArabicLLMExtraction | None:
        if not self.cfg.api_key:
            return None

        payload = {
            "model": self.cfg.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract structured financial facts only. Return valid JSON only. "
                        "Never output BUY/SELL/HOLD recommendations."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Extract financial event fields from this article.\n"
                        "Set unknown fields to null when needed.\n\n"
                        f"Title: {title}\n\nContent: {content[:12000]}"
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": EXTRACTION_JSON_SCHEMA,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }

        backoff = 1.0
        for attempt in range(1, self.cfg.max_retries + 1):
            self._rate_limit_wait()
            try:
                resp = requests.post(
                    self.cfg.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.cfg.timeout_seconds,
                )
                self._last_request_ts = time.time()
                resp.raise_for_status()
                extracted = self._extract_json(resp.json())
                return ArabicLLMExtraction.model_validate(extracted)
            except Exception as exc:
                logger.warning("Arabic LLM extraction attempt=%s failed: %s", attempt, exc)
                if attempt < self.cfg.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
        return None

    def _rate_limit_wait(self) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < self.cfg.min_request_interval_sec:
            time.sleep(self.cfg.min_request_interval_sec - elapsed)

    @staticmethod
    def _extract_json(payload: dict[str, Any]) -> dict[str, Any]:
        choices = payload.get("choices", [])
        if not choices:
            raise ValueError("No choices in response")
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, list):
            content_text = "".join(
                [str(item.get("text", "")) for item in content if isinstance(item, dict)]
            ).strip()
        else:
            content_text = str(content or "").strip()
        return json.loads(content_text)

