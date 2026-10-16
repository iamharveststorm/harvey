@echo off
chcp 65001 >nul
rem Harvey: rebuild drawings. Step 1 - models, views, dimensions (FreeCAD console).
rem Step 2 - PDF export (FreeCAD window opens and closes by itself).
rem FreeCAD console cannot open scripts from a non-Latin path, so a tiny runner in TEMP is used.
set "FC=%LOCALAPPDATA%\Programs\FreeCAD 1.1\bin"
set "HARVEY_DRAWINGS=%~dp0harvey_drawings.py"
set "RUNNER=%TEMP%\harvey_drawings_runner.py"
> "%RUNNER%" echo import os, runpy; runpy.run_path(os.environ["HARVEY_DRAWINGS"], run_name="__main__")
echo [1/2] FreeCAD: models, views, dimensions...
"%FC%\freecadcmd.exe" "%RUNNER%" >nul 2>nul
echo [2/2] FreeCAD: PDF export...
"%FC%\freecad.exe" "%RUNNER%"
del "%RUNNER%" >nul 2>nul
echo.
type "%~dp0_*.txt"
echo.
pause
