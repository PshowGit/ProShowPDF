# Guida Utente — ProShow PDF

Benvenuto! Questa guida ti spiega come usare ProShow PDF per convertire pagine web in PDF.

---

## Cos'è ProShow PDF?

ProShow PDF è un'applicazione che **converte pagine web in file PDF** mantenendo l'aspetto visivo della pagina (layout, colori, immagini, contenuti dinamici). Puoi convertire una singola pagina o un lotto di decine di pagine in parallelo.

**Perfetto per:**
- Salvare articoli web come PDF
- Archiviare pagine web per consultazione offline
- Creare PDF da elenchi di URL (da Excel, CSV, ecc.)
- Convertire siti senza area di stampa (perché usa il rendering a schermo)

---

## Avvio dell'Applicazione

1. Scarica e estrai il file `ProShowPDF-v1.0.0-windows-x64.zip`
2. Vai nella cartella `ProShowPDF`
3. Fai doppio clic su **`ProShowPDF.exe`**

L'applicazione si aprirà in pochi secondi. La finestra è divisa in sezioni:

```
[🌙 Tema]                              (pulsante in alto a destra)
──────────────────────────────────
📝 Inserisci URL (uno per riga)
   [paste URLs here]
   [URL caricate: X]   [Importa da file...]

⚙️  Opzioni
   [Timeout, scrolling, cookie banner...]

[Converti] [Annulla] [Pulisci] ...
──────────────────────────────────
📊 Avanzamento (durante la conversione)
📋 Risultati (alla fine)
```

---

## Come Convertire Pagine Web

### Metodo 1: Incolla URL direttamente

1. **Fare clic nella casella di testo** sotto "URL (uno per riga...)"
2. **Incolla URL**, uno per riga:
   ```
   https://example.com
   https://example.org/article
   https://site.com/page
   ```
3. **Fai clic su "Converti"**

### Metodo 2: Trascina file txt/csv/xlsx

Se hai un file con una lista di URL:

1. **Trascina il file direttamente nella casella di testo**
   - Formati supportati: `.txt`, `.csv`, `.xlsx`, `.xls`
   - Estensione: `.txt` – un URL per riga
   - Estensione: `.csv` o `.xlsx` – URL nella colonna 1

2. Gli URL vengono caricati automaticamente

### Metodo 3: Importa da file (pulsante)

1. **Fai clic su "Importa da file…"**
2. Seleziona un file `.txt`, `.csv`, `.xlsx` o `.xls`
3. Gli URL vengono aggiunti alla lista

---

## Nomi File Personalizzati

Se non vuoi usare il nome automatico del PDF, puoi specificare nomi personalizzati.

**Solo per file Excel (.xlsx / .xls) e CSV:**

- **Colonna 1:** URL (obbligatorio)
- **Colonna 2:** Nome file personalizzato (facoltativo, senza ".pdf")

**Esempio Excel:**
```
| URL                        | Nome File Personalizzato |
|---|---|
| https://example.com        | Articolo gennaio         |
| https://site.org/guide     | Guida completa           |
| https://blog.test/post-1   |                          |
```

**Risultato:**
- `Articolo gennaio.pdf`
- `Guida completa.pdf`
- `site.org_2026-06-17_123456.pdf` (auto)

---

## Opzioni di Conversione

Nella sezione **"Opzioni"**, puoi configurare:

### 📁 Cartella di Output
Dove salvare i PDF. Usa il pulsante **"Sfoglia"** per scegliere una cartella.

### ⏱️ Timeout per Pagina (secondi)
Tempo massimo per scaricare e renderizzare una pagina (default: 30s).
- **Troppo breve?** La pagina potrebbe non caricarsi completamente
- **Troppo lungo?** La conversione sarà più lenta

### 📜 Scroll Completo
Se abilitato (default), l'app scorrerà la pagina per caricare contenuti "lazy-load" (immagini che si caricano mentre scorri).

### 🍪 Dismissione Banner Cookie
Se abilitato (default), l'app cerca di chiudere automaticamente i banner di consenso cookie.
- Non funziona con tutti i siti
- Puoi disabilitare se causa problemi

### ⚡ Conversioni Parallele
Quante pagine convertire contemporaneamente (default: 3).
- **Valori alti = più veloci ma più CPU**
- **Valori bassi = più lenti ma più stabili**

---

## Avvio della Conversione

1. **Verifica gli URL** nella casella di testo
   - Vedi il numero "URL caricate: X" in basso a sinistra
2. **Configura le opzioni** (timeout, cartella output, ecc.)
3. **Fai clic su "Converti"**

L'applicazione:
- Mostra una **barra di avanzamento** con "3 / 12" (in conversione 3 di 12)
- Mostra l'**URL attuale**
- Mostra lo **stato** (scaricamento, rendering, salvataggio...)

**Durante la conversione, puoi:**
- Leggere i risultati parziali (in basso)
- Fare clic su **"Annulla"** per fermare tutto

---

## Visualizzazione dei Risultati

Al termine della conversione, vedrai:

### ✅ Riepilogo
- Quanti PDF sono stati creati con successo
- Quanti hanno avuto errori
- Tempo totale impiegato

### 📂 Apri Cartella
Fai clic su **"Apri Cartella"** per vedere i PDF salvati.

### ❌ Errori (se presenti)
Lista degli URL che non si sono potuti convertire e perché.

### 💾 Esporta Risultati
Fai clic su **"Esporta CSV"** per scaricare un file con il dettaglio di ogni conversione.

---

## Pulsanti Principali

| Pulsante | Cosa fa |
|---|---|
| **Converti** | Avvia la conversione degli URL |
| **Annulla** | Ferma una conversione in corso |
| **Pulisci** | Resetta il modulo (cancella URL, ripristina opzioni) |
| **🌙 Tema** | Cambia tra tema scuro (notte) e chiaro (giorno) |

---

## Domande Frequenti

### ❓ La conversione è lenta. Cosa posso fare?

1. **Aumenta il timeout** se la pagina è lenta a caricarsi
2. **Aumenta "Conversioni parallele"** (es. 5 invece di 3) se hai un PC potente
3. **Disabilita "Scroll Completo"** se non hai bisogno di contenuti lazy-load

### ❓ Un URL dice "Errore: timeout". Cosa significa?

La pagina ha impiegato troppo tempo a caricarsi. Prova:
- Aumentare il timeout da 30s a 45s o 60s
- Verificare che il sito sia raggiungibile (apri il link nel browser)
- Continuare con altri URL (questo non blocca gli altri)

### ❓ Il PDF non contiene tutte le immagini / non è completo.

Prova:
- **Aumentare il timeout** (alcuni siti caricano contenuti lentamente)
- **Abilitare "Scroll Completo"** se non lo è già
- **Disabilitare "Dismissione banner cookie"** se il banner copre il contenuto

### ❓ Dove trovo i PDF?

Nella cartella che hai scelto in "Opzioni" → "Cartella di Output" (default: `Documenti`).

Puoi aprirla direttamente dal pulsante **"Apri Cartella"** nei risultati.

### ❓ Come cambio tema (scuro/chiaro)?

Fai clic sul pulsante **"🌙 Tema"** in alto a destra. L'icona cambia:
- **☀️** quando il tema è scuro (cliccando vai a chiaro)
- **🌙** quando il tema è chiaro (cliccando vai a scuro)

### ❓ Posso specificare nomi file diversi per ogni PDF?

Sì! Solo con file Excel/CSV:
- **Colonna 1:** URL
- **Colonna 2:** Nome personalizzato (senza ".pdf")

Importa il file tramite drag-and-drop o "Importa da file…"

### ❓ Cosa succede se due pagine hanno lo stesso nome?

L'app:
1. Aggiunge un **numero** (es. `esempio_2.pdf`, `esempio_3.pdf`)
2. O mostra una finestra dove puoi scegliere se sovrascrivere

### ❓ L'app si ferma o crasha.

Prova:
- **Riavvia l'applicazione**
- **Aumenta il timeout** (alcune pagine sono molto complesse)
- **Riduci "Conversioni parallele"** (es. da 5 a 2)
- Se il problema persiste, contatta il supporto

---

## Limiti Noti

- ⚠️ **Pagine con login:** Non funzionano (l'app non ricorda le credenziali)
- ⚠️ **Anti-bot:** Alcuni siti bloccano il rendering automatico
- ⚠️ **PDF molto alti:** Pagine enorme possono creare PDF pesanti

---

## Suggerimenti Pratici

✅ **Per migliori risultati:**
1. Verifica che il sito sia raggiungibile (apri nel browser)
2. Usa timeout appropriati (30s per siti veloci, 60s+ per lenti)
3. Se il risultato non è perfetto, prova con "Scroll Completo" abilitato
4. Esporta i risultati in CSV per tenere traccia delle conversioni

✅ **Workflow consigliato:**
1. Prepara una lista di URL in Excel
2. Nella colonna 2, aggiungi nomi personalizzati (opzionale)
3. Salva come CSV o trascinaci il file nell'app
4. Configura timeout e opzioni
5. Avvia la conversione
6. Apri la cartella di output quando finisce

---

## Supporto

Se hai domande o problemi:
- Controlla questa guida (sezione "Domande Frequenti")
- Verifica il file di log (cartella "Log" nel tuo profilo Windows)
- Contatta il supporto con il numero di versione dell'app

---

**Versione:** 1.0.0  
**Ultimo aggiornamento:** Giugno 2026  
**Piattaforma:** Windows 64-bit
