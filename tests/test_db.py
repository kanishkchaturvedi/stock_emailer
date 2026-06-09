"""Tests for database models and client."""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from smart_money_tracker.db.client import DatabaseClient
from smart_money_tracker.db.models import (
    CongressionalTrade,
    EmailReport,
    Filing13F,
    FilingComparison,
    Holding,
    InsiderTransaction,
    Signal,
)


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
                # Ignore cleanup errors - files will be cleaned up by temp directory
                pass


class TestDatabaseClient:
    """Tests for DatabaseClient initialization and schema."""

    def test_database_client_initializes_without_error(self, temp_db):
        """Test that DatabaseClient initializes without error."""
        client = DatabaseClient(db_path=temp_db)
        assert client.db_path == temp_db
        assert Path(temp_db).exists()

    def test_all_seven_tables_created(self, temp_db):
        """Test that all 7 tables are created."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        # Query all table names
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_tables = {
            "investors",
            "filings_13f",
            "holdings",
            "insider_transactions",
            "congressional_trades",
            "signals",
            "email_history",
        }

        assert tables == expected_tables, f"Expected {expected_tables}, got {tables}"

    def test_investors_table_structure(self, temp_db):
        """Test that investors table has correct columns."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(investors)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        assert "id" in columns
        assert "name" in columns
        assert "cik" in columns

    def test_filings_13f_table_structure(self, temp_db):
        """Test that filings_13f table has correct columns and foreign key."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(filings_13f)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        assert "id" in columns
        assert "investor_id" in columns
        assert "filing_date" in columns
        assert "fetched_at" in columns

    def test_holdings_table_structure(self, temp_db):
        """Test that holdings table has correct columns and foreign key."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(holdings)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        assert "id" in columns
        assert "filing_id" in columns
        assert "ticker" in columns
        assert "company_name" in columns
        assert "shares" in columns
        assert "market_value" in columns
        assert "portfolio_weight" in columns

    def test_insider_transactions_table_structure(self, temp_db):
        """Test that insider_transactions table has correct columns."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(insider_transactions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        assert "id" in columns
        assert "ticker" in columns
        assert "insider_name" in columns
        assert "role" in columns
        assert "transaction_type" in columns
        assert "shares_bought" in columns
        assert "value_bought" in columns
        assert "transaction_date" in columns
        assert "fetched_at" in columns

    def test_congressional_trades_table_structure(self, temp_db):
        """Test that congressional_trades table has correct columns."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(congressional_trades)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        assert "id" in columns
        assert "politician" in columns
        assert "ticker" in columns
        assert "buy_or_sell" in columns
        assert "disclosure_date" in columns
        assert "estimated_amount" in columns
        assert "fetched_at" in columns

    def test_signals_table_structure(self, temp_db):
        """Test that signals table has correct columns."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(signals)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        assert "id" in columns
        assert "ticker" in columns
        assert "score" in columns
        assert "reasons" in columns
        assert "generated_at" in columns

    def test_email_history_table_structure(self, temp_db):
        """Test that email_history table has correct columns."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(email_history)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        assert "id" in columns
        assert "recipient" in columns
        assert "generated_at" in columns
        assert "sent_at" in columns
        assert "status" in columns

    def test_insert_into_investors_table(self, temp_db):
        """Test that inserting data into investors table works."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        cursor.execute("SELECT name, cik FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "Berkshire Hathaway"
        assert result[1] == "0000051143"

    def test_insert_into_filings_13f_table(self, temp_db):
        """Test that inserting data into filings_13f table works."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        # First insert an investor
        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        # Get investor id
        cursor.execute("SELECT id FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        investor_id = cursor.fetchone()[0]

        # Insert filing
        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, "2024-06-09", "2024-06-09T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT investor_id, filing_date FROM filings_13f WHERE investor_id = ?", (investor_id,))
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == investor_id
        assert result[1] == "2024-06-09"

    def test_insert_into_holdings_table(self, temp_db):
        """Test that inserting data into holdings table works."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        # Setup: Insert investor and filing
        cursor.execute(
            "INSERT INTO investors (name, cik) VALUES (?, ?)",
            ("Berkshire Hathaway", "0000051143")
        )
        conn.commit()

        cursor.execute("SELECT id FROM investors WHERE name = ?", ("Berkshire Hathaway",))
        investor_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
            (investor_id, "2024-06-09", "2024-06-09T10:00:00")
        )
        conn.commit()

        cursor.execute("SELECT id FROM filings_13f WHERE investor_id = ?", (investor_id,))
        filing_id = cursor.fetchone()[0]

        # Insert holding
        cursor.execute(
            """INSERT INTO holdings
               (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (filing_id, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
        )
        conn.commit()

        cursor.execute(
            "SELECT ticker, company_name, shares, market_value FROM holdings WHERE filing_id = ?",
            (filing_id,)
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "AAPL"
        assert result[1] == "Apple Inc"
        assert result[2] == 100000
        assert result[3] == 15000000.0

    def test_insert_into_insider_transactions_table(self, temp_db):
        """Test that inserting data into insider_transactions table works."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO insider_transactions
               (ticker, insider_name, role, transaction_type, shares_bought, value_bought, transaction_date, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("AAPL", "John Doe", "CEO", "BUY", 1000, 150000.0, "2024-06-09", "2024-06-09T10:00:00")
        )
        conn.commit()

        cursor.execute(
            "SELECT ticker, insider_name, role, transaction_type, shares_bought FROM insider_transactions WHERE ticker = ?",
            ("AAPL",)
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "AAPL"
        assert result[1] == "John Doe"
        assert result[2] == "CEO"
        assert result[3] == "BUY"
        assert result[4] == 1000

    def test_insert_into_congressional_trades_table(self, temp_db):
        """Test that inserting data into congressional_trades table works."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO congressional_trades
               (politician, ticker, buy_or_sell, disclosure_date, estimated_amount, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("Jane Smith", "MSFT", "BUY", "2024-06-09", 50000.0, "2024-06-09T10:00:00")
        )
        conn.commit()

        cursor.execute(
            "SELECT politician, ticker, buy_or_sell, estimated_amount FROM congressional_trades WHERE politician = ?",
            ("Jane Smith",)
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "Jane Smith"
        assert result[1] == "MSFT"
        assert result[2] == "BUY"
        assert result[3] == 50000.0

    def test_insert_into_signals_table(self, temp_db):
        """Test that inserting data into signals table works."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO signals
               (ticker, score, reasons, generated_at)
               VALUES (?, ?, ?, ?)""",
            ("AAPL", 85, "Strong insider buying activity", "2024-06-09T10:00:00")
        )
        conn.commit()

        cursor.execute(
            "SELECT ticker, score, reasons FROM signals WHERE ticker = ?",
            ("AAPL",)
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "AAPL"
        assert result[1] == 85
        assert result[2] == "Strong insider buying activity"

    def test_insert_into_email_history_table(self, temp_db):
        """Test that inserting data into email_history table works."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO email_history
               (recipient, generated_at, sent_at, status)
               VALUES (?, ?, ?, ?)""",
            ("user@example.com", "2024-06-09T10:00:00", "2024-06-09T10:05:00", "sent")
        )
        conn.commit()

        cursor.execute(
            "SELECT recipient, status FROM email_history WHERE recipient = ?",
            ("user@example.com",)
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "user@example.com"
        assert result[1] == "sent"

    def test_foreign_key_constraint_filings_13f(self, temp_db):
        """Test that foreign key constraint is enforced in filings_13f."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        # Try to insert filing with non-existent investor_id
        # This should fail with foreign key constraint
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO filings_13f (investor_id, filing_date, fetched_at) VALUES (?, ?, ?)",
                (9999, "2024-06-09", "2024-06-09T10:00:00")
            )
            conn.commit()

        conn.close()

    def test_foreign_key_constraint_holdings(self, temp_db):
        """Test that foreign key constraint is enforced in holdings."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()
        cursor = conn.cursor()

        # Try to insert holding with non-existent filing_id
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """INSERT INTO holdings
                   (filing_id, ticker, company_name, shares, market_value, portfolio_weight)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (9999, "AAPL", "Apple Inc", 100000, 15000000.0, 5.5)
            )
            conn.commit()

        conn.close()

    def test_schema_is_idempotent(self, temp_db):
        """Test that schema initialization can be called multiple times safely."""
        # Create initial client and schema
        client1 = DatabaseClient(db_path=temp_db)
        conn1 = client1.get_connection()
        cursor1 = conn1.cursor()
        cursor1.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        count1 = cursor1.fetchone()[0]
        conn1.close()

        # Create second client (should reinitialize schema)
        client2 = DatabaseClient(db_path=temp_db)
        conn2 = client2.get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        count2 = cursor2.fetchone()[0]
        conn2.close()

        # Table count should be the same
        assert count1 == count2 == 7

    def test_get_connection_returns_valid_connection(self, temp_db):
        """Test that get_connection returns a valid sqlite3.Connection."""
        client = DatabaseClient(db_path=temp_db)
        conn = client.get_connection()

        assert isinstance(conn, sqlite3.Connection)

        # Test that we can execute a query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1

        conn.close()


class TestPydanticModels:
    """Tests for Pydantic data models."""

    def test_holding_model(self):
        """Test Holding model creation and validation."""
        holding = Holding(
            ticker="AAPL",
            company_name="Apple Inc",
            shares=100000,
            market_value=15000000.0,
            portfolio_weight=5.5
        )

        assert holding.ticker == "AAPL"
        assert holding.company_name == "Apple Inc"
        assert holding.shares == 100000
        assert holding.market_value == 15000000.0
        assert holding.portfolio_weight == 5.5

    def test_filing_13f_model(self):
        """Test Filing13F model creation and validation."""
        holding = Holding(
            ticker="AAPL",
            company_name="Apple Inc",
            shares=100000,
            market_value=15000000.0,
            portfolio_weight=5.5
        )

        filing = Filing13F(
            investor_name="Berkshire Hathaway",
            cik="0000051143",
            filing_date=datetime(2024, 6, 9),
            holdings=[holding]
        )

        assert filing.investor_name == "Berkshire Hathaway"
        assert filing.cik == "0000051143"
        assert len(filing.holdings) == 1
        assert filing.holdings[0].ticker == "AAPL"

    def test_signal_model_with_defaults(self):
        """Test Signal model with default values."""
        signal = Signal(
            ticker="AAPL",
            score=85,
            reasons=["Strong insider buying"]
        )

        assert signal.ticker == "AAPL"
        assert signal.score == 85
        assert signal.has_13f_activity is False
        assert signal.has_insider_buying is False
        assert signal.has_congressional_activity is False

    def test_signal_model_with_custom_values(self):
        """Test Signal model with custom values."""
        signal = Signal(
            ticker="MSFT",
            score=75,
            reasons=["13F activity", "Congressional trading"],
            has_13f_activity=True,
            has_congressional_activity=True
        )

        assert signal.ticker == "MSFT"
        assert signal.score == 75
        assert signal.has_13f_activity is True
        assert signal.has_congressional_activity is True

    def test_email_report_model(self):
        """Test EmailReport model creation."""
        signal1 = Signal(ticker="AAPL", score=85, reasons=["Strong activity"])
        signal2 = Signal(ticker="MSFT", score=75, reasons=["Insider buying"])

        report = EmailReport(
            generated_at=datetime(2024, 6, 9, 10, 0, 0),
            stocks=[signal1, signal2],
            recipient="user@example.com"
        )

        assert len(report.stocks) == 2
        assert report.recipient == "user@example.com"
