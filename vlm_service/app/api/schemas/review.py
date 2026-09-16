from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import Cleanliness
from app.domain.models import HumanReviewDecision


class ReviewDecisionRequest(BaseModel):
    approve: bool
    reclassified_cleanliness: Cleanliness | None = Field(
        default=None,
        description="Required when approve is false: the corrected verdict.",
    )
    notes: str | None = None

    @model_validator(mode="after")
    def check_reclassification(self) -> "ReviewDecisionRequest":
        if not self.approve and self.reclassified_cleanliness is None:
            raise ValueError("reclassified_cleanliness is required when approve is false")
        return self

    def to_domain(self, result_id: str) -> HumanReviewDecision:
        return HumanReviewDecision(
            result_id=result_id,
            approve=self.approve,
            reclassified_cleanliness=self.reclassified_cleanliness,
            notes=self.notes,
        )
