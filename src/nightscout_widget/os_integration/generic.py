from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from nightscout_widget.os_integration.base import DesktopIntegration


class GenericDesktopIntegration(DesktopIntegration):
    def open_file(self, path: Path) -> None:
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            raise OSError(f"System nie potrafi otworzyć pliku: {path}")

    def open_url(self, url: str) -> None:
        if not QDesktopServices.openUrl(QUrl(url)):
            raise OSError(f"System nie potrafi otworzyć adresu: {url}")
