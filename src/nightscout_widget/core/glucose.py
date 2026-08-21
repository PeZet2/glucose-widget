from __future__ import annotations

from collections.abc import Sequence

from nightscout_widget.models import GlucoseReading, GlucoseSnapshot, GlucoseZone

_DIRECTION_ARROWS = {
    "DoubleUp": "⇈",
    "SingleUp": "↑",
    "FortyFiveUp": "↗",
    "Flat": "→",
    "FortyFiveDown": "↘",
    "SingleDown": "↓",
    "DoubleDown": "⇊",
    "NONE": "·",
    "NOT COMPUTABLE": "?",
    "RATE OUT OF RANGE": "?",
}


def build_snapshot(readings: Sequence[GlucoseReading], lookback: int) -> GlucoseSnapshot:
    lookback = max(1, min(10, int(lookback)))
    if not readings:
        raise ValueError("Nightscout nie zwrócił żadnych prawidłowych odczytów glikemii.")

    ordered = sorted(readings, key=lambda item: item.timestamp, reverse=True)
    latest = ordered[0]
    comparison = ordered[lookback] if len(ordered) > lookback else None
    delta = latest.value_mg_dl - comparison.value_mg_dl if comparison else None

    return GlucoseSnapshot(
        latest=latest,
        comparison=comparison,
        delta_mg_dl=delta,
        lookback=lookback,
    )


def direction_arrow(direction: str) -> str:
    return _DIRECTION_ARROWS.get(direction.strip(), "?")


def to_display_value(value_mg_dl: float, unit: str) -> float:
    if unit == "mmol/L":
        return value_mg_dl / 18.0
    return value_mg_dl


def zone_for_value(value_mg_dl: float, *, low: float, high: float, unit: str) -> GlucoseZone:
    value = to_display_value(value_mg_dl, unit)
    if value < low:
        return GlucoseZone.LOW
    if value > high:
        return GlucoseZone.HIGH
    return GlucoseZone.IN_RANGE


def format_value(value_mg_dl: float, unit: str) -> str:
    value = to_display_value(value_mg_dl, unit)
    return f"{value:.1f}" if unit == "mmol/L" else f"{value:.0f}"


def format_delta(delta_mg_dl: float | None, unit: str, lookback: int) -> str:
    if delta_mg_dl is None:
        return f"— (-{lookback})"

    delta = to_display_value(delta_mg_dl, unit)
    if unit == "mmol/L":
        return f"{delta:+.1f} (-{lookback})"
    return f"{delta:+.0f} (-{lookback})"
