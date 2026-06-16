# Build (Windows x64, dal venv)

```bat
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
playwright install chromium
pyinstaller packaging\proshowpdf.spec --noconfirm
```

Output: `dist\ProShowPDF\ProShowPDF.exe` (cartella onedir, con Chromium bundlato).
Distribuisci l'intera cartella `dist\ProShowPDF`.
