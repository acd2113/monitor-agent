@echo off
setlocal
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m src.tui.tui_app
) else (
    python -m src.tui.tui_app
)
endlocal
