@echo off
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\start.py" --docker --open-browser
if errorlevel 1 pause
