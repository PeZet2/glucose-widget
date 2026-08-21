# Nightscout Widget

Mały, bezramkowy widget „always on top” dla Windows, który pobiera ostatnie odczyty z Nightscout i pokazuje:

- bieżącą glikemię,
- deltę względem odczytu sprzed `N` pomiarów, np. `+14 (-3)`,
- strzałkę trendu,
- godzinę odczytu,
- kolor stanu: zielony w zakresie, bursztynowy powyżej progu, czerwony poniżej progu.

Domyślny rozmiar okna to **172 × 100 px**, czyli mniej więcej wielkość czerwonej ramki z przekazanego zrzutu ekranu.

> **Ważne:** to pomocniczy, prywatny widget, a nie wyrób medyczny. Nie używaj go jako jedynego źródła decyzji terapeutycznych ani jedynego alarmu. Awaria sieci, Nightscout, systemu powiadomień lub samej aplikacji może opóźnić albo uniemożliwić pokazanie danych.

## Zgodność z Windows PowerShell 5.1

Skrypty `scripts/*.ps1` są zapisane wyłącznie znakami ASCII i z końcami linii CRLF. Dzięki temu działają także w standardowym Windows PowerShell 5.1, który potrafi błędnie odczytać pliki UTF-8 bez znacznika BOM.

## Najszybsze uruchomienie na Windows

Wymagany jest jeden z wariantów:

- `uv`, albo
- Python 3.11+ dostępny jako `py` lub `python`.

1. Rozpakuj projekt.
2. Uruchom `START_WINDOWS.bat`.
3. Przy pierwszym uruchomieniu aplikacja utworzy pliki:

   ```text
   %APPDATA%\NightscoutWidget\config.toml
   %APPDATA%\NightscoutWidget\secrets.toml
   ```

4. Kliknij prawym przyciskiem ikonę kropli w trayu i wybierz:
   - `Otwórz config.toml`,
   - `Otwórz secrets.toml`.
5. Uzupełnij adres Nightscout i dane dostępowe.
6. Zapisz pliki i wybierz `Przeładuj konfigurację` albo uruchom aplikację ponownie.

Do diagnostyki uruchom `RUN_DEBUG_WINDOWS.bat`. Log znajduje się w katalogu zwracanym przez `platformdirs`, standardowo pod lokalnym profilem użytkownika, w folderze `NightscoutWidget`.

## Minimalna konfiguracja

`config.toml`:

```toml
[nightscout]
base_url = "https://twoja-instancja-nightscout.example.com"
auth_mode = "auto"
verify_tls = true
```

`secrets.toml` — zalecany osobny token tylko do odczytu:

```toml
[nightscout]
access_token = "nazwa-tokena-xxxxxxxxxxxxxxxx"
api_secret = ""
api_secret_is_sha1 = false
```

Alternatywnie możesz użyć surowego `API_SECRET`:

```toml
[nightscout]
access_token = ""
api_secret = "twoj-surowy-api-secret"
api_secret_is_sha1 = false
```

Aplikacja sama obliczy małymi literami SHA-1 wymagany przez API v1. Gdy podajesz już gotowy, 40-znakowy hash, ustaw `api_secret_is_sha1 = true`.

## Najważniejsze ustawienia

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

`max_retries = 3` oznacza trzy dodatkowe próby po pierwszym nieudanym wywołaniu. Każda następuje domyślnie po 15 sekundach. Po wyczerpaniu retry aplikacja czeka pełne `poll_interval_seconds`.

Błędy konfiguracji i uwierzytelnienia nie są bez sensu ponawiane co 15 sekund — po nich aplikacja wraca od razu do zwykłego interwału. Po poprawieniu plików wybierz `Przeładuj konfigurację`.

### Delta

`delta_lookback` jest w kodzie ograniczane do zakresu **1–10**. Aplikacja pobiera z Nightscout kilka najnowszych rekordów przy każdym odpytywaniu, więc delta jest dostępna od razu po uruchomieniu, bez czekania na zebranie lokalnej historii.

Dla `delta_lookback = 3`:

```text
+14 (-3)
```

oznacza, że obecna wartość jest o 14 jednostek wyższa niż wartość trzy pomiary temu.

### Alarm

Alarm może używać:

- systemowego dźwięku Windows,
- powiadomienia z traya.

Nie alarmuje ponownie dla dokładnie tego samego rekordu Nightscout. Dla kolejnych nowych rekordów poza zakresem może powtarzać alarm zgodnie z `repeat_minutes`. Wartość `0` oznacza alarm tylko przy wejściu w LOW/HIGH albo przy zmianie LOW ↔ HIGH.

Odczyt starszy niż `stale_after_minutes` jest oznaczany `!` i nie uruchamia alarmu.

### Opacity

`opacity` jest ograniczane do zakresu `0.20–1.00`. Przezroczyste jest tło karty, natomiast tekst pozostaje w pełni czytelny.

## Menu traya

Kliknięcie prawym przyciskiem ikony otwiera menu:

- `Zablokuj widget` / `Odblokuj widget` — blokuje lub pozwala przesuwać okno,
- `Pokaż widget` — przywraca i podnosi okno,
- `Otwórz w przeglądarce` — widoczne tylko przy skonfigurowanym `nightscout.base_url`; otwiera Nightscout w domyślnej przeglądarce,
- `Otwórz config.toml`,
- `Otwórz secrets.toml`,
- `Przeładuj konfigurację`,
- `Zakończ`.

Pozycja okna i stan blokady są zapisywane w `%APPDATA%\NightscoutWidget\state.json`. Gdy monitor zostanie odłączony, aplikacja wykryje pozycję poza ekranem i przeniesie widget na prawy dolny obszar aktywnego ekranu.

## Budowa EXE

Uruchom:

```text
BUILD_EXE_WINDOWS.bat
```

Wyniki:

```text
dist\NightscoutWidget\NightscoutWidget.exe
dist\NightscoutWidget-Windows.zip
```

Build jest typu `onedir`, a nie `onefile`. Dzięki temu start Qt jest szybszy i mniej podatny na problemy antywirusa związane z rozpakowywaniem aplikacji do katalogu tymczasowego.

## API Nightscout

Klient używa kompatybilnego endpointu API v1:

```text
/api/v1/entries/sgv.json?count=...
```

Obsługiwane tryby uwierzytelnienia:

- token dostępu wysyłany w nagłówku `api-secret`,
- surowy `API_SECRET`, lokalnie hashowany SHA-1,
- gotowy hash SHA-1,
- brak uwierzytelnienia dla publicznej instancji.

Token tylko do odczytu jest lepszy niż udostępnianie pełnego `API_SECRET`. Token utworzysz w Nightscout w `Admin Tools`, nadając mu rolę `readable`.

Dokumentacja Nightscout:

- https://nightscout.github.io/nightscout/admin_tools/
- https://nightscout.github.io/nightscout/security/

## Architektura

```text
src/nightscout_widget/
├── core/                 # API Nightscout i obliczenia, bez zależności od Windows
├── ui/                   # PySide6: widget, tray, polling w tle
├── os_integration/
│   ├── base.py
│   ├── generic.py        # minimalny fallback deweloperski
│   └── windows.py        # os.startfile i AppUserModelID
├── config.py
├── state.py
├── alarm.py
└── app.py
```

Folder nazywa się `os_integration`, a nie `platform`, aby nie zasłaniać standardowego modułu Pythona `platform`.

Kod wspólny jest przygotowany pod późniejsze dodanie dedykowanego `linux.py`. Obecna paczka i skrypty build są przeznaczone dla Windows; zachowanie „always on top”, traya i przezroczystości na Linuxie należy osobno sprawdzić na X11 i Waylandzie.

## Testy i lint

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

Możesz wskazać alternatywny katalog konfiguracji:

```bash
python -m nightscout_widget --config-dir ./portable-data
```

Albo tylko sprawdzić bieżącą lokalizację konfiguracji:

```bash
python -m nightscout_widget --print-config-dir
```

## Zmiany w 0.1.3

- Dodano `Otwórz w przeglądarce` bezpośrednio pod `Pokaż widget` w menu traya.
- Opcja jest widoczna tylko wtedy, gdy `nightscout.base_url` zawiera rzeczywisty adres Nightscout.
- Na Windows adres jest przekazywany do domyślnej przeglądarki przez mechanizm powłoki systemowej; uruchomiona przeglądarka standardowo otwiera go w nowej zakładce.
- Widoczność opcji aktualizuje się także po `Przeładuj konfigurację`.

## Zmiany w 0.1.2

- Naprawiono zamykanie aplikacji z menu traya: widget i ikona traya są teraz ukrywane/zamykane przed zakończeniem pętli Qt.
- Dodano ochronę przed wielokrotnym wywołaniem procedury zamykania.
- Przy zatrzymaniu odpytywania usuwane są oczekujące zadania z puli Qt.
