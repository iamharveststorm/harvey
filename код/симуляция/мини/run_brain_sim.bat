@echo off
chcp 65001 >nul
rem Harvey Compact Mini: the brain (PC) drives Harvey in the simulation. Opens the MuJoCo window and the brain console. ASCII-only file.
cd /d "%~dp0"
if not defined HARVEY_VENV set "HARVEY_VENV=C:\venvs\harvey"
if not exist "%HARVEY_VENV%\Scripts\python.exe" goto nopy
call "%HARVEY_VENV%\Scripts\activate.bat"
echo Starting: the MuJoCo window opens, the brain opens in its own console. Type phrases there.
python mini_brain.py --with-brain %*
pause
exit /b 0
:nopy
echo Environment %HARVEY_VENV% not found. Run run_mini_windows.bat once to create it.
pause
exit /b 1
