from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import httpx
import pytest

from glucose_widget.config import (
    ApplicationSettings,
    NightscoutSettings,
    SecretsSettings,
)
from glucose_widget.core import nightscout_client as client_module
from glucose_widget.core.nightscout_client import (
    NightscoutClient,
    NightscoutConfigurationError,
    _build_auth_headers,
    _build_entries_endpoint,
)


def test_build_entries_endpoint() -> None:
    assert (
        _build_entries_endpoint("https://example.com")
        == "https://example.com/api/v1/entries/sgv.json"
    )
    assert (
        _build_entries_endpoint("https://example.com/api/v1")
        == "https://example.com/api/v1/entries/sgv.json"
    )


def test_endpoint_rejects_query_token() -> None:
    with pytest.raises(NightscoutConfigurationError, match="secrets.toml"):
        _build_entries_endpoint("https://example.com/?token=abc")


def test_raw_api_secret_is_hashed() -> None:
    settings = ApplicationSettings(
        nightscout=NightscoutSettings(base_url="https://example.com", auth_mode="api_secret"),
        secrets=SecretsSettings(api_secret="super-secret", api_secret_is_sha1=False),
    )
    headers = _build_auth_headers(settings)
    assert headers["api-secret"] == hashlib.sha1(b"super-secret").hexdigest()


def test_access_token_is_sent_in_api_secret_header() -> None:
    settings = ApplicationSettings(
        nightscout=NightscoutSettings(base_url="https://example.com", auth_mode="token"),
        secrets=SecretsSettings(access_token="readable-123"),
    )
    assert _build_auth_headers(settings) == {"api-secret": "readable-123"}


def test_fetch_snapshot_parses_and_sorts_response(monkeypatch: pytest.MonkeyPatch) -> None:
    now_ms = int(datetime.now(UTC).timestamp() * 1_000)
    payload = [
        {"sgv": 100, "date": now_ms - 10 * 60_000, "direction": "Flat"},
        {"sgv": 115, "date": now_ms, "direction": "FortyFiveUp"},
        {"sgv": 108, "date": now_ms - 5 * 60_000, "direction": "Flat"},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/entries/sgv.json"
        assert request.headers["api-secret"] == "readable-123"
        return httpx.Response(200, json=payload, request=request)

    transport = httpx.MockTransport(handler)
    real_client_class = httpx.Client

    def client_factory(**kwargs: object) -> httpx.Client:
        return real_client_class(transport=transport, **kwargs)

    monkeypatch.setattr(client_module.httpx, "Client", client_factory)

    settings = ApplicationSettings(
        nightscout=NightscoutSettings(base_url="https://example.com", auth_mode="token"),
        secrets=SecretsSettings(access_token="readable-123"),
    )
    snapshot = NightscoutClient(settings).fetch_snapshot()

    assert snapshot.latest.value_mg_dl == 115
    assert snapshot.latest.direction == "FortyFiveUp"
    assert snapshot.delta_mg_dl == 7
