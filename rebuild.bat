@echo off
REM ProShow PDF - Rebuild and Create ZIP Script
REM Ricompila l'applicazione e crea il nuovo ZIP

setlocal enabledelayedexpansion

echo.
echo ===============================================
echo ProShow PDF - Rebuild & Create ZIP
echo ===============================================
echo.

REM Verifica che siamo nella cartella giusta
if not exist "packaging\proshowpdf.spec" (
    echo Error: proshowpdf.spec not found
    echo.
    echo Esegui questo script da: D:\Programmi\ProShowPDF
    echo.
    pause
    exit /b 1
)

REM Verifica venv
if not exist ".venv\Scripts\pyinstaller.exe" (
    echo Error: Virtual environment not found
    echo.
    echo Crea il venv con:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Step 1: Compilazione
echo [1/3] Compilazione con PyInstaller...
echo.

call .venv\Scripts\pyinstaller packaging\proshowpdf.spec --noconfirm

if errorlevel 1 (
    echo.
    echo ❌ Compilazione fallita!
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Compilazione completata
echo.

REM Verifica eseguibile
if not exist "dist\ProShowPDF\ProShowPDF.exe" (
    echo ❌ Eseguibile non trovato!
    echo.
    pause
    exit /b 1
)

REM Step 2: Backup ZIP vecchio
echo [2/3] Preparazione del ZIP...
if exist "ProShowPDF-v1.0.0-windows-x64.zip" (
    del "ProShowPDF-v1.0.0-windows-x64.zip"
    echo ZIP precedente eliminato
)

REM Step 3: Creazione ZIP
echo.
echo [3/3] Compressione in ZIP...
echo.

powershell -NoProfile -Command ^
    "cd dist; " ^
    "Compress-Archive -Path 'ProShowPDF' -DestinationPath '..\ProShowPDF-v1.0.0-windows-x64.zip' -Force; " ^
    "cd .."

if errorlevel 1 (
    echo.
    echo ❌ Creazione ZIP fallita!
    echo.
    pause
    exit /b 1
)

REM Verifica ZIP
if not exist "ProShowPDF-v1.0.0-windows-x64.zip" (
    echo.
    echo ❌ ZIP non creato!
    echo.
    pause
    exit /b 1
)

REM Mostra informazioni file
for %%I in ("ProShowPDF-v1.0.0-windows-x64.zip") do (
    set "size=%%~zI"
)

setlocal enabledelayedexpansion
set /a size_mb=!size! / 1048576
setlocal disabledelayedexpansion

echo.
echo ===============================================
echo ✅ BUILD COMPLETATO!
echo ===============================================
echo.
echo 📦 File ZIP pronto:
echo    D:\Programmi\ProShowPDF\ProShowPDF-v1.0.0-windows-x64.zip
echo    Dimensione: %size_mb% MB
echo.
echo 📍 Prossimo passo:
echo    1. Apri: https://github.com/PshowGit/ProShowPDF/releases/tag/v1.0.0
echo    2. Clicca "Edit release"
echo    3. Carica il nuovo ZIP in Assets
echo    4. Clicca "Update release"
echo.
echo ===============================================
echo.
pause
exit /b 0
