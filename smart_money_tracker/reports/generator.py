"""Report generator orchestrator coordinating all components."""

from datetime import datetime
from typing import Dict, List, Optional

from smart_money_tracker.ai.analyzer import AIAnalyzer
from smart_money_tracker.config.settings import settings
from smart_money_tracker.data_collection.congress import FetcherCongress
from smart_money_tracker.data_collection.filings_13f import Fetcher13F
from smart_money_tracker.data_collection.insider_form4 import FetcherForm4
from smart_money_tracker.db.client import db_client
from smart_money_tracker.email.renderer import EmailRenderer
from smart_money_tracker.email.sender import EmailSender
from smart_money_tracker.signals.scoring import ScoringEngine
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Orchestrates data collection, scoring, analysis, and reporting."""

    def __init__(self, min_score: int | None = None):
        """
        Initialize the report generator.

        Args:
            min_score: Minimum score threshold for stocks to include in report.
                      Defaults to settings.min_score_for_email if not provided.
        """
        self.min_score = min_score or settings.min_score_for_email
        self.scorer = ScoringEngine()
        self.analyzer = AIAnalyzer()
        self.renderer = EmailRenderer()
        self.sender = EmailSender()
        logger.info(
            f"ReportGenerator initialized with min_score={self.min_score}"
        )

    def collect_signals(self) -> Dict[str, Dict]:
        """
        Collect trading signals from all three data sources.

        Returns:
            Dictionary keyed by ticker with signal data:
            {
                'AAPL': {
                    'new_13f_position': True,
                    'position_increase_pct': 15.5,
                    'insider_purchases': 2,
                    'congressional_buys': 1
                },
                ...
            }
        """
        signals = {}

        # Step 1: Collect 13F signals
        try:
            logger.info("Collecting 13F signals")
            fetcher_13f = Fetcher13F()
            filings = fetcher_13f.fetch()

            for filing in filings:
                for holding in filing.holdings:
                    ticker = holding.ticker
                    if ticker not in signals:
                        signals[ticker] = {
                            "new_13f_position": False,
                            "position_increase_pct": 0.0,
                            "insider_purchases": 0,
                            "congressional_buys": 0,
                        }
                    # Mark as new position if detected
                    signals[ticker]["new_13f_position"] = True

            logger.info(f"Collected 13F signals for {len(signals)} tickers")

        except Exception as e:
            logger.warning(
                f"Failed to collect 13F signals: {type(e).__name__}: {str(e)}"
            )

        # Step 2: Collect Form 4 (insider) signals
        try:
            logger.info("Collecting insider transaction signals")
            fetcher_form4 = FetcherForm4()
            transactions = fetcher_form4.fetch()

            for transaction in transactions:
                ticker = transaction.ticker
                if ticker not in signals:
                    signals[ticker] = {
                        "new_13f_position": False,
                        "position_increase_pct": 0.0,
                        "insider_purchases": 0,
                        "congressional_buys": 0,
                    }
                # Count insider purchases
                signals[ticker]["insider_purchases"] += 1

            logger.info(
                f"Collected insider signals for {len([t for t in transactions])} transactions"
            )

        except Exception as e:
            logger.warning(
                f"Failed to collect Form 4 signals: {type(e).__name__}: {str(e)}"
            )

        # Step 3: Collect congressional signals
        try:
            logger.info("Collecting congressional trade signals")
            fetcher_congress = FetcherCongress()
            trades = fetcher_congress.fetch()

            for trade in trades:
                # Only count buy transactions
                if trade.buy_or_sell.lower() != "buy":
                    continue

                ticker = trade.ticker
                if ticker not in signals:
                    signals[ticker] = {
                        "new_13f_position": False,
                        "position_increase_pct": 0.0,
                        "insider_purchases": 0,
                        "congressional_buys": 0,
                    }
                # Count congressional buys
                signals[ticker]["congressional_buys"] += 1

            logger.info(
                f"Collected congressional signals for {len([t for t in trades if t.buy_or_sell.lower() == 'buy'])} trades"
            )

        except Exception as e:
            logger.warning(
                f"Failed to collect congressional signals: {type(e).__name__}: {str(e)}"
            )

        logger.info(f"Signal collection complete. Total tickers: {len(signals)}")
        return signals

    def generate_report(self) -> List[Dict]:
        """
        Generate a report of high-conviction stocks.

        Orchestration steps:
        1. Collect signals from all sources
        2. Score each stock using the scoring engine
        3. Filter stocks scoring >= min_score
        4. Sort by score descending
        5. Limit to top 10 stocks
        6. Enrich each stock with AI analysis
        7. Return list of stock dictionaries

        Returns:
            List of stock dictionaries with structure:
            [
                {
                    'ticker': 'AAPL',
                    'score': 85,
                    'reasons': ['New position', 'Insider purchase'],
                    'analysis': {
                        'bullish_thesis': '...',
                        'bearish_thesis': '...',
                        'key_risks': '...'
                    },
                    'data': {...signal data...}
                },
                ...
            ]
        """
        logger.info("Starting report generation")

        # Step 1: Collect signals
        signals = self.collect_signals()

        if not signals:
            logger.info("No signals collected. Returning empty report.")
            return []

        # Step 2-4: Score, filter, and sort
        scored_stocks = []
        for ticker, signal_data in signals.items():
            score, reasons = self.scorer.score_ticker(
                ticker,
                new_13f_position=signal_data["new_13f_position"],
                position_increase_pct=signal_data["position_increase_pct"],
                insider_purchases=signal_data["insider_purchases"],
                congressional_buys=signal_data["congressional_buys"],
            )

            # Only include stocks meeting minimum score threshold
            if score >= self.min_score:
                scored_stocks.append({
                    "ticker": ticker,
                    "score": score,
                    "reasons": reasons,
                    "data": signal_data,
                })

        logger.info(
            f"Scored {len(signals)} tickers. {len(scored_stocks)} qualified "
            f"with score >= {self.min_score}"
        )

        # Sort by score descending
        scored_stocks.sort(key=lambda x: x["score"], reverse=True)

        # Step 5: Limit to top 10
        top_stocks = scored_stocks[:10]
        logger.info(f"Selected top {len(top_stocks)} stocks for report")

        # Step 6: Enrich with AI analysis
        report_stocks = []
        for stock in top_stocks:
            try:
                analysis = self.analyzer.analyze_ticker(
                    stock["ticker"], stock["reasons"]
                )
                stock["analysis"] = analysis
                logger.info(
                    f"Analyzed {stock['ticker']} with score {stock['score']}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to analyze {stock['ticker']}: "
                    f"{type(e).__name__}: {str(e)}"
                )
                stock["analysis"] = None

            report_stocks.append(stock)

        logger.info(f"Report generation complete. {len(report_stocks)} stocks")
        return report_stocks

    def send_report(
        self, stocks: List[Dict], recipient: str | None = None
    ) -> bool:
        """
        Send the generated report via email.

        Args:
            stocks: List of stock dictionaries from generate_report()
            recipient: Email recipient address. Defaults to settings.report_email

        Returns:
            True if email sent successfully, False otherwise
        """
        recipient = recipient or settings.report_email

        try:
            logger.info(f"Sending report to {recipient}")

            # Render HTML from stocks
            generated_at = datetime.now()
            html = self.renderer.render(stocks, generated_at)
            logger.info(f"Rendered email HTML ({len(html)} bytes)")

            # Send email
            subject = f"Smart Money Tracker Report - {generated_at.strftime('%Y-%m-%d')}"
            success = self.sender.send(
                to_email=recipient,
                subject=subject,
                html=html,
            )

            if success:
                logger.info(f"Email sent successfully to {recipient}")
            else:
                logger.warning(f"Email send returned False for {recipient}")

            # Log to database
            try:
                self._log_email_history(
                    recipient=recipient,
                    generated_at=generated_at,
                    status="sent" if success else "failed",
                )
            except Exception as e:
                logger.error(
                    f"Failed to log email history: {type(e).__name__}: {str(e)}"
                )
                # Don't fail the send if logging fails
                pass

            return success

        except Exception as e:
            logger.error(
                f"Failed to send report: {type(e).__name__}: {str(e)}"
            )
            # Try to log failure
            try:
                self._log_email_history(
                    recipient=recipient,
                    generated_at=datetime.now(),
                    status="failed",
                )
            except Exception as log_error:
                logger.error(
                    f"Failed to log email failure: {type(log_error).__name__}: {str(log_error)}"
                )

            return False

    def _log_email_history(
        self,
        recipient: str,
        generated_at: datetime,
        status: str,
    ) -> None:
        """
        Log email send history to database.

        Args:
            recipient: Email recipient address
            generated_at: When the report was generated
            status: 'sent' or 'failed'

        Raises:
            Exception: On database errors
        """
        conn = db_client.get_connection()
        cursor = conn.cursor()

        try:
            generated_at_str = generated_at.isoformat()
            sent_at_str = datetime.now().isoformat() if status == "sent" else None

            cursor.execute(
                """
                INSERT INTO email_history (recipient, generated_at, sent_at, status)
                VALUES (?, ?, ?, ?)
                """,
                (recipient, generated_at_str, sent_at_str, status),
            )

            conn.commit()
            logger.info(
                f"Logged email history: {recipient}, status={status}"
            )

        except Exception as e:
            logger.error(
                f"Error logging email history: {type(e).__name__}: {str(e)}"
            )
            conn.rollback()
            raise
        finally:
            conn.close()
