@echo off
setlocal
rem Portas padrao: backend 43871, frontend 43873 (scripts\dev.ps1).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\dev.ps1" -OpenBrowser %*
pause
exit /b %ERRORLEVEL%
