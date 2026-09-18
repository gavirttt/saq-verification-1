"""Provider-agnostic normalization from a parsed raw payload to the domain
InstallationAssessment. Every concrete VLM adapter (OpenAI-compatible,
Bedrock, etc.) parses its own wire format into a RawAssessmentPayload, then
calls `normalize_assessment` here so the coercion/repair rules live in
exactly one place.
"""
from __future__ import annotations

from app.clients.vlm.schemas import RawAssessmentPayload
from app.domain.enums import InstallationStatus, DevicePowerStatus, WorkmanshipQuality, ComplianceFlags
from app.domain.models import InstallationAssessment


def normalize_assessment(raw: RawAssessmentPayload) -> InstallationAssessment:
    installation_status = InstallationStatus.coerce(
        raw.installation_status.strip().lower(), fallback=InstallationStatus.INCOMPLETE
    )
    device_power_status = DevicePowerStatus.coerce(
        raw.device_power_status.strip().lower(), fallback=DevicePowerStatus.UNCLEAR
    )
    workmanship_quality = WorkmanshipQuality.coerce(
        raw.workmanship_quality.strip().lower(), fallback=WorkmanshipQuality.ACCEPTABLE
    )

    compliance_flags = tuple(ComplianceFlags.coerce(c_f.strip().lower()) for c_f in raw.compliance_flags)

    confidence = max(0.0, min(1.0, raw.confidence))

    return InstallationAssessment(
        installation_status=installation_status,
        workmanship_quality=workmanship_quality,
        device_power_status = device_power_status,
        compliance_flags=compliance_flags,
        technical_observations=tuple(raw.technical_observations),
        confidence=confidence,
        raw_description=raw.raw_description,
    )
