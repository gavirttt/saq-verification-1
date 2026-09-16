"""Abstract interface for the results repository.

The canonical Protocol lives in `app.domain.interfaces.ResultsRepository`
(so `services` can depend on it without importing `repositories`). This
module re-exports it as the local contract that concrete implementations
in this package must satisfy, keeping the feature folder self-describing.
"""
from __future__ import annotations

from app.domain.interfaces import ResultsRepository

__all__ = ["ResultsRepository"]
