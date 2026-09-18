"""Pure domain enums. No I/O, no third-party dependencies beyond stdlib."""
from __future__ import annotations

from enum import Enum


class InstallationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"

class DevicePowerStatus(str, Enum):
    GREEN = "green"
    RED = "red"
    OFF = "off"
    UNCLEAR = "unclear"
    NOTAPPLICABLE = "na"

class WorkmanshipQuality(str, Enum):
    PROFESSIONAL = "professional"
    ACCEPTABLE = "acceptable"
    POOR = "poor"

class ComplianceFlags(str, Enum):
    UNSECURED_CABLES = "unsecured_cables"
    MISSING_STRAIN_RELIEF = "missing_strain_relief"
    SHARP_FIBER_BENDS = "sharp_fiber_bends"
    LOOSE_LEFTOVER_LINES = "loose_leftover_lines"
    UNPOWERED_DEVICE = "unpowered_device"
    OTHER = "other"

    @classmethod
    def coerce(cls, value: str) -> "ComplianceFlags":
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
