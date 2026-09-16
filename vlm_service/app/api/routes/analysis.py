"""HTTP routes for triggering and querying site cleanliness analysis.

No business logic here — routes validate/parse input, call the service,
and map domain models to response schemas. Errors propagate as domain
exceptions and are translated centrally by `core.exceptions`.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.dependencies import get_orchestrator
from app.api.schemas.analysis import (
    AnalysisJobResponse,
    AnalysisResultResponse,
    TriggerAnalysisRequest,
)
from app.services.analysis.orchestrator import AnalysisOrchestrator

router = APIRouter(prefix="/api/v1", tags=["analysis"])


@router.post(
    "/sites/{site_id}/analyze",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_site_analysis(
    site_id: str,
    body: TriggerAnalysisRequest,
    background_tasks: BackgroundTasks,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
) -> AnalysisJobResponse:
    """Creates the job row synchronously (so the client gets an id and image
    count immediately) then runs the potentially long per-image loop in a
    background task. Poll GET /jobs/{job_id} for progress."""
    job = await orchestrator.create_job(site_id, body.site_path)
    background_tasks.add_task(orchestrator.run_job, job)
    return AnalysisJobResponse.from_domain(job)


@router.get("/jobs/{job_id}", response_model=AnalysisJobResponse)
async def get_job(
    job_id: str,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
) -> AnalysisJobResponse:
    job = await orchestrator.get_job(job_id)
    return AnalysisJobResponse.from_domain(job)


@router.get("/sites/{site_id}/results", response_model=list[AnalysisResultResponse])
async def list_site_results(
    site_id: str,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
) -> list[AnalysisResultResponse]:
    results = await orchestrator.list_results_for_site(site_id)
    return [AnalysisResultResponse.from_domain(r) for r in results]


@router.get("/results/{result_id}", response_model=AnalysisResultResponse)
async def get_result(
    result_id: str,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
) -> AnalysisResultResponse:
    result = await orchestrator.get_result(result_id)
    return AnalysisResultResponse.from_domain(result)
