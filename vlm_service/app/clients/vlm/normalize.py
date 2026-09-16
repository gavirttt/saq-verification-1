"""Provider-agnostic normalization from a parsed raw payload to the domain
CleanlinessAssessment. Every concrete VLM adapter (local OpenAI-compatible,
Bedrock, etc.) parses its own wire format into a RawAssessmentPayload, then
calls `normalize_assessment` here so the coercion/repair rules live in
exactly one place.
"""
from __future__ import annotations

from app.clients.vlm.schemas import RawAssessmentPayload
from app.domain.enums import Cleanliness, MessType, Severity
from app.domain.models import CleanlinessAssessment


def normalize_assessment(raw: RawAssessmentPayload) -> CleanlinessAssessment:
    try:
        cleanliness = Cleanliness(raw.cleanliness.strip().lower())
    except ValueError:
        cleanliness = Cleanliness.UNCLEAR

    mess_types = tuple(MessType.coerce(mt.strip().lower()) for mt in raw.mess_types)

    try:
        severity = Severity(raw.severity.strip().lower())
    except ValueError:
        severity = Severity.NONE if cleanliness == Cleanliness.CLEAN else Severity.MODERATE

    if cleanliness == Cleanliness.CLEAN:
        severity = Severity.NONE
    elif severity == Severity.NONE:
        severity = Severity.MINOR

    confidence = max(0.0, min(1.0, raw.confidence))

    return CleanlinessAssessment(
        cleanliness=cleanliness,
        mess_types=mess_types,
        severity=severity,
        observations=tuple(raw.observations),
        confidence=confidence,
        raw_description=raw.raw_description,
    )
