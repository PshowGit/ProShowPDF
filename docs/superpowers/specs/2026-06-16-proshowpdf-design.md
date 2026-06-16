# ProShow PDF — Design Doc

**Data:** 2026-06-16
**Stato:** approvato (architettura), in attesa di review dello spec
**Target:** Windows x64, uso interno (Professional Show)

## 1. Obiettivo

Applicazione desktop Windows x64 che converte una o più pagine web in PDF
preservando il più fedelmente possibile l'aspetto a schermo (layout, font,
immagini, CSS, contenuti renderizzati via JS), con altezza dinamica per ottenere
un PDF a pagina unica/continua senza tagli.

## 2. Stack (vincolato)

- **GUI:** PySide6 (Qt for Python) — QSS per theming, QPropertyAnimation per
  animazioni, supporto High-DPI abilitato.
- **Rendering & PDF:** Playwright (Chromium headless), API **async**, `page.pdf()`
  con dimensioni custom.
- **Target:** Windows 64 bit esclusivamente. Su sistemi a 32 bit l'app mostra un
  errore chiaro e termina (Chromium di Playwright è solo x64).
- **Ambiente:** venv Python; tutte le dipendenze nel venv.
- **Python:** 3.13 (verificato sul sistema di sviluppo: 3.13.5).

## 3. Decisioni architetturali

### 3.1 Concorrenza (scelta: async loop dedicato in un QThread)

Un `QThread` worker ospita un `asyncio` event loop privato. Dentro l'event loop:

- **Una sola** istanza Chromium (`chromium.launch()`) riutilizzata per l'intero batch.
- Ogni URL elaborato in un `BrowserContext` isolato (stato pulito per pagina).
- Limite di conversioni simultanee imposto da `asyncio.Semaphore(N)`.
- Cancellazione cooperativa via `task.cancel()` + blocchi `finally` che chiudono
  pagine → context → browser → niente processi Chromium orfani.
- Comunicazione con la GUI **solo** tramite segnali Qt (thread-safe); il worker
  non tocca mai i widget.

**Perché non QThreadPool + API sync:** duplicherebbe risorse browser (o
richiederebbe lock sull'API sync), rende cancellazione e riuso del browser più
macchinosi. L'approccio async dà riuso ottimale su liste lunghe e cancellazione
nativa.

### 3.2 Packaging (scelta: PyInstaller onedir)

Build `onedir` (cartella con `.exe` + dipendenze + Chromium di Playwright
bundlato accanto). Avvio rapido, debug facile, bundling dei browser più
affidabile rispetto a onefile. Build eseguita dall'interno del venv.

### 3.3 Distribuzione

Uso interno: niente firma codice né installer complesso. Si forniscono build e
istruzioni (`packaging/build.md`).

## 4. Strati e confini

```
UI LAYER (PySide6)        → solo Qt, ignora Playwright/asyncio
   ▲  segnali / comandi
BRIDGE LAYER              → ConversionController(QObject): QThread + asyncio loop
   ▲  callback / await
CORE LAYER (puro)         → niente import PySide6, 100% testabile con pytest
```

- `core/` non importa mai Qt → testabile in isolamento.
- `ui/` non importa mai Playwright/asyncio.
- `bridge/` è l'unico punto di contatto tra i due mondi.

## 5. Struttura del progetto

```
ProShowPDF/
├── .venv/                      # in .gitignore
├── .gitignore
├── README.md
├── requirements.txt
├── pyproject.toml             # config pytest + metadati
├── PROMPT.txt
│
├── proshowpdf/
│   ├── __init__.py
│   ├── __main__.py            # check x64, High-DPI, avvio QApplication
│   ├── app.py                 # bootstrap QApplication, tema, MainWindow
│   │
│   ├── core/                  # CORE PURO
│   │   ├── __init__.py
│   │   ├── models.py          # ConversionSettings, JobItem, JobResult, JobStatus
│   │   ├── errors.py          # eccezioni tipizzate
│   │   ├── url_utils.py       # validazione/normalizzazione URL, parse .txt/.csv
│   │   ├── naming.py          # nomi file sicuri Windows, anti-collisione
│   │   ├── browser_pool.py    # ciclo vita Playwright + browser singolo + semaforo
│   │   ├── page_converter.py  # per-pagina: load→cookie→scroll→altezza→pdf
│   │   ├── cookie_banner.py   # euristiche consensi (disattivabile)
│   │   └── converter_engine.py# orchestrazione batch, progress, retry+backoff
│   │
│   ├── bridge/
│   │   ├── __init__.py
│   │   └── controller.py      # ConversionController(QObject)
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── widgets/
│   │   │   ├── url_input.py
│   │   │   ├── options_panel.py
│   │   │   ├── progress_view.py
│   │   │   └── results_panel.py
│   │   ├── theme.py
│   │   └── animations.py
│   │
│   ├── persistence/
│   │   ├── __init__.py
│   │   └── settings_store.py  # QSettings
│   │
│   ├── logging_setup.py       # RotatingFileHandler, logging strutturato
│   │
│   └── resources/
│       ├── qss/{dark.qss,light.qss}
│       └── icons/
│
├── tests/
│   ├── test_url_utils.py
│   ├── test_naming.py
│   └── test_page_converter.py
│
└── packaging/
    ├── proshowpdf.spec
    └── build.md
```

## 6. Flusso dati (un batch)

1. UI raccoglie URL + `ConversionSettings` → `controller.start(...)`.
2. Controller posta `engine.run(items, settings, on_progress)` nel loop del worker.
3. `BrowserPool` lancia un Chromium; `engine` crea task per URL governati dal semaforo.
4. Per ogni URL `PageConverter`: nuovo context → `goto(networkidle)` → chiude
   cookie banner → scroll completo (lazy-load) → torna su → `document.fonts.ready`
   → misura `scrollHeight` → `page.pdf(width=W, height=H, print_background=True,
   margin=0, scale=…)` con `emulate_media("screen")`.
5. Ogni evento (queued/running/done/error, conteggio) → callback → segnale Qt → UI.
6. Errori per-URL catturati e raccolti, non bloccano il batch; a fine batch
   riepilogo + export CSV (URL, tipo errore, messaggio, timestamp).
7. Cancellazione: `task.cancel()` → `finally` chiude tutto.

## 7. Requisiti funzionali → componente responsabile

| # | Requisito | Componente |
|---|-----------|-----------|
| 1 | Input flessibile (URL / lista / import .txt,.csv) | `ui/widgets/url_input.py`, `core/url_utils.py` |
| 2 | Larghezza configurabile (px) | `core/models.py`, `core/page_converter.py` |
| 3 | Altezza dinamica (scrollHeight, networkidle, font) | `core/page_converter.py` |
| 4 | Fedeltà rendering (print_background, screen, margin 0, scale, scroll) | `core/page_converter.py` |
| 5 | Cookie banner (euristiche, disattivabile) | `core/cookie_banner.py` |
| 6 | Progress bar realtime ("3/12", URL corrente) | `ui/widgets/progress_view.py`, segnali bridge |
| 7 | Annullamento pulito (no Chromium orfani) | `bridge/controller.py`, `core/converter_engine.py` |
| 8 | Concorrenza configurabile (semaforo, browser unico) | `core/browser_pool.py`, `core/converter_engine.py` |
| 9 | Output (cartella, naming sicuro, conflitti, apri cartella) | `core/naming.py`, `ui/widgets/results_panel.py` |
| 10 | Errori chiari + riepilogo + export CSV | `core/errors.py`, `core/converter_engine.py`, `ui/widgets/results_panel.py` |
| 11 | Persistenza impostazioni | `persistence/settings_store.py` |
| 12 | Timeout/retry configurabili da UI | `core/models.py`, `core/converter_engine.py`, `ui/widgets/options_panel.py` |

## 8. Scelte di fedeltà rese esplicite

- **`emulate_media("screen")`:** aspetto a schermo, non lo stile `print` (che
  spesso nasconde immagini/colori). Coerente col requisito di fedeltà.
- **Altezza:** misura dopo `networkidle` + scroll completo + `document.fonts.ready`;
  `Math.max(body.scrollHeight, documentElement.scrollHeight)`.
- **Larghezza/scale:** `device_scale_factor` impostato a livello di context per
  coerenza con la larghezza scelta.
- **Cookie banner:** euristiche leggere senza dipendenze esterne (selettori
  comuni "Accept/Accetta", id/classi note, iframe Didomi/OneTrust/Cookiebot);
  disattivabile da UI.
- **MCP/skill in runtime:** nessuno (overhead inutile per uso interno). In
  sviluppo si può usare context7 per la doc aggiornata di Playwright/PySide6.

## 9. Gestione errori

Gerarchia in `core/errors.py`: `ConversionError` base →
`NavigationError`, `TimeoutError`, `RenderError`, `OutputError`. Ogni
`JobResult` fallito porta URL, tipo, messaggio, timestamp. Retry con backoff
esponenziale (numero configurabile). Riepilogo finale esportabile in CSV.

## 10. Logging

`logging_setup.py`: logging strutturato su file con livelli e
`RotatingFileHandler` (rotazione per dimensione). Path in cartella dati utente.

## 11. Testing (pytest, solo core)

- `test_url_utils.py`: validazione/normalizzazione URL, parsing .txt/.csv.
- `test_naming.py`: sanitizzazione nomi file Windows, anti-collisione.
- `test_page_converter.py`: logica altezza dinamica con `page` mockata.

## 12. Setup (venv)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## 13. Build (Windows x64, dal venv)

PyInstaller onedir via `packaging/proshowpdf.spec`, con bundling del Chromium di
Playwright. Dettagli operativi in `packaging/build.md`.

## 14. Limiti noti / estensioni future

- Pagine con anti-bot aggressivo o login possono fallire o richiedere sessione.
- Euristiche cookie banner non coprono il 100% dei provider.
- PDF a pagina unica molto alto può risultare pesante su pagine enormi.
- Estensioni possibili: profili browser persistenti per siti con login, supporto
  formati pagina standard (A4) opzionale, code di job persistenti, multilingua UI.
```
