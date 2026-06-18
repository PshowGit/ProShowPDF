@echo off
REM ProShow PDF - Rebuild and Create ZIP Script
REM Ricompila l'applicazione e crea il nuovo ZIP (nome fisso, versione automatica)

setlocal enabledelayedexpansion

echo.
echo ===============================================
echo ProShow PDF - Rebuild ^& Create ZIP
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

REM Legge la versione da proshowpdf\__init__.py (singola fonte di verita')
set "VERSION="
for /f "usebackq delims=" %%v in (`.venv\Scripts\python.exe -c "import proshowpdf; print(proshowpdf.__version__)" 2^>nul`) do set "VERSION=%%v"
if not defined VERSION (
    echo Error: impossibile leggere __version__ da proshowpdf\__init__.py
    echo.
    pause
    exit /b 1
)
echo Versione rilevata: v%VERSION%
echo.

REM Nome ZIP FISSO (senza versione): la landing page punta sempre allo stesso file
set "ZIP=ProShowPDF-windows-x64.zip"

REM Step 1: Compilazione
echo [1/3] Compilazione con PyInstaller...
echo.

call .venv\Scripts\pyinstaller packaging\proshowpdf.spec --noconfirm

if errorlevel 1 (
    echo.
    echo Compilazione fallita!
    echo.
    pause
    exit /b 1
)

echo.
echo Compilazione completata
echo.

REM Verifica eseguibile
if not exist "dist\ProShowPDF\ProShowPDF.exe" (
    echo Eseguibile non trovato!
    echo.
    pause
    exit /b 1
)

REM Step 2: Elimina ZIP precedente (stesso nome fisso)
echo [2/3] Preparazione del ZIP...
if exist "%ZIP%" (
    del "%ZIP%"
    echo ZIP precedente eliminato
)

REM Step 3: Creazione ZIP
echo.
echo [3/3] Compressione in ZIP...
echo.

powershell -NoProfile -Command ^
    "cd dist; " ^
    "Compress-Archive -Path 'ProShowPDF' -DestinationPath '..\%ZIP%' -Force; " ^
    "cd .."

if errorlevel 1 (
    echo.
    echo Creazione ZIP fallita!
    echo.
    pause
    exit /b 1
)

REM Verifica ZIP
if not exist "%ZIP%" (
    echo.
    echo ZIP non creato!
    echo.
    pause
    exit /b 1
)

REM Mostra dimensione
for %%I in ("%ZIP%") do set "size=%%~zI"
set /a size_mb=!size! / 1048576

echo.
echo ===============================================
echo BUILD COMPLETATO!  (v%VERSION%)
echo ===============================================
echo.
echo File ZIP pronto:
echo    %CD%\%ZIP%
echo    Dimensione: %size_mb% MB
echo.
echo Prossimo passo: pubblica la release con
echo    deploy.bat
echo (creera' il tag v%VERSION% e caricara' %ZIP%)
echo.
echo ===============================================
echo.
pause
exit /b 0
