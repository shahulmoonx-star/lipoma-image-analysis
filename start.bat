@echo off
rem Double-click, or run "start.bat" in a terminal opened in this folder.
cd /d "%~dp0"
set LIPOMA_OWN_CONSOLE=0
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 run.py %*
  goto done
)
python --version >nul 2>nul
if %errorlevel%==0 (
  python run.py %*
  goto done
)
echo.
echo Python is not installed (or not on the PATH).
echo Install Python 3.11 or 3.12 (64-bit) from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" on the first screen. Then double-click start.bat again.
echo.
pause
exit /b 1
:done
if errorlevel 1 pause
