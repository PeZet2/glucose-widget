from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from nightscout_widget.constants import APP_DISPLAY_NAME
from nightscout_widget.models import GlucoseZone
from nightscout_widget.ui.icons import tray_icon


class TrayController(QObject):
    toggle_lock_requested = Signal()
    open_config_requested = Signal()
    open_secrets_requested = Signal()
    reload_requested = Signal()
    show_widget_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.icon = QSystemTrayIcon(tray_icon(), self)
        self.icon.setToolTip(APP_DISPLAY_NAME)

        self.menu = QMenu()
        self.lock_action = QAction("Zablokuj widget", self.menu)
        self.open_config_action = QAction("Otwórz config.toml", self.menu)
        self.open_secrets_action = QAction("Otwórz secrets.toml", self.menu)
        self.reload_action = QAction("Przeładuj konfigurację", self.menu)
        self.show_action = QAction("Pokaż widget", self.menu)
        self.quit_action = QAction("Zakończ", self.menu)

        self.menu.addAction(self.lock_action)
        self.menu.addAction(self.show_action)
        self.menu.addSeparator()
        self.menu.addAction(self.open_config_action)
        self.menu.addAction(self.open_secrets_action)
        self.menu.addAction(self.reload_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        self.icon.setContextMenu(self.menu)

        self.lock_action.triggered.connect(lambda _checked=False: self.toggle_lock_requested.emit())
        self.open_config_action.triggered.connect(
            lambda _checked=False: self.open_config_requested.emit()
        )
        self.open_secrets_action.triggered.connect(
            lambda _checked=False: self.open_secrets_requested.emit()
        )
        self.reload_action.triggered.connect(lambda _checked=False: self.reload_requested.emit())
        self.show_action.triggered.connect(lambda _checked=False: self.show_widget_requested.emit())
        self.quit_action.triggered.connect(lambda _checked=False: self.quit_requested.emit())
        self.icon.activated.connect(self._on_activated)

    def show(self) -> None:
        self.icon.show()

    def hide(self) -> None:
        self.icon.hide()

    def set_locked(self, locked: bool) -> None:
        self.lock_action.setText(
            "Odblokuj widget" if locked else "Zablokuj widget"
        )

    def set_zone(self, zone: GlucoseZone | None) -> None:
        self.icon.setIcon(tray_icon(zone))

    def set_tooltip(self, text: str) -> None:
        # Windows truncates long tray tooltips, so keep the useful part first.
        self.icon.setToolTip(text[:125])

    def show_information(self, title: str, message: str, timeout_ms: int = 7_000) -> None:
        self.icon.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            timeout_ms,
        )

    def show_warning(self, title: str, message: str, timeout_ms: int = 10_000) -> None:
        self.icon.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Warning,
            timeout_ms,
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_widget_requested.emit()
