#requires -Version 5.1
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Synchronizing the environment with uv..."
    & uv sync | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "uv sync failed."
    }

    $UvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $UvPython)) {
        throw "uv sync completed, but .venv\Scripts\python.exe was not found."
    }

    Write-Output $UvPython
    return
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating .venv..."

    if (Get-Command py -ErrorAction SilentlyContinue) {
        $VersionOk = & py -3 -c "import sys; print(int(sys.version_info >= (3, 11)))"
        if ($LASTEXITCODE -ne 0 -or $VersionOk -ne "1") {
            throw "The default Python 3 version is older than 3.11."
        }
        & py -3 -m venv .venv | Out-Host
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $VersionOk = & python -c "import sys; print(int(sys.version_info >= (3, 11)))"
        if ($LASTEXITCODE -ne 0 -or $VersionOk -ne "1") {
            throw "Python is older than 3.11."
        }
        & python -m venv .venv | Out-Host
    }
    else {
        throw "Python 3.11+ and uv were not found. Install Python or uv, then run this script again."
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create .venv."
    }
}

Write-Host "Installing dependencies..."
& $VenvPython -m pip install --upgrade pip | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed."
}

& $VenvPython -m pip install -e . | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed."
}

Write-Output $VenvPython
