@echo off
set "CFG=%APPDATA%\GlucoseWidget"
if not exist "%CFG%" mkdir "%CFG%"
start "" "%CFG%"
