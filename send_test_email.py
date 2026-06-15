#!/usr/bin/env python3
"""Send a test email using a minimal stock payload to verify SMTP delivery."""

from datetime import datetime

from smart_money_tracker.config.settings import settings
from smart_money_tracker.email.renderer import EmailRenderer
from smart_money_tracker.email.sender import EmailSender
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


def send_test_email() -> int:
    stocks = [
        {
            "ticker": "TEST",
            "score": 75,
            "reasons": ["Test email — SMTP delivery check"],
            "insiders": ["John Doe (CEO) — 10,000 shares @ $100.00 = $1,000,000 on 2026-06-15"],
            "institutional_holders": ["Vanguard Group — 5,000,000 shares — ~$500.0M position"],
            "price": 100.00,
            "market_cap": 10_000_000_000,
            "politicians": [],
            "notable_activity": None,
            "analysis": None,
        }
    ]

    renderer = EmailRenderer()
    html = renderer.render(stocks, datetime.now())

    sender = EmailSender()
    success = sender.send(
        to_email=settings.report_email,
        subject=f"Smart Money Tracker — Test Email {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        html=html,
    )

    if success:
        logger.info(f"Test email sent successfully to {settings.report_email}")
        return 0
    else:
        logger.error("Test email failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(send_test_email())
