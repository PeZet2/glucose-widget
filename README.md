# Glucose Widget

A small, frameless, always-on-top Windows widget that fetches recent readings from Nightscout and displays:

- current glucose,
- the delta relative to the reading `N` measurements ago, for example `+14 (-3)`,
- a trend arrow,
- the reading time,
- a status color: green in range, amber above the threshold, and red below the threshold.

The default window size is **172 × 100 px**, approximately matching the red frame in the supplied screenshot.

> **Important:** This is a private helper widget, not a medical device. Do not use it as the sole source for treatment decisions or your only alarm. Network, Nightscout, notification-system, or application failures may delay or prevent data from being displayed.

## Windows PowerShell 5.1 compatibility

The `scripts/*.ps1` scripts use ASCII characters only and CRLF line endings, so they also work in standard Windows PowerShell 5.1, which can otherwise misread UTF-8 files without a BOM.

## Quick start on Windows

You need either:

- `uv`, or
- Python 3.11+ available as `py` or `python`.

1. Extract the project.
2. Run `START_WINDOWS.bat`.
3. On first launch, the application creates:

   ```text
   %APPDATA%\GlucoseWidget\config.toml
   %APPDATA%\GlucoseWidget\secrets.toml
   ```

4. Right-click the drop icon in the tray and choose:
   - `Open config.toml` for Nightscout url and other configuration
   - `Open secrets.toml` for secret keys and tokens
5. Fill the necessary data.
6. Save the files and choose `Reload configuration`, or restart the application.

For diagnostics, run `RUN_DEBUG_WINDOWS.bat`. The log is stored in the directory returned by `platformdirs`, normally under the user's local profile in `GlucoseWidget`.

## Minimal configuration

`config.toml`:

```toml
[nightscout]
base_url = "https://your-nightscout-instance.example.com"
auth_mode = "auto"
verify_tls = true
```

`secrets.toml` — a separate read-only token is recommended:

```toml
[nightscout]
access_token = "token-name-xxxxxxxxxxxxxxxx"
api_secret = ""
api_secret_is_sha1 = false
```

Alternatively, use a raw `API_SECRET`:

```toml
[nightscout]
access_token = ""
api_secret = "your-raw-api-secret"
api_secret_is_sha1 = false
```

The application calculates the lowercase SHA-1 hash required by API v1. If you provide an existing 40-character hash, set `api_secret_is_sha1 = true`.

## Main settings

```toml
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
```

### Retry

`max_retries = 3` means three additional attempts after the first failed request. By default, each follows after 15 seconds. Once retries are exhausted, the application waits for the full `poll_interval_seconds` interval.

Configuration and authentication errors are not repeatedly retried every 15 seconds; after them, the application immediately returns to its regular interval. After fixing the files, choose `Reload configuration`.

### Delta

`delta_lookback` is limited in code to **1–10**. The application fetches several recent records from Nightscout on each poll, so the delta is available immediately after launch without waiting to build local history.

For `delta_lookback = 3`:

```text
+14 (-3)
```

This means the current value is 14 units higher than the value three measurements ago.

### Alarm

The alarm can use:

- the Windows system sound,
- a tray notification.

The same Nightscout record is not alarmed twice. For subsequent new out-of-range records, the alarm may repeat according to `repeat_minutes`. A value of `0` means alert only when entering LOW/HIGH or switching between LOW and HIGH.

A reading older than `stale_after_minutes` is marked with `!` and does not trigger an alarm.

### Opacity

`opacity` is limited to `0.20–1.00`. The card background is transparent while the text remains fully readable.

## Tray menu

Right-clicking the icon opens the menu:

- `Lock widget` / `Unlock widget` — locks or allows moving the window,
- `Show widget` — restores and raises the window,
- `Open in browser` — visible only when `nightscout.base_url` is configured; opens Nightscout in the default browser,
- `Open config.toml`,
- `Open secrets.toml`,
- `Reload configuration`,
- `Exit`.

The window position and lock state are saved in `%APPDATA%\GlucoseWidget\state.json`. If a monitor is disconnected, the application detects an off-screen position and moves the widget to the lower-right area of the active screen.

## Building the EXE

Run:

```text
BUILD_EXE_WINDOWS.bat
```

Output:

```text
dist\GlucoseWidget\GlucoseWidget.exe
dist\GlucoseWidget-Windows.zip
```

The build uses `onedir`, not `onefile`. This makes Qt start faster and reduces antivirus issues caused by extracting the application into a temporary directory.

## Nightscout API

The client uses the compatible API v1 endpoint:

```text
/api/v1/entries/sgv.json?count=...
```

Supported authentication modes:

- an access token sent in the `api-secret` header,
- a raw `API_SECRET` hashed locally with SHA-1,
- an existing SHA-1 hash,
- no authentication for a public instance.

A read-only token is preferable to sharing the full `API_SECRET`. Create a token in Nightscout under `Admin Tools` and give it the `readable` role.

Nightscout's Documentation:

- https://nightscout.github.io/nightscout/admin_tools/
- https://nightscout.github.io/nightscout/security/

## Architecture

```text
src/glucose_widget/
├── core/                 # Nightscout API and calculations, independent of Windows
├── ui/                   # PySide6: widget, tray, background polling
├── os_integration/
│   ├── base.py
│   ├── generic.py        # minimal developers fallback
│   └── windows.py        # os.startfile and AppUserModelID
├── config.py
├── state.py
├── alarm.py
└── app.py
```

The folder is named `os_integration`, rather than `platform`, to avoid shadowing Python's standard `platform` module.

The shared code is prepared for a future dedicated `linux.py`. The current package and build scripts target Windows; always-on-top behavior, the tray, and transparency on Linux should be checked separately on X11 and Wayland.

## Tests and lint

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

You can specify an alternative configuration directory:

```bash
python -m glucose_widget --config-dir ./portable-data
```

Or only print the current configuration location:

```bash
python -m glucose_widget --print-config-dir
```

