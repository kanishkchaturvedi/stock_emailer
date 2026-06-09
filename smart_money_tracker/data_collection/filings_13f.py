"""13F SEC filings fetcher using SEC EDGAR API."""

from datetime import datetime
from typing import List
import xml.etree.ElementTree as ET

import requests

from smart_money_tracker.config.investors import TRACKED_INVESTORS
from smart_money_tracker.data_collection.base import BaseFetcher
from smart_money_tracker.db.client import db_client
from smart_money_tracker.db.models import Filing13F, Holding
from smart_money_tracker.utils.logger import get_logger
from smart_money_tracker.utils.retries import retry

logger = get_logger(__name__)

# SEC EDGAR API endpoints
SEC_EDGAR_API = "https://www.sec.gov/cgi-bin/browse-edgar"
SEC_FILINGS_URL = "https://www.sec.gov/cgi-bin/viewer"


class Fetcher13F(BaseFetcher):
    """Fetches 13F SEC filings for tracked investors."""

    def __init__(self, db_client_instance=None, timeout=10):
        """
        Initialize 13F fetcher.

        Args:
            db_client_instance: Database client instance (for testing)
            timeout: Request timeout in seconds
        """
        self.db_client = db_client_instance or db_client
        self.timeout = timeout

    @retry(max_attempts=3, base_delay=1.0, backoff=2.0)
    def _fetch_impl(self) -> List[Filing13F]:
        """
        Fetch latest 13F filings for all tracked investors.

        Returns:
            List of Filing13F objects with holdings

        Raises:
            Exception: On network errors or parsing failures
        """
        filings = []

        for investor_name, cik in TRACKED_INVESTORS.items():
            try:
                logger.info(f"Fetching 13F filing for {investor_name} (CIK: {cik})")
                filing = self._fetch_investor_filing(investor_name, cik)
                if filing:
                    filings.append(filing)
                    logger.info(
                        f"Successfully fetched 13F for {investor_name} "
                        f"with {len(filing.holdings)} holdings"
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to fetch 13F for {investor_name}: "
                    f"{type(e).__name__}: {str(e)}"
                )
                # Continue to next investor instead of failing entirely
                continue

        self._store_filings(filings)
        return filings

    def _fetch_investor_filing(self, investor_name: str, cik: str) -> Filing13F | None:
        """
        Fetch the latest 13F filing for a single investor.

        Args:
            investor_name: Name of the investor
            cik: CIK code of the investor

        Returns:
            Filing13F object or None if fetch fails

        Raises:
            Exception: On network or parsing errors
        """
        # Query SEC EDGAR for latest 13F filing
        params = {
            "action": "getcompany",
            "CIK": cik,
            "type": "13F-HR",
            "dateb": "",
            "owner": "exclude",
            "count": 1,
            "output": "json",
        }

        response = requests.get(
            SEC_EDGAR_API, params=params, timeout=self.timeout
        )
        response.raise_for_status()

        data = response.json()

        # Extract filing URL from response
        if "filings" not in data or not data["filings"].get("filing"):
            logger.warning(f"No 13F filings found for {investor_name}")
            return None

        filing_entry = data["filings"]["filing"][0]
        filing_url = filing_entry.get("filing_href")

        if not filing_url:
            logger.warning(f"No filing URL found for {investor_name}")
            return None

        # Fetch the actual 13F XML document
        filing_date_str = filing_entry.get("filing_date", "")
        filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")

        holdings = self._parse_13f_xml(filing_url)

        return Filing13F(
            investor_name=investor_name,
            cik=cik,
            filing_date=filing_date,
            holdings=holdings,
        )

    def _parse_13f_xml(self, filing_url: str) -> List[Holding]:
        """
        Parse 13F XML document to extract holdings.

        Args:
            filing_url: URL to the 13F XML document

        Returns:
            List of Holding objects

        Raises:
            Exception: On network or XML parsing errors
        """
        # Construct the correct URL for the XML document
        # SEC filing URLs often point to the HTML version, need to get XML
        xml_url = filing_url.replace(".htm", ".xml")
        if not xml_url.endswith(".xml"):
            xml_url = filing_url.rsplit("/", 1)[0] + "/0001193125-" + filing_url.split(
                "0001193125-"
            )[1].split(".")[0] + ".xml"

        response = requests.get(xml_url, timeout=self.timeout)
        response.raise_for_status()

        # Parse XML to extract holdings
        holdings = []
        try:
            root = ET.fromstring(response.content)

            # Define namespace for 13F XML
            namespaces = {
                "": "http://www.sec.gov/cgi-bin/viewer",
            }

            # Find all InfoTable entries (each represents a holding)
            # The structure varies, so we try multiple approaches
            for info_table in root.iter():
                if info_table.tag.endswith("infoTable"):
                    holding = self._parse_holding(info_table)
                    if holding:
                        holdings.append(holding)

        except ET.ParseError as e:
            logger.error(f"Failed to parse 13F XML: {e}")
            raise

        return holdings

    def _parse_holding(self, info_table_elem) -> Holding | None:
        """
        Parse a single holding from an infoTable XML element.

        Args:
            info_table_elem: XML element representing a holding

        Returns:
            Holding object or None if parsing fails

        Raises:
            KeyError: If required fields are missing
        """
        try:
            # Extract fields from the XML element
            # Field names may vary (with or without namespaces)
            ticker = None
            company_name = None
            shares = None
            market_value = None
            portfolio_weight = None

            for child in info_table_elem:
                tag = child.tag
                if tag.endswith("nameOfIssuer"):
                    company_name = child.text
                elif tag.endswith("cusip"):
                    # Could extract ticker from CUSIP if needed
                    pass
                elif tag.endswith("shrsOrPrnAmt"):
                    # Get share amount
                    shares_elem = child.find(".//*")
                    if shares_elem is not None:
                        shares = int(shares_elem.text or 0)
                elif tag.endswith("value"):
                    market_value = float(child.text or 0)
                elif tag.endswith("percentOfClass"):
                    portfolio_weight = float(child.text or 0)

            # Try to extract from alternative tag structures
            for child in info_table_elem:
                tag_lower = child.tag.lower()
                if "ticker" in tag_lower or "symbol" in tag_lower:
                    ticker = child.text
                elif "sharesorprnamt" in tag_lower and shares is None:
                    for sub_child in child:
                        if "value" in sub_child.tag.lower() or sub_child.text:
                            try:
                                shares = int(sub_child.text)
                                break
                            except (ValueError, TypeError):
                                pass

            # If ticker not found, try to extract from company name or skip
            if not ticker:
                # Use first few letters of company name as placeholder
                if company_name:
                    ticker = company_name.split()[0][:4].upper()
                else:
                    logger.warning("Could not extract ticker from holding")
                    return None

            if not company_name or shares is None or market_value is None:
                logger.warning(
                    f"Missing required fields for holding: "
                    f"company_name={company_name}, shares={shares}, "
                    f"market_value={market_value}"
                )
                return None

            return Holding(
                ticker=ticker,
                company_name=company_name,
                shares=shares,
                market_value=market_value,
                portfolio_weight=portfolio_weight or 0.0,
            )

        except (AttributeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse holding: {e}")
            return None

    def _store_filings(self, filings: List[Filing13F]) -> None:
        """
        Store fetched filings and holdings in the database.

        Args:
            filings: List of Filing13F objects to store

        Raises:
            Exception: On database errors
        """
        if not filings:
            logger.info("No filings to store")
            return

        try:
            conn = self.db_client.get_connection()
            cursor = conn.cursor()

            for filing in filings:
                try:
                    # Insert investor record (or ignore if exists)
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO investors (name, cik)
                        VALUES (?, ?)
                        """,
                        (filing.investor_name, filing.cik),
                    )

                    # Get investor_id
                    cursor.execute(
                        "SELECT id FROM investors WHERE cik = ?",
                        (filing.cik,),
                    )
                    investor_id = cursor.fetchone()[0]

                    # Insert filing record
                    fetched_at = datetime.now().isoformat()
                    filing_date = filing.filing_date.isoformat()

                    cursor.execute(
                        """
                        INSERT INTO filings_13f (investor_id, filing_date, fetched_at)
                        VALUES (?, ?, ?)
                        """,
                        (investor_id, filing_date, fetched_at),
                    )
                    filing_id = cursor.lastrowid

                    # Insert holdings
                    for holding in filing.holdings:
                        cursor.execute(
                            """
                            INSERT INTO holdings
                            (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                filing_id,
                                holding.ticker,
                                holding.company_name,
                                holding.shares,
                                holding.market_value,
                                holding.portfolio_weight,
                            ),
                        )

                    logger.info(
                        f"Stored filing for {filing.investor_name} with "
                        f"{len(filing.holdings)} holdings"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to store filing for {filing.investor_name}: {e}"
                    )
                    conn.rollback()
                    raise

            conn.commit()
            logger.info(f"Successfully stored {len(filings)} filings")

        except Exception as e:
            logger.error(f"Database error while storing filings: {e}")
            raise
        finally:
            conn.close()

    def store(self, data: List[Filing13F]) -> None:
        """
        Store fetched 13F filings in the database.

        Args:
            data: List of Filing13F objects to store
        """
        self._store_filings(data)
