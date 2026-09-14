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
    echo Usage: installer\build.cmd [all, installer]
    echo.
    echo   all       - Build osdocs-mcp.exe and installer
    echo   installer - Build installer only
    exit /b 1
)

if "%1"=="all" goto build_all
if "%1"=="installer" goto build_installer

echo ERROR: Unknown command '%1'
exit /b 1

:build_all
where uv >nul 2>nul
if errorlevel 1 (
    echo [*] uv not found, installing...
    winget install --id=astral-sh.uv -e --source winget
    if errorlevel 1 powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

echo [*] Installing dependencies...
REM --reinstall-package onnxruntime: uv sync trusts existing onnxruntime-*.dist-info
REM metadata and skips reinstalling even after the onnxruntime-directml swap below
REM overwrites the package files -- force it every time so the plain onnxruntime
REM package is always the clean starting point.
call uv sync --reinstall-package onnxruntime

set VENV_PYTHON=.venv\Scripts\python.exe
if not exist %VENV_PYTHON% (
    echo ERROR: .venv not found
    exit /b 1
)

if not exist dist\ mkdir dist\
if not exist !DIST_DIR! mkdir !DIST_DIR!

echo [*] Swapping onnxruntime for onnxruntime-directml ^(AMD/Intel/NVIDIA GPU via DirectML^)...
call uv pip install --python %VENV_PYTHON% --force-reinstall --no-deps onnxruntime-directml
if errorlevel 1 exit /b 1

REM Nuitka needs an MSVC C++ toolchain to compile the standalone exe. Detect it via
REM vswhere (installed alongside any VS product/Build Tools); install Build Tools with
REM the VC++ workload via winget if nothing satisfies that requirement.
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
set "MSVC_FOUND="
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%I in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "MSVC_FOUND=%%I"
)
if not defined MSVC_FOUND (
    echo [*] MSVC Build Tools not found, installing via winget...
    winget install --id Microsoft.VisualStudio.2022.BuildTools -e --source winget --override "--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
)

echo [*] Building osdocs-mcp.exe...
call %VENV_PYTHON% -m nuitka --standalone --assume-yes-for-downloads --follow-imports --include-package=osdocs --include-package=hf_xet --include-package=onnxruntime --include-package-data=onnxruntime --output-dir=dist --output-file=osdocs-mcp.exe src\osdocs_mcp.py
REM Check the actual output file rather than trusting nuitka's exit code: a post-build
REM step can return nonzero even after successfully producing the exe.
if not exist dist\osdocs_mcp.dist\osdocs-mcp.exe (
    echo ERROR: Nuitka did not produce dist\osdocs_mcp.dist\osdocs-mcp.exe
    exit /b 1
)

echo [*] Merging corporate CA certs into bundled certifi store...
set "CACERT=dist\osdocs_mcp.dist\certifi\cacert.pem"
call :merge_ca "installer\zscaler-ca.cert" "zscaler-ca.cert"
call :merge_ca "installer\cloudflare-gateway-ca.cert" "cloudflare-gateway-ca.cert"

goto organize

REM Appends %1 to CACERT under a marker comment naming %2, skipping if already merged
REM (idempotent across repeat builds without a clean).
:merge_ca
if not exist %1 (
    echo [SKIP] %1 not found
    exit /b 0
)
findstr /C:"# osdocs-mcp: %~2" "!CACERT!" >nul
if not errorlevel 1 (
    echo [SKIP] %~2 already merged
    exit /b 0
)
(
    echo.
    echo # osdocs-mcp: %~2
    type %1
) >> "!CACERT!"
exit /b 0

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
    echo [*] Inno Setup not found, installing via winget...
    winget install --id JRSoftware.InnoSetup -e --source winget
    set "INNO_PATH="
    for /f "delims=" %%I in ('where iscc 2^>nul') do if not defined INNO_PATH set "INNO_PATH=%%I"
    if not defined INNO_PATH if exist "%USERPROFILE%\AppData\Local\Programs\Inno Setup 6\ISCC.exe" set "INNO_PATH=%USERPROFILE%\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
    if not defined INNO_PATH if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "INNO_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    if not defined INNO_PATH if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "INNO_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)
if not exist "!INNO_PATH!" (
    echo [SKIP] Inno Setup still not found at !INNO_PATH! after install attempt
    echo Run: installer\build.cmd installer
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
