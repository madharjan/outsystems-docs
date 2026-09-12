@echo off
REM Build script for OutSystems-Docs MCP

setlocal enabledelayedexpansion
cd /d "%~dp0.."

REM Cache and .venv are commonly on different drives; hardlinking then isn't possible and
REM uv falls back to a full copy anyway, just with a noisy warning. Silence it.
set "UV_LINK_MODE=copy"

REM Resolve iscc.exe: PATH first (covers choco's iscc shim), then known install
REM locations for winget's per-user install and choco's Program Files install.
set "INNO_PATH="
for /f "delims=" %%I in ('where iscc 2^>nul') do if not defined INNO_PATH set "INNO_PATH=%%I"
if not defined INNO_PATH if exist "%USERPROFILE%\AppData\Local\Programs\Inno Setup 6\ISCC.exe" set "INNO_PATH=%USERPROFILE%\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
if not defined INNO_PATH if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "INNO_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined INNO_PATH if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "INNO_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined INNO_PATH set "INNO_PATH=%USERPROFILE%\AppData\Local\Programs\Inno Setup 6\ISCC.exe"

set "ISS_FILE=installer\outsystems-docs.iss"
set "DIST_DIR=dist\OutSystems-Docs"
set "SETUP_PATH=dist\OutSystems-Docs-Setup.exe"

if "%1"=="" (
    echo Usage: installer\build.cmd [all, installer] [--directml]
    echo.
    echo   all       - Build osdocs-mcp.exe and installer
    echo   installer - Build installer only
    echo   --directml - Swap onnxruntime for onnxruntime-directml ^(AMD/Intel/NVIDIA GPU via DirectML^)
    exit /b 1
)

if "%1"=="all" goto build_all
if "%1"=="installer" goto build_installer

echo ERROR: Unknown command '%1'
exit /b 1

:build_all
echo [*] Installing dependencies...
REM --reinstall-package onnxruntime: a prior --directml build swaps in onnxruntime-directml,
REM which shares onnxruntime's package directory. Uninstalling/swapping it back can leave
REM stale onnxruntime-*.dist-info metadata with the actual package files gone -- uv sync
REM trusts that metadata and skips reinstalling, so force it every time to guarantee a
REM working onnxruntime regardless of --directml having been used before.
call uv sync --reinstall-package onnxruntime

set VENV_PYTHON=.venv\Scripts\python.exe
if not exist %VENV_PYTHON% (
    echo ERROR: .venv not found
    exit /b 1
)

if not exist dist\ mkdir dist\
if not exist !DIST_DIR! mkdir !DIST_DIR!

if "%2"=="--directml" (
    echo [*] Swapping onnxruntime for onnxruntime-directml ^(AMD/Intel/NVIDIA GPU via DirectML^)...
    call uv pip install --python %VENV_PYTHON% --force-reinstall --no-deps onnxruntime-directml
    if errorlevel 1 exit /b 1
)

echo [*] Building osdocs-mcp.exe...
call %VENV_PYTHON% -m nuitka --standalone --follow-imports --include-package=osdocs --include-package=hf_xet --include-package=onnxruntime --include-package-data=onnxruntime --output-dir=dist --output-file=osdocs-mcp.exe src\osdocs_mcp.py
REM Check the actual output file rather than trusting nuitka's exit code: a post-build
REM step can return nonzero even after successfully producing the exe.
if not exist dist\osdocs_mcp.dist\osdocs-mcp.exe (
    echo ERROR: Nuitka did not produce dist\osdocs_mcp.dist\osdocs-mcp.exe
    exit /b 1
)

goto organize

:build_installer
if not exist dist\osdocs_mcp.dist\osdocs-mcp.exe (
    echo ERROR: osdocs-mcp.exe not found. Run installer\build.cmd all first
    exit /b 1
)

:organize
echo [*] Organizing distribution...
if not exist !DIST_DIR! mkdir !DIST_DIR!
if exist dist\osdocs_mcp.dist xcopy dist\osdocs_mcp.dist !DIST_DIR! /E /I /Y 2>nul
if exist installer\README.md copy /Y installer\README.md !DIST_DIR! 2>nul
if exist installer\config.yaml copy /Y installer\config.yaml !DIST_DIR! 2>nul

echo [*] Synchronizing version from pyproject.toml...
%VENV_PYTHON% installer\sync-version.py
if errorlevel 1 (
    echo [WARNING] Failed to sync version, proceeding with existing version
)

echo [*] Building installer...
if not exist "!INNO_PATH!" (
    echo [SKIP] Inno Setup not found at !INNO_PATH!
    echo.
    echo To create Windows installer, install Inno Setup with:
    echo.
    echo   winget install --id JRSoftware.InnoSetup -e -s winget -i
    echo.
    echo Then run: installer\build.cmd installer
) else (
    if not exist "!ISS_FILE!" (
        echo [SKIP] Installer script not found: !ISS_FILE!
    ) else (
        echo [INFO] Building Windows installer...
        "!INNO_PATH!" "!ISS_FILE!"
        if errorlevel 1 (
            echo [ERROR] Inno Setup compilation failed
            exit /b 1
        ) else (
            echo [OK] Installer created: !SETUP_PATH!
        )
    )
)

echo.
echo [OK] Build complete
exit /b 0
