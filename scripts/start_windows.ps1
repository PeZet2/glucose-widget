$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = & (Join-Path $PSScriptRoot "bootstrap_windows.ps1")
$PythonW = Join-Path (Split-Path -Parent $Python) "pythonw.exe"
if (-not (Test-Path $PythonW)) { $PythonW = $Python }

Write-Host "Uruchamianie Nightscout Widget..."
Start-Process -FilePath $PythonW -ArgumentList @("-m", "nightscout_widget") -WorkingDirectory $ProjectRoot
