"""Congressional trades fetcher from Senate Stock Watcher API."""

from datetime import datetime, timedelta
from typing import List
import json

import requests

from smart_money_tracker.data_collection.base import BaseFetcher
from smart_money_tracker.db.client import db_client
from smart_money_tracker.db.models import CongressionalTrade
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)

# API endpoints for congressional trades
SENATE_STOCK_WATCHER_API = "https://senatestockwatcher.com/api/trades"
HOUSE_STOCK_WATCHER_API = "https://housestockwatcher.com/api/trades"


class FetcherCongress(BaseFetcher):
    """Fetches recent congressional stock trades from public APIs."""

    def __init__(self, db_client_instance=None, timeout=10):
        """
        Initialize congressional trades fetcher.

        Args:
            db_client_instance: Database client instance (for testing)
            timeout: Request timeout in seconds
        """
        self.db_client = db_client_instance or db_client
        self.timeout = timeout

    def _fetch_impl(self) -> List[CongressionalTrade]:
        """
        Fetch recent congressional trades from Senate Stock Watcher API.

        Returns:
            List of CongressionalTrade objects

        Raises:
            Exception: On network errors or parsing failures
        """
        trades = []

        try:
            logger.info("Fetching congressional trades from Senate Stock Watcher API")

            # Try Senate API first
            trades = self._fetch_from_senate_api()

            # If Senate API returns no results, try House API as fallback
            if not trades:
                logger.info("No trades from Senate API, trying House Stock Watcher API")
                trades = self._fetch_from_house_api()

            logger.info(f"Fetched {len(trades)} total congressional trades")
            self._store_trades(trades)
            return trades

        except Exception as e:
            logger.error(
                f"Error fetching congressional trades: {type(e).__name__}: {str(e)}"
            )
            raise

    def _fetch_from_senate_api(self) -> List[CongressionalTrade]:
        """
        Fetch trades from Senate Stock Watcher API.

        Returns:
            List of CongressionalTrade objects

        Raises:
            Exception: On network errors or parsing failures
        """
        trades = []

        try:
            logger.debug(f"Fetching from Senate API: {SENATE_STOCK_WATCHER_API}")
            response = requests.get(
                SENATE_STOCK_WATCHER_API, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            # Handle both list and dict responses
            if isinstance(data, dict):
                # If response is a dict, look for 'trades', 'results', or 'data' key
                trades_data = data.get('trades') or data.get('results') or data.get('data') or []
                if isinstance(trades_data, list):
                    data = trades_data
                else:
                    data = [data]
            elif not isinstance(data, list):
                data = [data]

            logger.info(f"Senate API returned {len(data)} trade records")

            for trade_data in data:
                try:
                    trade = self._parse_trade(trade_data)
                    if trade:
                        trades.append(trade)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse trade record: {type(e).__name__}: {str(e)}"
                    )
                    continue

            logger.info(f"Parsed {len(trades)} trades from Senate API")
            return trades

        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Senate API request failed: {type(e).__name__}: {str(e)}"
            )
            raise

    def _fetch_from_house_api(self) -> List[CongressionalTrade]:
        """
        Fetch trades from House Stock Watcher API as fallback.

        Returns:
            List of CongressionalTrade objects

        Raises:
            Exception: On network errors or parsing failures
        """
        trades = []

        try:
            logger.debug(f"Fetching from House API: {HOUSE_STOCK_WATCHER_API}")
            response = requests.get(
                HOUSE_STOCK_WATCHER_API, timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            # Handle both list and dict responses
            if isinstance(data, dict):
                trades_data = data.get('trades') or data.get('results') or data.get('data') or []
                if isinstance(trades_data, list):
                    data = trades_data
                else:
                    data = [data]
            elif not isinstance(data, list):
                data = [data]

            logger.info(f"House API returned {len(data)} trade records")

            for trade_data in data:
                try:
                    trade = self._parse_trade(trade_data)
                    if trade:
                        trades.append(trade)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse trade record: {type(e).__name__}: {str(e)}"
                    )
                    continue

            logger.info(f"Parsed {len(trades)} trades from House API")
            return trades

        except requests.exceptions.RequestException as e:
            logger.warning(
                f"House API request failed: {type(e).__name__}: {str(e)}"
            )
            raise

    def _parse_trade(self, trade_data: dict) -> CongressionalTrade | None:
        """
        Parse a single trade record from API response.

        Handles various field name variations from different API sources.

        Args:
            trade_data: Raw trade data dictionary

        Returns:
            CongressionalTrade object or None if parsing fails

        Raises:
            Exception: On parsing errors
        """
        try:
            # Extract politician name (handle variations)
            politician = (
                trade_data.get('politician_name') or
                trade_data.get('politician') or
                trade_data.get('name') or
                trade_data.get('representative') or
                trade_data.get('senator') or
                ''
            )
            politician = politician.strip() if politician else None

            # Extract ticker (handle variations)
            ticker = (
                trade_data.get('ticker') or
                trade_data.get('symbol') or
                ''
            )
            ticker = ticker.upper().strip() if ticker else None

            # Extract transaction type (buy/sell)
            transaction_type = (
                trade_data.get('transaction_type') or
                trade_data.get('buy_or_sell') or
                trade_data.get('type') or
                trade_data.get('action') or
                ''
            )
            transaction_type = transaction_type.lower().strip() if transaction_type else None

            # Normalize transaction type
            if transaction_type:
                if 'buy' in transaction_type.lower():
                    buy_or_sell = 'buy'
                elif 'sell' in transaction_type.lower():
                    buy_or_sell = 'sell'
                else:
                    logger.debug(f"Unknown transaction type: {transaction_type}")
                    return None
            else:
                logger.debug("Missing transaction type")
                return None

            # Extract disclosure date (handle variations)
            disclosure_date_str = (
                trade_data.get('disclosure_date') or
                trade_data.get('date') or
                trade_data.get('transaction_date') or
                trade_data.get('filing_date') or
                ''
            )

            if not disclosure_date_str:
                logger.debug("Missing disclosure date")
                return None

            # Parse date (handle common formats)
            disclosure_date = self._parse_date(disclosure_date_str)
            if not disclosure_date:
                logger.debug(f"Failed to parse date: {disclosure_date_str}")
                return None

            # Extract estimated amount (handle variations)
            estimated_amount_str = (
                trade_data.get('estimated_amount') or
                trade_data.get('amount') or
                trade_data.get('value') or
                trade_data.get('transaction_amount') or
                '0'
            )

            # Parse amount (remove common currency symbols and convert to float)
            estimated_amount = self._parse_amount(estimated_amount_str)

            # Validate required fields
            if not all([politician, ticker, buy_or_sell, disclosure_date]):
                logger.debug(
                    f"Missing required fields: "
                    f"politician={politician}, ticker={ticker}, "
                    f"buy_or_sell={buy_or_sell}, date={disclosure_date}"
                )
                return None

            return CongressionalTrade(
                politician=politician,
                ticker=ticker,
                buy_or_sell=buy_or_sell,
                disclosure_date=disclosure_date,
                estimated_amount=estimated_amount,
            )

        except (AttributeError, ValueError, KeyError, TypeError) as e:
            logger.debug(f"Failed to parse trade: {type(e).__name__}: {str(e)}")
            return None

    def _parse_date(self, date_str: str) -> datetime | None:
        """
        Parse date string in various formats.

        Args:
            date_str: Date string to parse

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str:
            return None

        date_str = str(date_str).strip()

        # Common date formats to try
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%m-%d-%Y",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.debug(f"Could not parse date with any format: {date_str}")
        return None

    def _parse_amount(self, amount_str: str | float | int) -> float:
        """
        Parse amount from various formats.

        Removes common currency symbols and converts to float.

        Args:
            amount_str: Amount string, float, or int

        Returns:
            Float value of amount
        """
        if isinstance(amount_str, (int, float)):
            return float(amount_str)

        if not amount_str:
            return 0.0

        amount_str = str(amount_str).strip()

        # Handle range formats like "1,000,000 - 5,000,000" before removing commas
        if ' - ' in amount_str or ' to ' in amount_str:
            try:
                # Split on the separator
                if ' - ' in amount_str:
                    parts = amount_str.split(' - ')
                else:
                    parts = amount_str.split(' to ')

                if len(parts) == 2:
                    # Remove currency symbols and commas from each part
                    lower_str = parts[0].strip()
                    upper_str = parts[1].strip()

                    for char in ['$', '€', '£', '¥', ',', ' ']:
                        lower_str = lower_str.replace(char, '')
                        upper_str = upper_str.replace(char, '')

                    lower = float(lower_str)
                    upper = float(upper_str)
                    return (lower + upper) / 2.0
            except (ValueError, IndexError):
                pass

        # Remove common currency symbols and formatting
        for char in ['$', '€', '£', '¥', ',', ' ']:
            amount_str = amount_str.replace(char, '')

        # Try to parse as float
        try:
            return float(amount_str)
        except ValueError:
            logger.debug(f"Failed to parse amount: {amount_str}")
            return 0.0

    def _store_trades(self, trades: List[CongressionalTrade]) -> None:
        """
        Store congressional trades in the database.

        Args:
            trades: List of CongressionalTrade objects to store

        Raises:
            Exception: On database errors
        """
        if not trades:
            logger.info("No trades to store")
            return

        try:
            conn = self.db_client.get_connection()
            cursor = conn.cursor()

            for trade in trades:
                try:
                    fetched_at = datetime.now().isoformat()
                    disclosure_date = trade.disclosure_date.isoformat()

                    cursor.execute(
                        """
                        INSERT INTO congressional_trades
                        (politician, ticker, buy_or_sell, disclosure_date, estimated_amount, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            trade.politician,
                            trade.ticker,
                            trade.buy_or_sell,
                            disclosure_date,
                            trade.estimated_amount,
                            fetched_at,
                        ),
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to store trade for {trade.ticker}: {e}"
                    )
                    conn.rollback()
                    raise

            conn.commit()
            logger.info(f"Successfully stored {len(trades)} congressional trades")

        except Exception as e:
            logger.error(f"Database error while storing trades: {e}")
            raise
        finally:
            conn.close()

    def store(self, data: List[CongressionalTrade]) -> None:
        """
        Store fetched congressional trades in the database.

        Args:
            data: List of CongressionalTrade objects to store
        """
        self._store_trades(data)
