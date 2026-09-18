from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import InstallationStatus
from app.domain.models import HumanReviewDecision


class ReviewDecisionRequest(BaseModel):
    approve: bool
    reclassified_installation_status: InstallationStatus | None = Field(
        default=None,
        description="Required when approve is false: the corrected verdict.",
    )
    notes: str | None = None

    @model_validator(mode="after")
    def check_reclassification(self) -> "ReviewDecisionRequest":
        if not self.approve and self.reclassified_installation_status is None:
            raise ValueError("reclassified_installation_status is required when approve is false")
        return self

    def to_domain(self, result_id: str) -> HumanReviewDecision:
        return HumanReviewDecision(
            result_id=result_id,
            approve=self.approve,
            reclassified_installation_status=self.reclassified_installation_status,
            notes=self.notes,
        )
