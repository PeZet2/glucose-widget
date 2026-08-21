$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = & (Join-Path $PSScriptRoot "bootstrap_windows.ps1")
& $Python -m nightscout_widget
exit $LASTEXITCODE
