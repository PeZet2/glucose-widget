from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class GlucoseZone(str, Enum):
    LOW = "low"
    IN_RANGE = "in_range"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class GlucoseReading:
    value_mg_dl: float
    timestamp: datetime
    direction: str


@dataclass(frozen=True, slots=True)
class GlucoseSnapshot:
    latest: GlucoseReading
    comparison: GlucoseReading | None
    delta_mg_dl: float | None
    lookback: int
