# ADR-003: Pipeline In-Memory con Modelli Tipizzati e Serializzazione JSON vs Database Integrato

## Status
Accepted

## Date
2026-09-11

## Context
In fase di design del Core, si è valutata la possibilità di integrare un database relazionale (es. SQLite o PostgreSQL) o un vector database (es. ChromaDB) direttamente all'interno del modulo `sec_core` per memorizzare la cronologia dei filing e gli embeddings testuali.

Dato che le tre applicazioni a valle presentano esigenze architetturali divergenti:
1. **Portfolio Alert Bot:** richiede verosimilmente uno storage leggero per evitare notifiche duplicate (es. stato degli ultimi ID visti).
2. **Social Media Automation:** lavora a batch (es. cron settimanale sui filing più clamorosi) o su code di messaggi.
3. **Merger Arbitrage Tracker:** richiede un modello dati relazionale complesso per tracciare le condizioni di chiusura del deal, le date antitrust e gli spread di prezzo nel tempo.

## Decision
Non accoppiare `sec_core` ad alcun database persistente o layer ORM. 

`sec_core` opera come un motore puro di estrazione e normalizzazione in-memory:
- Restituisce istanze tipizzate di Dataclass Python (`FeedEntry`, `InsiderFiling`, `MaterialEventFiling`, `EventItem`).
- Ciascuna Dataclass espone i metodi `.to_dict()` e serializzazione in JSON standard.
- L'unica persistenza interna a `sec_core` è la cache su file locale per il file `company_tickers.json` della SEC (`.cache/company_tickers.json`) per azzerare le chiamate ridondanti di risoluzione CIK.

## Alternatives Considered

### Alternative 1: Integrare SQLite con schema fisso nel Core
- **Pros:** Deduplica automatica dei filing già scaricati all'interno della stessa libreria.
- **Cons:**
  - Impone una struttura di tabelle rigida non adatta a tutti i consumatori a valle.
  - Introduce concorrenza/locking su file di database in scenari multi-processo.
  - Aggiunge migrazioni e complessità di manutenzione schema.
- **Rejected:** Accoppiamento precoce (premature coupling).

### Alternative 2: Integrare un Vector DB locale (es. Chroma/FAISS)
- **Pros:** Ricerca semantica istantanea sui testi dei filing.
- **Cons:** Dipendenze pesantissime, consumo elevato di RAM e lock-in su specifici modelli di embedding prima di aver validato i prompt effettivi.
- **Rejected:** La vettorizzazione appartiene al layer applicativo downstream, non all'ingestion engine.

## Consequences
- `sec_core` è completamente stateless e privo di effetti collaterali indesiderati.
- Massima flessibilità per chi consuma la libreria: può scegliere se salvare su SQLite, DuckDB, MongoDB, file JSON locali o inviare i dati direttamente tramite webhook.
- La deduplica dei filing (es. tramite `accession_number`) è demandata al chiamante.
