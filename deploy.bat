@echo off
REM ProShow PDF v1.0.0 Deployment Script
REM Creates a GitHub release with the compiled executable

setlocal enabledelayedexpansion

echo.
echo ===============================================
echo ProShow PDF v1.0.0 - Deployment Script
echo ===============================================
echo.

REM Check if we're in the right directory
if not exist "ProShowPDF-v1.0.0-windows-x64.zip" (
    echo Error: ProShowPDF-v1.0.0-windows-x64.zip not found
    echo.
    echo Please run this script from: D:\Programmi\ProShowPDF
    echo And ensure the executable has been compiled with:
    echo   pyinstaller packaging\proshowpdf.spec --noconfirm
    echo.
    pause
    exit /b 1
)

echo [1/3] Checking GitHub CLI (gh)...
where gh >nul 2>&1
if errorlevel 1 (
    echo.
    echo Error: GitHub CLI (gh) not found!
    echo.
    echo Install it with:
    echo   choco install gh
    echo.
    echo Or download from: https://github.com/cli/cli/releases
    echo.
    pause
    exit /b 1
)
echo OK - gh CLI found

echo.
echo [2/3] Verifying authentication...
gh auth status >nul 2>&1
if errorlevel 1 (
    echo.
    echo GitHub authentication required. Run:
    echo   gh auth login
    echo.
    pause
    exit /b 1
)
echo OK - Authenticated to GitHub

echo.
echo [3/3] Creating GitHub release v1.0.0...
echo.

REM Create the release with the zip file
gh release create v1.0.0 ^
  --title "ProShow PDF v1.0.0" ^
  --notes "Web-to-PDF Converter for Windows x64 - Production Ready" ^
  ProShowPDF-v1.0.0-windows-x64.zip

if errorlevel 1 (
    echo.
    echo Error: Release creation failed
    echo.
    echo Possible reasons:
    echo - Tag v1.0.0 already exists (delete it with: gh release delete v1.0.0)
    echo - Network error
    echo - Authentication issue
    echo.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo SUCCESS! Release v1.0.0 created and published
echo ===============================================
echo.
echo Download link: https://github.com/PshowGit/ProShowPDF/releases/tag/v1.0.0
echo.
echo Users can now download ProShowPDF-v1.0.0-windows-x64.zip
echo and run ProShowPDF.exe without any installation!
echo.
pause
exit /b 0
