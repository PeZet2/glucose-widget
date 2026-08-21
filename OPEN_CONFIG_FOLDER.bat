@echo off
set "CFG=%APPDATA%\NightscoutWidget"
if not exist "%CFG%" mkdir "%CFG%"
start "" "%CFG%"
