from __future__ import annotations

from datetime import UTC, datetime, timedelta

import glucose_widget.alarm as alarm_module
from glucose_widget.alarm import AlarmManager
from glucose_widget.config import (
    AlarmLevelSettings,
    AlarmSettings,
    ApplicationSettings,
    GlucoseSettings,
)
from glucose_widget.models import GlucoseReading, GlucoseSnapshot, GlucoseZone


class FakeTray:
    def __init__(self) -> None:
        self.warnings: list[tuple[str, str]] = []

    def show_warning(self, title: str, message: str) -> None:
        self.warnings.append((title, message))


def _snapshot(value: float, minutes_ago: int = 0) -> GlucoseSnapshot:
    return GlucoseSnapshot(
        latest=GlucoseReading(
            value_mg_dl=value,
            timestamp=datetime.now(UTC) - timedelta(minutes=minutes_ago),
            direction="Flat",
        ),
        comparison=None,
        delta_mg_dl=None,
        lookback=1,
    )


def test_low_and_high_channels_use_distinct_outputs(monkeypatch) -> None:
    beeps: list[bool] = []
    monkeypatch.setattr(alarm_module.QApplication, "beep", lambda: beeps.append(True))
    tray = FakeTray()
    settings = ApplicationSettings(
        glucose=GlucoseSettings(),
        alarm=AlarmSettings(
            enabled=True,
            low=AlarmLevelSettings(sound=True, tray_notification=False),
            high=AlarmLevelSettings(sound=False, tray_notification=True),
            repeat_minutes=0,
        ),
    )
    manager = AlarmManager(settings, tray)

    manager.evaluate(_snapshot(60), GlucoseZone.LOW, is_stale=False)
    manager.evaluate(_snapshot(200), GlucoseZone.HIGH, is_stale=False)

    assert len(beeps) == 1
    assert tray.warnings == [("High glucose", "200 mg/dL")]


def test_disabled_level_does_not_alert(monkeypatch) -> None:
    beeps: list[bool] = []
    monkeypatch.setattr(alarm_module.QApplication, "beep", lambda: beeps.append(True))
    tray = FakeTray()
    settings = ApplicationSettings(
        alarm=AlarmSettings(
            enabled=True,
            low=AlarmLevelSettings(enabled=False),
            high=AlarmLevelSettings(enabled=True, sound=False, tray_notification=True),
        )
    )
    manager = AlarmManager(settings, tray)

    manager.evaluate(_snapshot(60), GlucoseZone.LOW, is_stale=False)

    assert beeps == []
    assert tray.warnings == []
