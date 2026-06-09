"""13F filing comparison logic for tracking position changes between filings."""

from datetime import datetime, timedelta
from typing import List, Optional

from smart_money_tracker.db.client import db_client
from smart_money_tracker.db.models import FilingComparison, Holding
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class Comparator:
    """Compares 13F filings to detect position changes."""

    def compare(
        self,
        previous: List[Holding],
        current: List[Holding],
        ticker: str
    ) -> FilingComparison:
        """
        Compare holdings between two filings for a specific ticker.

        Args:
            previous: List of holdings from previous filing
            current: List of holdings from current filing
            ticker: Stock ticker symbol to compare

        Returns:
            FilingComparison object with calculated deltas and percentages
        """
        logger.debug(f"Comparing holdings for ticker: {ticker}")

        # Find matching holdings in previous and current lists
        previous_holding = next(
            (h for h in previous if h.ticker == ticker),
            None
        )
        current_holding = next(
            (h for h in current if h.ticker == ticker),
            None
        )

        # Extract share counts (handle None cases)
        previous_shares = previous_holding.shares if previous_holding else None
        current_shares = current_holding.shares if current_holding else 0

        # Determine position type changes
        # Treat 0 shares as no position (same as None) for comparison purposes
        has_previous_position = previous_shares is not None and previous_shares > 0
        has_current_position = current_shares is not None and current_shares > 0

        is_new_position = not has_previous_position and has_current_position
        is_closed_position = has_previous_position and not has_current_position

        # Calculate position change percentages
        position_increase_pct = None
        position_decrease_pct = None

        # Only calculate percentages if position wasn't closed completely
        if previous_shares is not None and previous_shares > 0 and not is_closed_position:
            delta = current_shares - previous_shares

            if delta > 0:
                position_increase_pct = (delta / previous_shares) * 100
                logger.debug(
                    f"Position increase for {ticker}: {position_increase_pct:.2f}%"
                )
            elif delta < 0:
                position_decrease_pct = (abs(delta) / previous_shares) * 100
                logger.debug(
                    f"Position decrease for {ticker}: {position_decrease_pct:.2f}%"
                )

        comparison = FilingComparison(
            ticker=ticker,
            previous_shares=previous_shares,
            current_shares=current_shares,
            is_new_position=is_new_position,
            is_closed_position=is_closed_position,
            position_increase_pct=position_increase_pct,
            position_decrease_pct=position_decrease_pct
        )

        logger.debug(
            f"Comparison result for {ticker}: "
            f"new={is_new_position}, closed={is_closed_position}, "
            f"prev_shares={previous_shares}, curr_shares={current_shares}"
        )

        return comparison

    def get_recent_changes(
        self,
        ticker: str,
        limit_days: int = 90
    ) -> List[FilingComparison]:
        """
        Get all position changes for a ticker within a time window.

        Compares consecutive filings to detect position deltas.

        Args:
            ticker: Stock ticker symbol
            limit_days: Number of days to look back (default 90 days)

        Returns:
            List of FilingComparison objects for consecutive filing pairs with changes
        """
        logger.info(
            f"Getting recent changes for {ticker} within {limit_days} days"
        )

        # Calculate date cutoff
        cutoff_date = datetime.now() - timedelta(days=limit_days)

        # Query all filings within time window, sorted by date
        conn = db_client.get_connection()
        cursor = conn.cursor()

        try:
            # Get all unique filing dates that have holdings for this ticker
            # We query all filings (not just within window) to allow comparisons
            cursor.execute(
                """
                SELECT DISTINCT f.filing_date, f.id
                FROM filings_13f f
                JOIN holdings h ON f.id = h.filing_id
                WHERE h.ticker = ?
                ORDER BY f.filing_date ASC
                """,
                (ticker,)
            )

            all_filing_rows = cursor.fetchall()
            logger.debug(
                f"Found {len(all_filing_rows)} total filings with {ticker} holdings"
            )

            # Filter to only those within the time window
            filing_rows = [
                row for row in all_filing_rows
                if datetime.strptime(row[0], "%Y-%m-%d") >= cutoff_date
            ]

            logger.debug(
                f"Found {len(filing_rows)} filings within {limit_days} day window"
            )

            if len(filing_rows) < 2:
                logger.debug(
                    f"Need at least 2 filings to compare, found {len(filing_rows)}"
                )
                return []

            # Compare consecutive filing pairs
            comparisons = []
            for i in range(len(filing_rows) - 1):
                prev_filing_date = filing_rows[i][0]
                curr_filing_date = filing_rows[i + 1][0]

                # Get holdings for each filing
                previous_holdings = self._get_holdings_at_date(
                    ticker, prev_filing_date, cursor
                )
                current_holdings = self._get_holdings_at_date(
                    ticker, curr_filing_date, cursor
                )

                # Compare filings
                comparison = self.compare(
                    previous_holdings,
                    current_holdings,
                    ticker
                )

                # Only include comparisons with changes
                if (comparison.is_new_position or
                    comparison.is_closed_position or
                    comparison.position_increase_pct is not None or
                    comparison.position_decrease_pct is not None):
                    comparisons.append(comparison)
                    logger.debug(
                        f"Added comparison from {prev_filing_date} to "
                        f"{curr_filing_date}"
                    )

            logger.info(
                f"Found {len(comparisons)} changes for {ticker} "
                f"within {limit_days} days"
            )
            return comparisons

        finally:
            conn.close()

    def _get_holdings_at_date(
        self,
        ticker: str,
        filing_date: str,
        cursor=None
    ) -> List[Holding]:
        """
        Query holdings from database at a specific filing date.

        Private method used internally by get_recent_changes().

        Args:
            ticker: Stock ticker symbol
            filing_date: Filing date to query holdings for
            cursor: Optional cursor to use (if None, creates new connection)

        Returns:
            List of Holding objects for the ticker at the specified date
        """
        logger.debug(f"Getting holdings for {ticker} at date {filing_date}")

        should_close_conn = cursor is None
        if cursor is None:
            conn = db_client.get_connection()
            cursor = conn.cursor()
        else:
            conn = None

        try:
            # Query holdings for the ticker at this filing date
            cursor.execute(
                """
                SELECT ticker, company_name, shares, market_value, portfolio_weight
                FROM holdings
                WHERE ticker = ? AND filing_id IN (
                    SELECT id FROM filings_13f WHERE filing_date = ?
                )
                """,
                (ticker, filing_date)
            )

            rows = cursor.fetchall()
            holdings = [
                Holding(
                    ticker=row[0],
                    company_name=row[1],
                    shares=row[2],
                    market_value=row[3],
                    portfolio_weight=row[4]
                )
                for row in rows
            ]

            logger.debug(
                f"Retrieved {len(holdings)} holdings for {ticker} at {filing_date}"
            )
            return holdings

        finally:
            if should_close_conn and conn is not None:
                conn.close()
