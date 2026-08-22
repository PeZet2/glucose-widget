from __future__ import annotations

from pathlib import Path

import pytest

from glucose_widget.config import ConfigurationError, load_settings


BASE_CONFIG = """
[nightscout]
base_url = "https://example.com"
auth_mode = "auto"
verify_tls = true

[network]
poll_interval_seconds = 120
request_timeout_seconds = 10
retry_delay_seconds = 15
max_retries = 3

[glucose]
display_unit = "mg/dL"
low = 70
high = 180
delta_lookback = 1
stale_after_minutes = 15

[widget]
width = 172
height = 100
opacity = 0.94
start_locked = false
always_on_top = true
show_reading_time = true

[alarm]
enabled = false
sound = true
tray_notification = true
repeat_minutes = 10
"""

BASE_SECRETS = """
[nightscout]
access_token = "token=readable-abc123"
api_secret = ""
api_secret_is_sha1 = false
"""


def _write_files(tmp_path: Path, config: str = BASE_CONFIG, secrets: str = BASE_SECRETS):
    config_path = tmp_path / "config.toml"
    secrets_path = tmp_path / "secrets.toml"
    config_path.write_text(config, encoding="utf-8")
    secrets_path.write_text(secrets, encoding="utf-8")
    return config_path, secrets_path


def test_load_settings_and_normalize_token(tmp_path: Path) -> None:
    config_path, secrets_path = _write_files(tmp_path)
    settings = load_settings(config_path, secrets_path)

    assert settings.network.poll_interval_seconds == 120
    assert settings.glucose.delta_lookback == 1
    assert settings.widget.width == 172
    assert settings.secrets.access_token == "readable-abc123"
    assert settings.alarm.low.sound is True
    assert settings.alarm.high.tray_notification is True


def test_alarm_levels_can_be_configured_independently(tmp_path: Path) -> None:
    config = BASE_CONFIG + """

[alarm.low]
enabled = true
sound = true
tray_notification = false

[alarm.high]
enabled = false
sound = false
tray_notification = true
"""
    config_path, secrets_path = _write_files(tmp_path, config=config)
    settings = load_settings(config_path, secrets_path)

    assert settings.alarm.low.enabled is True
    assert settings.alarm.low.sound is True
    assert settings.alarm.low.tray_notification is False
    assert settings.alarm.high.enabled is False
    assert settings.alarm.high.sound is False
    assert settings.alarm.high.tray_notification is True


def test_legacy_alarm_channel_options_apply_to_both_levels(tmp_path: Path) -> None:
    config = BASE_CONFIG.replace("sound = true", "sound = false").replace(
        "tray_notification = true", "tray_notification = false"
    )
    config_path, secrets_path = _write_files(tmp_path, config=config)
    settings = load_settings(config_path, secrets_path)

    assert settings.alarm.low.sound is False
    assert settings.alarm.high.sound is False
    assert settings.alarm.low.tray_notification is False
    assert settings.alarm.high.tray_notification is False


def test_delta_and_opacity_are_clamped(tmp_path: Path) -> None:
    config = BASE_CONFIG.replace("delta_lookback = 1", "delta_lookback = 99").replace(
        "opacity = 0.94", "opacity = 0.01"
    )
    config_path, secrets_path = _write_files(tmp_path, config=config)
    settings = load_settings(config_path, secrets_path)

    assert settings.glucose.delta_lookback == 10
    assert settings.widget.opacity == 0.20


def test_low_must_be_lower_than_high(tmp_path: Path) -> None:
    config = BASE_CONFIG.replace("low = 70", "low = 200")
    config_path, secrets_path = _write_files(tmp_path, config=config)

    with pytest.raises(ConfigurationError, match="low"):
        load_settings(config_path, secrets_path)


def test_token_mode_requires_token(tmp_path: Path) -> None:
    config = BASE_CONFIG.replace('auth_mode = "auto"', 'auth_mode = "token"')
    secrets = BASE_SECRETS.replace('access_token = "token=readable-abc123"', 'access_token = ""')
    config_path, secrets_path = _write_files(tmp_path, config=config, secrets=secrets)

    with pytest.raises(ConfigurationError, match="access_token"):
        load_settings(config_path, secrets_path)


def test_bundled_default_files_are_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from glucose_widget.paths import AppPaths

    monkeypatch.setenv("GLUCOSE_WIDGET_HOME", str(tmp_path))
    paths = AppPaths.discover()
    paths.ensure()
    settings = load_settings(paths.config_file, paths.secrets_file)

    assert settings.network.poll_interval_seconds == 120
    assert settings.network.retry_delay_seconds == 15
    assert settings.network.max_retries == 3
    assert settings.glucose.delta_lookback == 1
    assert settings.widget.width == 172
    assert settings.widget.height == 100
