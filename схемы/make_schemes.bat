@echo off
rem Harvey Kompakt mini: wiring (WireViz) and bus interface (schemdraw). ASCII-only on purpose.
cd /d "%~dp0"
if not defined HARVEY_SCHEMES_VENV set "HARVEY_SCHEMES_VENV=C:\venvs\harvey-schemes"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY="%LOCALAPPDATA%\Programs\Python\Python314\python.exe""
if not exist "%HARVEY_SCHEMES_VENV%\Scripts\python.exe" (
  echo Creating Python environment in %HARVEY_SCHEMES_VENV% ...
  %PY% -m venv "%HARVEY_SCHEMES_VENV%" || goto fail
  "%HARVEY_SCHEMES_VENV%\Scripts\python.exe" -m pip install wireviz schemdraw matplotlib pyyaml || goto fail
)
where dot >nul 2>nul || set "PATH=C:\Program Files\Graphviz\bin;%PATH%"
where dot >nul 2>nul || (echo Graphviz not found. Install it: winget install Graphviz.Graphviz & goto fail)
"%HARVEY_SCHEMES_VENV%\Scripts\python.exe" make_wiring.py || goto fail
echo Done: mini_power.html, mini_bus.html, bus_buffer.svg
pause
exit /b 0
:fail
pause
exit /b 1
