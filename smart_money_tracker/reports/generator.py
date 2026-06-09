"""Report generator orchestrator coordinating all components."""

from datetime import datetime
from typing import Dict, List, Optional

from smart_money_tracker.ai.analyzer import AIAnalyzer
from smart_money_tracker.config.settings import settings
from smart_money_tracker.data_collection.finnhub import FinnhubFetcher
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
        self.min_score = min_score if min_score is not None else settings.min_score_for_email
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

        # Note: SEC APIs (13F and Form 4) are currently blocked with 403 errors
        # Using Finnhub API as primary data source for insider transactions

        # Step 1: Collect Finnhub insider data
        try:
            logger.info("Collecting Finnhub insider sentiment signals")
            finnhub_fetcher = FinnhubFetcher()
            insider_data = finnhub_fetcher.fetch()

            for ticker, transactions in insider_data.items():
                if ticker not in signals:
                    signals[ticker] = {
                        "new_13f_position": False,
                        "position_increase_pct": 0.0,
                        "insider_purchases": 0,
                        "congressional_buys": 0,
                    }
                # Add insider purchase count from Finnhub
                signals[ticker]["insider_purchases"] += len(transactions)
                # Store detailed transactions for email display
                if transactions:
                    signals[ticker]["finnhub_insiders"] = transactions

            logger.info(f"Collected Finnhub data for {len(insider_data)} tickers")

        except Exception as e:
            logger.warning(
                f"Failed to collect Finnhub signals: {type(e).__name__}: {str(e)}"
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
