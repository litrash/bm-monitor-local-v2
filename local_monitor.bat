@echo off
cd /d "%~dp0"

echo [%date% %time%] Starting local monitor...
echo.

set ZJ_PAGES=3

call .venv\Scripts\activate.bat
python unified_monitor.py

echo.
echo [%date% %time%] Done.
echo.
echo Press any key to close...
pause >nul