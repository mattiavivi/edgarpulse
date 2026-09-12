# EdgarPulse: EDGAR Ingestion & Parsing Engine

> Lightweight, dependency-free (only `requests`) Python engine for high-value SEC EDGAR data: **Form 8-K** material events, **Form 4** insider trading, real-time **Atom feed**. Returns typed Python objects + clean JSON ready for LLM prompts or market alerts.
>
> Leggero motore Python per dati SEC EDGAR ad alto valore: eventi 8-K, insider Form 4, feed Atom real-time. Output tipizzato + JSON pulito pronto per LLM.
>
> Ex `sec-core`, rinominato `edgarpulse` per unicità su PyPI/GitHub.

---

## English

### Install

```bash
pip install -r requirements.txt
# or (editable, after publishing / locally):
pip install -e .
```

Requirements: Python 3.8+, `requests` only. No pandas / lxml / pyarrow.

Set a SEC-compliant User-Agent (required, else HTTP 403):

```bash
export SEC_USER_AGENT="MyApp admin@myapp.com"
```

### Quick start

```bash
python3 examples/demo.py
# output -> examples/output.json
```

```python
from edgarpulse import SECClient, SECFeed, SECInsider, SECEventManager

client = SECClient(user_agent="MyPortfolioBot admin@myportfoliobot.com")

# 1. Ticker -> CIK
cik = client.get_cik("AAPL")  # '0000320193'

# 2. Real-time Atom feed, 8-K + Form 4 only
feed = SECFeed(client=client)
filings = feed.get_latest_filings(target_forms=["8-K", "4"], count=50)

# 3. Insider trading (native Form 4 XML)
insider = SECInsider(client=client)
reports = insider.get_latest_insider_trades("NVDA", limit=5)

# 4. Material events & M&A (8-K / DEFM14A / S-4 / 425)
events_mgr = SECEventManager(client=client)
events = events_mgr.get_latest_material_events("NVDA", limit=3)
```

See `examples/demo.py` and `examples/output.json` for full end-to-end output.

### Layout

```
edgarpulse/
├── edgarpulse/             # extraction package (stable API, don't break)
│   ├── __init__.py         # main exports
│   ├── client.py           # SECClient: session, rate limit, CIK cache
│   ├── feed.py             # SECFeed: real-time Atom ingestion
│   ├── insider.py          # SECInsider: Form 4 XML parser
│   └── events.py           # SECEventManager: 8-K HTML cleaner / Items / M&A
├── examples/
│   ├── demo.py             # end-to-end validation script
│   └── output.json         # sample generated output
├── docs/
│   ├── ideas/sec-core.md   # historic spec (old name)
│   └── decisions/ADR-00*.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── LICENSE (MIT)
└── README.md
```

`edgarpulse/` is the **extraction layer**. Future projects (alerts, bots, LLM analysts) should live alongside as separate packages/apps and import `edgarpulse`, never fork it.

### SEC compliance

1. **User-Agent** `Name admin@domain.com` format is mandatory.
2. **Rate limit 10 req/s** — client enforces ~9 req/s (0.11s interval) + exponential backoff on 429.
3. **XSL rendering** — Form 4 `xslF345X...` paths are resolved to raw `.xml`.

ADRs in `docs/decisions/`: custom lightweight engine vs `edgartools`, 10-K/XBRL out of scope (use `yfinance`), in-memory JSON pipeline vs DB.

---

## Italiano

### Installazione

```bash
pip install -r requirements.txt
pip install -e .   # sviluppo locale
```

Solo Python 3.8+ e `requests`.

### Demo

```bash
python3 examples/demo.py
```

Moduli: `SECClient` (sessione + CIK cache in `.cache/`), `SECFeed` (Atom live filtrato), `SECInsider` (XML Form 4: nome, ruolo, azioni, prezzo, controvalore USD), `SECEventManager` (cleaner HTML, split per Item 8-K, flag M&A).

Struttura pubblicata: pacchetto `edgarpulse/` = layer di estrazione stabile; gli altri tuoi progetti futuri importano da qui.

### Pubblicazione

```bash
python -m build
twine upload dist/*
```

Prima del push: verifica `LICENSE`, `python -m pytest`, `ruff check edgarpulse`.
Repo: `https://github.com/mattiavivi/edgarpulse`.

---
License: MIT. Data source: SEC EDGAR (respect rate limits / User-Agent policy).
