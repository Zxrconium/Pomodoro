@echo off
REM ─────────────────────────────────────────────────────
REM  Tomodoro — Windows build script
REM  Requirements: Python 3.10+, pip
REM  Output:  dist\Tomodoro.exe  (standalone, no console)
REM ─────────────────────────────────────────────────────

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Building Tomodoro.exe ...
pyinstaller tomodoro.spec --clean --noconfirm

echo.
if exist dist\Tomodoro.exe (
    echo BUILD SUCCESS!
    echo Output: dist\Tomodoro.exe
) else (
    echo BUILD FAILED — check output above.
)
pause
