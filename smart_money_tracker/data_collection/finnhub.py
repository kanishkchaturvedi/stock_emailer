"""Fetch insider and company data from Finnhub API."""

import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta

from smart_money_tracker.data_collection.base import BaseFetcher
from smart_money_tracker.config.settings import settings
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class FinnhubFetcher(BaseFetcher):
    """Fetch insider transactions and company data from Finnhub API."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self):
        """Initialize Finnhub fetcher."""
        if not settings.finnhub_api_key:
            logger.warning("Finnhub API key not configured")
        self.api_key = settings.finnhub_api_key

    def _fetch_impl(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch insider transactions for popular stocks."""
        if not self.api_key:
            logger.warning("Finnhub API key not set, skipping insider data")
            return {}

        # Top stocks to track
        symbols = [
            "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL",
            "IBM", "JPM", "V", "JNJ", "KO",
            "META", "AMZN", "PG", "PEP", "MCD"
        ]

        insider_data = {}

        for symbol in symbols:
            try:
                logger.info(f"Fetching insider data for {symbol}")
                insiders = self._get_insider_transactions(symbol)

                if insiders:
                    insider_data[symbol] = insiders
                    logger.info(f"Found {len(insiders)} insider transactions for {symbol}")

            except Exception as e:
                logger.warning(f"Failed to fetch insider data for {symbol}: {e}")
                continue

        return insider_data

    def _get_insider_transactions(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch insider transactions for a symbol."""
        try:
            url = f"{self.BASE_URL}/stock/insider-transactions"
            params = {
                "symbol": symbol,
                "token": self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Filter for recent buys (last 30 days)
            cutoff_date = datetime.now() - timedelta(days=30)

            transactions = []
            if isinstance(data, dict) and "data" in data:
                for txn in data["data"]:
                    # Only include buys and recent transactions
                    if txn.get("share") and txn.get("share") > 0:
                        try:
                            txn_date_str = txn.get("transactionDate", "")
                            txn_date = datetime.strptime(txn_date_str, "%Y-%m-%d") if txn_date_str else datetime.now()
                            if txn_date >= cutoff_date:
                                transactions.append({
                                    "name": txn.get("name", "Unknown"),
                                    "title": txn.get("title", ""),
                                    "shares": txn.get("share", 0),
                                    "price": txn.get("price", 0),
                                    "value": txn.get("share", 0) * txn.get("price", 0),
                                    "date": txn_date.isoformat(),
                                    "change_pct": txn.get("change", 0)
                                })
                        except Exception as e:
                            logger.debug(f"Failed to parse transaction: {e}")
                            continue

            return sorted(transactions, key=lambda x: x["value"], reverse=True)[:5]  # Top 5 by value

        except requests.exceptions.RequestException as e:
            logger.error(f"Finnhub API error for {symbol}: {e}")
            raise

    def get_insider_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Get insider sentiment for a symbol."""
        if not self.api_key:
            return {}

        try:
            url = f"{self.BASE_URL}/stock/insider-sentiment"
            params = {
                "symbol": symbol,
                "token": self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data and len(data.get("data", [])) > 0:
                latest = data["data"][0]
                return {
                    "buy_count": latest.get("buy", 0),
                    "sell_count": latest.get("sell", 0),
                    "net_sentiment": latest.get("buy", 0) - latest.get("sell", 0)
                }

            return {}

        except Exception as e:
            logger.warning(f"Failed to get insider sentiment for {symbol}: {e}")
            return {}
