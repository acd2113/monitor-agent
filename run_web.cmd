@echo off
setlocal
cd /d "%~dp0"

echo.
echo MonitorAgent Web
echo URL: http://127.0.0.1:8000
echo.

start "" http://127.0.0.1:8000

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000
) else (
    python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000
)

endlocal
