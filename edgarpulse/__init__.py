"""
edgarpulse: Libreria modulare e lightweight per l'ingestion di dati SEC EDGAR.
Focalizzata su:
1. Feed RSS/Atom in tempo reale
2. Insider Trading (Form 4 XML)
3. Eventi straordinari e M&A (Form 8-K / DEFM14A)
"""

from .client import SECClient
from .feed import SECFeed, FeedEntry
from .insider import SECInsider, InsiderFiling, InsiderTransaction
from .events import SECEventManager, MaterialEventFiling, EventItem

__all__ = [
    "SECClient",
    "SECFeed",
    "FeedEntry",
    "SECInsider",
    "InsiderFiling",
    "InsiderTransaction",
    "SECEventManager",
    "MaterialEventFiling",
    "EventItem"
]
