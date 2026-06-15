"""SEC EDGAR Form 4 fetcher — real open-market insider purchases."""

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List

import requests

from smart_money_tracker.data_collection.base import BaseFetcher
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)

# SEC requires a descriptive User-Agent or requests are rejected with 403
HEADERS = {
    "User-Agent": "SmartMoneyTracker kanishkchaturvedi0804@gmail.com",
    "Accept-Encoding": "gzip, deflate",
}

# Tickers to monitor — expand freely
TRACKED_TICKERS = [
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "NFLX",
    # Semiconductors
    "AMD", "INTC", "QCOM", "AVGO", "MU", "AMAT",
    # Financials
    "JPM", "BAC", "GS", "MS", "WFC", "C", "V", "MA", "AXP", "BLK",
    # Healthcare
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT",
    # Energy
    "XOM", "CVX", "COP", "SLB",
    # Consumer
    "KO", "PEP", "MCD", "WMT", "COST", "TGT", "NKE",
    # Industrials
    "HON", "GE", "CAT", "BA", "LMT", "RTX",
    # Enterprise tech
    "IBM", "ORCL", "CRM", "SAP", "NOW", "ADBE",
    # Telecom / media
    "T", "VZ", "DIS", "CMCSA",
]


class SECEdgarFetcher(BaseFetcher):
    """
    Fetches Form 4 insider purchases directly from SEC EDGAR.

    Only 'P' (open-market purchase) transaction codes are returned —
    RSU vesting, option exercises, sales, and gifts are excluded.
    This is the highest-conviction insider signal: an executive spending
    their own cash to buy shares on the open market.
    """

    def __init__(self, days_back: int = 30, timeout: int = 15):
        self.days_back = days_back
        self.timeout = timeout
        self._cik_map: Dict[str, str] = {}

    def _fetch_impl(self) -> Dict[str, List[dict]]:
        """
        Fetch recent Form 4 'P' transactions for tracked tickers.

        Returns:
            Dict mapping ticker → list of purchase dicts, each with:
            name, title, shares, price, value, date
        """
        self._load_cik_map()
        cutoff = datetime.now() - timedelta(days=self.days_back)
        insider_data: Dict[str, List[dict]] = {}

        for ticker in TRACKED_TICKERS:
            cik = self._cik_map.get(ticker)
            if not cik:
                logger.debug(f"No CIK found for {ticker}, skipping")
                continue

            try:
                purchases = self._get_purchases(ticker, cik, cutoff)
                if purchases:
                    insider_data[ticker] = purchases
                    logger.info(
                        f"{ticker}: {len(purchases)} open-market purchases (P)"
                    )
                else:
                    logger.debug(
                        f"{ticker}: no open-market purchases in last {self.days_back}d"
                    )
                time.sleep(0.15)  # SEC rate limit: max ~10 req/s
            except Exception as e:
                logger.warning(
                    f"Failed to fetch SEC data for {ticker}: "
                    f"{type(e).__name__}: {e}"
                )
                continue

        return insider_data

    def _load_cik_map(self) -> None:
        """Load the full ticker → zero-padded CIK mapping from SEC."""
        url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(url, headers=HEADERS, timeout=self.timeout)
        resp.raise_for_status()
        for entry in resp.json().values():
            ticker = entry.get("ticker", "").upper()
            cik = str(entry.get("cik_str", ""))
            if ticker and cik:
                self._cik_map[ticker] = cik.zfill(10)
        logger.info(f"Loaded CIK map: {len(self._cik_map)} tickers")

    def _get_purchases(
        self, ticker: str, cik: str, cutoff: datetime
    ) -> List[dict]:
        """Return 'P' transactions for a ticker filed on or after cutoff."""
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=HEADERS, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])

        purchases: List[dict] = []

        for form, acc, date_str, primary_doc in zip(
            forms, accessions, filing_dates, primary_docs
        ):
            if form not in ("4", "4/A"):
                continue
            try:
                filing_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            if filing_date < cutoff:
                break  # Results are reverse-chronological

            try:
                txns = self._parse_form4(int(cik), acc, primary_doc)
                purchases.extend(txns)
                time.sleep(0.1)
            except Exception as e:
                logger.debug(
                    f"Skipping Form 4 {acc} for {ticker}: {e}"
                )
                continue

        return purchases

    def _parse_form4(
        self, cik_int: int, accession: str, primary_doc: str
    ) -> List[dict]:
        """Fetch the Form 4 XML and return only 'P' transactions."""
        acc_nodash = accession.replace("-", "")

        # primaryDocument is e.g. "xslF345X06/form4.xml" — the XSLT prefix
        # is just the browser renderer; the raw XML is the filename part only.
        raw_filename = primary_doc.split("/")[-1]
        xml_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_int}/{acc_nodash}/{raw_filename}"
        )

        resp = requests.get(xml_url, headers=HEADERS, timeout=self.timeout)
        resp.raise_for_status()

        return self._extract_purchases(resp.content)

    def _extract_purchases(self, xml_content: bytes) -> List[dict]:
        """Parse Form 4 XML, returning only open-market purchase ('P') transactions."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.debug(f"XML parse error: {e}")
            return []

        def tag(elem) -> str:
            return elem.tag.split("}")[-1].lower()

        # Insider identity from the reporting owner section
        insider_name = ""
        insider_title = ""
        for elem in root.iter():
            t = tag(elem)
            if t == "rptownername" and elem.text:
                insider_name = elem.text.strip()
            elif t == "officertitle" and not insider_title and elem.text:
                insider_title = elem.text.strip()

        purchases = []
        for txn in root.iter():
            if tag(txn) != "nonderivativetransaction":
                continue

            code = shares = price = date_str = None

            for child in txn:
                t = tag(child)
                if t == "transactioncoding":
                    for sub in child:
                        if tag(sub) == "transactioncode" and sub.text:
                            code = sub.text.strip()
                elif t == "transactionamounts":
                    for sub in child:
                        st = tag(sub)
                        if st == "transactionshares":
                            for v in sub:
                                if tag(v) == "value" and v.text:
                                    try:
                                        shares = float(v.text)
                                    except (ValueError, TypeError):
                                        pass
                        elif st == "transactionpricepershare":
                            for v in sub:
                                if tag(v) == "value" and v.text:
                                    try:
                                        price = float(v.text)
                                    except (ValueError, TypeError):
                                        pass
                elif t == "transactiondate":
                    for sub in child:
                        if tag(sub) == "value" and sub.text:
                            date_str = sub.text.strip()

            if code == "P" and shares and shares > 0:
                purchases.append({
                    "name": insider_name or "Unknown",
                    "title": insider_title,
                    "shares": shares,
                    "price": price or 0.0,
                    "value": shares * (price or 0.0),
                    "date": date_str or "",
                })

        return purchases

