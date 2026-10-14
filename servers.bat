@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1" -OpenBrowser %*
exit /b %ERRORLEVEL%
