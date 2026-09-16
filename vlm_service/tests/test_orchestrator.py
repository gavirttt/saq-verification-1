"""Proves the layering works: AnalysisOrchestrator is exercised with fake
implementations of VLMClient, ResultsRepository, JobsRepository, and
ImageSource — no HTTP, no filesystem, no SQLite involved."""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.domain.enums import AnalysisJobStatus, Cleanliness, MessType, Severity
from app.domain.models import AnalysisJob, AnalysisResult, CleanlinessAssessment, ImageRef
from app.services.analysis.image_processor import ImagePreprocessor
from app.services.analysis.orchestrator import AnalysisOrchestrator


class FakeVLMClient:
    """Implements the VLMClient Protocol without any network I/O."""

    def __init__(self, assessment: CleanlinessAssessment) -> None:
        self._assessment = assessment
        self.calls = 0

    async def assess_image(self, image_bytes: bytes, mime_type: str) -> CleanlinessAssessment:
        self.calls += 1
        return self._assessment


class FakeResultsRepository:
    def __init__(self) -> None:
        self.saved: list[AnalysisResult] = []

    async def add(self, result: AnalysisResult) -> None:
        self.saved.append(result)

    async def get(self, result_id: str) -> AnalysisResult | None:
        return next((r for r in self.saved if r.id == result_id), None)

    async def list_by_site(self, site_id: str):
        return [r for r in self.saved if r.site_id == site_id]

    async def list_flagged(self, site_id: str | None = None):
        return [r for r in self.saved if r.flagged_for_review]

    async def update(self, result: AnalysisResult) -> None:
        for i, r in enumerate(self.saved):
            if r.id == result.id:
                self.saved[i] = result


class FakeJobsRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, AnalysisJob] = {}

    async def add(self, job: AnalysisJob) -> None:
        self.jobs[job.id] = job

    async def get(self, job_id: str) -> AnalysisJob | None:
        return self.jobs.get(job_id)

    async def update(self, job: AnalysisJob) -> None:
        self.jobs[job.id] = job


class FakeImageSource:
    def __init__(self, refs: list[ImageRef]) -> None:
        self._refs = refs

    def discover(self, site_id: str, site_root: str):
        return self._refs

    def read_bytes(self, image: ImageRef) -> bytes:
        buf = io.BytesIO()
        Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
        return buf.getvalue()


def _messy_assessment() -> CleanlinessAssessment:
    return CleanlinessAssessment(
        cleanliness=Cleanliness.MESSY,
        mess_types=(MessType.CLUTTER,),
        severity=Severity.MODERATE,
        observations=("boxes in hallway",),
        confidence=0.9,
        raw_description="Cluttered hallway with boxes.",
    )


@pytest.mark.asyncio
async def test_orchestrator_processes_all_images_and_flags_messy_results():
    from pathlib import PurePosixPath

    refs = [
        ImageRef(site_id="site-1", path=PurePosixPath("/data/site-1/a.jpg"), size_bytes=2048),
        ImageRef(site_id="site-1", path=PurePosixPath("/data/site-1/b.jpg"), size_bytes=2048),
    ]
    vlm_client = FakeVLMClient(_messy_assessment())
    results_repo = FakeResultsRepository()
    jobs_repo = FakeJobsRepository()

    orchestrator = AnalysisOrchestrator(
        image_source=FakeImageSource(refs),
        image_preprocessor=ImagePreprocessor(max_dimension_px=512),
        vlm_client=vlm_client,
        results_repository=results_repo,
        jobs_repository=jobs_repo,
        review_confidence_threshold=0.6,
    )

    job = await orchestrator.start_site_analysis("site-1", "/data/site-1")

    assert job.status == AnalysisJobStatus.COMPLETED
    assert job.processed_images == 2
    assert job.failed_images == 0
    assert vlm_client.calls == 2
    assert len(results_repo.saved) == 2
    assert all(r.flagged_for_review for r in results_repo.saved)
    assert all(r.assessment.cleanliness == Cleanliness.MESSY for r in results_repo.saved)


@pytest.mark.asyncio
async def test_orchestrator_raises_for_site_with_no_images():
    from app.domain.errors import SiteNotFoundError

    orchestrator = AnalysisOrchestrator(
        image_source=FakeImageSource([]),
        image_preprocessor=ImagePreprocessor(max_dimension_px=512),
        vlm_client=FakeVLMClient(_messy_assessment()),
        results_repository=FakeResultsRepository(),
        jobs_repository=FakeJobsRepository(),
        review_confidence_threshold=0.6,
    )

    with pytest.raises(SiteNotFoundError):
        await orchestrator.start_site_analysis("empty-site", "/data/empty-site")
