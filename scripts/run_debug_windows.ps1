#requires -Version 5.1
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = (& (Join-Path $PSScriptRoot "bootstrap_windows.ps1") | Select-Object -Last 1)
if ([string]::IsNullOrWhiteSpace($Python)) {
    throw "bootstrap_windows.ps1 did not return a Python executable path."
}
$Python = $Python.Trim()

& $Python -m nightscout_widget
exit $LASTEXITCODE
