@echo off
cd /d "%~dp0"
python scripts\build_release.py --exe
if errorlevel 1 (
    py scripts\build_release.py --exe
)
pause
