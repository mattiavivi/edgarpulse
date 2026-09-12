# ADR-001: Implementazione di un Engine Leggero Custom (`sec_core`) rispetto a `edgartools` o `sec-edgar-downloader`

## Status
Accepted

## Date
2026-09-11

## Context
Per supportare tre potenziali applicazioni a valle (1. Notifiche di portafoglio, 2. Generazione post social via LLM, 3. Screener M&A/Merger Arbitrage), avevamo bisogno di una pipeline di ingestione ed estrazione dai server EDGAR della SEC (Securities and Exchange Commission).

I requisiti chiave erano:
- **Streaming in tempo reale:** Rilevazione quasi istantanea di nuovi filing via Feed Atom.
- **Parsing selettivo ad alto valore:** Estrazione tabellare pulita di transazioni insider (Form 4) e segmentazione per "Item" dei comunicati straordinari (Form 8-K / accordi M&A).
- **Leggerezza e zero lock-in:** Capacità di girare come worker leggero o modulo importabile senza overhead di decine di dipendenze pesanti.
- **Conformità SEC:** Rispetto scrupoloso dell'header `User-Agent` e del limite di velocità (max 10 req/s) per prevenire blocchi HTTP 403 e 429.

Nel panorama open-source Python esistevano due alternative note: `sec-edgar-downloader` e `edgartools` (`edgar`).

## Decision
Sviluppare un core engine proprietario su misura (`sec_core`), basato unicamente su standard library Python e sul client HTTP `requests`, con parser XML nativi (`xml.etree.ElementTree`) e cleaner HTML standard (`html.parser`).

## Alternatives Considered

### Alternative 1: `sec-edgar-downloader`
- **Pros:** API immediata per scaricare file grezzi per ticker e tipologia di form.
- **Cons:**
  - È esclusivamente un downloader che scrive file HTML/TXT grezzi su disco in directory annidate (`sec-edgar-filings/AAPL/...`).
  - Nessun layer di parsing: lascia all'utente il compito di ripulire tag HTML, parsare XML o estrarre campi tabellari.
  - Nessun supporto per lo streaming real-time via Atom/RSS feed.
  - Non opera in-memory.
- **Rejected:** Avrebbe richiesto comunque la scrittura dell'intero layer di parsing e non supportava il requisito di streaming.

### Alternative 2: `edgartools` (`edgar`)
- **Pros:**
  - Libreria matura e molto ricca di funzionalità.
  - Parser completi per 10-K, 10-Q, 8-K, Form 4, 13F.
  - Integrazione nativa con `pandas` e rendering Markdown per terminali/notebook.
- **Cons:**
  - Dipendenze estremamente pesanti: impone `pandas`, `pyarrow`, `rich`, `lxml`, `httpx`, `fastapi`, ecc., aumentando le dimensioni dell'ambiente e il tempo di avvio.
  - È progettata principalmente per Data Science esplorativa e ambienti Jupyter Notebook interattivi, non come micro-engine event-driven o worker da eseguire a basso consumo.
  - Gestione del feed real-time meno diretta e focalizzata.
- **Rejected:** Eccessiva complessità e "black box" non necessaria per gli specifici flussi richiesti.

### Alternative 3: Sviluppo di `sec_core` (Scelta adottata)
- **Pros:**
  - Zero dipendenze pesanti (solo `requests` + moduli standard Python: `xml.etree`, `html.parser`, `re`, `json`).
  - Controllo millimetrico sul rate limiter (9 req/s automatico) e sulla cache locale dei CIK.
  - Produce direttamente oggetti dataclass Python e dizionari pronti per la serializzazione `.to_json()` e l'invio a prompt LLM.
- **Cons:**
  - Supporta solo i formati target (`8-K`, `4`, feed Atom, `DEFM14A`/`S-4`), non l'intero catalogo di oltre 100 form SEC.
- **Adopted:** Perfettamente allineato al principio "Simplicity is the ultimate sophistication" e mirato ai nostri casi d'uso.

## Consequences
- Il codebase rimane compatto (< 500 righe totali), manutenibile e privo di conflitti di dipendenze.
- L'esecuzione è istantanea (i test end-to-end completano in 1-2 secondi).
- Eventuali modifiche alle euristiche di estrazione M&A o campi insider possono essere implementate direttamente senza attendere aggiornamenti di librerie terze.
- Non possiamo delegare il parsing di nuovi formati a una libreria esterna, ma dobbiamo scrivere le regex/regole XML per ciascun nuovo formato aggiunto.
