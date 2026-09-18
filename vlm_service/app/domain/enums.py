from __future__ import annotations
from enum import Enum
from typing import TypeVar, Type

E = TypeVar("E", bound="CoercibleEnum")


class CoercibleEnum(str, Enum):
    """str-Enum with a shared `coerce` classmethod."""

    @classmethod
    def coerce(cls: Type[E], value: str, fallback: E | None = None) -> E:
        try:
            return cls(value)
        except ValueError:
            if fallback is not None:
                return fallback
            other = getattr(cls, "OTHER", None)
            if other is not None:
                return other
            raise


class InstallationStatus(CoercibleEnum):
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"

class DevicePowerStatus(CoercibleEnum):
    GREEN = "green"
    RED = "red"
    OFF = "off"
    UNCLEAR = "unclear"
    NOTAPPLICABLE = "n/a"

class WorkmanshipQuality(CoercibleEnum):
    PROFESSIONAL = "professional"
    ACCEPTABLE = "acceptable"
    POOR = "poor"

class ComplianceFlags(CoercibleEnum):
    UNSECURED_CABLES = "unsecured_cables"
    MISSING_STRAIN_RELIEF = "missing_strain_relief"
    SHARP_FIBER_BENDS = "sharp_fiber_bends"
    LOOSE_LEFTOVER_LINES = "loose_leftover_lines"
    UNPOWERED_DEVICE = "unpowered_device"
    OTHER = "other"


class ReviewStatus(CoercibleEnum):
    PENDING = "pending"
    APPROVED = "approved"
    RECLASSIFIED = "reclassified"


class AnalysisJobStatus(CoercibleEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
