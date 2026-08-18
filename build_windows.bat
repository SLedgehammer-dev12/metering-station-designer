@echo off
REM ================================================================
REM  Metering Station Designer v1.0.0 — Windows Build Script
REM  Uses PyInstaller to create a standalone .exe
REM ================================================================

echo ================================================================
echo  Metering Station Designer — Windows Build (PyInstaller)
echo ================================================================
echo.

REM --- Clean ---
if exist "dist" (
    echo [1/3] Cleaning previous builds...
    rmdir /s /q dist 2>nul
    rmdir /s /q build 2>nul
)

REM --- Install ---
echo [2/3] Installing dependencies...
pip install -r requirements.txt pyinstaller 2>nul
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

REM --- Build ---
echo [3/3] Building with PyInstaller (3-5 minutes)...

echo Generating VERSION file...
python -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])" > VERSION
if errorlevel 1 (
    echo WARNING: failed to read version from pyproject.toml; building without VERSION.
)

pyinstaller --onedir --windowed --name MeteringStationDesigner ^
  --add-data "knowledge;knowledge" ^
  --add-data "VERSION;." ^
  --add-data "streamlit_app;streamlit_app" ^
  --add-data "metering_designer;metering_designer" ^
  --collect-all streamlit ^
  --hidden-import=plotly ^
  --hidden-import=numpy --hidden-import=pandas ^
  --hidden-import=pyaga8 --hidden-import=CoolProp ^
  --hidden-import=fluids --hidden-import=thermo ^
  --hidden-import=openpyxl --hidden-import=reportlab ^
  launcher.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo BUILD COMPLETE
echo.
echo Output: dist\MeteringStationDesigner\
echo Run:    dist\MeteringStationDesigner\MeteringStationDesigner.exe
echo.
echo NOTE: Copy the entire MeteringStationDesigner folder to deploy.
echo        Streamlit runs a web server on http://localhost:8501
echo        Open your browser after launching the .exe
echo ================================================================
pause
