@echo off
REM Fillmore CRM -- portable runner (Windows). No install: everything lives
REM in a local .venv folder next to this script. Your data lives in
REM %LOCALAPPDATA%\fillmore-crm so re-downloading this folder never touches
REM your real records.
cd /d "%~dp0"

if not exist ".venv" (
    echo == First run: setting up ^(one-time, ~30s^) ==
    python -m venv .venv
)

call .venv\Scripts\pip install -q -r requirements.txt

if "%FILLMORE_DATA_DIR%"=="" set FILLMORE_DATA_DIR=%LOCALAPPDATA%\fillmore-crm
mkdir "%FILLMORE_DATA_DIR%\photos" 2>nul

.venv\Scripts\python -c "import sys; sys.path.insert(0, 'app'); import app as fillmore_app; fillmore_app.init_db(); fillmore_app.migrate_db()"
.venv\Scripts\python app\seed.py

echo == Starting Fillmore CRM ==
if "%FILLMORE_PORT%"=="" set FILLMORE_PORT=8850
start "" "http://127.0.0.1:%FILLMORE_PORT%/"

cd app
"..\.venv\Scripts\python" app.py
