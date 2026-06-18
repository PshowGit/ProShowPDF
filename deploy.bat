@echo off
REM ProShow PDF Deployment Script
REM Pubblica una GitHub Release con tag v<__version__> e lo ZIP a nome fisso

setlocal enabledelayedexpansion

echo.
echo ===============================================
echo ProShow PDF - Deployment Script
echo ===============================================
echo.

REM Legge la versione da proshowpdf\__init__.py (stessa fonte della build)
set "VERSION="
for /f "usebackq delims=" %%v in (`.venv\Scripts\python.exe -c "import proshowpdf; print(proshowpdf.__version__)" 2^>nul`) do set "VERSION=%%v"
if not defined VERSION (
    echo Error: impossibile leggere __version__ da proshowpdf\__init__.py
    echo.
    pause
    exit /b 1
)

set "ZIP=ProShowPDF-windows-x64.zip"
set "TAG=v%VERSION%"
echo Versione: %TAG%
echo.

REM Verifica presenza ZIP
if not exist "%ZIP%" (
    echo Error: %ZIP% non trovato
    echo.
    echo Esegui prima rebuild.bat per creare lo ZIP.
    echo.
    pause
    exit /b 1
)

echo [1/4] Checking GitHub CLI (gh)...
REM Cerca gh nel PATH; se assente, usa il percorso d'installazione di default
REM (winget non aggiorna il PATH dei terminali gia' aperti / del doppio click).
set "GH="
where gh >nul 2>&1 && set "GH=gh"
if not defined GH if exist "%ProgramFiles%\GitHub CLI\gh.exe" set "GH=%ProgramFiles%\GitHub CLI\gh.exe"
if not defined GH (
    echo.
    echo Error: GitHub CLI gh non trovato.
    echo Installa con: winget install --id GitHub.cli   e poi RIAPRI il terminale.
    echo.
    pause
    exit /b 1
)
echo OK - gh trovato

echo.
echo [2/4] Verifying authentication...
"%GH%" auth status >nul 2>&1
if errorlevel 1 (
    echo.
    echo GitHub authentication required. Run: gh auth login
    echo.
    pause
    exit /b 1
)
echo OK - Authenticated to GitHub

echo.
echo [3/4] Controllo tag esistente %TAG%...
"%GH%" release view %TAG% >nul 2>&1
if not errorlevel 1 (
    echo.
    echo La release %TAG% esiste gia'.
    echo Hai dimenticato di aggiornare __version__ in proshowpdf\__init__.py?
    echo Per ripubblicare lo stesso tag, prima eliminalo:  gh release delete %TAG%
    echo.
    pause
    exit /b 1
)

echo.
echo [4/4] Creazione release %TAG%...
echo.

"%GH%" release create %TAG% ^
  --title "ProShow PDF %TAG%" ^
  --notes "Web-to-PDF Converter for Windows x64" ^
  "%ZIP%"

if errorlevel 1 (
    echo.
    echo Error: Release creation failed - rete o autenticazione?
    echo.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo SUCCESS! Release %TAG% pubblicata
echo ===============================================
echo.
echo Pagina release:
echo    https://github.com/PshowGit/ProShowPDF/releases/tag/%TAG%
echo.
echo Link FISSO per la landing page (punta sempre all'ultima):
echo    https://github.com/PshowGit/ProShowPDF/releases/latest/download/%ZIP%
echo.
echo Gli utenti con una versione precedente vedranno l'avviso di aggiornamento.
echo.
pause
exit /b 0
