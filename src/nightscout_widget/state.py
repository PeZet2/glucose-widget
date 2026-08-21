from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WindowState:
    x: int | None = None
    y: int | None = None
    locked: bool | None = None


class StateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> WindowState:
        if not self._path.exists():
            return WindowState()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return WindowState(
                x=_optional_int(raw.get("x")),
                y=_optional_int(raw.get("y")),
                locked=_optional_bool(raw.get("locked")),
            )
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Nie można odczytać stanu okna: %s", exc)
            return WindowState()

    def save(self, state: WindowState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        try:
            temporary.write_text(
                json.dumps(asdict(state), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self._path)
        except OSError as exc:
            logger.warning("Nie można zapisać stanu okna: %s", exc)


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None
