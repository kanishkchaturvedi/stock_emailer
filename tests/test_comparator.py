"""Tests for 13F filing comparator."""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smart_money_tracker.db.client import DatabaseClient
from smart_money_tracker.db.models import FilingComparison, Holding
from smart_money_tracker.signals.comparator import Comparator


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup - try multiple times to handle Windows file locking
    path = Path(db_path)
    if path.exists():
        try:
            path.unlink()
        except PermissionError:
            import time
            time.sleep(0.1)
            try:
                path.unlink()
            except PermissionError:
                # Ignore cleanup errors
                pass


@pytest.fixture
def comparator():
    """Create a Comparator instance for testing."""
    return Comparator()


@pytest.fixture
def sample_holding():
    """Create a sample holding."""
    return Holding(
        ticker="AAPL",
        company_name="Apple Inc",
        shares=100000,
        market_value=15000000.0,
        portfolio_weight=5.5
    )


@pytest.fixture
def sample_holding_msft():
    """Create a sample MSFT holding."""
    return Holding(
        ticker="MSFT",
        company_name="Microsoft Corp",
        shares=50000,
        market_value=20000000.0,
        portfolio_weight=8.0
    )


class TestComparatorCompare:
    """Tests for Comparator.compare() method."""

    def test_new_position_detection(self, comparator, sample_holding):
        """Test detection of new positions."""
        previous = []
        current = [sample_holding]

        result = comparator.compare(previous, current, "AAPL")

        assert result.ticker == "AAPL"
        assert result.previous_shares is None
        assert result.current_shares == 100000
        assert result.is_new_position is True
        assert result.is_closed_position is False
        assert result.position_increase_pct is None
        assert result.position_decrease_pct is None

    def test_closed_position_detection(self, comparator, sample_holding):
        """Test detection of closed positions."""
        previous = [sample_holding]
        current = []

        result = comparator.compare(previous, current, "AAPL")

        assert result.ticker == "AAPL"
        assert result.previous_shares == 100000
        assert result.current_shares == 0
        assert result.is_new_position is False
        assert result.is_closed_position is True
        assert result.position_increase_pct is None
        assert result.position_decrease_pct is None

    def test_closed_position_with_zero_shares(self, comparator):
        """Test closed position when current shares are explicitly 0."""
        previous = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=100000,
                market_value=15000000.0,
                portfolio_weight=5.5
            )
        ]
        current = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=0,
                market_value=0.0,
                portfolio_weight=0.0
            )
        ]

        result = comparator.compare(previous, current, "AAPL")

        assert result.is_closed_position is True

    def test_position_increase_percentage(self, comparator):
        """Test calculation of position increase percentage."""
        previous = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=100000,
                market_value=15000000.0,
                portfolio_weight=5.5
            )
        ]
        current = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=150000,  # 50% increase
                market_value=22500000.0,
                portfolio_weight=8.25
            )
        ]

        result = comparator.compare(previous, current, "AAPL")

        assert result.is_new_position is False
        assert result.is_closed_position is False
        assert result.position_increase_pct == 50.0
        assert result.position_decrease_pct is None

    def test_position_decrease_percentage(self, comparator):
        """Test calculation of position decrease percentage."""
        previous = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=100000,
                market_value=15000000.0,
                portfolio_weight=5.5
            )
        ]
        current = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=60000,  # 40% decrease
                market_value=9000000.0,
                portfolio_weight=3.3
            )
        ]

        result = comparator.compare(previous, current, "AAPL")

        assert result.is_new_position is False
        assert result.is_closed_position is False
        assert result.position_increase_pct is None
        assert result.position_decrease_pct == 40.0

    def test_no_change_same_shares(self, comparator):
        """Test when holdings have no change."""
        previous = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=100000,
                market_value=15000000.0,
                portfolio_weight=5.5
            )
        ]
        current = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=100000,
                market_value=15000000.0,
                portfolio_weight=5.5
            )
        ]

        result = comparator.compare(previous, current, "AAPL")

        assert result.is_new_position is False
        assert result.is_closed_position is False
        assert result.position_increase_pct is None
        assert result.position_decrease_pct is None

    def test_position_not_found_in_previous_or_current(self, comparator):
        """Test when ticker not found in either previous or current."""
        previous = []
        current = []

        result = comparator.compare(previous, current, "AAPL")

        assert result.ticker == "AAPL"
        assert result.previous_shares is None
        assert result.current_shares == 0
        assert result.is_new_position is False
        assert result.is_closed_position is False

    def test_multiple_holdings_finds_correct_ticker(self, comparator):
        """Test that correct holding is found among multiple holdings."""
        previous = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=100000,
                market_value=15000000.0,
                portfolio_weight=5.5
            ),
            Holding(
                ticker="MSFT",
                company_name="Microsoft Corp",
                shares=50000,
                market_value=20000000.0,
                portfolio_weight=8.0
            )
        ]
        current = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=120000,
                market_value=18000000.0,
                portfolio_weight=6.6
            ),
            Holding(
                ticker="MSFT",
                company_name="Microsoft Corp",
                shares=40000,
                market_value=16000000.0,
                portfolio_weight=6.4
            )
        ]

        result = comparator.compare(previous, current, "AAPL")

        # Should only compare AAPL, not MSFT
        assert result.ticker == "AAPL"
        assert result.previous_shares == 100000
        assert result.current_shares == 120000
        assert result.position_increase_pct == 20.0

    def test_small_percentage_increase(self, comparator):
        """Test calculation with small percentage increase."""
        previous = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=1000000,
                market_value=150000000.0,
                portfolio_weight=50.0
            )
        ]
        current = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=1001000,  # 0.1% increase
                market_value=150150000.0,
                portfolio_weight=50.05
            )
        ]

        result = comparator.compare(previous, current, "AAPL")

        assert abs(result.position_increase_pct - 0.1) < 0.001

    def test_large_percentage_decrease(self, comparator):
        """Test calculation with large percentage decrease."""
        previous = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=100000,
                market_value=15000000.0,
                portfolio_weight=5.5
            )
        ]
        current = [
            Holding(
                ticker="AAPL",
                company_name="Apple Inc",
                shares=10000,  # 90% decrease
                market_value=1500000.0,
                portfolio_weight=0.55
            )
        ]

        result = comparator.compare(previous, current, "AAPL")

        assert result.position_decrease_pct == 90.0


class TestComparatorGetRecentChanges:
    """Tests for Comparator.get_recent_changes() method."""

    def test_get_recent_changes_with_no_filings(self, temp_db):
        """Test get_recent_changes with empty database."""
        client = DatabaseClient(db_path=temp_db)
        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            changes = comparator.get_recent_changes("AAPL", limit_days=90)

            assert changes == []

    def test_get_recent_changes_with_single_filing(self, temp_db):
        """Test get_recent_changes with only one filing (no pairs to compare)."""
        client = DatabaseClient(db_path=temp_db)

        # Insert test data
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        cursor.execute("SELECT id FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        investor_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, "2024-06-01", "2024-06-01T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE investor_id = ?", (investor_id,))
        filing_id = cursor.fetchone()[0]

        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing_id, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
        )
        conn.commit()
        conn.close()

        # Test get_recent_changes
        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            changes = comparator.get_recent_changes("AAPL", limit_days=90)

            assert changes == []

    def test_get_recent_changes_with_two_filings_no_change(self, temp_db):
        """Test get_recent_changes with two filings showing no change."""
        client = DatabaseClient(db_path=temp_db)

        # Insert test data
        conn = client.get_connection()
        cursor = conn.cursor()

        # Insert investor
        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        cursor.execute("SELECT id FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        investor_id = cursor.fetchone()[0]

        # Insert two filings
        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, "2024-06-01", "2024-06-01T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", ("2024-06-01",))
        filing1_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, "2024-09-01", "2024-09-01T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", ("2024-09-01",))
        filing2_id = cursor.fetchone()[0]

        # Insert holdings (same amount in both filings)
        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing1_id, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
        )
        conn.commit()

        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing2_id, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
        )
        conn.commit()
        conn.close()

        # Test get_recent_changes - should return empty list (no change)
        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            changes = comparator.get_recent_changes("AAPL", limit_days=90)

            # No changes should be included
            assert changes == []

    def test_get_recent_changes_with_position_increase(self, temp_db):
        """Test get_recent_changes detecting a position increase."""
        from datetime import datetime, timedelta

        client = DatabaseClient(db_path=temp_db)

        # Insert test data
        conn = client.get_connection()
        cursor = conn.cursor()

        # Insert investor
        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        cursor.execute("SELECT id FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        investor_id = cursor.fetchone()[0]

        # Use recent dates
        date1 = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        date2 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # Insert two filings
        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, date1, f"{date1}T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", (date1,))
        filing1_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, date2, f"{date2}T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", (date2,))
        filing2_id = cursor.fetchone()[0]

        # Insert holdings (50% increase)
        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing1_id, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
        )
        conn.commit()

        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing2_id, "AAPL", "Apple Inc", 150000, 22500000.0, 8.25)
        )
        conn.commit()
        conn.close()

        # Test get_recent_changes
        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            changes = comparator.get_recent_changes("AAPL", limit_days=365)

            assert len(changes) == 1
            assert changes[0].ticker == "AAPL"
            assert changes[0].previous_shares == 100000
            assert changes[0].current_shares == 150000
            assert changes[0].position_increase_pct == 50.0

    def test_get_recent_changes_with_new_position(self, temp_db):
        """Test get_recent_changes detecting a new position (from 0 to non-zero shares)."""
        from datetime import datetime, timedelta

        client = DatabaseClient(db_path=temp_db)

        # Insert test data
        conn = client.get_connection()
        cursor = conn.cursor()

        # Insert investor
        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        cursor.execute("SELECT id FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        investor_id = cursor.fetchone()[0]

        # Use recent dates
        date1 = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        date2 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # Insert two filings
        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, date1, f"{date1}T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", (date1,))
        filing1_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, date2, f"{date2}T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", (date2,))
        filing2_id = cursor.fetchone()[0]

        # Insert holdings: AAPL with 0 shares in first filing, 100000 in second (new position)
        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing1_id, "AAPL", "Apple Inc", 0, 0.0, 0.0)
        )
        conn.commit()

        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing2_id, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
        )
        conn.commit()
        conn.close()

        # Test get_recent_changes for AAPL (should detect new position)
        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            changes = comparator.get_recent_changes("AAPL", limit_days=365)

            assert len(changes) == 1
            assert changes[0].ticker == "AAPL"
            assert changes[0].is_new_position is True
            assert changes[0].current_shares == 100000

    def test_get_recent_changes_respects_time_window(self, temp_db):
        """Test that get_recent_changes respects the time window."""
        from datetime import datetime, timedelta

        client = DatabaseClient(db_path=temp_db)

        # Insert test data
        conn = client.get_connection()
        cursor = conn.cursor()

        # Insert investor
        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        cursor.execute("SELECT id FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        investor_id = cursor.fetchone()[0]

        # Use relative dates: old filing (200 days ago), recent filing (30 days ago)
        date1 = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        date2 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        # Insert old filing (before time window)
        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, date1, f"{date1}T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", (date1,))
        filing1_id = cursor.fetchone()[0]

        # Insert recent filing (within time window)
        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, date2, f"{date2}T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", (date2,))
        filing2_id = cursor.fetchone()[0]

        # Insert holdings with change
        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing1_id, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
        )
        conn.commit()

        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing2_id, "AAPL", "Apple Inc", 150000, 22500000.0, 8.25)
        )
        conn.commit()
        conn.close()

        # Test with narrow time window (30 days) - should find nothing
        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            changes = comparator.get_recent_changes("AAPL", limit_days=30)

            # Old filing is outside window, can't compare
            assert changes == []

        # Test with wide time window (365 days) - should find change
        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            changes = comparator.get_recent_changes("AAPL", limit_days=365)

            assert len(changes) == 1


class TestComparatorGetHoldingsAtDate:
    """Tests for Comparator._get_holdings_at_date() method."""

    def test_get_holdings_at_date_returns_correct_holding(self, temp_db):
        """Test that _get_holdings_at_date returns correct holding."""
        client = DatabaseClient(db_path=temp_db)

        # Insert test data
        conn = client.get_connection()
        cursor = conn.cursor()

        # Insert investor and filing
        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        cursor.execute("SELECT id FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        investor_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, "2024-06-01", "2024-06-01T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", ("2024-06-01",))
        filing_id = cursor.fetchone()[0]

        # Insert holdings
        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing_id, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
        )
        conn.commit()

        cursor_test = conn.cursor()

        # Test _get_holdings_at_date
        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            holdings = comparator._get_holdings_at_date("AAPL", "2024-06-01", cursor_test)

            assert len(holdings) == 1
            assert holdings[0].ticker == "AAPL"
            assert holdings[0].company_name == "Apple Inc"
            assert holdings[0].shares == 100000
            assert holdings[0].market_value == 15000000.0
            assert holdings[0].portfolio_weight == 5.5

        conn.close()

    def test_get_holdings_at_date_empty_result(self, temp_db):
        """Test that _get_holdings_at_date returns empty list when no holdings found."""
        client = DatabaseClient(db_path=temp_db)

        conn = client.get_connection()
        cursor = conn.cursor()

        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            holdings = comparator._get_holdings_at_date("AAPL", "2024-06-01", cursor)

            assert holdings == []

        conn.close()

    def test_get_holdings_at_date_without_cursor(self, temp_db):
        """Test that _get_holdings_at_date works without providing a cursor."""
        client = DatabaseClient(db_path=temp_db)

        # Insert test data
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        cursor.execute("SELECT id FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        investor_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, "2024-06-01", "2024-06-01T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE filing_date = ?", ("2024-06-01",))
        filing_id = cursor.fetchone()[0]

        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing_id, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
        )
        conn.commit()
        conn.close()

        # Test _get_holdings_at_date without cursor parameter
        with patch('smart_money_tracker.signals.comparator.db_client', client):
            comparator = Comparator()
            holdings = comparator._get_holdings_at_date("AAPL", "2024-06-01")

            assert len(holdings) == 1
            assert holdings[0].ticker == "AAPL"
