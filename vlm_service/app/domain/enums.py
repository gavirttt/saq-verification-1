"""Pure domain enums. No I/O, no third-party dependencies beyond stdlib."""
from __future__ import annotations

from enum import Enum


class Cleanliness(str, Enum):
    CLEAN = "clean"
    MESSY = "messy"
    UNCLEAR = "unclear"


class Severity(str, Enum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


class MessType(str, Enum):
    CLUTTER = "clutter"
    DEBRIS = "debris"
    STAINS = "stains"
    DISORGANIZED_CABLING = "disorganized_cabling"
    OBSTRUCTION = "obstruction"
    POOR_HOUSEKEEPING = "poor_housekeeping"
    OTHER = "other"

    @classmethod
    def coerce(cls, value: str) -> "MessType":
        try:
            return cls(value)
        except ValueError:
            return cls.OTHER


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    RECLASSIFIED = "reclassified"


class AnalysisJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
