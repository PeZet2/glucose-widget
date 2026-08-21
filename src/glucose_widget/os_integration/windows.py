from __future__ import annotations

import ctypes
import os
import subprocess
from pathlib import Path

from glucose_widget.constants import APP_USER_MODEL_ID
from glucose_widget.os_integration.base import DesktopIntegration


class WindowsDesktopIntegration(DesktopIntegration):
    def prepare_process(self) -> None:
        try:
            shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]
            shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except (AttributeError, OSError):
            # Cosmetic only: the application still works without an explicit AppUserModelID.
            pass

    def open_file(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(path)
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError:
            # .toml is not associated with an editor on every Windows installation.
            subprocess.Popen(["notepad.exe", str(path)], close_fds=True)

    def open_url(self, url: str) -> None:
        # ShellExecute (used by os.startfile on Windows) delegates the URL to the
        # system default browser. If that browser is already running, modern
        # browsers normally open the address in a new tab of the existing process.
        os.startfile(url)  # type: ignore[attr-defined]
