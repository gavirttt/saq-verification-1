"""Business logic orchestrating a full site analysis run.

Depends only on domain models/enums and interfaces (Protocols) — never on
concrete clients or repositories. Concrete implementations are injected by
`core.container` / FastAPI `Depends`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.logging import get_logger, set_correlation_id
from app.domain.enums import AnalysisJobStatus
from app.domain.errors import (
    ImageProcessingError,
    JobNotFoundError,
    ResultNotFoundError,
    SiteNotFoundError,
    VLMResponseError,
    VLMUnavailableError,
)
from app.domain.interfaces import ImageSource, JobsRepository, ResultsRepository, VLMClient
from app.domain.models import AnalysisJob, AnalysisResult
from app.services.analysis.image_processor import ImagePreprocessor

logger = get_logger(__name__)


class AnalysisOrchestrator:
    def __init__(
        self,
        image_source: ImageSource,
        image_preprocessor: ImagePreprocessor,
        vlm_client: VLMClient,
        results_repository: ResultsRepository,
        jobs_repository: JobsRepository,
        review_confidence_threshold: float,
    ) -> None:
        self._image_source = image_source
        self._image_preprocessor = image_preprocessor
        self._vlm_client = vlm_client
        self._results_repository = results_repository
        self._jobs_repository = jobs_repository
        self._review_confidence_threshold = review_confidence_threshold

    async def start_site_analysis(self, site_id: str, site_path: str) -> AnalysisJob:
        """Synchronous end-to-end run: discovers images, processes every one,
        and returns only once the job has finished. Useful for tests / CLI
        usage; the HTTP route uses `create_job` + `run_job` instead so it can
        return immediately and process in a background task."""
        job = await self.create_job(site_id, site_path)
        return await self.run_job(job)

    async def create_job(self, site_id: str, site_path: str) -> AnalysisJob:
        images = self._image_source.discover(site_id, site_path)
        if not images:
            raise SiteNotFoundError(site_id)

        job = AnalysisJob(site_id=site_id, site_path=site_path, total_images=len(images))
        await self._jobs_repository.add(job)
        return job

    async def run_job(self, job: AnalysisJob) -> AnalysisJob:
        images = self._image_source.discover(job.site_id, job.site_path)

        job.status = AnalysisJobStatus.RUNNING
        await self._jobs_repository.update(job)

        for image in images:
            set_correlation_id(f"{job.site_id}:{image.filename}")
            try:
                raw_bytes = self._image_source.read_bytes(image)
                processed_bytes, mime_type = self._image_preprocessor.process(
                    raw_bytes, str(image.path)
                )
                assessment = await self._vlm_client.assess_image(processed_bytes, mime_type)
                needs_review = assessment.needs_review(self._review_confidence_threshold)
                result = AnalysisResult(
                    site_id=job.site_id,
                    image_path=str(image.path),
                    assessment=assessment,
                    flagged_for_review=needs_review,
                )
                await self._results_repository.add(result)
                job.processed_images += 1
            except (ImageProcessingError, VLMUnavailableError, VLMResponseError) as exc:
                logger.error("Failed to analyze image %s: %s", image.path, exc)
                job.failed_images += 1
            except Exception as exc:  # noqa: BLE001 - never let one bad image kill the job
                logger.error("Unexpected error analyzing image %s: %s", image.path, exc)
                job.failed_images += 1
            finally:
                await self._jobs_repository.update(job)

        job.status = (
            AnalysisJobStatus.FAILED
            if job.processed_images == 0 and job.failed_images > 0
            else AnalysisJobStatus.COMPLETED
        )
        job.completed_at = datetime.now(timezone.utc)
        await self._jobs_repository.update(job)
        return job

    async def get_job(self, job_id: str) -> AnalysisJob:
        job = await self._jobs_repository.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    async def list_results_for_site(self, site_id: str) -> list[AnalysisResult]:
        return list(await self._results_repository.list_by_site(site_id))

    async def get_result(self, result_id: str) -> AnalysisResult:
        result = await self._results_repository.get(result_id)
        if result is None:
            raise ResultNotFoundError(result_id)
        return result
