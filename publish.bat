@echo off
REM NuoYi - Build and upload to PyPI
REM Usage: publish.bat [test|prod]

setlocal enabledelayedexpansion

set TARGET=%1
if "%TARGET%"=="" set TARGET=test

cd /d "%~dp0"

echo === NuoYi PyPI Publisher ===

REM Read version
for /f "delims=" %%v in ('python -c "exec(open('src/nuoyi/__init__.py').read());print(__version__)"') do set VERSION=%%v
echo Version: %VERSION%

REM Step 1: Clean
echo.
echo [1/4] Cleaning old builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
for /d %%d in (src\*.egg-info) do rmdir /s /q "%%d"

REM Step 2: Install build tools
echo [2/4] Checking build tools...
python -m pip install --quiet build twine

REM Step 3: Build
echo [3/4] Building sdist and wheel...
python -m build

echo.
echo Built files:
dir /b dist\

REM Step 4: Upload
echo.
if "%TARGET%"=="prod" (
    echo [4/4] Uploading to PyPI (production^)...
    echo WARNING: This will publish to the real PyPI!
    set /p confirm="Continue? [y/N] "
    if /i "!confirm!"=="y" (
        python -m twine upload dist\*
        echo.
        echo Done! Install with: pip install nuoyi==%VERSION%
    ) else (
        echo Cancelled.
    )
) else if "%TARGET%"=="test" (
    echo [4/4] Uploading to TestPyPI...
    python -m twine upload --repository testpypi dist\*
    echo.
    echo Done! Test install with:
    echo   pip install -i https://test.pypi.org/simple/ nuoyi==%VERSION%
) else (
    echo [4/4] Skipping upload (unknown target: %TARGET%^)
    echo Usage: publish.bat [test^|prod]
)

endlocal
