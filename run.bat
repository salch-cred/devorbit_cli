@echo off
cd /d %~dp0
if not exist .venv (
  echo Run install.bat first.
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m acli.main %*
