@echo off
cd /d "%~dp0.."

set "COUNT=0"

rem Clean script: removes build artifacts and caches
rem Removes: __pycache__, .pyc, .pytest_cache, coverage, logs, .cache/, temp/, tmp/, dist/, hash tracking files

rem Delete __pycache__ in specific directories (never recurses into .venv)
for /d /r "src\osdocs" %%d in (__pycache__) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%d
            set /a COUNT+=1
        )
    )
)
for /d /r "src\tests" %%d in (__pycache__) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%d
            set /a COUNT+=1
        )
    )
)

rem Delete .pyc files in specific directories
for /r "src\osdocs" %%f in (*.pyc) do (
    if exist "%%f" (
        del /q "%%f" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%f
            set /a COUNT+=1
        )
    )
)
for /r "src\tests" %%f in (*.pyc) do (
    if exist "%%f" (
        del /q "%%f" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%f
            set /a COUNT+=1
        )
    )
)

rem Delete .pytest_cache in specific directories
for /d /r "src\osdocs" %%d in (.pytest_cache) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%d
            set /a COUNT+=1
        )
    )
)
for /d /r "src\tests" %%d in (.pytest_cache) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%d
            set /a COUNT+=1
        )
    )
)

rem Delete coverage data and reports
if exist ".coverage" (
    del /q ".coverage" 2>nul
    echo   [DEL] .coverage
    set /a COUNT+=1
)
for /d /r "." %%d in (htmlcov) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%d
            set /a COUNT+=1
        )
    )
)

rem Delete type checker caches
for /d /r "src\osdocs" %%d in (.mypy_cache) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%d
            set /a COUNT+=1
        )
    )
)
if exist ".dmypy.json" (
    del /q ".dmypy.json" 2>nul
    echo   [DEL] .dmypy.json
    set /a COUNT+=1
)

rem Delete logs directory
if exist "logs" (
    rd /s /q "logs" 2>nul
    if not errorlevel 1 (
        echo   [DEL] logs\
        set /a COUNT+=1
    )
)

rem Delete fastembed/model cache directories
if exist ".cache" (
    rd /s /q ".cache" 2>nul
    if not errorlevel 1 (
        echo   [DEL] .cache\
        set /a COUNT+=1
    )
)

rem Delete temp/tmp scratch directories
if exist "temp" (
    rd /s /q "temp" 2>nul
    if not errorlevel 1 (
        echo   [DEL] temp\
        set /a COUNT+=1
    )
)
if exist "tmp" (
    rd /s /q "tmp" 2>nul
    if not errorlevel 1 (
        echo   [DEL] tmp\
        set /a COUNT+=1
    )
)

rem Delete dist directory and all build artifacts
if exist "dist" (
    rd /s /q "dist" 2>nul
    if not errorlevel 1 (
        echo   [DEL] dist\
        set /a COUNT+=1
    )
)

rem Delete Nuitka build folders
for /d /r "." %%d in (*.build) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%d
            set /a COUNT+=1
        )
    )
)
for /d /r "." %%d in (*.dist) do (
    if exist "%%d" (
        rd /s /q "%%d" 2>nul
        if not errorlevel 1 (
            echo   [DEL] %%d
            set /a COUNT+=1
        )
    )
)

rem Delete .nuitka cache
if exist ".nuitka" (
    rd /s /q ".nuitka" 2>nul
    if not errorlevel 1 (
        echo   [DEL] .nuitka\
        set /a COUNT+=1
    )
)

rem Delete build_info.py (generated during build)
if exist "src\build_info.py" (
    del /q "src\build_info.py" 2>nul
    if not errorlevel 1 (
        echo   [DEL] src\build_info.py
        set /a COUNT+=1
    )
)

rem Delete hash tracking files (build gates)
if exist "installer\.deps.hash" (
    del /q "installer\.deps.hash" 2>nul
    echo   [DEL] installer\.deps.hash
    set /a COUNT+=1
)
if exist "installer\.src.hash" (
    del /q "installer\.src.hash" 2>nul
    echo   [DEL] installer\.src.hash
    set /a COUNT+=1
)
if exist "installer\.pyd.hash" (
    del /q "installer\.pyd.hash" 2>nul
    echo   [DEL] installer\.pyd.hash
    set /a COUNT+=1
)
if exist "installer\.exe.hash" (
    del /q "installer\.exe.hash" 2>nul
    echo   [DEL] installer\.exe.hash
    set /a COUNT+=1
)
if exist "installer\.setup.hash" (
    del /q "installer\.setup.hash" 2>nul
    echo   [DEL] installer\.setup.hash
    set /a COUNT+=1
)
if exist "installer\.iss.hash" (
    del /q "installer\.iss.hash" 2>nul
    echo   [DEL] installer\.iss.hash
    set /a COUNT+=1
)

rem Clean up legacy hash files
if exist ".dll.hash" (
    del /q ".dll.hash" 2>nul
    echo   [DEL] .dll.hash ^(legacy^)
    set /a COUNT+=1
)
if exist ".exe.hash" (
    del /q ".exe.hash" 2>nul
    echo   [DEL] .exe.hash ^(legacy^)
    set /a COUNT+=1
)
if exist ".setup.hash" (
    del /q ".setup.hash" 2>nul
    echo   [DEL] .setup.hash ^(legacy^)
    set /a COUNT+=1
)

if %COUNT% equ 0 (
    echo Nothing to clean.
) else (
    echo.
    echo Clean done. %COUNT% item^(s^) removed.
)
