#!/usr/bin/env python3
"""
Send test email with stocks from database.
"""
import os
from datetime import datetime
from smart_money_tracker.email.renderer import EmailRenderer
from smart_money_tracker.email.sender import EmailSender
from smart_money_tracker.db.client import db_client
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)

def send_test_email():
    """Send email with test stocks from database"""
    conn = db_client.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT ticker, score, reasons FROM signals ORDER BY score DESC')
    rows = cursor.fetchall()
    conn.close()

    stocks = []
    for ticker, score, reasons in rows:
        # Parse reasons string: reasons|investors|insiders|politicians
        parts = reasons.split('|||') if reasons else ['', '', '', '']
        reason_list = parts[0].split('|') if parts[0] else []
        investors = parts[1].split('|') if len(parts) > 1 and parts[1] else []
        insiders = parts[2].split('|') if len(parts) > 2 and parts[2] else []
        politicians = parts[3].split('|') if len(parts) > 3 and parts[3] else []

        stocks.append({
            'ticker': ticker,
            'score': score,
            'reasons': [r.strip() for r in reason_list if r.strip()],
            'investors': [inv.strip() for inv in investors if inv.strip()],
            'insiders': [ins.strip() for ins in insiders if ins.strip()],
            'politicians': [pol.strip() for pol in politicians if pol.strip()],
            'analysis': {
                'bullish_thesis': 'Professional investors are accumulating this position.',
                'bearish_thesis': 'Recent activity could reflect profit-taking or portfolio rebalancing.',
                'key_risks': 'Market conditions and broader economic factors.'
            }
        })

    if stocks:
        logger.info(f"Sending report with {len(stocks)} stocks...")
        renderer = EmailRenderer()
        html = renderer.render(stocks, datetime.now())

        sender = EmailSender()
        success = sender.send(
            to_email=os.environ['REPORT_EMAIL'],
            subject=f"Smart Money Tracker Report - {datetime.now().strftime('%Y-%m-%d')}",
            html=html
        )

        if success:
            logger.info("Email sent successfully!")
            return 0
        else:
            logger.error("Email failed!")
            return 1
    else:
        logger.warning("No stocks found in database")
        return 1

if __name__ == "__main__":
    exit(send_test_email())
