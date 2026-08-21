from __future__ import annotations

import logging
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal

from glucose_widget.config import ApplicationSettings
from glucose_widget.ui.worker import FetchFailure, FetchWorker

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PollFailureStatus:
    message: str
    retry_number: int
    max_retries: int
    next_delay_seconds: int
    will_retry: bool


class PollController(QObject):
    snapshot_received = Signal(object)
    failure_reported = Signal(object)
    fetch_started = Signal()

    def __init__(self, settings: ApplicationSettings, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.fetch_now)
        self._thread_pool = QThreadPool.globalInstance()
        self._retry_number = 0
        self._next_job_id = 0
        self._active_job_id: int | None = None
        self._stopped = True

    def start(self) -> None:
        self._stopped = False
        self.fetch_now()

    def stop(self) -> None:
        self._stopped = True
        self._timer.stop()
        self._active_job_id = None
        # Drop work that has not started yet. A currently running HTTP request
        # will finish on its own, but its result is invalidated above.
        self._thread_pool.clear()

    def apply_settings(self, settings: ApplicationSettings) -> None:
        self._settings = settings
        self._retry_number = 0
        self._timer.stop()
        # Invalidate any result from a worker started with the previous settings.
        self._active_job_id = None
        if not self._stopped:
            self.fetch_now()

    def fetch_now(self) -> None:
        if self._stopped or self._active_job_id is not None:
            return

        self._next_job_id += 1
        job_id = self._next_job_id
        self._active_job_id = job_id

        worker = FetchWorker(job_id, self._settings)
        worker.signals.succeeded.connect(self._on_success)
        worker.signals.failed.connect(self._on_failure)
        self.fetch_started.emit()
        self._thread_pool.start(worker)

    def _on_success(self, job_id: int, snapshot: object) -> None:
        if job_id != self._active_job_id:
            return
        self._active_job_id = None
        self._retry_number = 0
        self.snapshot_received.emit(snapshot)
        self._schedule(self._settings.network.poll_interval_seconds)

    def _on_failure(self, job_id: int, failure: FetchFailure) -> None:
        if job_id != self._active_job_id:
            return
        self._active_job_id = None

        can_retry = (
            failure.retryable
            and self._retry_number < self._settings.network.max_retries
        )
        if can_retry:
            self._retry_number += 1
            delay = self._settings.network.retry_delay_seconds
            retry_number = self._retry_number
        else:
            delay = self._settings.network.poll_interval_seconds
            retry_number = self._retry_number
            self._retry_number = 0

        status = PollFailureStatus(
            message=failure.message,
            retry_number=retry_number,
            max_retries=self._settings.network.max_retries,
            next_delay_seconds=delay,
            will_retry=can_retry,
        )
        logger.warning("%s Next attempt in %ss.", failure.message, delay)
        self.failure_reported.emit(status)
        self._schedule(delay)

    def _schedule(self, seconds: int) -> None:
        if not self._stopped:
            self._timer.start(max(1, seconds) * 1_000)
