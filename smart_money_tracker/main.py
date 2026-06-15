#!/usr/bin/env python3
"""Main entry point for Smart Money Tracker CLI."""

import sys
from argparse import ArgumentParser
from datetime import datetime

from smart_money_tracker.config.settings import settings
from smart_money_tracker.reports.generator import ReportGenerator
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> int:
    parser = ArgumentParser(
        description="Smart Money Tracker - Track insider and smart money trading signals"
    )
    parser.add_argument("--dry-run", action="store_true", help="Render report only, do not send email")
    parser.add_argument("--recipient", type=str, default=None, help="Override recipient email address")
    parser.add_argument("--min-score", type=int, default=60, help="Minimum score threshold (default: 60)")
    args = parser.parse_args()

    try:
        logger.info("=" * 50)
        logger.info("Smart Money Tracker - Daily Report")
        logger.info(f"Started at {datetime.now().isoformat()}")
        logger.info("=" * 50)

        generator = ReportGenerator(min_score=args.min_score)
        report = generator.generate_report()

        stocks = report.get("stocks", [])
        tips_india = report.get("tips_india", [])
        tips_us = report.get("tips_us", [])

        if not stocks and not tips_india and not tips_us:
            logger.warning("No signals or tips generated")
            logger.info(f"Completed at {datetime.now().isoformat()}")
            return 0

        logger.info(f"Found {len(stocks)} high-conviction stocks:")
        for stock in stocks:
            reasons_str = ", ".join(stock["reasons"][:2])
            logger.info(f"  {stock['ticker']}: {stock['score']}/100 - {reasons_str}")

        logger.info(f"AI tips: {len(tips_india)} India, {len(tips_us)} US")

        recipient = args.recipient or settings.report_email

        if args.dry_run:
            logger.info(f"[DRY RUN] Would send report to {recipient} (not sending)")
        else:
            success = generator.send_report(report, recipient)
            if not success:
                logger.error("Failed to send report")
                logger.info(f"Completed at {datetime.now().isoformat()}")
                return 1
            logger.info(f"Report sent successfully to {recipient}")

        logger.info(f"Completed at {datetime.now().isoformat()}")
        return 0

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 1
    except Exception as e:
        logger.exception(f"Fatal error: {type(e).__name__}: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
