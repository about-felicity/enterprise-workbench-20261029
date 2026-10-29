@echo off
setlocal
pushd "%~dp0"
if not exist "start_monitor.ps1" goto missing
if /I "%~1"=="--check" goto check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\start_monitor.ps1"
set "START_RESULT=%ERRORLEVEL%"
if not "%START_RESULT%"=="0" echo Startup failed. Please read the error above.
popd
pause
exit /b %START_RESULT%
:check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\start_monitor.ps1" -CheckPackage
set "START_RESULT=%ERRORLEVEL%"
popd
exit /b %START_RESULT%
:missing
echo ERROR: start_monitor.ps1 is missing from this folder.
echo Extract ALL files from the ZIP first. Do not run inside a ZIP preview.
echo Do not copy START.cmd alone. Keep it beside start_monitor.ps1.
echo If a security tool removed a file, check its notification before retrying.
echo Current folder:
cd
popd
if /I not "%~1"=="--check" pause
exit /b 2
