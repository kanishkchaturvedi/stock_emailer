"""Database module for Smart Money Tracker."""

from smart_money_tracker.db.client import DatabaseClient, db_client
from smart_money_tracker.db.models import (
    CongressionalTrade,
    EmailReport,
    Filing13F,
    FilingComparison,
    Holding,
    InsiderTransaction,
    Signal,
)

__all__ = [
    "DatabaseClient",
    "db_client",
    "Holding",
    "Filing13F",
    "FilingComparison",
    "InsiderTransaction",
    "CongressionalTrade",
    "Signal",
    "EmailReport",
]
