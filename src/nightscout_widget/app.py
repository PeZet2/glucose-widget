from __future__ import annotations

import logging
import time
from pathlib import Path

from PySide6.QtCore import QObject, QRect
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from nightscout_widget.alarm import AlarmManager
from nightscout_widget.config import (
    ConfigurationError,
    default_settings,
    load_settings,
)
from nightscout_widget.constants import APP_DISPLAY_NAME
from nightscout_widget.core.glucose import (
    direction_arrow,
    format_value,
    zone_for_value,
)
from nightscout_widget.models import GlucoseSnapshot, GlucoseZone
from nightscout_widget.os_integration.base import DesktopIntegration
from nightscout_widget.paths import AppPaths
from nightscout_widget.state import StateStore
from nightscout_widget.ui.polling import PollController, PollFailureStatus
from nightscout_widget.ui.tray import TrayController
from nightscout_widget.ui.widget import GlucoseWidget

logger = logging.getLogger(__name__)


class NightscoutWidgetController(QObject):
    def __init__(
        self,
        application: QApplication,
        paths: AppPaths,
        integration: DesktopIntegration,
    ) -> None:
        super().__init__()
        self._application = application
        self._paths = paths
        self._integration = integration
        self._state_store = StateStore(paths.state_file)
        self._state = self._state_store.load()
        self._last_zone: GlucoseZone | None = None
        self._has_snapshot = False
        self._last_failure_message: str | None = None
        self._last_failure_notice_at = 0.0
        self._quitting = False

        try:
            self._settings = load_settings(paths.config_file, paths.secrets_file)
            initial_config_error: str | None = None
        except ConfigurationError as exc:
            logger.error("Błąd konfiguracji: %s", exc)
            self._settings = default_settings()
            initial_config_error = str(exc)

        self.widget = GlucoseWidget(self._settings.widget)
        locked = (
            self._state.locked
            if self._state.locked is not None
            else self._settings.widget.start_locked
        )
        self.widget.set_locked(locked)
        self._restore_or_choose_position()

        self.tray = TrayController(self)
        self.tray.set_locked(locked)
        self.tray.set_nightscout_url_available(self._has_configured_nightscout_url())
        self.alarm = AlarmManager(self._settings, self.tray)
        self.poller = PollController(self._settings, self)

        self._connect_signals()
        self.tray.show()
        self.widget.show()

        if initial_config_error:
            self.widget.show_configuration_error(initial_config_error)
            self.tray.set_tooltip(f"{APP_DISPLAY_NAME} — błąd konfiguracji")
            self.tray.show_warning("Błąd konfiguracji", initial_config_error)
        else:
            self.poller.start()

    def _connect_signals(self) -> None:
        self.widget.position_changed.connect(self._on_position_changed)
        self.tray.toggle_lock_requested.connect(self.toggle_lock)
        self.tray.open_config_requested.connect(
            lambda: self._open_file(self._paths.config_file)
        )
        self.tray.open_secrets_requested.connect(
            lambda: self._open_file(self._paths.secrets_file)
        )
        self.tray.open_nightscout_requested.connect(self.open_nightscout)
        self.tray.reload_requested.connect(self.reload_configuration)
        self.tray.show_widget_requested.connect(self.show_widget)
        self.tray.quit_requested.connect(self.quit)
        self.poller.snapshot_received.connect(self._on_snapshot)
        self.poller.failure_reported.connect(self._on_poll_failure)

    def toggle_lock(self) -> None:
        locked = not self.widget.locked
        self.widget.set_locked(locked)
        self.tray.set_locked(locked)
        self._state.locked = locked
        self._save_state()

    def reload_configuration(self) -> None:
        try:
            settings = load_settings(self._paths.config_file, self._paths.secrets_file)
        except ConfigurationError as exc:
            logger.error("Nie udało się przeładować konfiguracji: %s", exc)
            if not self._has_snapshot:
                self.widget.show_configuration_error(str(exc))
            self.tray.show_warning("Błąd konfiguracji", str(exc))
            return

        self._settings = settings
        self.widget.apply_widget_settings(settings.widget)
        self.widget.set_locked(self.widget.locked)
        self._ensure_widget_visible_on_a_screen()
        self.alarm.apply_settings(settings)
        self.tray.set_nightscout_url_available(self._has_configured_nightscout_url())

        # apply_settings starts a fresh fetch when the poller is running. The poller
        # is started explicitly here too, which covers recovery from an initial TOML error.
        self.poller.apply_settings(settings)
        self.poller.start()
        self.tray.show_information(
            "Nightscout Widget",
            "Konfiguracja została przeładowana.",
            timeout_ms=4_000,
        )

    def show_widget(self) -> None:
        self.widget.show()
        self.widget.raise_()

    def open_nightscout(self) -> None:
        url = self._settings.nightscout.base_url.strip()
        if not self._has_configured_nightscout_url():
            return
        try:
            self._integration.open_url(url)
        except OSError as exc:
            logger.exception("Nie można otworzyć Nightscout w przeglądarce: %s", url)
            self.tray.show_warning("Nie można otworzyć Nightscout", str(exc))

    def quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True

        self.poller.stop()
        self._state.x = self.widget.x()
        self._state.y = self.widget.y()
        self._state.locked = self.widget.locked
        self._save_state()

        # The widget used to ignore every closeEvent. QApplication.quit() stops
        # the event loop, but that did not guarantee that the still-live widget
        # disappeared immediately on Windows. Explicitly shut down both UI
        # surfaces first, then terminate the event loop.
        self.tray.hide()
        self.widget.shutdown()
        self._application.quit()

    def _on_snapshot(self, snapshot: object) -> None:
        if not isinstance(snapshot, GlucoseSnapshot):
            logger.error("Worker zwrócił nieznany typ wyniku: %r", type(snapshot))
            return

        self._has_snapshot = True
        self._last_failure_message = None
        self._last_failure_notice_at = 0.0
        glucose = self._settings.glucose
        zone = zone_for_value(
            snapshot.latest.value_mg_dl,
            low=glucose.low,
            high=glucose.high,
            unit=glucose.display_unit,
        )
        self._last_zone = zone
        is_stale = self.widget.show_snapshot(snapshot, self._settings)
        self.tray.set_zone(zone)

        value = format_value(snapshot.latest.value_mg_dl, glucose.display_unit)
        arrow = direction_arrow(snapshot.latest.direction)
        stale_suffix = " | odczyt nieaktualny" if is_stale else ""
        self.tray.set_tooltip(
            f"{value} {glucose.display_unit} {arrow} | "
            f"{snapshot.latest.timestamp:%H:%M}{stale_suffix}"
        )
        self.alarm.evaluate(snapshot, zone, is_stale=is_stale)

    def _on_poll_failure(self, status: object) -> None:
        if not isinstance(status, PollFailureStatus):
            return

        self.widget.show_connection_error(status.message)
        if not self._has_snapshot:
            self.tray.set_zone(None)

        if status.will_retry:
            retry_note = (
                f"retry {status.retry_number}/{status.max_retries} "
                f"za {status.next_delay_seconds}s"
            )
        else:
            retry_note = f"następna próba za {status.next_delay_seconds}s"
            now = time.monotonic()
            should_notify = (
                status.message != self._last_failure_message
                or now - self._last_failure_notice_at >= 30 * 60
            )
            if should_notify:
                self.tray.show_warning("Nightscout — błąd", status.message)
                self._last_failure_message = status.message
                self._last_failure_notice_at = now

        self.tray.set_tooltip(f"{APP_DISPLAY_NAME} — {retry_note}")

    def _has_configured_nightscout_url(self) -> bool:
        url = self._settings.nightscout.base_url.strip()
        return bool(url) and "YOUR-NIGHTSCOUT" not in url.upper()

    def _open_file(self, path: Path) -> None:
        try:
            self._integration.open_file(path)
        except OSError as exc:
            logger.exception("Nie można otworzyć pliku %s", path)
            self.tray.show_warning("Nie można otworzyć pliku", str(exc))

    def _on_position_changed(self, x: int, y: int) -> None:
        self._state.x = x
        self._state.y = y
        self._save_state()

    def _save_state(self) -> None:
        self._state_store.save(self._state)

    def _restore_or_choose_position(self) -> None:
        if self._state.x is not None and self._state.y is not None:
            self.widget.move(self._state.x, self._state.y)
            if self._is_widget_on_any_screen():
                return
        self._move_to_default_position()

    def _ensure_widget_visible_on_a_screen(self) -> None:
        if not self._is_widget_on_any_screen():
            self._move_to_default_position()

    def _is_widget_on_any_screen(self) -> bool:
        rect = QRect(
            self.widget.x(),
            self.widget.y(),
            self.widget.width(),
            self.widget.height(),
        )
        # Require a useful visible area, not merely a one-pixel intersection.
        for screen in QGuiApplication.screens():
            intersection = screen.availableGeometry().intersected(rect)
            if intersection.width() >= 40 and intersection.height() >= 30:
                return True
        return False

    def _move_to_default_position(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.widget.move(20, 20)
            return
        geometry = screen.availableGeometry()
        margin = 14
        x = geometry.right() - self.widget.width() - margin + 1
        y = geometry.bottom() - self.widget.height() - margin + 1
        self.widget.move(x, y)
        self._state.x = x
        self._state.y = y
        self._save_state()
