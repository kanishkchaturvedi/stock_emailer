"""Pytest configuration and shared fixtures for Smart Money Tracker tests."""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_db():
    """
    Create a temporary SQLite database for testing.

    Yields a path to the temporary database file.
    """
    # Create a temporary file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)  # Close the file descriptor

    try:
        # Create basic schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables that the application might need
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                sent_at TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                source TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                data TEXT,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                score INTEGER NOT NULL,
                reasons TEXT,
                scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.commit()
        conn.close()

        yield db_path

    finally:
        # Clean up: remove the temporary database file
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass


@pytest.fixture
def mock_settings(monkeypatch):
    """
    Mock environment variables for testing.

    Provides a mock settings object with sensible defaults.
    """
    # Set environment variables for Settings class
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setenv("REPORT_EMAIL", "test@example.com")
    monkeypatch.setenv("DATABASE_PATH", ":memory:")
    monkeypatch.setenv("MIN_SCORE_FOR_EMAIL", "60")

    # Optional settings
    monkeypatch.setenv("SMTP_EMAIL", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "password123")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

    return {
        "openai_api_key": "test-key-12345",
        "report_email": "test@example.com",
        "database_path": ":memory:",
        "min_score_for_email": 60,
        "smtp_email": "sender@example.com",
        "smtp_password": "password123",
        "openai_model": "gpt-4o-mini",
    }


@pytest.fixture
def mock_db_client(temp_db, monkeypatch):
    """
    Mock the database client with a temporary database.

    Patches the global db_client to use a temporary database.
    """
    from smart_money_tracker.db.client import DatabaseClient

    # Create a database client pointing to temp_db
    mock_client = DatabaseClient(db_path=temp_db)

    # Patch the global db_client
    monkeypatch.setattr(
        "smart_money_tracker.db.client.db_client",
        mock_client,
    )

    return mock_client


@pytest.fixture
def cleanup():
    """
    Cleanup fixture for tests.

    Yields control back to tests, then cleans up after.
    """
    yield
    # Cleanup happens here (or in other fixtures' finally blocks)


@pytest.fixture(autouse=True)
def reset_logger():
    """
    Reset logger handlers before each test.

    This prevents logger handler accumulation across tests.
    """
    import logging

    # Get all loggers
    for logger_name in list(logging.Logger.manager.loggerDict):
        logger = logging.getLogger(logger_name)
        # Clear handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    yield

    # Reset after test
    for logger_name in list(logging.Logger.manager.loggerDict):
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
