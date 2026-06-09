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
    """
    Main entry point for the Smart Money Tracker application.

    Orchestrates:
    1. CLI argument parsing
    2. Report generation with configurable scoring threshold
    3. Optional report sending via email
    4. Proper exit codes and error handling

    Returns:
        0 on success, 1 on error
    """
    parser = ArgumentParser(
        description="Smart Money Tracker - Track insider and smart money trading signals"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render report only, do not send email",
    )
    parser.add_argument(
        "--recipient",
        type=str,
        default=None,
        help="Override recipient email address",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=60,
        help="Minimum score threshold for stocks to include (default: 60)",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip data collection, use database only",
    )

    args = parser.parse_args()

    try:
        # Log start
        logger.info("=" * 50)
        logger.info("Smart Money Tracker - Daily Report")
        logger.info(f"Started at {datetime.now().isoformat()}")
        logger.info("=" * 50)

        # Create report generator with min_score
        logger.info(f"Generating report with min_score={args.min_score}")
        generator = ReportGenerator(min_score=args.min_score)

        # Generate report
        stocks = generator.generate_report()

        # Check if any stocks found
        if not stocks:
            logger.warning("No stocks found (no signals detected)")
            logger.info(f"Completed at {datetime.now().isoformat()}")
            return 0

        # Log summary
        logger.info(f"Found {len(stocks)} high-conviction stocks:")
        for stock in stocks:
            reasons_str = ", ".join(stock["reasons"][:2])
            logger.info(
                f"  {stock['ticker']}: {stock['score']}/100 - {reasons_str}"
            )

        # Handle dry-run vs send
        if args.dry_run:
            recipient = args.recipient or settings.report_email
            logger.info(
                f"[DRY RUN] Would send report to {recipient} (not sending)"
            )
        else:
            recipient = args.recipient or settings.report_email
            logger.info(f"Sending report to {recipient}")
            success = generator.send_report(stocks, recipient)

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
