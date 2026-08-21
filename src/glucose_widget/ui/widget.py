from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QCloseEvent, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from glucose_widget.config import ApplicationSettings, WidgetSettings
from glucose_widget.core.glucose import (
    direction_arrow,
    format_delta,
    format_value,
    zone_for_value,
)
from glucose_widget.models import GlucoseSnapshot, GlucoseZone
from glucose_widget.ui.icons import NEUTRAL_COLOR, ZONE_COLORS


class GlucoseWidget(QWidget):
    position_changed = Signal(int, int)

    def __init__(self, settings: WidgetSettings) -> None:
        super().__init__()
        self._settings = settings
        self._locked = False
        self._drag_offset: QPoint | None = None
        self._last_snapshot: GlucoseSnapshot | None = None
        self._last_zone: GlucoseZone | None = None
        self._connection_error: str | None = None
        self._shutdown_requested = False

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._card = QFrame(self)
        self._card.setObjectName("card")

        self._value_label = QLabel("---")
        self._value_label.setObjectName("value")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._trend_label = QLabel("?")
        self._trend_label.setObjectName("trend")
        self._trend_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._delta_label = QLabel("— (-1)")
        self._delta_label.setObjectName("delta")
        self._delta_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._time_label = QLabel("waiting…")
        self._time_label.setObjectName("time")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        for drag_surface in (
            self._card,
            self._value_label,
            self._trend_label,
            self._delta_label,
            self._time_label,
        ):
            drag_surface.installEventFilter(self)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(4)
        top_row.addWidget(self._value_label, 1)
        top_row.addWidget(self._trend_label, 0)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(4)
        bottom_row.addWidget(self._delta_label, 1)
        bottom_row.addWidget(self._time_label, 0)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(11, 7, 10, 7)
        card_layout.setSpacing(0)
        card_layout.addLayout(top_row, 1)
        card_layout.addLayout(bottom_row, 0)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self._card)

        self.apply_widget_settings(settings)
        self.show_waiting()

    @property
    def locked(self) -> bool:
        return self._locked

    def apply_widget_settings(self, settings: WidgetSettings) -> None:
        self._settings = settings
        self.setFixedSize(settings.width, settings.height)
        self._apply_window_flags()
        self._refresh_style(self._last_zone)

    def _apply_window_flags(self) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        if self._settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        self._drag_offset = None
        self.setCursor(
            Qt.CursorShape.ArrowCursor if locked else Qt.CursorShape.SizeAllCursor
        )

    def show_waiting(self) -> None:
        self._last_snapshot = None
        self._last_zone = None
        self._connection_error = None
        self._value_label.setText("---")
        self._trend_label.setText("·")
        self._delta_label.setText("waiting for data")
        self._time_label.setText("")
        self._time_label.setStyleSheet("")
        self._set_tooltip("Waiting for the first Nightscout reading.")
        self._refresh_style(None)

    def show_configuration_error(self, message: str) -> None:
        self._last_snapshot = None
        self._last_zone = None
        self._connection_error = message
        self._value_label.setText("CFG")
        self._trend_label.setText("!")
        self._delta_label.setText("open config")
        self._time_label.setText("")
        self._time_label.setStyleSheet("")
        self._set_tooltip(message)
        self._refresh_style(None)

    def show_snapshot(self, snapshot: GlucoseSnapshot, settings: ApplicationSettings) -> bool:
        self._last_snapshot = snapshot
        self._connection_error = None
        glucose = settings.glucose
        zone = zone_for_value(
            snapshot.latest.value_mg_dl,
            low=glucose.low,
            high=glucose.high,
            unit=glucose.display_unit,
        )
        self._last_zone = zone

        self._value_label.setText(
            format_value(snapshot.latest.value_mg_dl, glucose.display_unit)
        )
        self._trend_label.setText(direction_arrow(snapshot.latest.direction))
        self._delta_label.setText(
            format_delta(snapshot.delta_mg_dl, glucose.display_unit, snapshot.lookback)
        )

        age_seconds = max(
            0.0,
            (datetime.now().astimezone() - snapshot.latest.timestamp).total_seconds(),
        )
        is_stale = age_seconds > glucose.stale_after_minutes * 60
        self._time_label.setStyleSheet("")
        reading_time = snapshot.latest.timestamp.strftime("%H:%M")
        unit = glucose.display_unit
        if settings.widget.show_reading_time:
            meta = f"{unit} {reading_time}"
        else:
            meta = unit
        self._time_label.setText(f"! {meta}" if is_stale else meta)

        stale_note = " The reading is stale." if is_stale else ""
        self._set_tooltip(
            f"{format_value(snapshot.latest.value_mg_dl, glucose.display_unit)} "
            f"{glucose.display_unit}, direction: {snapshot.latest.direction}, "
            f"time: {snapshot.latest.timestamp:%Y-%m-%d %H:%M:%S}."
            f"{stale_note}"
        )
        self._refresh_style(zone)
        return is_stale

    def show_connection_error(self, message: str) -> None:
        self._connection_error = message
        if self._last_snapshot is None:
            self._value_label.setText("ERR")
            self._trend_label.setText("!")
            self._delta_label.setText("no connection")
            self._last_zone = None
            self._refresh_style(None)
        self._time_label.setText("offline")
        self._time_label.setStyleSheet("color: #D32F2F; font-weight: 700;")
        self._set_tooltip(message)

    def _set_tooltip(self, message: str) -> None:
        self.setToolTip(message)
        self._card.setToolTip(message)
        for label in (
            self._value_label,
            self._trend_label,
            self._delta_label,
            self._time_label,
        ):
            label.setToolTip(message)

    def _refresh_style(self, zone: GlucoseZone | None) -> None:
        foreground = ZONE_COLORS.get(zone, NEUTRAL_COLOR)
        alpha = round(max(0.20, min(1.0, self._settings.opacity)) * 255)
        value_size = max(28, min(39, round(self._settings.height * 0.39)))
        trend_size = max(25, min(36, round(self._settings.height * 0.34)))
        meta_size = max(10, min(14, round(self._settings.height * 0.13)))

        self.setStyleSheet(
            f"""
            QFrame#card {{
                background-color: rgba(250, 250, 250, {alpha});
                border: 2px solid {foreground};
                border-radius: 11px;
            }}
            QLabel {{
                background: transparent;
                color: {foreground};
                font-family: "Segoe UI", "Noto Sans", sans-serif;
            }}
            QLabel#value {{
                font-size: {value_size}px;
                font-weight: 700;
            }}
            QLabel#trend {{
                font-family: "Segoe UI Symbol", "Noto Sans Symbols", sans-serif;
                font-size: {trend_size}px;
                font-weight: 600;
            }}
            QLabel#delta {{
                font-size: {meta_size}px;
                font-weight: 600;
            }}
            QLabel#time {{
                font-size: {max(9, meta_size - 1)}px;
                font-weight: 500;
            }}
            """
        )

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if isinstance(event, QMouseEvent):
            if self._begin_drag(event) or self._continue_drag(event) or self._finish_drag(event):
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._begin_drag(event):
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._continue_drag(event):
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not self._finish_drag(event):
            super().mouseReleaseEvent(event)

    def _begin_drag(self, event: QMouseEvent) -> bool:
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and not self._locked
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return True
        return False

    def _continue_drag(self, event: QMouseEvent) -> bool:
        if (
            event.type() == QEvent.Type.MouseMove
            and not self._locked
            and self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return True
        return False

    def _finish_drag(self, event: QMouseEvent) -> bool:
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and self._drag_offset is not None
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self._drag_offset = None
            self.position_changed.emit(self.x(), self.y())
            event.accept()
            return True
        return False

    def shutdown(self) -> None:
        """Close the widget as part of an explicit application shutdown."""
        self._shutdown_requested = True

        # Hide first so the UI disappears immediately even if a background
        # Nightscout request is still unwinding for a moment.
        self.hide()
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        # Ignore accidental/user close requests because the app is controlled
        # through the tray. Explicit shutdown is the only close we accept.
        if self._shutdown_requested:
            event.accept()
        else:
            event.ignore()
