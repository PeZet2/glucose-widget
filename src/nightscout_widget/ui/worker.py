from __future__ import annotations

import logging
from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from nightscout_widget.config import ApplicationSettings
from nightscout_widget.core.nightscout_client import (
    NightscoutAuthenticationError,
    NightscoutClient,
    NightscoutConfigurationError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FetchFailure:
    message: str
    retryable: bool


class FetchSignals(QObject):
    succeeded = Signal(int, object)
    failed = Signal(int, object)


class FetchWorker(QRunnable):
    def __init__(self, job_id: int, settings: ApplicationSettings) -> None:
        super().__init__()
        self.job_id = job_id
        self.settings = settings
        self.signals = FetchSignals()

    @Slot()
    def run(self) -> None:
        try:
            snapshot = NightscoutClient(self.settings).fetch_snapshot()
        except Exception as exc:  # Worker boundary: report all failures to the GUI thread.
            retryable = not isinstance(
                exc, (NightscoutConfigurationError, NightscoutAuthenticationError)
            )
            logger.exception("Pobranie danych z Nightscout nie powiodło się.")
            self.signals.failed.emit(
                self.job_id,
                FetchFailure(message=str(exc) or exc.__class__.__name__, retryable=retryable),
            )
            return

        self.signals.succeeded.emit(self.job_id, snapshot)
