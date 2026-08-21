from __future__ import annotations

from datetime import UTC, datetime, timedelta

from nightscout_widget.core.glucose import (
    build_snapshot,
    direction_arrow,
    format_delta,
    format_value,
    zone_for_value,
)
from nightscout_widget.models import GlucoseReading, GlucoseZone


def _reading(value: float, minutes_ago: int, direction: str = "Flat") -> GlucoseReading:
    return GlucoseReading(
        value_mg_dl=value,
        timestamp=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        direction=direction,
    )


def test_delta_uses_nth_previous_reading() -> None:
    readings = [
        _reading(124, 0, "FortyFiveUp"),
        _reading(120, 5),
        _reading(116, 10),
        _reading(110, 15),
    ]

    snapshot = build_snapshot(readings, lookback=3)

    assert snapshot.latest.value_mg_dl == 124
    assert snapshot.comparison is not None
    assert snapshot.comparison.value_mg_dl == 110
    assert snapshot.delta_mg_dl == 14
    assert format_delta(snapshot.delta_mg_dl, "mg/dL", 3) == "+14 (-3)"


def test_lookback_is_limited_to_ten() -> None:
    readings = [_reading(100 + index, index * 5) for index in range(11)]
    snapshot = build_snapshot(readings, lookback=30)
    assert snapshot.lookback == 10


def test_units_zone_and_arrow() -> None:
    assert format_value(108, "mmol/L") == "6.0"
    assert format_delta(18, "mmol/L", 1) == "+1.0 (-1)"
    assert direction_arrow("SingleDown") == "↓"
    assert zone_for_value(65, low=70, high=180, unit="mg/dL") == GlucoseZone.LOW
    assert zone_for_value(120, low=70, high=180, unit="mg/dL") == GlucoseZone.IN_RANGE
    assert zone_for_value(200, low=70, high=180, unit="mg/dL") == GlucoseZone.HIGH
