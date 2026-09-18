"""Domain-level exceptions. These carry meaning across layer boundaries;
adapters (clients/repositories) translate their own errors into these."""
from __future__ import annotations


class DomainError(Exception):
    """Base class for all application errors."""


class SiteNotFoundError(DomainError):
    def __init__(self, site_id: str) -> None:
        super().__init__(f"Site not found or has no images: {site_id}")
        self.site_id = site_id


class ImageProcessingError(DomainError):
    def __init__(self, image_path: str, reason: str) -> None:
        super().__init__(f"Failed to process image {image_path}: {reason}")
        self.image_path = image_path
        self.reason = reason


class VLMUnavailableError(DomainError):
    """Raised by the VLM client adapter when the model host is unreachable
    or fails after exhausting retries. Contains no VLM-specific payload
    details so callers outside clients/vlm never see transport internals."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class VLMResponseError(DomainError):
    """Raised when the VLM responded but its content could not be
    normalized into a InstallationAssessment even after repair attempts."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ResultNotFoundError(DomainError):
    def __init__(self, result_id: str) -> None:
        super().__init__(f"Analysis result not found: {result_id}")
        self.result_id = result_id


class JobNotFoundError(DomainError):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"Analysis job not found: {job_id}")
        self.job_id = job_id
