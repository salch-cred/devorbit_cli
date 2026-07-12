@echo off
setlocal
cd /d %~dp0
if not exist .venv (
  call install.bat || exit /b 1
)
call .venv\Scripts\activate.bat

echo.
echo ============================================
echo   DevOrbit Desktop Application Builder
echo ============================================
echo.

echo [1/4] Installing PyInstaller...
python -m pip install pyinstaller -q

echo [2/4] Building Python executable...
python packaging\build.py || exit /b 1

echo.
echo [3/4] Building Electron app (if Node.js available)...
where npm >nul 2>nul
if %errorlevel%==0 (
  cd electron
  npm install
  npm run build:win
  cd ..
  echo   Electron app built: electron\release\
) else (
  echo   Node.js not found - skipping Electron build
)

echo.
echo [4/4] Build complete!
echo   Executable: dist\DevOrbit.exe
echo   Portable:  DevOrbit-portable-windows-*.zip
echo.
echo To run: desktop.bat --mock
echo.
endlocal
