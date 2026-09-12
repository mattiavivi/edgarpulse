import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from .client import SECClient

@dataclass
class InsiderTransaction:
    security_title: str
    transaction_date: str
    transaction_code: str          # 'P' = Purchase, 'S' = Sale, 'M' = Option Exercise, 'A' = Grant
    acquired_disposed_code: str    # 'A' = Acquired, 'D' = Disposed
    shares: float
    price_per_share: Optional[float]
    total_value: Optional[float]
    is_direct: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class InsiderFiling:
    ticker: str
    issuer_name: str
    owner_name: str
    is_officer: bool
    officer_title: Optional[str]
    is_director: bool
    is_ten_percent_owner: bool
    period_of_report: str
    transactions: List[InsiderTransaction] = field(default_factory=list)
    
    # Metriche sintetiche calcolate
    total_shares_bought: float = 0.0
    total_shares_sold: float = 0.0
    total_usd_bought: float = 0.0
    total_usd_sold: float = 0.0

    def compute_summary(self):
        self.total_shares_bought = sum(t.shares for t in self.transactions if t.acquired_disposed_code == 'A')
        self.total_shares_sold = sum(t.shares for t in self.transactions if t.acquired_disposed_code == 'D')
        self.total_usd_bought = sum(t.total_value or 0.0 for t in self.transactions if t.acquired_disposed_code == 'A')
        self.total_usd_sold = sum(t.total_value or 0.0 for t in self.transactions if t.acquired_disposed_code == 'D')

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

class SECInsider:
    """
    Modulo 2: Parser XML nativo per Form 4 (Insider Trading).
    - Estrae acquirenti/venditori, ruoli aziendali e controvalori delle transazioni.
    """
    def __init__(self, client: Optional[SECClient] = None):
        self.client = client or SECClient()

    def parse_form4_xml(self, xml_content: str) -> InsiderFiling:
        """Esegue il parsing di un documento XML Form 4 nativo."""
        root = ET.fromstring(xml_content)
        
        # Info Emittente (Azienda)
        issuer_symbol = ""
        symbol_elem = root.find(".//issuer/issuerTradingSymbol")
        if symbol_elem is not None and symbol_elem.text:
            issuer_symbol = symbol_elem.text.strip().upper()
            
        issuer_name = ""
        name_elem = root.find(".//issuer/issuerName")
        if name_elem is not None and name_elem.text:
            issuer_name = name_elem.text.strip()
            
        period_elem = root.find(".//periodOfReport")
        period_of_report = period_elem.text.strip() if period_elem is not None and period_elem.text else ""

        # Info Insider (Reporting Owner)
        owner_name = ""
        owner_elem = root.find(".//reportingOwnerId/rptOwnerName")
        if owner_elem is not None and owner_elem.text:
            owner_name = owner_elem.text.strip()

        rel_elem = root.find(".//reportingOwnerRelationship")
        is_officer = False
        is_director = False
        is_ten_percent_owner = False
        officer_title = None

        if rel_elem is not None:
            is_officer = (rel_elem.findtext("isOfficer", "0") in ("1", "true", "True"))
            is_director = (rel_elem.findtext("isDirector", "0") in ("1", "true", "True"))
            is_ten_percent_owner = (rel_elem.findtext("isTenPercentOwner", "0") in ("1", "true", "True"))
            title_node = rel_elem.find("officerTitle")
            if title_node is not None and title_node.text:
                officer_title = title_node.text.strip()

        filing = InsiderFiling(
            ticker=issuer_symbol,
            issuer_name=issuer_name,
            owner_name=owner_name,
            is_officer=is_officer,
            officer_title=officer_title,
            is_director=is_director,
            is_ten_percent_owner=is_ten_percent_owner,
            period_of_report=period_of_report
        )

        # Transazioni non derivate (Azioni ordinarie)
        for tx in root.findall(".//nonDerivativeTransaction"):
            sec_title = tx.findtext(".//securityTitle/value", "Common Stock")
            tx_date = tx.findtext(".//transactionDate/value", "")
            tx_code = tx.findtext(".//transactionCoding/transactionCode", "")
            shares_str = tx.findtext(".//transactionShares/value", "0")
            price_str = tx.findtext(".//transactionPricePerShare/value", "")
            ad_code = tx.findtext(".//transactionAcquiredDisposedCode/value", "")
            ownership_nature = tx.findtext(".//directOrIndirectOwnership/value", "D")

            try:
                shares = float(shares_str)
            except ValueError:
                shares = 0.0

            try:
                price = float(price_str) if price_str else None
            except ValueError:
                price = None

            total_val = (shares * price) if (price is not None) else None

            filing.transactions.append(InsiderTransaction(
                security_title=sec_title,
                transaction_date=tx_date,
                transaction_code=tx_code,
                acquired_disposed_code=ad_code,
                shares=shares,
                price_per_share=price,
                total_value=total_val,
                is_direct=(ownership_nature.upper() == "D")
            ))

        filing.compute_summary()
        return filing

    def get_latest_insider_trades(self, ticker: str, limit: int = 5) -> List[InsiderFiling]:
        """
        Recupera e analizza gli ultimi Form 4 depositati per un determinato ticker.
        """
        submissions = self.client.get_submissions(ticker)
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        cik = str(submissions.get("cik", "")).zfill(10)

        results: List[InsiderFiling] = []
        for i, form in enumerate(forms):
            if form == "4":
                acc = accessions[i]
                doc = primary_docs[i]
                
                # Se il documento primario è il rendering HTML (xsl...), puntiamo al file .xml puro
                clean_doc = doc
                if "xsl" in doc.lower():
                    # Esempio: xslF345X06/wk-form4_1788901755.xml -> wk-form4_1788901755.xml
                    clean_doc = doc.split("/")[-1]
                
                xml_url = self.client.get_archive_url(cik, acc, clean_doc)
                try:
                    res = self.client.get(xml_url)
                    filing = self.parse_form4_xml(res.text)
                    results.append(filing)
                except Exception as e:
                    # In caso di path alternativo o eccezione di parsing, continua
                    pass

                if len(results) >= limit:
                    break

        return results
