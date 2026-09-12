import re
from html.parser import HTMLParser
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from .client import SECClient

class HTMLTextExtractor(HTMLParser):
    """
    Parser HTML leggero e veloce basato sulla libreria standard Python.
    Rimuove tag di stile, script, commenti e preserva la spaziatura leggibile.
    """
    def __init__(self):
        super().__init__()
        self._reset()

    def _reset(self):
        self.text_parts = []
        self.ignore_tags = {"style", "script", "head", "meta", "link"}
        self.current_ignore_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.ignore_tags:
            self.current_ignore_depth += 1
        elif tag.lower() in ("p", "div", "br", "tr", "h1", "h2", "h3", "h4", "li"):
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.ignore_tags:
            self.current_ignore_depth = max(0, self.current_ignore_depth - 1)
        elif tag.lower() in ("p", "div", "tr", "h1", "h2", "h3", "h4"):
            self.text_parts.append("\n")

    def handle_data(self, data):
        if self.current_ignore_depth == 0:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned + " ")

    def get_clean_text(self) -> str:
        raw_text = "".join(self.text_parts)
        # Normalizza righe multiple vuote
        normalized = re.sub(r"\n{3,}", "\n\n", raw_text)
        # Normalizza spazi multipli
        normalized = re.sub(r"[ \t]{2,}", " ", normalized)
        return normalized.strip()

@dataclass
class EventItem:
    item_code: str         # es. "1.01", "5.02", "8.01"
    item_title: str        # es. "Entry into a Material Definitive Agreement"
    content_preview: str   # primi ~1000 caratteri di testo pulito
    full_content: str
    is_ma_related: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MaterialEventFiling:
    ticker: str
    company_name: str
    form: str              # "8-K", "DEFM14A", "S-4", ecc.
    filing_date: str
    accession_number: str
    document_url: str
    items_detected: List[str] = field(default_factory=list)
    parsed_items: List[EventItem] = field(default_factory=list)
    is_ma_deal: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class SECEventManager:
    """
    Modulo 3: Estrazione e segmentazione di eventi straordinari (8-K) e filing M&A.
    """
    ITEM_TITLES = {
        "1.01": "Entry into a Material Definitive Agreement",
        "1.02": "Termination of a Material Definitive Agreement",
        "1.03": "Bankruptcy or Receivership",
        "2.01": "Completion of Acquisition or Disposition of Assets",
        "2.02": "Results of Operations and Financial Condition",
        "3.01": "Notice of Delisting or Failure to Satisfy a Continued Listing Rule",
        "5.01": "Changes in Control of Registrant",
        "5.02": "Departure of Directors or Certain Officers; Election of Directors",
        "7.01": "Regulation FD Disclosure",
        "8.01": "Other Events",
        "9.01": "Financial Statements and Exhibits"
    }

    MA_KEYWORDS = [
        "merger agreement", "acquisition", "tender offer", "business combination",
        "reorganization", "purchase agreement", "termination fee", "breakup fee"
    ]

    def __init__(self, client: Optional[SECClient] = None):
        self.client = client or SECClient()

    def clean_html(self, html_content: str) -> str:
        """Pulisce l'HTML grezzo EDGAR estraendo testo pulito formattato."""
        parser = HTMLTextExtractor()
        parser.feed(html_content)
        return parser.get_clean_text()

    def extract_items_from_text(self, text: str) -> List[EventItem]:
        """
        Segmenta il testo di un 8-K riconoscendo le sezioni 'Item X.XX'.
        """
        item_regex = re.compile(r"(Item\s+(\d\.\d\d))\s*([^\n\r]+)?", re.IGNORECASE)
        matches = list(item_regex.finditer(text))
        
        parsed_items: List[EventItem] = []
        for i, match in enumerate(matches):
            item_code = match.group(2)
            title_candidate = match.group(3).strip() if match.group(3) else ""
            
            # Se il titolo non è ben formattato, usa il mapping ufficiale
            standard_title = self.ITEM_TITLES.get(item_code, title_candidate or f"Item {item_code}")
            
            start_pos = match.end()
            end_pos = matches[i + 1].start() if (i + 1 < len(matches)) else len(text)
            
            # Blocca se si arriva alla sezione SIGNATURES
            sig_match = re.search(r"\n\s*SIGNATURES?", text[start_pos:end_pos], re.IGNORECASE)
            if sig_match:
                end_pos = start_pos + sig_match.start()
                
            item_content = text[start_pos:end_pos].strip()
            
            # Controllo se correlato a M&A
            is_ma = (item_code in ("1.01", "1.02", "2.01", "5.01")) or any(
                kw in item_content.lower() for kw in self.MA_KEYWORDS
            )
            
            parsed_items.append(EventItem(
                item_code=item_code,
                item_title=standard_title,
                content_preview=item_content[:800] + ("..." if len(item_content) > 800 else ""),
                full_content=item_content,
                is_ma_related=is_ma
            ))
            
        return parsed_items

    def get_latest_material_events(self, ticker: str, limit: int = 5) -> List[MaterialEventFiling]:
        """
        Scarica gli ultimi Form 8-K e filing M&A per il ticker specificato.
        """
        submissions = self.client.get_submissions(ticker)
        company_name = submissions.get("name", ticker)
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])
        items_list = recent.get("items", [])
        cik = str(submissions.get("cik", "")).zfill(10)

        events: List[MaterialEventFiling] = []
        target_forms = {"8-K", "8-K/A", "DEFM14A", "S-4", "425"}

        for i, form in enumerate(forms):
            if form in target_forms:
                acc = accessions[i]
                doc = primary_docs[i]
                filing_date = dates[i] if i < len(dates) else ""
                declared_items = [it.strip() for it in items_list[i].split(",") if it.strip()] if i < len(items_list) else []
                
                doc_url = self.client.get_archive_url(cik, acc, doc)
                
                # Scarica e pulisci il testo del documento
                parsed_items = []
                is_ma_deal = ("1.01" in declared_items) or (form in ("DEFM14A", "S-4", "425"))
                
                try:
                    res = self.client.get(doc_url)
                    clean_txt = self.clean_html(res.text)
                    parsed_items = self.extract_items_from_text(clean_txt)
                    if any(p.is_ma_related for p in parsed_items):
                        is_ma_deal = True
                except Exception:
                    pass

                events.append(MaterialEventFiling(
                    ticker=ticker.upper(),
                    company_name=company_name,
                    form=form,
                    filing_date=filing_date,
                    accession_number=acc,
                    document_url=doc_url,
                    items_detected=declared_items,
                    parsed_items=parsed_items,
                    is_ma_deal=is_ma_deal
                ))

                if len(events) >= limit:
                    break

        return events
