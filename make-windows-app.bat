@echo off
setlocal
cd /d %~dp0
if not exist .venv (
  call install.bat || exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install pyinstaller || exit /b 1
python packaging\build.py || exit /b 1
echo.
echo Build complete. Open the dist folder for DevOrbit.exe.
endlocal
