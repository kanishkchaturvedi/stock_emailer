"""Form 4 SEC filings fetcher for insider stock purchases."""

from datetime import datetime, timedelta
from typing import List
import xml.etree.ElementTree as ET

import requests

from smart_money_tracker.data_collection.base import BaseFetcher
from smart_money_tracker.db.client import db_client
from smart_money_tracker.db.models import InsiderTransaction
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)

# SEC EDGAR API endpoints
SEC_EDGAR_BROWSE = "https://www.sec.gov/cgi-bin/browse-edgar"


class FetcherForm4(BaseFetcher):
    """Fetches Form 4 SEC filings for insider stock purchases."""

    def __init__(self, db_client_instance=None, timeout=10):
        """
        Initialize Form 4 fetcher.

        Args:
            db_client_instance: Database client instance (for testing)
            timeout: Request timeout in seconds
        """
        self.db_client = db_client_instance or db_client
        self.timeout = timeout

    def _fetch_impl(self) -> List[InsiderTransaction]:
        """
        Fetch recent Form 4 filings and extract insider purchase transactions.

        Returns:
            List of InsiderTransaction objects (only purchases)

        Raises:
            Exception: On network errors or parsing failures
        """
        transactions = []

        try:
            logger.info("Fetching recent Form 4 filings")

            # Calculate 7-day window
            days_back = 7
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )

            # Query SEC EDGAR for recent Form 4 filings
            params = {
                "action": "getcompany",
                "type": "4",
                "dateb": "",
                "owner": "exclude",
                "count": 100,
                "search_text": "",
            }

            response = requests.get(
                SEC_EDGAR_BROWSE, params=params, timeout=self.timeout
            )
            response.raise_for_status()

            # Parse the HTML response to extract Form 4 filing URLs
            filing_urls = self._extract_form4_urls(response.text, cutoff_date)

            logger.info(f"Found {len(filing_urls)} Form 4 filings from past 7 days")

            # For each filing, fetch and parse the XML document
            for filing_url in filing_urls:
                try:
                    filing_transactions = self._parse_form4_xml(filing_url)
                    # Filter to only include purchase transactions
                    purchase_transactions = [
                        t
                        for t in filing_transactions
                        if t.transaction_type == "purchase"
                    ]
                    transactions.extend(purchase_transactions)
                    logger.info(
                        f"Extracted {len(purchase_transactions)} purchase "
                        f"transactions from {filing_url}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to parse Form 4 filing {filing_url}: "
                        f"{type(e).__name__}: {str(e)}"
                    )
                    # Continue to next filing instead of failing entirely
                    continue

            logger.info(f"Fetched {len(transactions)} total insider purchases")
            self._store_transactions(transactions)
            return transactions

        except Exception as e:
            logger.error(
                f"Error fetching Form 4 filings: {type(e).__name__}: {str(e)}"
            )
            raise

    def _extract_form4_urls(self, html_content: str, cutoff_date: str) -> List[str]:
        """
        Extract Form 4 filing URLs from SEC EDGAR HTML response.

        Args:
            html_content: HTML response from SEC EDGAR
            cutoff_date: Date cutoff in YYYY-MM-DD format

        Returns:
            List of filing URLs

        Raises:
            Exception: On parsing failures
        """
        urls = []
        try:
            # Parse the HTML to find Form 4 filings
            # Look for lines containing 4 and filing dates within 7 days
            lines = html_content.split("\n")
            for i, line in enumerate(lines):
                # Look for links that contain "4" filing type
                if '">4<' in line or 'type=4' in line or "/Archives/" in line:
                    # Try to extract the URL from this line or nearby lines
                    if href_url := self._extract_url_from_line(line):
                        urls.append(href_url)

            return urls
        except Exception as e:
            logger.error(f"Failed to extract Form 4 URLs: {e}")
            raise

    def _extract_url_from_line(self, line: str) -> str | None:
        """
        Extract URL from an HTML line.

        Args:
            line: HTML line to parse

        Returns:
            URL string or None if not found
        """
        try:
            # Look for href="..." pattern
            import re

            match = re.search(r'href="([^"]*)"', line)
            if match:
                url = match.group(1)
                # Convert relative URLs to absolute
                if url.startswith("/"):
                    url = "https://www.sec.gov" + url
                if url.startswith("http") and "Archives" in url:
                    return url
        except Exception:
            pass

        return None

    def _parse_form4_xml(self, filing_url: str) -> List[InsiderTransaction]:
        """
        Parse Form 4 XML document to extract insider transactions.

        Args:
            filing_url: URL to the Form 4 filing (HTML page)

        Returns:
            List of InsiderTransaction objects (all transaction types)

        Raises:
            Exception: On network or XML parsing errors
        """
        # Convert HTML URL to XML URL
        xml_url = filing_url.replace(".htm", ".xml")
        if not xml_url.endswith(".xml"):
            # Try to construct XML URL
            parts = filing_url.rsplit("/", 1)
            if len(parts) == 2:
                base_path = parts[0]
                filename = parts[1].replace(".htm", "")
                xml_url = f"{base_path}/{filename}.xml"

        logger.debug(f"Fetching Form 4 XML from {xml_url}")

        response = requests.get(xml_url, timeout=self.timeout)
        response.raise_for_status()

        transactions = []
        try:
            root = ET.fromstring(response.content)

            # Find all transaction entries
            # Form 4 XML structure has transactionTable with transactions
            for transaction_elem in root.iter():
                if transaction_elem.tag.endswith("transaction"):
                    transaction = self._parse_transaction(transaction_elem, root)
                    if transaction:
                        transactions.append(transaction)

        except ET.ParseError as e:
            logger.error(f"Failed to parse Form 4 XML: {e}")
            raise

        return transactions

    def _parse_transaction(
        self, transaction_elem, root
    ) -> InsiderTransaction | None:
        """
        Parse a single transaction from Form 4 XML element.

        Args:
            transaction_elem: XML element representing a transaction
            root: Root XML element (to access reporting owner info)

        Returns:
            InsiderTransaction object or None if parsing fails

        Raises:
            Exception: On parsing errors
        """
        try:
            # Extract transaction details
            transaction_code = None
            shares = None
            value = None
            transaction_date = None

            # Parse transaction code and details
            for child in transaction_elem:
                tag_lower = child.tag.lower()

                if "transactioncode" in tag_lower:
                    transaction_code = child.text
                elif "transactiondate" in tag_lower or "transactiondt" in tag_lower:
                    transaction_date = child.text
                elif (
                    "shares" in tag_lower
                    or "sharesorprnamt" in tag_lower
                    or "transactionshares" in tag_lower
                ):
                    # Try to get shares value
                    try:
                        shares = int(float(child.text or 0))
                    except (ValueError, TypeError):
                        # May have nested structure
                        for nested in child:
                            if "value" in nested.tag.lower():
                                try:
                                    shares = int(float(nested.text or 0))
                                    break
                                except (ValueError, TypeError):
                                    pass
                elif (
                    "pricepershare" in tag_lower
                    or "transactionprice" in tag_lower
                    or "value" in tag_lower
                ):
                    try:
                        price_per_share = float(child.text or 0)
                        if shares and shares > 0:
                            value = price_per_share * shares
                    except (ValueError, TypeError):
                        pass

            # Filter to only include purchase transactions (code 'P')
            if transaction_code != "P":
                return None

            # Extract insider info
            insider_name = self._extract_insider_name(root)
            role = self._extract_insider_role(root)
            ticker = self._extract_ticker(root)

            if not all([insider_name, ticker, shares is not None, transaction_date]):
                logger.debug(
                    f"Missing required fields: "
                    f"name={insider_name}, ticker={ticker}, "
                    f"shares={shares}, date={transaction_date}"
                )
                return None

            # Parse transaction date
            transaction_date_obj = datetime.strptime(
                transaction_date.strip(), "%Y-%m-%d"
            )

            return InsiderTransaction(
                ticker=ticker,
                insider_name=insider_name,
                role=role or "Unknown",
                transaction_type="purchase",
                shares_bought=int(shares),
                value_bought=value or 0.0,
                transaction_date=transaction_date_obj,
            )

        except (AttributeError, ValueError, KeyError) as e:
            logger.debug(f"Failed to parse transaction: {e}")
            return None

    def _extract_insider_name(self, root) -> str | None:
        """
        Extract insider name from Form 4 XML root element.

        Args:
            root: Root XML element

        Returns:
            Insider name or None if not found
        """
        try:
            for elem in root.iter():
                tag_lower = elem.tag.lower()
                if "reportingowner" in tag_lower or "ownername" in tag_lower:
                    for child in elem:
                        if "name" in child.tag.lower():
                            return child.text
                elif tag_lower.endswith("name") and elem.text:
                    # Try to find reporting owner name
                    parent = elem
                    parent_tag = parent.tag.lower()
                    if any(
                        x in parent_tag
                        for x in [
                            "reportingowner",
                            "owner",
                            "insider",
                            "principal",
                        ]
                    ):
                        return elem.text
        except Exception as e:
            logger.debug(f"Failed to extract insider name: {e}")

        return None

    def _extract_insider_role(self, root) -> str | None:
        """
        Extract insider role/title from Form 4 XML root element.

        Args:
            root: Root XML element

        Returns:
            Insider role or None if not found
        """
        try:
            for elem in root.iter():
                tag_lower = elem.tag.lower()
                if (
                    "reportingowner" in tag_lower
                    or "relationshiptoissuers" in tag_lower
                ):
                    for child in elem:
                        tag_lower_child = child.tag.lower()
                        if (
                            "officer" in tag_lower_child
                            or "director" in tag_lower_child
                            or "title" in tag_lower_child
                        ):
                            return child.text
        except Exception as e:
            logger.debug(f"Failed to extract insider role: {e}")

        return None

    def _extract_ticker(self, root) -> str | None:
        """
        Extract ticker symbol from Form 4 XML root element.

        Args:
            root: Root XML element

        Returns:
            Ticker symbol or None if not found
        """
        try:
            for elem in root.iter():
                tag_lower = elem.tag.lower()
                if (
                    "ticker" in tag_lower
                    or "symbol" in tag_lower
                    or "cusip" in tag_lower
                ):
                    if elem.text:
                        return elem.text.upper()
        except Exception as e:
            logger.debug(f"Failed to extract ticker: {e}")

        return None

    def _store_transactions(self, transactions: List[InsiderTransaction]) -> None:
        """
        Store insider transactions in the database.

        Args:
            transactions: List of InsiderTransaction objects to store

        Raises:
            Exception: On database errors
        """
        if not transactions:
            logger.info("No transactions to store")
            return

        try:
            conn = self.db_client.get_connection()
            cursor = conn.cursor()

            for transaction in transactions:
                try:
                    fetched_at = datetime.now().isoformat()
                    transaction_date = transaction.transaction_date.isoformat()

                    cursor.execute(
                        """
                        INSERT INTO insider_transactions
                        (ticker, insider_name, role, transaction_type, shares_bought, value_bought, transaction_date, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            transaction.ticker,
                            transaction.insider_name,
                            transaction.role,
                            transaction.transaction_type,
                            transaction.shares_bought,
                            transaction.value_bought,
                            transaction_date,
                            fetched_at,
                        ),
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to store transaction for {transaction.ticker}: {e}"
                    )
                    conn.rollback()
                    raise

            conn.commit()
            logger.info(f"Successfully stored {len(transactions)} insider transactions")

        except Exception as e:
            logger.error(f"Database error while storing transactions: {e}")
            raise
        finally:
            conn.close()

    def store(self, data: List[InsiderTransaction]) -> None:
        """
        Store fetched insider transactions in the database.

        Args:
            data: List of InsiderTransaction objects to store
        """
        self._store_transactions(data)
