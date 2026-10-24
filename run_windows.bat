@echo off
title Stationery Hub
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Python/pip setup failed. Install Python from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
py app.py
pause
