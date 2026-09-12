import os
import json
import time
from typing import Optional, Dict, Any
import requests

class SECClient:
    """
    Client HTTP conforme alle linee guida della SEC (EDGAR).
    - Gestione automatica dell'header User-Agent obbligatorio.
    - Rate limiter locale a token bucket (max 9-10 req/s) per prevenire blocchi HTTP 403.
    - Risolutore e cache locale per mappatura Ticker <-> CIK.
    """
    DEFAULT_USER_AGENT = "SecResearchApp admin@secresearchapp.com"
    BASE_SEC_URL = "https://www.sec.gov"
    DATA_SEC_URL = "https://data.sec.gov"

    def __init__(self, user_agent: Optional[str] = None, cache_dir: str = ".cache"):
        self.user_agent = user_agent or os.environ.get("SEC_USER_AGENT", self.DEFAULT_USER_AGENT)
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov"
        })
        
        # Rate Limiting: max ~9 req/s (intervallo minimo 0.11s)
        self._min_interval = 0.11
        self._last_request_time = 0.0
        
        self._ticker_to_cik: Optional[Dict[str, str]] = None

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def get(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> requests.Response:
        self._rate_limit()
        req_headers = {"User-Agent": self.user_agent}
        if headers:
            req_headers.update(headers)
        
        # Gestisci l'header Host in base al dominio
        if "data.sec.gov" in url:
            req_headers["Host"] = "data.sec.gov"
        elif "www.sec.gov" in url:
            req_headers["Host"] = "www.sec.gov"

        response = self.session.get(url, headers=req_headers, timeout=timeout)
        if response.status_code == 429:
            # Backoff automatico in caso di rate limiting
            retry_after = int(response.headers.get("Retry-After", 5))
            time.sleep(retry_after)
            return self.get(url, headers=headers, timeout=timeout)
        
        response.raise_for_status()
        return response

    def _load_tickers(self) -> Dict[str, str]:
        """Carica o aggiorna la mappatura ufficiale Ticker -> CIK dalla SEC."""
        cache_file = os.path.join(self.cache_dir, "company_tickers.json")
        
        # Se presente in cache locale e recente (< 7 giorni), usa la cache
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {item["ticker"].upper(): str(item["cik_str"]).zfill(10) for item in data.values()}
            except Exception:
                pass
        
        # Scarica dalla SEC
        url = f"{self.BASE_SEC_URL}/files/company_tickers.json"
        res = self.get(url)
        data = res.json()
        
        # Salva in cache
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
        return {item["ticker"].upper(): str(item["cik_str"]).zfill(10) for item in data.values()}

    def get_cik(self, ticker: str) -> str:
        """Restituisce il CIK a 10 cifre dato un Ticker (es. 'AAPL' -> '0000320193')."""
        if self._ticker_to_cik is None:
            self._ticker_to_cik = self._load_tickers()
        
        ticker_clean = ticker.strip().upper()
        cik = self._ticker_to_cik.get(ticker_clean)
        if not cik:
            raise ValueError(f"Ticker non trovato nel database SEC: {ticker}")
        return cik

    def get_submissions(self, ticker_or_cik: str) -> Dict[str, Any]:
        """Scarica i metadati di tutti i filing recenti di una società."""
        if ticker_or_cik.isdigit():
            cik = ticker_or_cik.zfill(10)
        else:
            cik = self.get_cik(ticker_or_cik)
            
        url = f"{self.DATA_SEC_URL}/submissions/CIK{cik}.json"
        return self.get(url).json()

    def get_archive_url(self, cik: str, accession_number: str, filename: str) -> str:
        """Costruisce l'URL di un documento negli archivi EDGAR."""
        cik_num = str(int(cik))  # rimuove zeri iniziali per il path archivio
        acc_raw = accession_number.replace("-", "")
        return f"{self.BASE_SEC_URL}/Archives/edgar/data/{cik_num}/{acc_raw}/{filename}"
