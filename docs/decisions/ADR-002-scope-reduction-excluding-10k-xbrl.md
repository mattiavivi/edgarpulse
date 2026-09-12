# ADR-002: Riduzione del Perimetro ed Esclusione dei Bilanci Contabili (Form 10-K / 10-Q XBRL)

## Status
Accepted

## Date
2026-09-11

## Context
Nella fase iniziale di brainstorming, era stato ipotizzato di includere in `sec_core` anche l'estrazione dei bilanci storici e delle metriche fondamentali (stato patrimoniale, conto economico, flussi di cassa) contenuti nei report annuali (`10-K`) e trimestrali (`10-Q`) della SEC.

Tuttavia, l'analisi tecnica ha evidenziato due fattori critici:
1. **Complessità dei dati XBRL:** I bilanci SEC sono memorizzati in alberi semantici XBRL o documenti Inline XBRL (iXBRL) che contengono tassonomie contabili mutevoli di anno in anno, rendendo il parsing robusto un progetto a sé stante di enorme complessità.
2. **Ridondanza con servizi esistenti:** Numerose librerie gratuite e altamente ottimizzate (es. `yfinance`, Financial Modeling Prep API) estraggono già i dati di bilancio storici, multipli P/E, EPS e debiti in modo pulito con una singola riga di codice.

Al contrario, i dati su **notizie straordinarie in tempo reale (8-K)**, **insider trading (Form 4)** e **accordi di fusione/M&A (DEFM14A, S-4)** non sono coperti adeguatamente o tempestivamente dalle API gratuite di mercato.

## Decision
Escludere categoricamente l'ingestione e il parsing dei dati quantitativi contabili da 10-K e 10-Q in `sec_core`. Delegare qualsiasi futuro requisito di metriche finanziarie contabili a `yfinance` o a provider di mercato dedicati.

Concentrare il 100% dell'effort sui tre formati a maggior asimmetria informativa ("Alpha"):
- **Streaming Live Atom:** per l'intercettazione istantanea dei filing.
- **Form 4 XML:** per il tracciamento degli acquisti e vendite dei dirigenti (insider trading).
- **Form 8-K & Proxy Statements M&A:** per contratti definitivi, cambi di leadership e clausole di fusione.

## Alternatives Considered

### Alternative 1: Parsing nativo dell'albero XBRL con `arelle` o parser custom
- **Pros:** Accesso diretto e non filtrato alle voci di bilancio ufficiali depositate.
- **Cons:** Aggiunge dipendenze enormi (libreria `arelle` pesa centinaia di megabyte) e introduce una fragilità elevata legata alle tassonomie contabili US-GAAP / IFRS.
- **Rejected:** Richiede settimane di sviluppo senza aggiungere reale valore differenziante rispetto a quanto offerto gratuitamente da `yfinance`.

### Alternative 2: Scraping del testo HTML dei 10-K
- **Pros:** Estrazione delle sezioni narrative (MD&A, Risk Factors).
- **Cons:** Documenti da centinaia di pagine (10-20 MB di HTML) che consumano enormi volumi di memoria e token LLM.
- **Rejected:** Fuori dall'MVP e non prioritario per le 3 idee target (alert di portafoglio, post social, merger arbitrage).

## Consequences
- Riduzione stimata del 70% della complessità implementativa del Core Engine.
- Il Core Engine rimane rapido, snello e focalizzato solo su eventi ad alto impatto.
- Se un'applicazione finale richiederà metriche di bilancio (es. EV/EBITDA per una transazione M&A), potrà combinare `sec_core` con `yfinance` a livello di applicazione/script client.
