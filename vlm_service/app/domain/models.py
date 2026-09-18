"""Pure domain models (value objects / entities). No I/O, no framework deps."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import PurePosixPath

from app.domain.enums import (
    InstallationStatus,
    DevicePowerStatus,
    WorkmanshipQuality,
    ComplianceFlags,
    AnalysisJobStatus,
    ReviewStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class ImageRef:
    """Reference to a single image on disk, scoped to a site."""

    site_id: str
    path: PurePosixPath
    size_bytes: int

    @property
    def filename(self) -> str:
        return self.path.name


@dataclass(frozen=True)
class InstallationAssessment:
    """Normalized, validated result of a single VLM call for one image."""

    installation_status: InstallationStatus
    device_power_status: DevicePowerStatus
    workmanship_quality: WorkmanshipQuality
    compliance_flags: tuple[ComplianceFlags, ...]
    technical_observations: tuple[str, ...]
    confidence: float
    raw_description: str

    def needs_review(self, confidence_threshold: float) -> bool:
        return (
            self.installation_status in (InstallationStatus.FAIL, InstallationStatus.INCOMPLETE)
            or self.device_power_status in (DevicePowerStatus.RED, DevicePowerStatus.OFF, DevicePowerStatus.UNCLEAR)
            or self.workmanship_quality is WorkmanshipQuality.POOR
            or self.confidence < confidence_threshold
        )


@dataclass
class AnalysisResult:
    """One persisted record: an image plus its installation assessment."""

    site_id: str
    image_path: str
    assessment: InstallationAssessment
    id: str = field(default_factory=_new_id)
    created_at: datetime = field(default_factory=_utcnow)
    flagged_for_review: bool = False
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_notes: str | None = None
    reviewed_installation_status: InstallationStatus | None = None
    reviewed_device_power_status: DevicePowerStatus | None = None
    reviewed_workmanship_quality: WorkmanshipQuality | None = None
    reviewed_at: datetime | None = None


@dataclass
class AnalysisJob:
    """Represents one "analyze this site" run, tracked for status queries."""

    site_id: str
    site_path: str
    id: str = field(default_factory=_new_id)
    status: AnalysisJobStatus = AnalysisJobStatus.PENDING
    total_images: int = 0
    processed_images: int = 0
    failed_images: int = 0
    created_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None
    error: str | None = None


@dataclass
class HumanReviewDecision:
    """Input to applying a human review decision to an AnalysisResult."""

    result_id: str
    approve: bool
    reclassified_installation_status: InstallationStatus | None = None
    reclassified_device_power_status: DevicePowerStatus | None = None
    reclassified_workmanship_quality: WorkmanshipQuality | None = None
    notes: str | None = None
