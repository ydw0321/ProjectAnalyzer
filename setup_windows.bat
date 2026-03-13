@echo off
setlocal

cd /d "%~dp0"

echo [1/4] Checking Python...
where py >nul 2>nul
if %errorlevel%==0 goto use_py

where python >nul 2>nul
if %errorlevel%==0 goto use_python

echo [ERROR] Python 3 was not found in PATH.
echo Install Python 3.10+ first and enable "Add python.exe to PATH".
exit /b 1

:use_py
set "PYTHON_CMD=py -3"
goto create_venv

:use_python
set "PYTHON_CMD=python"

:create_venv
echo [2/4] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        exit /b 1
    )
) else (
    echo Existing .venv detected, reuse it.
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    exit /b 1
)

echo [3/4] Installing Python dependencies...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip tooling.
    exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install requirements.
    exit /b 1
)

echo [4/4] Initializing environment file...
if not exist ".env" (
    copy /Y ".env.example" ".env" >nul
    echo Created .env from .env.example
) else (
    echo Existing .env detected, keep current configuration.
)

echo.
echo Setup completed.
echo Next steps:
echo   1. Edit .env and set PROJECT_PATH / LLM_API_KEY / Neo4j settings.
echo   2. Run run_pipeline_windows.bat --index-all
echo   3. If Neo4j is ready, run run_dashboard_windows.bat
exit /b 0