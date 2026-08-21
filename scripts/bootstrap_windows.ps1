$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Synchronizacja środowiska przez uv..."
    & uv sync | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "uv sync zakończył się błędem." }
    Write-Output (Join-Path $ProjectRoot ".venv\Scripts\python.exe")
    return
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Tworzenie .venv..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $VersionOk = & py -3 -c "import sys; print(int(sys.version_info >= (3, 11)))"
        if ($VersionOk -ne "1") { throw "Domyślny Python 3 jest starszy niż 3.11." }
        & py -3 -m venv .venv | Out-Host
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $VersionOk = & python -c "import sys; print(int(sys.version_info >= (3, 11)))"
        if ($VersionOk -ne "1") { throw "Python jest starszy niż 3.11." }
        & python -m venv .venv | Out-Host
    } else {
        throw "Nie znaleziono Pythona 3.11+ ani uv. Zainstaluj Python lub uv i uruchom skrypt ponownie."
    }
    if ($LASTEXITCODE -ne 0) { throw "Nie udało się utworzyć .venv." }
}

Write-Host "Instalowanie zależności..."
& $VenvPython -m pip install --upgrade pip | Out-Host
& $VenvPython -m pip install -e . | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Instalacja zależności zakończyła się błędem." }

Write-Output $VenvPython
