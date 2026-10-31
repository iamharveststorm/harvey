@echo off
rem Harvey bench: ub-mode code quality (crapper: CRAP under 10, dryer: duplicates). ASCII-only on purpose.
rem Usage: check_quality.bat [package]   default package: harvey_bench
cd /d "%~dp0"
set "V=C:\venvs\harvey-quality\Scripts"
if not exist "%V%\crapper.exe" (echo Tools not found in %V%. See CLAUDE.md, section ub-mode. & goto fail)
set "PKG=%~1"
if "%PKG%"=="" set "PKG=harvey_bench"
set PYTHONUTF8=1
"%V%\crapper.exe" --threshold 10 %PKG%
"%V%\dryer.exe" %PKG%
pause
exit /b 0
:fail
pause
exit /b 1
