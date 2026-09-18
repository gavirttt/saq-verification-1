"""Request/response schemas for the analysis API. These are HTTP-facing
DTOs only — the api layer maps domain models to/from these, never exposing
domain dataclasses directly on the wire."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import InstallationStatus, DevicePowerStatus, WorkmanshipQuality, ComplianceFlags, AnalysisJobStatus, ReviewStatus
from app.domain.models import AnalysisJob, AnalysisResult


class TriggerAnalysisRequest(BaseModel):
    site_id: str = Field(..., min_length=1)
    site_path: str = Field(..., min_length=1, description="Filesystem path to the site's image folder")


class AnalysisJobResponse(BaseModel):
    id: str
    site_id: str
    site_path: str
    status: AnalysisJobStatus
    total_images: int
    processed_images: int
    failed_images: int
    created_at: datetime
    completed_at: datetime | None
    error: str | None

    @classmethod
    def from_domain(cls, job: AnalysisJob) -> "AnalysisJobResponse":
        return cls(
            id=job.id,
            site_id=job.site_id,
            site_path=job.site_path,
            status=job.status,
            total_images=job.total_images,
            processed_images=job.processed_images,
            failed_images=job.failed_images,
            created_at=job.created_at,
            completed_at=job.completed_at,
            error=job.error,
        )


class InstallationAssessmentResponse(BaseModel):
    installation_status: InstallationStatus
    device_power_status: DevicePowerStatus
    workmanship_quality: WorkmanshipQuality
    compliance_flags: list[ComplianceFlags]
    technical_observations: list[str]
    confidence: float
    raw_description: str


class AnalysisResultResponse(BaseModel):
    id: str
    site_id: str
    image_path: str
    assessment: InstallationAssessmentResponse
    flagged_for_review: bool
    review_status: ReviewStatus
    review_notes: str | None
    reviewed_installation_status: InstallationStatus | None
    created_at: datetime
    reviewed_at: datetime | None

    @classmethod
    def from_domain(cls, result: AnalysisResult) -> "AnalysisResultResponse":
        return cls(
            id=result.id,
            site_id=result.site_id,
            image_path=result.image_path,
            assessment=InstallationAssessmentResponse(
                installation_status=result.assessment.installation_status,
                device_power_status=result.assessment.device_power_status,
                workmanship_quality=result.assessment.workmanship_quality,
                compliance_flags=list(result.assessment.compliance_flags),
                technical_observations=list(result.assessment.technical_observations),
                confidence=result.assessment.confidence,
                raw_description=result.assessment.raw_description,
            ),
            flagged_for_review=result.flagged_for_review,
            review_status=result.review_status,
            review_notes=result.review_notes,
            reviewed_installation_status=result.reviewed_installation_status,
            created_at=result.created_at,
            reviewed_at=result.reviewed_at,
        )
