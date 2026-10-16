@echo off
chcp 65001 >nul
rem Harvey: servo bench (STS3215). The file is kept ASCII-only: cmd misreads UTF-8 text after chcp.
cd /d "%~dp0"
rem Python environment lives outside OneDrive so OneDrive does not sync thousands of files.
if not defined HARVEY_BENCH_VENV set "HARVEY_BENCH_VENV=C:\venvs\harvey-bench"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python314\python.exe""
if not exist "%HARVEY_BENCH_VENV%\Scripts\python.exe" (
  echo Creating Python environment in %HARVEY_BENCH_VENV% ...
  %PY% -m venv "%HARVEY_BENCH_VENV%" || goto nopy
)
call "%HARVEY_BENCH_VENV%\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt || goto fail
echo.
echo Serial ports found:
python -c "from serial.tools import list_ports; [print('  ', p.device, '-', p.description) for p in list_ports.comports()] or print('   none - connect the FE-URT-1 adapter via USB')"
echo.
set "PORT="
set /p PORT=Adapter port (e.g. COM5) or SIM for simulation [Enter = SIM]:
if "%PORT%"=="" set "PORT=SIM"
if /I "%PORT%"=="SIM" (
  python -m harvey_bench.bench --sim
) else (
  python -m harvey_bench.bench --port %PORT%
)
pause
exit /b 0
:nopy
echo Python 3.10-3.14 not found. Install it from python.org and tick "Add python.exe to PATH".
pause
exit /b 1
:fail
echo Could not install packages. Check the internet connection.
pause
exit /b 1
