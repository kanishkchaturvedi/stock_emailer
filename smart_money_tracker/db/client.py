"""SQLite database client for Smart Money Tracker."""

import sqlite3

from smart_money_tracker.config.settings import settings
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseClient:
    """SQLite database client with schema initialization."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.database_path
        logger.info(f"Initializing DatabaseClient with path: {self.db_path}")
        self._init_schema()
        logger.info("Database schema initialization complete")

    def _init_schema(self) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
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
            conn.commit()
            logger.info("All database tables created/verified successfully")
        except sqlite3.Error as e:
            logger.error(f"Database schema initialization error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


# Module-level database client instance
db_client = DatabaseClient()
