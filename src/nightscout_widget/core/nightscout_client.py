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
            raise NightscoutError("Nightscout request timed out.") from exc
        except httpx.RequestError as exc:
            raise NightscoutError(f"Nightscout connection error: {exc}") from exc

        if response.status_code in {401, 403}:
            raise NightscoutAuthenticationError(
                "Nightscout rejected the credentials (HTTP "
                f"{response.status_code}). Check auth_mode and secrets.toml."
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NightscoutError(
                f"Nightscout returned HTTP {response.status_code}."
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise NightscoutResponseError("Nightscout did not return valid JSON.") from exc

        if not isinstance(payload, list):
            raise NightscoutResponseError(
                "Unexpected Nightscout response format: expected a list of readings."
            )

        parsed: list[GlucoseReading] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            try:
                parsed.append(_parse_entry(entry))
            except (TypeError, ValueError, KeyError) as exc:
                logger.warning("Skipped invalid Nightscout record: %s", exc)

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
            raise NightscoutResponseError("Nightscout returned no valid SGV readings.")
        return unique


def _build_entries_endpoint(base_url: str) -> str:
    base_url = base_url.strip()
    if not base_url or "YOUR-NIGHTSCOUT" in base_url.upper():
        raise NightscoutConfigurationError(
            "Set nightscout.base_url in config.toml."
        )

    parts = urlsplit(base_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise NightscoutConfigurationError(
            "nightscout.base_url must be a complete http:// or https:// URL."
        )
    if parts.query or parts.fragment:
        raise NightscoutConfigurationError(
            "nightscout.base_url must not contain a query or fragment; "
            "put the token in secrets.toml."
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
        raise NightscoutConfigurationError("access_token is missing from secrets.toml.")
    if mode == "api_secret":
        raise NightscoutConfigurationError("api_secret is missing from secrets.toml.")
    raise NightscoutConfigurationError(f"Unsupported auth_mode: {mode}")


def _parse_entry(entry: dict[str, Any]) -> GlucoseReading:
    raw_value = entry.get("sgv")
    if raw_value is None:
        raise KeyError("missing sgv field")
    value = float(raw_value)
    if not 1 <= value <= 1_000:
        raise ValueError(f"sgv value outside a sensible range: {value}")

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

    raise KeyError("missing date/mills/dateString field")
