#requires -Version 5.1
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = (& (Join-Path $PSScriptRoot "bootstrap_windows.ps1") | Select-Object -Last 1)
if ([string]::IsNullOrWhiteSpace($Python)) {
    throw "bootstrap_windows.ps1 did not return a Python executable path."
}
$Python = $Python.Trim()

$PythonW = Join-Path (Split-Path -Parent $Python) "pythonw.exe"
if (-not (Test-Path $PythonW)) {
    $PythonW = $Python
}

Write-Host "Starting Glucose Widget..."
Start-Process -FilePath $PythonW -ArgumentList @("-m", "glucose_widget") -WorkingDirectory $ProjectRoot
