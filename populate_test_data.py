#!/usr/bin/env python3
"""
Populate database with test stocks for demonstration purposes.
This helps verify the email pipeline works when external APIs are unavailable.
"""
import sqlite3
from datetime import datetime
from smart_money_tracker.db.client import db_client

def add_test_signals():
    """Add test signals to the database"""
    conn = db_client.get_connection()
    cursor = conn.cursor()

    test_stocks = [
        ("AAPL", 85, "New 13F position|Position increased 45.2%|Insider purchase"),
        ("MSFT", 72, "Position increased 28.5%|Multiple insider purchases"),
        ("TSLA", 65, "Congressional buy|Insider purchase"),
        ("NVDA", 58, "Position increased 12.3%"),
        ("GOOGL", 45, "New 13F position"),
        ("AMZN", 38, "Position decreased 5.1%"),
        ("META", 25, "No recent activity"),
    ]

    for ticker, score, reasons in test_stocks:
        cursor.execute(
            '''INSERT OR REPLACE INTO signals (ticker, score, reasons, generated_at)
               VALUES (?, ?, ?, ?)''',
            (ticker, score, reasons, datetime.now().isoformat())
        )

    conn.commit()
    conn.close()

    print(f"[+] Added {len(test_stocks)} test stocks to database")
    for ticker, score, _ in test_stocks:
        print(f"    {ticker}: {score}/100")

if __name__ == "__main__":
    add_test_signals()
