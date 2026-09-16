"""Composition root. Builds concrete adapters/services from Settings.

Nothing here is instantiated at import time — `Container` instances are
created inside the FastAPI lifespan (see `main.py`) and handed out via
`Depends`, so tests can build their own `Container` (or bypass it entirely)
with fakes instead of real adapters.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.clients.filesystem.image_source import FilesystemImageSource
from app.clients.vlm.bedrock_client import BedrockVLMClient
from app.clients.vlm.client import OpenAICompatibleVLMClient
from app.core.config import Settings
from app.domain.interfaces import VLMClient
from app.repositories.jobs.sqlite import SQLiteJobsRepository
from app.repositories.results.sqlite import SQLiteResultsRepository
from app.services.analysis.image_processor import ImagePreprocessor
from app.services.analysis.orchestrator import AnalysisOrchestrator
from app.services.review.reviewer import ReviewService


@dataclass
class Container:
    settings: Settings
    orchestrator: AnalysisOrchestrator
    review_service: ReviewService
    http_client: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()


def _build_vlm_client(settings: Settings) -> tuple[VLMClient, httpx.AsyncClient | None]:
    """Returns the configured VLMClient plus the httpx client it owns (if
    any), so the caller can close that resource on shutdown. Only one
    provider's client is ever constructed — this is the single place in the
    app that branches on `vlm_provider`."""
    if settings.vlm_provider == "bedrock":
        vlm_client: VLMClient = BedrockVLMClient(
            model_id=settings.bedrock_model_id,
            region_name=settings.bedrock_region,
            max_tokens=settings.bedrock_max_tokens,
            max_retries=settings.bedrock_max_retries,
            retry_backoff_seconds=settings.bedrock_retry_backoff_seconds,
        )
        return vlm_client, None

    http_client = httpx.AsyncClient(
        base_url=settings.vlm_base_url,
        timeout=settings.vlm_timeout_seconds,
        headers={"Authorization": f"Bearer {settings.vlm_api_key}"},
    )
    vlm_client = OpenAICompatibleVLMClient(
        base_url=settings.vlm_base_url,
        api_key=settings.vlm_api_key,
        model=settings.vlm_model,
        timeout_seconds=settings.vlm_timeout_seconds,
        max_retries=settings.vlm_max_retries,
        retry_backoff_seconds=settings.vlm_retry_backoff_seconds,
        http_client=http_client,
    )
    return vlm_client, http_client


def build_container(settings: Settings) -> Container:
    vlm_client, http_client = _build_vlm_client(settings)

    image_source = FilesystemImageSource(
        allowed_extensions=settings.image_allowed_extensions,
        min_size_bytes=settings.image_min_size_bytes,
    )
    image_preprocessor = ImagePreprocessor(
        max_dimension_px=settings.image_max_dimension_px,
        jpeg_quality=settings.image_jpeg_quality,
    )

    results_repository = SQLiteResultsRepository(settings.database_path)
    jobs_repository = SQLiteJobsRepository(settings.database_path)

    orchestrator = AnalysisOrchestrator(
        image_source=image_source,
        image_preprocessor=image_preprocessor,
        vlm_client=vlm_client,
        results_repository=results_repository,
        jobs_repository=jobs_repository,
        review_confidence_threshold=settings.review_confidence_threshold,
    )
    review_service = ReviewService(results_repository=results_repository)

    return Container(
        settings=settings,
        orchestrator=orchestrator,
        review_service=review_service,
        http_client=http_client,
    )
