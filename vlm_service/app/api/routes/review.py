"""HTTP routes for the human review queue."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_review_service
from app.api.schemas.analysis import AnalysisResultResponse
from app.api.schemas.review import ReviewDecisionRequest
from app.services.review.reviewer import ReviewService

router = APIRouter(prefix="/api/v1", tags=["review"])


@router.get("/review/pending", response_model=list[AnalysisResultResponse])
async def list_pending_review(
    site_id: str | None = Query(default=None),
    review_service: ReviewService = Depends(get_review_service),
) -> list[AnalysisResultResponse]:
    results = await review_service.list_pending(site_id)
    return [AnalysisResultResponse.from_domain(r) for r in results]


@router.post("/review/{result_id}", response_model=AnalysisResultResponse)
async def submit_review_decision(
    result_id: str,
    body: ReviewDecisionRequest,
    review_service: ReviewService = Depends(get_review_service),
) -> AnalysisResultResponse:
    result = await review_service.apply_decision(body.to_domain(result_id))
    return AnalysisResultResponse.from_domain(result)
