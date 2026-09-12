# SEC-Core: Ingestion & Parser Engine per Dati SEC

## 1. Problem Statement
> **Come possiamo creare un modulo Python snello e unificato che intercetti i dati ad alto valore della SEC (EDGAR) — in particolare eventi straordinari (8-K), insider trading (Form 4) e operazioni M&A — restituendo strutture dati e JSON puliti, senza farsi bloccare dalle restrizioni della SEC e senza disperdere energie su dati già accessibili altrove (es. bilanci su yfinance)?**

---

## 2. Recommended Direction: Architettura a 3 Moduli Specializzati

Il core scarta completamente i bilanci contabili (10-K/10-Q) e i prospetti burocratici, focalizzandosi esclusivamente sui 3 flussi a più alto valore informativo:

```
                          ┌──────────────────────────────────────┐
                          │               sec_core               │
                          │   (Client Conforme, User-Agent,      │
                          │    Rate-Limiter 10 req/s, Cache CIK) │
                          └──────────────────┬───────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             ▼                               ▼                               ▼
  [Modulo 1: Live Stream]       [Modulo 2: Insider Engine]       [Modulo 3: M&A & Events]
   Feed RSS / Atom Real-Time           Form 4 (XML)                 8-K / DEFM14A (HTML)
  ─────────────────────────     ─────────────────────────       ─────────────────────────
  - Polling live SEC            - Parsing XML nativo            - Pulizia HTML / Markdown
  - Filtro su Watchlist         - Chi (Insider/Ruolo)           - Segmentazione per "Item"
  - Rilevazione nuovi filing    - Operazione (Buy/Sell, Prezzo) - Riconoscimento Deal M&A
```

---

### Dettaglio dei 3 Moduli

#### 📡 Modulo 1: Real-Time Stream & Watchlist Filter (`feed.py`)
* **Fonte dati:** SEC Atom Feed in tempo reale (`https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom`).
* **Funzionalità:**
  * Polling continuo o a intervalli configurabili degli ultimi filing depositati.
  * Filtro istantaneo: ignora il "rumore" burocratico (`EFFECT`, `144`, `CORRESP`) e intercetta solo i filing monitorati.
  * Match con una lista di ticker monitorati (Watchlist) o su scala globale per eventi specifici (es. tutti i Form 4 > $1M o tutti gli 8-K Item 1.01).
* **Output:** Oggetto evento Python / JSON con `ticker`, `cik`, `form_type`, `filing_date`, `accession_number`, `document_url`.

#### 👤 Modulo 2: Insider Trading Engine (`insider.py`)
* **Fonte dati:** SEC Form 4 (Statement of Changes in Beneficial Ownership).
* **Funzionalità:**
  * Sfrutta il formato **XML nativo** fornito direttamente da EDGAR (nessun HTML sporco da raschiare).
  * Estrazione campi chiave:
    * **Chi:** Nome dell'insider, ruolo aziendale (`officerTitle`, `isDirector`, `isTenPercentOwner`).
    * **Cosa:** Ticker, data transazione, tipo strumento (azioni ordinarie, stock options).
    * **Azione:** Codice di acquisizione o cessione (`A` = Acquisto a mercato, `D` = Vendita a mercato, `M` = Esercizio opzioni).
    * **Valore:** Numero di quote, prezzo per azione e controvalore totale in USD.
* **Output:** Tabella normalizzata o JSON pronto per generare post social (Idea 2) o alert portfolio (Idea 1).

#### 🤝 Modulo 3: Events & Merger Arbitrage Parser (`events.py` / `merger.py`)
* **Fonte dati:** Form 8-K (comunicati straordinari) e filing M&A (`DEFM14A`, `S-4`, `SC TO`, `Form 425`).
* **Funzionalità:**
  * Normalizzazione HTML con pulizia radicale di tag CSS, script e boilerplate legale EDGAR.
  * **Parser per "Items" dell'8-K:**
    * *Item 1.01:* Entry into a Material Definitive Agreement (Accordi di fusione / contratti miliardari).
    * *Item 1.02:* Termination of Material Agreement (Rottura di deal / contenziosi).
    * *Item 2.02:* Risultati operativi (Flash earnings trimestrali).
    * *Item 5.02:* Cambio di vertici aziendali (CEO, CFO, membri del CdA).
  * Per M&A (DEFM14A / S-4): estrazione preliminare del testo chiave relativo a corrispettivo dell'offerta (cash vs stock), termination fee e clausole regolatorie antitrust.
* **Output:** Testo strutturato pulito, pronto per essere letto direttamente o passato a un prompt LLM senza saturare i token.

---

## 3. Key Assumptions to Validate
- [ ] **SEC User-Agent Compliance:** Il rispetto scrupoloso delle intestazioni `User-Agent: Nome email@dominio.com` e il rate-limiting locale (max 8-10 req/s) garantiscono zero blocchi HTTP 403.
- [ ] **XML Uniformity per Form 4:** L'XML dei Form 4 è consistente e standardizzato tra le diverse società quotate.
- [ ] **Item Regex Parsing:** La segmentazione degli "Item" nell'8-K è sufficientemente robusta per isolare le notizie rilevanti senza scartare testo critico.
- [ ] **CIK Mapping Cache:** La mappa Ticker -> CIK (`company_tickers.json` della SEC) può essere salvata localmente in cache per risolvere le chiamate con latenza zero.

---

## 4. MVP Scope (Cosa c'è dentro nel primo rilascio)
1. **Client di base (`client.py`):**
   * Gestione sessione HTTP conforme con header e rate limiter integrato.
   * Mapper Ticker <-> CIK automatico.
2. **Modulo 1 (`feed.py`):**
   * Funzione `get_latest_filings(filter_forms=['8-K', '4'], tickers=None)` con output lista/JSON.
3. **Modulo 2 (`insider.py`):**
   * Funzione `get_insider_trades(ticker, limit=5)` con estrazione XML nativo.
4. **Modulo 3 (`events.py`):**
   * Funzione `get_material_events(ticker, limit=5)` con estrazione e pulizia degli Item dell'8-K.
5. **Script Demo (`demo.py`):**
   * Test funzionante su 2-3 ticker (es. AAPL, NVDA o target M&A recente) che stampa a video e salva in `.json` i risultati puliti.

---

## 5. Not Doing (and Why)
- ❌ **Nessun parsing di Bilanci 10-K / 10-Q (XBRL):** Per dati di bilancio, utili e multipli si usa `yfinance`. Parsare l'XBRL nativo è una complessità non necessaria.
- ❌ **Nessuna dipendenza diretta da LLM nel Core:** Il Core estrae e normalizza. Gli script downstream (bot Telegram, generatore post Instagram, analista M&A) integreranno il proprio LLM preferito passando il testo prodotto dal Core.
- ❌ **Nessun database persistente obbligatorio:** Il Core restituisce oggetti Python serializzabili con metodo `.to_json()` / `.to_dict()`. La scelta di salvarli su SQLite, Postgres o file locali spetta all'applicazione finale.
- ❌ **Nessun filing burocratico (EFFECT, 144, CORRESP, S-1 standard):** Filtrati a monte per azzerare il rumore informativo.

---

## 6. Prossimi Passi
1. Creare la struttura del pacchetto:
   ```
   sec/
   ├── sec_core/
   │   ├── __init__.py
   │   ├── client.py        # SEC HTTP Client, Rate Limiter & CIK Cache
   │   ├── feed.py          # Real-time RSS/Atom Stream
   │   ├── insider.py       # Form 4 XML Parser
   │   └── events.py        # 8-K & M&A HTML Cleaner / Item Extractor
   ├── docs/
   │   └── ideas/
   │       └── sec-core.md  # Questo documento di specifica
   └── demo.py              # Script di test e validazione
   ```
2. Implementare `client.py` e testare la risposta della SEC.
