$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "Instalowanie zależności build przez uv..."
    uv sync --extra build
    if ($LASTEXITCODE -ne 0) { throw "uv sync --extra build zakończył się błędem." }
    uv run pyinstaller --noconfirm --clean NightscoutWidget.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller zakończył się błędem." }
} else {
    $Python = & (Join-Path $PSScriptRoot "bootstrap_windows.ps1")
    & $Python -m pip install -e ".[build]"
    if ($LASTEXITCODE -ne 0) { throw "Instalacja PyInstaller zakończyła się błędem." }
    & $Python -m PyInstaller --noconfirm --clean NightscoutWidget.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller zakończył się błędem." }
}

$DistFolder = Join-Path $ProjectRoot "dist\NightscoutWidget"
Copy-Item README.md $DistFolder -Force
Copy-Item LICENSE $DistFolder -Force

$ZipPath = Join-Path $ProjectRoot "dist\NightscoutWidget-Windows.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $DistFolder "*") -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host ""
Write-Host "Gotowe:"
Write-Host "  EXE: $DistFolder\NightscoutWidget.exe"
Write-Host "  ZIP: $ZipPath"
