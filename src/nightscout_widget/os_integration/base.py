from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class DesktopIntegration(ABC):
    def prepare_process(self) -> None:
        """Apply process-level OS integration before QApplication is created."""

    @abstractmethod
    def open_file(self, path: Path) -> None:
        """Open a file with the user's default application."""

    @abstractmethod
    def open_url(self, url: str) -> None:
        """Open a URL in the user's default web browser."""
