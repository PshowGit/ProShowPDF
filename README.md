# ProShow PDF

Convertitore web→PDF per Windows x64. Trasforma una o più pagine web in PDF a
pagina unica/continua, preservando l'aspetto a schermo (layout, font, immagini,
CSS, contenuti renderizzati via JS). GUI moderna PySide6, rendering via
Playwright (Chromium headless).

## Requisiti

- Windows 64 bit (x64). L'app si rifiuta di partire su sistemi a 32 bit
  (il Chromium di Playwright è distribuito solo per x64).
- Python 3.13+.

## Setup (venv)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## Avvio (dal venv)

```bat
.venv\Scripts\activate
python -m proshowpdf
```

## Funzionalità

- Input flessibile: singolo URL, lista multilinea o import da .txt/.csv.
- Larghezza PDF configurabile; altezza dinamica (misura `scrollHeight` dopo
  networkidle, scroll lazy-load e caricamento web font) per un PDF continuo.
- Fedeltà: `print_background`, `emulate_media("screen")`, margini 0,
  scroll completo per i contenuti lazy.
- Chiusura automatica dei banner cookie più comuni (disattivabile).
- Conversioni in parallelo configurabili (un solo browser, più context,
  semaforo sul limite).
- Barra di avanzamento in tempo reale ("3 / 12") con URL corrente e stato
  per pagina; annullamento pulito senza processi Chromium orfani.
- Output: cartella destinazione, nomi file sicuri per Windows (titolo pagina o
  dominio+timestamp), gestione conflitti (rinomina/sovrascrivi), apri cartella.
- Errori per-URL non bloccanti, riepilogati a fine batch ed esportabili in CSV.
- Timeout e retry (con backoff) configurabili; persistenza preferenze via
  QSettings; tema chiaro/scuro.

## Test

```bat
.venv\Scripts\python -m pytest -q
```

## Build (eseguibile Windows x64)

Vedi `packaging/build.md`. In sintesi, dal venv attivo:

```bat
pyinstaller packaging\proshowpdf.spec --noconfirm
```

Produce `dist\ProShowPDF\ProShowPDF.exe` (onedir) con Chromium bundlato; si
distribuisce l'intera cartella `dist\ProShowPDF`.

## Architettura

Tre strati con confini netti:

- `proshowpdf/core/` — logica di conversione pura (Playwright async), testabile
  senza Qt.
- `proshowpdf/bridge/` — `ConversionController`: esegue l'engine async in un
  thread dedicato con event loop asyncio, comunica con la GUI via segnali Qt.
- `proshowpdf/ui/` — interfaccia PySide6 (widget, temi, animazioni).

## Limiti noti

- Pagine con anti-bot aggressivo o che richiedono login possono fallire.
- Le euristiche per i banner cookie non coprono tutti i provider.
- Un PDF a pagina unica molto alto può risultare pesante su pagine enormi.

## Estensioni future

Profili browser persistenti per siti con login, formato pagina standard (A4)
opzionale, code di job persistenti, UI multilingua.
