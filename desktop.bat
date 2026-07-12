@echo off
cd /d %~dp0
if not exist .venv (
  echo Missing .venv. Run install.bat first.
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m acli.desktop.launch %*
