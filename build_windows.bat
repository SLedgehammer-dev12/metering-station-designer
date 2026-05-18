@echo off
REM ================================================================
REM  Metering Station Designer v1.0.0 — Windows Build Script
REM  Uses Nuitka to create a standalone .exe (no Python needed)
REM ================================================================

echo ================================================================
echo  Metering Station Designer — Windows Build (Nuitka)
echo ================================================================
echo.

REM --- Clean previous builds ---
if exist "dist" (
    echo [1/4] Cleaning previous builds...
    rmdir /s /q dist 2>nul
    rmdir /s /q build 2>nul
)

REM --- Install dependencies ---
echo [2/4] Installing dependencies...
pip install -r requirements.txt nuitka ordered-set zstandard 2>nul
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    echo Try: pip install --upgrade pip
    pause
    exit /b 1
)

REM --- Nuitka build ---
echo [3/4] Building with Nuitka (this may take 10-30 minutes)...
echo.
python -m nuitka ^
  --standalone ^
  --windows-console-mode=disable ^
  --enable-plugin=tk-inter ^
  --include-package=streamlit ^
  --include-package=plotly ^
  --include-package=numpy ^
  --include-package=pandas ^
  --include-package=pyaga8 ^
  --include-package=CoolProp ^
  --include-package=fluids ^
  --include-package=thermo ^
  --include-package=openpyxl ^
  --include-package=reportlab ^
  --include-package=metering_designer ^
  --include-package=streamlit_app ^
  --include-data-dir=knowledge="knowledge" ^
  --output-dir=dist ^
  --assume-yes-for-downloads ^
  --windows-company-name="Metering Designer" ^
  --windows-product-name="Metering Station Designer" ^
  --windows-file-description="Measurement Station Design Tool" ^
  --windows-file-version=1.0.0 ^
  --windows-product-version=1.0.0 ^
  streamlit_app/app.py

if errorlevel 1 (
    echo.
    echo ERROR: Nuitka build failed. Check output above.
    pause
    exit /b 1
)

REM --- Verify ---
echo.
echo [4/4] Build complete!
echo.
echo Output: dist\app.dist\
echo Run:    dist\app.dist\app.exe
echo.
echo NOTE: Streamlit runs a web server on http://localhost:8501
echo Open your browser after launching the .exe
echo.

REM Optional: check VirusTotal
where curl >nul 2>&1
if %errorlevel% equ 0 (
    echo Would you like to scan on VirusTotal? (y/n)
    set /p SCAN=
    if /i "%SCAN%"=="y" (
        echo Uploading to VirusTotal...
        curl -X POST https://www.virustotal.com/api/v3/files ^
          -H "x-apikey: YOUR_API_KEY" ^
          -F "file=@dist/app.dist/app.exe"
        echo Check results at: https://www.virustotal.com
    )
)

echo ================================================================
echo DONE. Launch with: dist\app.dist\app.exe
echo ================================================================
pause
