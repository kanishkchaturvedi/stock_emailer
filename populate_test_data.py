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

    # Format: (ticker, score, reasons, investors, insiders, politicians)
    test_stocks = [
        ("AAPL", 85, "New 13F position|Position increased 45.2%|Insider purchase",
         "Berkshire Hathaway (increased 2.5%)|Scion Capital (new position)",
         "CEO Tim Cook (+$50M)|CFO Luca Maestri (+$25M)",
         "Senator Feinstein (buy $100k-$250k)"),

        ("MSFT", 72, "Position increased 28.5%|Multiple insider purchases",
         "Pershing Square (+15%)",
         "CTO Kevin Scott (+$75M)|Board Member Amy Hood (+$40M)",
         "Congressman Pallone (buy $50k-$100k)"),

        ("TSLA", 65, "Congressional buy|Insider purchase",
         "Baupost Group (new position)",
         "CFO Zachary Kirkhorn (+$30M)",
         "Senator Boozman (buy $250k-$500k)|Rep. Torres (sell $100k-$250k)"),

        ("NVDA", 82, "Insider purchase|Position increased 33%",
         "Third Point (increased 8%)|Duquesne Capital (+12%)",
         "CEO Jensen Huang (+$100M)",
         "Senator Cornyn (buy $50k-$100k)"),

        ("GOOGL", 45, "New 13F position",
         "Icahn Capital (new position)",
         "Board Member Sundar Pichai (no recent activity)",
         ""),

        ("IBM", 60, "New 13F position|Congressional buy",
         "Berkshire Hathaway (maintained 7.1%)",
         "CFO James Kavanaugh (+$10M)",
         "Senator Warner (buy $100k-$250k)"),

        ("JPM", 55, "Position increased 18%",
         "Pershing Square (increased 5%)",
         "CEO Jamie Dimon (+$50M)",
         "Senator Menendez (buy $50k-$100k)"),

        ("V", 52, "Insider purchase",
         "Scion Capital (no change)",
         "Director Robert Reisner (+$20M)",
         ""),

        ("AMZN", 38, "Position decreased 5.1%",
         "Berkshire Hathaway (decreased 1%)",
         "VP Andy Jassy (no recent activity)",
         "Rep. Ocasio-Cortez (sell $250k-$500k)"),

        ("META", 25, "No recent activity",
         "No major holdings",
         "CTO Bosworth (no recent activity)",
         "Senator Vance (buy $50k-$100k)"),

        ("JNJ", 48, "Position decreased 3%",
         "Appaloosa (+6%)",
         "CEO Joaquin Duato (+$25M)",
         ""),

        ("KO", 42, "New position",
         "Baupost (new 1.5%)",
         "CFO James Quincey (no activity)",
         "Senator Cornyn (buy $100k-$250k)"),

        ("PG", 35, "No signals",
         "Duquesne (+2%)",
         "Board Member Clayton (no activity)",
         ""),

        ("AMZN", 38, "Position decreased 5.1%",
         "Berkshire (decreased 1%)",
         "VP Andy Jassy (no activity)",
         "Rep. AOC (sell $250k-$500k)"),
    ]

    # Clear old test data first
    cursor.execute('DELETE FROM signals')

    for ticker, score, reasons, investors, insiders, politicians in test_stocks:
        cursor.execute(
            '''INSERT INTO signals (ticker, score, reasons, generated_at)
               VALUES (?, ?, ?, ?)''',
            (ticker, score, f"{reasons}|||{investors}|||{insiders}|||{politicians}", datetime.now().isoformat())
        )

    conn.commit()
    conn.close()

    print(f"[+] Added {len(test_stocks)} test stocks to database")
    for row in test_stocks:
        ticker, score = row[0], row[1]
        print(f"    {ticker}: {score}/100")

if __name__ == "__main__":
    add_test_signals()
