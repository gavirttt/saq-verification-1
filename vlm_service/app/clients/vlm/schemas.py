"""OpenAI-compatible chat-completion wire schemas for the local VLM.

These types are intentionally private to `clients.vlm` — nothing outside
this package may import them. The rest of the codebase only ever sees
`app.domain.models.InstallationAssessment`.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class RawAssessmentPayload(BaseModel):
    """Schema of the JSON object we ask the model to produce. Validated
    loosely here (raw strings), then normalized/coerced into the domain
    InstallationAssessment by `clients.vlm.client`."""

    installation_status: str
    device_power_status: str
    workmanship_quality: str
    compliance_flags: list[str] = Field(default_factory=list)
    technical_observations: list[str] = Field(default_factory=list)
    raw_description: str = ""
    confidence: float

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class ChatMessageContent(BaseModel):
    type: str
    text: str | None = None
    image_url: dict[str, str] | None = None


class ChatMessage(BaseModel):
    role: str
    content: list[ChatMessageContent] | str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.0
    max_tokens: int = 800
    response_format: dict[str, Any] | None = None


def try_parse_raw_payload(text: str) -> RawAssessmentPayload | None:
    """Best-effort extraction of a JSON object from model output that may
    contain surrounding prose or code fences."""
    import json
    import re

    candidates = [text.strip()]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1))
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        candidates.append(brace_match.group(0))

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            return RawAssessmentPayload.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            continue
    return None
