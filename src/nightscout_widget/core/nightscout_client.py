from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from nightscout_widget.config import ApplicationSettings
from nightscout_widget.core.glucose import build_snapshot
from nightscout_widget.models import GlucoseReading, GlucoseSnapshot

logger = logging.getLogger(__name__)


class NightscoutError(RuntimeError):
    """Base Nightscout client error."""


class NightscoutConfigurationError(NightscoutError):
    """The local Nightscout connection configuration is incomplete."""


class NightscoutAuthenticationError(NightscoutError):
    """Nightscout rejected the configured credentials."""


class NightscoutResponseError(NightscoutError):
    """Nightscout returned malformed or unusable data."""


class NightscoutClient:
    def __init__(self, settings: ApplicationSettings) -> None:
        self._settings = settings
        self._endpoint = _build_entries_endpoint(settings.nightscout.base_url)
        self._headers = _build_auth_headers(settings)

    def fetch_snapshot(self) -> GlucoseSnapshot:
        lookback = self._settings.glucose.delta_lookback
        # A small cushion helps if the server contains duplicate timestamps or malformed rows.
        requested_count = min(50, max(lookback + 6, 12))
        readings = self._fetch_readings(requested_count)
        return build_snapshot(readings, lookback)

    def _fetch_readings(self, count: int) -> list[GlucoseReading]:
        try:
            with httpx.Client(
                timeout=self._settings.network.request_timeout_seconds,
                follow_redirects=True,
                verify=self._settings.nightscout.verify_tls,
                headers={"User-Agent": "NightscoutWidget/0.1"},
            ) as client:
                response = client.get(
                    self._endpoint,
                    params={"count": count},
                    headers=self._headers,
                )
        except httpx.TimeoutException as exc:
            raise NightscoutError("Przekroczono czas oczekiwania na Nightscout.") from exc
        except httpx.RequestError as exc:
            raise NightscoutError(f"Błąd połączenia z Nightscout: {exc}") from exc

        if response.status_code in {401, 403}:
            raise NightscoutAuthenticationError(
                "Nightscout odrzucił dane dostępowe (HTTP "
                f"{response.status_code}). Sprawdź auth_mode oraz secrets.toml."
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NightscoutError(
                f"Nightscout zwrócił HTTP {response.status_code}."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise NightscoutResponseError("Nightscout nie zwrócił prawidłowego JSON-a.") from exc

        if not isinstance(payload, list):
            raise NightscoutResponseError(
                "Nieoczekiwany format odpowiedzi Nightscout: oczekiwano listy odczytów."
            )

        parsed: list[GlucoseReading] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            try:
                parsed.append(_parse_entry(entry))
            except (TypeError, ValueError, KeyError) as exc:
                logger.warning("Pominięto nieprawidłowy rekord Nightscout: %s", exc)

        # De-duplicate by timestamp, keeping the first (newest response order is typical,
        # but we sort explicitly to avoid relying on server ordering).
        parsed.sort(key=lambda item: item.timestamp, reverse=True)
        unique: list[GlucoseReading] = []
        seen_timestamps: set[datetime] = set()
        for reading in parsed:
            if reading.timestamp in seen_timestamps:
                continue
            seen_timestamps.add(reading.timestamp)
            unique.append(reading)

        if not unique:
            raise NightscoutResponseError("Nightscout nie zwrócił prawidłowych odczytów SGV.")
        return unique


def _build_entries_endpoint(base_url: str) -> str:
    base_url = base_url.strip()
    if not base_url or "YOUR-NIGHTSCOUT" in base_url.upper():
        raise NightscoutConfigurationError(
            "Uzupełnij nightscout.base_url w config.toml."
        )

    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise NightscoutConfigurationError(
            "nightscout.base_url musi być pełnym adresem http:// albo https://."
        )
    if parts.query or parts.fragment:
        raise NightscoutConfigurationError(
            "nightscout.base_url nie powinien zawierać parametrów ani fragmentu; "
            "token wpisz w secrets.toml."
        )

    path = parts.path.rstrip("/")
    direct_suffix = "/api/v1/entries/sgv.json"
    if path.endswith(direct_suffix):
        endpoint_path = path
    elif path.endswith("/api/v1"):
        endpoint_path = f"{path}/entries/sgv.json"
    else:
        endpoint_path = f"{path}{direct_suffix}"

    return urlunsplit((parts.scheme, parts.netloc, endpoint_path, "", ""))


def _build_auth_headers(settings: ApplicationSettings) -> dict[str, str]:
    mode = settings.nightscout.auth_mode
    secrets = settings.secrets

    if mode == "none":
        return {}

    if mode in {"auto", "token"} and secrets.access_token:
        return {"api-secret": secrets.access_token}

    if mode in {"auto", "api_secret"} and secrets.api_secret:
        secret = secrets.api_secret
        if secrets.api_secret_is_sha1:
            hashed_secret = secret.lower()
        else:
            hashed_secret = hashlib.sha1(secret.encode("utf-8")).hexdigest()
        return {"api-secret": hashed_secret}

    if mode == "auto":
        return {}
    if mode == "token":
        raise NightscoutConfigurationError("Brak access_token w secrets.toml.")
    if mode == "api_secret":
        raise NightscoutConfigurationError("Brak api_secret w secrets.toml.")
    raise NightscoutConfigurationError(f"Nieobsługiwany auth_mode: {mode}")


def _parse_entry(entry: dict[str, Any]) -> GlucoseReading:
    raw_value = entry.get("sgv")
    if raw_value is None:
        raise KeyError("brak pola sgv")
    value = float(raw_value)
    if not 1 <= value <= 1_000:
        raise ValueError(f"wartość sgv poza sensownym zakresem: {value}")

    timestamp = _parse_timestamp(entry)
    direction = str(entry.get("direction") or "NONE")
    return GlucoseReading(value_mg_dl=value, timestamp=timestamp, direction=direction)


def _parse_timestamp(entry: dict[str, Any]) -> datetime:
    raw_timestamp = entry.get("date", entry.get("mills"))
    if raw_timestamp is not None:
        milliseconds = float(raw_timestamp)
        if milliseconds < 100_000_000_000:
            milliseconds *= 1_000
        return datetime.fromtimestamp(milliseconds / 1_000, tz=UTC).astimezone()

    date_string = entry.get("dateString")
    if isinstance(date_string, str) and date_string.strip():
        normalized = date_string.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone()

    raise KeyError("brak pola date/mills/dateString")
