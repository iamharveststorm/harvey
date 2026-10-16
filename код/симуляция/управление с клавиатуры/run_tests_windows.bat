@echo off
chcp 65001 >nul
rem Harvey: headless checks of the simulation. ASCII-only: cmd misreads UTF-8 text after chcp.
cd /d "%~dp0"
if not defined HARVEY_VENV set "HARVEY_VENV=C:\venvs\harvey"
if not exist "%HARVEY_VENV%\Scripts\python.exe" ( echo Run run_windows.bat first & pause & exit /b 1 )
call "%HARVEY_VENV%\Scripts\activate.bat"
echo Quick control check without a window...
python harvey_teleop.py --test
echo.
echo Scenarios: surfaces and table edge (a few minutes)...
python harvey_scenarios.py surfaces edge
pause
