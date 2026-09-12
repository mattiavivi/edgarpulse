import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from .client import SECClient

@dataclass
class FeedEntry:
    title: str
    form: str
    company_name: str
    cik: str
    updated: str
    link: str
    accession_number: Optional[str] = None
    file_number: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class SECFeed:
    """
    Modulo 1: Streaming e filtro in tempo reale dei feed Atom della SEC.
    - Monitora l'Atom feed globale o per specifici form/aziende.
    - Filtra per watchlist ticker o per form ad alto valore (8-K, Form 4, DEFM14A).
    """
    ATOM_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom"
    
    # Regex per estrarre: Form - Nome Azienda (CIK) (Ruolo)
    TITLE_PATTERN = re.compile(r"^(.+?)\s+-\s+(.+?)\s*\((\d{10})\)\s*\((Filer|Reporting|Issuer)\)", re.IGNORECASE)
    ACCESSION_PATTERN = re.compile(r"AccNo:\s*([0-9\-]+)")

    def __init__(self, client: Optional[SECClient] = None):
        self.client = client or SECClient()

    def get_latest_filings(
        self,
        target_forms: Optional[List[str]] = None,
        watchlist_tickers: Optional[List[str]] = None,
        count: int = 100
    ) -> List[FeedEntry]:
        """
        Recupera gli ultimi filing pubblicati su EDGAR, applicando filtri mirati.
        - target_forms: lista di form consentiti (es. ['8-K', '4', 'DEFM14A'])
        - watchlist_tickers: lista di ticker da intercettare (es. ['AAPL', 'NVDA'])
        """
        url = f"{self.ATOM_URL}&count={count}"
        response = self.client.get(url)
        
        # Mappa ticker watchlist in CIK per match veloce
        watchlist_ciks = set()
        if watchlist_tickers:
            for ticker in watchlist_tickers:
                try:
                    watchlist_ciks.add(self.client.get_cik(ticker))
                except ValueError:
                    pass
        
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        entries: List[FeedEntry] = []
        for entry_elem in root.findall("atom:entry", ns):
            title_elem = entry_elem.find("atom:title", ns)
            updated_elem = entry_elem.find("atom:updated", ns)
            link_elem = entry_elem.find("atom:link", ns)
            summary_elem = entry_elem.find("atom:summary", ns)
            
            raw_title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            updated = updated_elem.text.strip() if updated_elem is not None and updated_elem.text else ""
            link = link_elem.attrib.get("href", "") if link_elem is not None else ""
            summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""
            
            # Match titolo con regex
            match = self.TITLE_PATTERN.match(raw_title)
            if match:
                form = match.group(1).strip()
                company_name = match.group(2).strip()
                cik = match.group(3).strip()
            else:
                # Fallback di sicurezza se la formattazione varia
                parts = raw_title.split(" - ", 1)
                form = parts[0].strip() if parts else "UNKNOWN"
                company_name = parts[1].strip() if len(parts) > 1 else raw_title
                cik_search = re.search(r"\((\d{10})\)", raw_title)
                cik = cik_search.group(1) if cik_search else ""

            # Estrai Accession Number
            acc_match = self.ACCESSION_PATTERN.search(summary)
            accession_number = acc_match.group(1) if acc_match else None

            # Filtro per Form
            if target_forms:
                target_forms_upper = [f.upper() for f in target_forms]
                form_upper = form.upper()
                def matches_form(f_cur: str, f_target: str) -> bool:
                    if f_cur == f_target:
                        return True
                    if f_cur == f"{f_target}/A":  # Amendment
                        return True
                    if f_target.endswith("*") and f_cur.startswith(f_target[:-1]):
                        return True
                    return False
                
                if not any(matches_form(form_upper, tf) for tf in target_forms_upper):
                    continue

            # Filtro per Watchlist CIK
            if watchlist_ciks and cik not in watchlist_ciks:
                continue

            entries.append(FeedEntry(
                title=raw_title,
                form=form,
                company_name=company_name,
                cik=cik,
                updated=updated,
                link=link,
                accession_number=accession_number
            ))

        return entries
