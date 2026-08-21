from __future__ import annotations

import logging
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from nightscout_widget.constants import DEFAULT_WINDOW_HEIGHT, DEFAULT_WINDOW_WIDTH

logger = logging.getLogger(__name__)

_ALLOWED_AUTH_MODES = {"auto", "token", "api_secret", "none"}
_ALLOWED_UNITS = {"mg/dL", "mmol/L"}
_SHA1_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class ConfigurationError(ValueError):
    """Raised when a user configuration file cannot be used."""


@dataclass(frozen=True, slots=True)
class NightscoutSettings:
    base_url: str = ""
    auth_mode: str = "auto"
    verify_tls: bool = True


@dataclass(frozen=True, slots=True)
class NetworkSettings:
    poll_interval_seconds: int = 120
    request_timeout_seconds: float = 10.0
    retry_delay_seconds: int = 15
    max_retries: int = 3


@dataclass(frozen=True, slots=True)
class GlucoseSettings:
    low: float = 70.0
    high: float = 180.0
    display_unit: str = "mg/dL"
    delta_lookback: int = 1
    stale_after_minutes: int = 15


@dataclass(frozen=True, slots=True)
class WidgetSettings:
    width: int = DEFAULT_WINDOW_WIDTH
    height: int = DEFAULT_WINDOW_HEIGHT
    opacity: float = 0.94
    start_locked: bool = False
    always_on_top: bool = True
    show_reading_time: bool = True


@dataclass(frozen=True, slots=True)
class AlarmSettings:
    enabled: bool = False
    sound: bool = True
    tray_notification: bool = True
    repeat_minutes: int = 10


@dataclass(frozen=True, slots=True)
class SecretsSettings:
    access_token: str = ""
    api_secret: str = ""
    api_secret_is_sha1: bool = False


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    nightscout: NightscoutSettings = NightscoutSettings()
    network: NetworkSettings = NetworkSettings()
    glucose: GlucoseSettings = GlucoseSettings()
    widget: WidgetSettings = WidgetSettings()
    alarm: AlarmSettings = AlarmSettings()
    secrets: SecretsSettings = SecretsSettings()


def default_settings() -> ApplicationSettings:
    return ApplicationSettings()


def load_settings(config_path: Path, secrets_path: Path) -> ApplicationSettings:
    config = _load_toml(config_path, required=True)
    secrets = _load_toml(secrets_path, required=True)

    ns = _table(config, "nightscout")
    network = _table(config, "network")
    glucose = _table(config, "glucose")
    widget = _table(config, "widget")
    alarm = _table(config, "alarm")
    secret_ns = _table(secrets, "nightscout")

    auth_mode = _string(ns, "auth_mode", "auto").lower()
    if auth_mode not in _ALLOWED_AUTH_MODES:
        raise ConfigurationError(
            f"nightscout.auth_mode musi być jednym z: {', '.join(sorted(_ALLOWED_AUTH_MODES))}."
        )

    display_unit = _string(glucose, "display_unit", "mg/dL")
    normalized_unit = _normalize_unit(display_unit)

    low = _number(glucose, "low", 70.0)
    high = _number(glucose, "high", 180.0)
    if low >= high:
        raise ConfigurationError("glucose.low musi być mniejsze niż glucose.high.")

    delta_lookback_raw = _integer(glucose, "delta_lookback", 1)
    delta_lookback = _clamp_int(
        "glucose.delta_lookback", delta_lookback_raw, minimum=1, maximum=10
    )

    opacity_raw = _number(widget, "opacity", 0.94)
    opacity = _clamp_float("widget.opacity", opacity_raw, minimum=0.20, maximum=1.0)

    access_token = _string(secret_ns, "access_token", "").strip()
    if access_token.lower().startswith("token="):
        access_token = access_token[6:].strip()

    api_secret = _string(secret_ns, "api_secret", "").strip()
    api_secret_is_sha1 = _boolean(secret_ns, "api_secret_is_sha1", False)
    if api_secret_is_sha1 and api_secret and not _SHA1_RE.fullmatch(api_secret):
        raise ConfigurationError(
            "nightscout.api_secret_is_sha1=true, ale api_secret nie jest 40-znakowym SHA-1."
        )

    settings = ApplicationSettings(
        nightscout=NightscoutSettings(
            base_url=_string(ns, "base_url", "").strip(),
            auth_mode=auth_mode,
            verify_tls=_boolean(ns, "verify_tls", True),
        ),
        network=NetworkSettings(
            poll_interval_seconds=_bounded_int(
                network, "poll_interval_seconds", 120, minimum=5, maximum=86_400
            ),
            request_timeout_seconds=_bounded_float(
                network, "request_timeout_seconds", 10.0, minimum=1.0, maximum=120.0
            ),
            retry_delay_seconds=_bounded_int(
                network, "retry_delay_seconds", 15, minimum=1, maximum=3_600
            ),
            max_retries=_bounded_int(network, "max_retries", 3, minimum=0, maximum=10),
        ),
        glucose=GlucoseSettings(
            low=low,
            high=high,
            display_unit=normalized_unit,
            delta_lookback=delta_lookback,
            stale_after_minutes=_bounded_int(
                glucose, "stale_after_minutes", 15, minimum=1, maximum=1_440
            ),
        ),
        widget=WidgetSettings(
            width=_bounded_int(widget, "width", DEFAULT_WINDOW_WIDTH, minimum=130, maximum=600),
            height=_bounded_int(widget, "height", DEFAULT_WINDOW_HEIGHT, minimum=80, maximum=400),
            opacity=opacity,
            start_locked=_boolean(widget, "start_locked", False),
            always_on_top=_boolean(widget, "always_on_top", True),
            show_reading_time=_boolean(widget, "show_reading_time", True),
        ),
        alarm=AlarmSettings(
            enabled=_boolean(alarm, "enabled", False),
            sound=_boolean(alarm, "sound", True),
            tray_notification=_boolean(alarm, "tray_notification", True),
            repeat_minutes=_bounded_int(alarm, "repeat_minutes", 10, minimum=0, maximum=1_440),
        ),
        secrets=SecretsSettings(
            access_token=access_token,
            api_secret=api_secret,
            api_secret_is_sha1=api_secret_is_sha1,
        ),
    )

    _validate_auth(settings)
    return settings


def _validate_auth(settings: ApplicationSettings) -> None:
    mode = settings.nightscout.auth_mode
    if mode == "token" and not settings.secrets.access_token:
        raise ConfigurationError(
            "nightscout.auth_mode='token', ale secrets.toml nie zawiera access_token."
        )
    if mode == "api_secret" and not settings.secrets.api_secret:
        raise ConfigurationError(
            "nightscout.auth_mode='api_secret', ale secrets.toml nie zawiera api_secret."
        )


def _load_toml(path: Path, *, required: bool) -> dict[str, Any]:
    if not path.exists():
        if required:
            raise ConfigurationError(f"Brak pliku konfiguracyjnego: {path}")
        return {}
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"Niepoprawny TOML w {path.name}: {exc}") from exc
    except OSError as exc:
        raise ConfigurationError(f"Nie można odczytać {path}: {exc}") from exc


def _table(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"Sekcja [{key}] musi być tabelą TOML.")
    return value


def _string(data: Mapping[str, Any], key: str, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} musi być tekstem.")
    return value


def _boolean(data: Mapping[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} musi mieć wartość true albo false.")
    return value


def _number(data: Mapping[str, Any], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{key} musi być liczbą.")
    return float(value)


def _integer(data: Mapping[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} musi być liczbą całkowitą.")
    return value


def _bounded_int(
    data: Mapping[str, Any],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    return _clamp_int(key, _integer(data, key, default), minimum=minimum, maximum=maximum)


def _bounded_float(
    data: Mapping[str, Any],
    key: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    return _clamp_float(key, _number(data, key, default), minimum=minimum, maximum=maximum)


def _clamp_int(name: str, value: int, *, minimum: int, maximum: int) -> int:
    clamped = max(minimum, min(maximum, value))
    if clamped != value:
        logger.warning(
            "%s=%s ograniczono do %s (zakres %s-%s).",
            name,
            value,
            clamped,
            minimum,
            maximum,
        )
    return clamped


def _clamp_float(name: str, value: float, *, minimum: float, maximum: float) -> float:
    clamped = max(minimum, min(maximum, value))
    if clamped != value:
        logger.warning(
            "%s=%s ograniczono do %s (zakres %s-%s).",
            name,
            value,
            clamped,
            minimum,
            maximum,
        )
    return clamped


def _normalize_unit(value: str) -> str:
    compact = value.strip().lower().replace(" ", "")
    aliases = {
        "mg/dl": "mg/dL",
        "mgdl": "mg/dL",
        "mmol/l": "mmol/L",
        "mmoll": "mmol/L",
    }
    normalized = aliases.get(compact)
    if normalized not in _ALLOWED_UNITS:
        raise ConfigurationError("glucose.display_unit musi być 'mg/dL' albo 'mmol/L'.")
    return normalized
