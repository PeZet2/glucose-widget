from __future__ import annotations

import sys

from glucose_widget.os_integration.base import DesktopIntegration
from glucose_widget.os_integration.generic import GenericDesktopIntegration
from glucose_widget.os_integration.windows import WindowsDesktopIntegration


def create_desktop_integration() -> DesktopIntegration:
    if sys.platform == "win32":
        return WindowsDesktopIntegration()
    # This is only a minimal fallback for development. A dedicated Linux
    # implementation can later be added without changing the core or UI.
    return GenericDesktopIntegration()
