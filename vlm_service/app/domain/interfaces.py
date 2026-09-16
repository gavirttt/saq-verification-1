"""Abstract interfaces (ports) that services depend on. Living in `domain`
keeps them dependency-free; concrete adapters in `clients/` and
`repositories/` implement them and depend on `domain`, never the reverse."""
from __future__ import annotations

from typing import Protocol, Sequence

from app.domain.models import AnalysisJob, AnalysisResult, CleanlinessAssessment, ImageRef


class VLMClient(Protocol):
    """Port for the vision-language model adapter. Implementations live in
    clients/vlm and MUST NOT leak provider-specific types through this
    boundary — only domain types cross it."""

    async def assess_image(self, image_bytes: bytes, mime_type: str) -> CleanlinessAssessment:
        """Send one preprocessed image to the VLM and return a normalized,
        validated CleanlinessAssessment. Raises VLMUnavailableError or
        VLMResponseError (domain errors) on failure."""
        ...


class ResultsRepository(Protocol):
    """Port for persisting and querying AnalysisResult records."""

    async def add(self, result: AnalysisResult) -> None: ...

    async def get(self, result_id: str) -> AnalysisResult | None: ...

    async def list_by_site(self, site_id: str) -> Sequence[AnalysisResult]: ...

    async def list_flagged(self, site_id: str | None = None) -> Sequence[AnalysisResult]: ...

    async def update(self, result: AnalysisResult) -> None: ...


class JobsRepository(Protocol):
    """Port for persisting and querying AnalysisJob records."""

    async def add(self, job: AnalysisJob) -> None: ...

    async def get(self, job_id: str) -> AnalysisJob | None: ...

    async def update(self, job: AnalysisJob) -> None: ...


class ImageSource(Protocol):
    """Port for discovering images belonging to a site. Kept as an
    interface so the concrete filesystem walk can be swapped (e.g. for a
    future object-storage backend) without touching services."""

    def discover(self, site_id: str, site_root: str) -> Sequence[ImageRef]: ...

    def read_bytes(self, image: ImageRef) -> bytes: ...
