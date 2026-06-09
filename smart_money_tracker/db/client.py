"""SQLite database client for Smart Money Tracker."""

import sqlite3
from pathlib import Path

from smart_money_tracker.config.settings import settings
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseClient:
    """SQLite database client with schema initialization."""

    def __init__(self, db_path: str | None = None):
        """
        Initialize database client and create schema.

        Args:
            db_path: Path to SQLite database file. Defaults to settings.database_path
        """
        self.db_path = db_path or settings.database_path
        logger.info(f"Initializing DatabaseClient with path: {self.db_path}")
        self._init_schema()
        logger.info("Database schema initialization complete")

    def _init_schema(self) -> None:
        """Create all required tables if they don't exist."""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Create investors table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS investors (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    cik TEXT UNIQUE NOT NULL
                )
                """
            )
            logger.debug("Created/verified investors table")

            # Create filings_13f table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS filings_13f (
                    id INTEGER PRIMARY KEY,
                    investor_id INTEGER NOT NULL,
                    filing_date TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    FOREIGN KEY (investor_id) REFERENCES investors(id)
                )
                """
            )
            logger.debug("Created/verified filings_13f table")

            # Create holdings table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY,
                    filing_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    shares INTEGER NOT NULL,
                    market_value REAL NOT NULL,
                    portfolio_weight REAL NOT NULL,
                    FOREIGN KEY (filing_id) REFERENCES filings_13f(id)
                )
                """
            )
            logger.debug("Created/verified holdings table")

            # Create insider_transactions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS insider_transactions (
                    id INTEGER PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    insider_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    shares_bought INTEGER NOT NULL,
                    value_bought REAL NOT NULL,
                    transaction_date TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )
                """
            )
            logger.debug("Created/verified insider_transactions table")

            # Create congressional_trades table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS congressional_trades (
                    id INTEGER PRIMARY KEY,
                    politician TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    buy_or_sell TEXT NOT NULL,
                    disclosure_date TEXT NOT NULL,
                    estimated_amount REAL NOT NULL,
                    fetched_at TEXT NOT NULL
                )
                """
            )
            logger.debug("Created/verified congressional_trades table")

            # Create signals table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    reasons TEXT NOT NULL,
                    generated_at TEXT NOT NULL
                )
                """
            )
            logger.debug("Created/verified signals table")

            # Create email_history table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS email_history (
                    id INTEGER PRIMARY KEY,
                    recipient TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    sent_at TEXT,
                    status TEXT NOT NULL
                )
                """
            )
            logger.debug("Created/verified email_history table")

            conn.commit()
            logger.info("All database tables created/verified successfully")

        except sqlite3.Error as e:
            logger.error(f"Database schema initialization error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a SQLite database connection.

        Returns:
            sqlite3.Connection object
        """
        conn = sqlite3.connect(self.db_path)
        # Enable foreign key constraint enforcement
        conn.execute("PRAGMA foreign_keys = ON")
        logger.debug(f"Opened database connection to {self.db_path}")
        return conn


# Module-level database client instance
db_client = DatabaseClient()
