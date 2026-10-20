@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (set PY=py -3) else (set PY=python)
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
if errorlevel 1 (echo Python 3 gerekli. & pause & exit /b 1)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Paket kurulumu basarisiz. & pause & exit /b 1)
start "" http://127.0.0.1:8765
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
pause
