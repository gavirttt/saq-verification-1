"""Business logic for applying human review decisions to analysis results."""
from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums import ReviewStatus
from app.domain.errors import ResultNotFoundError
from app.domain.interfaces import ResultsRepository
from app.domain.models import AnalysisResult, HumanReviewDecision


class ReviewService:
    def __init__(self, results_repository: ResultsRepository) -> None:
        self._results_repository = results_repository

    async def list_pending(self, site_id: str | None = None) -> list[AnalysisResult]:
        return list(await self._results_repository.list_flagged(site_id))

    async def apply_decision(self, decision: HumanReviewDecision) -> AnalysisResult:
        result = await self._results_repository.get(decision.result_id)
        if result is None:
            raise ResultNotFoundError(decision.result_id)

        result.reviewed_at = datetime.now(timezone.utc)
        result.review_notes = decision.notes

        if decision.approve:
            result.review_status = ReviewStatus.APPROVED
        else:
            result.review_status = ReviewStatus.RECLASSIFIED
            result.reviewed_cleanliness = decision.reclassified_cleanliness

        result.flagged_for_review = False
        await self._results_repository.update(result)
        return result
