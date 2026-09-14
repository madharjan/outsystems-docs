@echo off
REM Run OutSystems-Docs MCP using the project-local .venv (created on first run)
REM Usage: scripts\run.cmd --sync
setlocal enabledelayedexpansion

REM Cache and .venv are commonly on different drives; hardlinking then isn't possible and
REM uv falls back to a full copy anyway, just with a noisy warning. Silence it.
set "UV_LINK_MODE=copy"

set VENV_PYTHON=%~dp0..\.venv\Scripts\python.exe

where uv >nul 2>nul
if errorlevel 1 (
    echo [*] uv not found, installing...
    winget install --id=astral-sh.uv -e --source winget
    if errorlevel 1 powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

if not exist "%VENV_PYTHON%" (
    echo [*] .venv not found, creating it...
    call uv sync
)

echo [*] Swapping onnxruntime for onnxruntime-directml ^(AMD/Intel/NVIDIA GPU via DirectML^)...
call uv pip install --python "%VENV_PYTHON%" --force-reinstall --no-deps onnxruntime-directml
if errorlevel 1 exit /b 1

"%VENV_PYTHON%" "%~dp0..\src\osdocs_mcp.py" %*
exit /b %ERRORLEVEL%
