from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtWidgets import QApplication

from glucose_widget.config import ApplicationSettings
from glucose_widget.core.glucose import format_value
from glucose_widget.models import GlucoseSnapshot, GlucoseZone
from glucose_widget.ui.tray import TrayController


class AlarmManager:
    def __init__(self, settings: ApplicationSettings, tray: TrayController) -> None:
        self._settings = settings
        self._tray = tray
        self._last_zone: GlucoseZone | None = None
        self._last_alarm_at: datetime | None = None
        self._last_seen_reading_at: datetime | None = None

    def apply_settings(self, settings: ApplicationSettings) -> None:
        self._settings = settings
        self._last_zone = None
        self._last_alarm_at = None
        self._last_seen_reading_at = None

    def evaluate(
        self,
        snapshot: GlucoseSnapshot,
        zone: GlucoseZone,
        *,
        is_stale: bool,
    ) -> None:
        if self._last_seen_reading_at == snapshot.latest.timestamp:
            return
        self._last_seen_reading_at = snapshot.latest.timestamp

        if zone == GlucoseZone.IN_RANGE:
            self._last_zone = zone
            self._last_alarm_at = None
            return

        if not self._settings.alarm.enabled or is_stale:
            self._last_zone = zone
            return

        now = datetime.now().astimezone()
        zone_changed = zone != self._last_zone
        repeat_minutes = self._settings.alarm.repeat_minutes
        repeat_due = (
            repeat_minutes > 0
            and self._last_alarm_at is not None
            and now - self._last_alarm_at >= timedelta(minutes=repeat_minutes)
        )
        should_alarm = self._last_alarm_at is None or zone_changed or repeat_due
        self._last_zone = zone

        if not should_alarm:
            return

        self._last_alarm_at = now
        value = format_value(
            snapshot.latest.value_mg_dl,
            self._settings.glucose.display_unit,
        )
        if zone == GlucoseZone.LOW:
            title = "Low glucose"
        else:
            title = "High glucose"
        message = f"{value} {self._settings.glucose.display_unit}"

        if self._settings.alarm.sound:
            QApplication.beep()
        if self._settings.alarm.tray_notification:
            self._tray.show_warning(title, message)
