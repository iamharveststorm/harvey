@echo off
chcp 65001 >nul
rem Harvey: photorealistic window (Filament PBR) with the same control panel. ASCII-only: cmd misreads UTF-8 text after chcp.
cd /d "%~dp0"
rem Python environment lives outside OneDrive so OneDrive does not sync thousands of files.
if not defined HARVEY_VENV set "HARVEY_VENV=C:\venvs\harvey"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python314\python.exe""
if not exist "%HARVEY_VENV%\Scripts\python.exe" (
  echo [1/3] Creating Python environment in %HARVEY_VENV% ...
  %PY% -m venv "%HARVEY_VENV%" || goto nopy
)
call "%HARVEY_VENV%\Scripts\activate.bat"
echo [2/3] Installing MuJoCo and numpy (first time about a minute)...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || goto fail
echo [3/3] Starting: the photo window and the control panel will open.
python harvey_teleop.py --photo
pause
exit /b 0
:nopy
echo Python 3.10-3.14 not found. Install it from python.org and tick "Add python.exe to PATH".
pause
exit /b 1
:fail
echo Could not install packages. Check the internet connection and Python version (3.10-3.14).
pause
exit /b 1
