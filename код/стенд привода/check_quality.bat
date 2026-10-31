@echo off
rem Harvey bench: ub-mode code quality. ASCII-only on purpose.
rem   1. tests under coverage.py in the bench environment (crapper alone would call the
rem      Microsoft Store "python3" stub on Windows and score every function 0%%)
rem   2. crapper: complexity x coverage, goal CRAP under 10
rem   3. dryer: duplicated code, similarity 0.8 and above
rem   4. mutator (only with "mutate"): do the tests catch planted bugs. Slow: minutes per file.
rem Usage: check_quality.bat            - steps 1-3 for harvey_bench
rem        check_quality.bat mutate sts - also mutation testing of harvey_bench\sts.py
cd /d "%~dp0"
set PYTHONUTF8=1
set "Q=C:\venvs\harvey-quality\Scripts"
set "B=C:\venvs\harvey-bench\Scripts\python.exe"
if not exist "%Q%\crapper.exe" (echo Tools not found in %Q%. See CLAUDE.md, section ub-mode. & goto fail)
if not exist "%B%" (echo Bench environment not found. Run run_bench_windows.bat once. & goto fail)
"%B%" -m pip install -q -r requirements-dev.txt || goto fail
if not exist target\coverage\python mkdir target\coverage\python
"%B%" -m coverage run --data-file=target\coverage\python\.coverage --source=harvey_bench -m pytest -q tests || goto fail
"%B%" -m coverage lcov -q --data-file=target\coverage\python\.coverage -o target\coverage\python\lcov.info || goto fail
"%B%" -m coverage report --data-file=target\coverage\python\.coverage
"%Q%\crapper.exe" --use-existing-coverage --threshold 10 harvey_bench
"%Q%\dryer.exe" harvey_bench
if /i not "%~1"=="mutate" goto done
if "%~2"=="" (echo Usage: check_quality.bat mutate ^<module^>, for example: mutate sts & goto fail)
"%Q%\mutator.exe" --use-existing-coverage --max-workers 4 --timeout-factor 3 --test-command "%B% -m pytest -q -x tests" harvey_bench\%~2.py
:done
echo Reports: .metrics\crap.edn, .metrics\mutate\
pause
exit /b 0
:fail
pause
exit /b 1
