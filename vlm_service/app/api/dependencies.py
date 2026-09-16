"""FastAPI dependency providers. Routes depend on these, never on the
container or concrete adapters directly."""
from __future__ import annotations

from fastapi import Request

from app.services.analysis.orchestrator import AnalysisOrchestrator
from app.services.review.reviewer import ReviewService


def get_orchestrator(request: Request) -> AnalysisOrchestrator:
    return request.app.state.container.orchestrator


def get_review_service(request: Request) -> ReviewService:
    return request.app.state.container.review_service
