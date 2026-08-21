from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from platformdirs import user_config_path, user_log_path

from nightscout_widget.constants import APP_NAME


@dataclass(frozen=True, slots=True)
class AppPaths:
    config_dir: Path
    config_file: Path
    secrets_file: Path
    state_file: Path
    log_dir: Path

    @classmethod
    def discover(cls) -> "AppPaths":
        override = os.environ.get("NIGHTSCOUT_WIDGET_HOME", "").strip()
        if override:
            config_dir = Path(override).expanduser().resolve()
            log_dir = config_dir / "logs"
        else:
            config_dir = Path(user_config_path(APP_NAME, appauthor=False, roaming=True))
            log_dir = Path(user_log_path(APP_NAME, appauthor=False))

        return cls(
            config_dir=config_dir,
            config_file=config_dir / "config.toml",
            secrets_file=config_dir / "secrets.toml",
            state_file=config_dir / "state.json",
            log_dir=log_dir,
        )

    def ensure(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._copy_default_if_missing("default_config.toml", self.config_file)
        self._copy_default_if_missing("default_secrets.toml", self.secrets_file)

        # Best effort: restrictive on POSIX, harmless on Windows.
        try:
            self.secrets_file.chmod(0o600)
        except OSError:
            pass

    @staticmethod
    def _copy_default_if_missing(resource_name: str, target: Path) -> None:
        if target.exists():
            return
        content = (
            resources.files("nightscout_widget.resources")
            .joinpath(resource_name)
            .read_text(encoding="utf-8")
        )
        target.write_text(content, encoding="utf-8")
