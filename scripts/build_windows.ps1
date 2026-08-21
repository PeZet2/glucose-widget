#requires -Version 5.1
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Installing build dependencies with uv..."
    & uv sync --extra build | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "uv sync --extra build failed."
    }

    & uv run pyinstaller --noconfirm --clean NightscoutWidget.spec | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }
}
else {
    $Python = (& (Join-Path $PSScriptRoot "bootstrap_windows.ps1") | Select-Object -Last 1)
    if ([string]::IsNullOrWhiteSpace($Python)) {
        throw "bootstrap_windows.ps1 did not return a Python executable path."
    }
    $Python = $Python.Trim()

    & $Python -m pip install -e ".[build]" | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller dependency installation failed."
    }

    & $Python -m PyInstaller --noconfirm --clean NightscoutWidget.spec | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }
}

$DistFolder = Join-Path $ProjectRoot "dist\NightscoutWidget"
if (-not (Test-Path $DistFolder)) {
    throw "Build output folder was not found: $DistFolder"
}

Copy-Item README.md $DistFolder -Force
Copy-Item LICENSE $DistFolder -Force

$ZipPath = Join-Path $ProjectRoot "dist\NightscoutWidget-Windows.zip"
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $DistFolder "*") -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host ""
Write-Host "Done:"
Write-Host "  EXE: $DistFolder\NightscoutWidget.exe"
Write-Host "  ZIP: $ZipPath"
