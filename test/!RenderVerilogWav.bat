@echo off
setlocal

set "TEST_DIR=%~dp0"
set "REPO_DIR=%TEST_DIR%.."
set "PYTHON=%REPO_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Missing project Python environment:
    echo   "%PYTHON%"
    echo.
    echo Create it from the repository root with:
    echo   py -3 -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r test\requirements.txt
    exit /b 1
)

pushd "%REPO_DIR%"
"%PYTHON%" test\run_cocotb.py render-wav
set "RESULT=%ERRORLEVEL%"
popd

if not "%RESULT%"=="0" (
    echo.
    echo WAV render failed.
    exit /b %RESULT%
)

echo.
echo Wrote "%TEST_DIR%chipsynth_render.wav"
