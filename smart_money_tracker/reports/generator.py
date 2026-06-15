"""Report generator orchestrator coordinating all components."""

from datetime import datetime
from typing import Dict, List, Optional

from smart_money_tracker.ai.tips_generator import generate_tips
from smart_money_tracker.config.settings import settings
from smart_money_tracker.data_collection.sec_edgar import SECEdgarFetcher, TRACKED_TICKERS
from smart_money_tracker.data_collection.stock_screener import (
    INDIA_WATCHLIST,
    US_WATCHLIST,
    screen_stocks,
)
from smart_money_tracker.data_collection.yfinance_fetcher import (
    fetch_institutional_holders,
    fetch_stock_info,
)
from smart_money_tracker.db.client import db_client
from smart_money_tracker.email.renderer import EmailRenderer
from smart_money_tracker.email.sender import EmailSender
from smart_money_tracker.signals.scoring import ScoringEngine
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Orchestrates data collection, scoring, analysis, and reporting."""

    def __init__(self, min_score: int | None = None):
        self.min_score = min_score if min_score is not None else settings.min_score_for_email
        self.scorer = ScoringEngine()
        self.renderer = EmailRenderer()
        self.sender = EmailSender()
        logger.info(f"ReportGenerator initialized with min_score={self.min_score}")

    def collect_signals(self) -> Dict[str, Dict]:
        """
        Collect trading signals from all data sources.

        Returns:
            {ticker: {"insider_purchases": int, "sec_insiders": [...], "institutional_holders": [...]}}
        """
        signals: Dict[str, Dict] = {}

        # Step 1: Form 4 — open-market insider purchases
        try:
            logger.info("Collecting SEC EDGAR Form 4 insider purchase signals")
            sec_fetcher = SECEdgarFetcher(days_back=60)
            insider_data = sec_fetcher.fetch()

            for ticker, transactions in insider_data.items():
                if ticker not in signals:
                    signals[ticker] = {"insider_purchases": 0}
                signals[ticker]["insider_purchases"] += len(transactions)
                if transactions:
                    signals[ticker]["sec_insiders"] = transactions

            logger.info(f"Form 4 data for {len(insider_data)} tickers")

        except Exception as e:
            logger.warning(f"Failed Form 4 fetch: {type(e).__name__}: {str(e)}")

        # Step 2: Institutional holders via yfinance (aggregated from 13F filings)
        try:
            logger.info("Collecting institutional holders via yfinance")
            all_tickers = list(set(list(signals.keys()) + TRACKED_TICKERS))
            institutional = fetch_institutional_holders(all_tickers)
            for ticker, holders in institutional.items():
                if ticker not in signals:
                    signals[ticker] = {"insider_purchases": 0}
                signals[ticker]["institutional_holders"] = holders
            logger.info(f"Institutional holders found for {len(institutional)} tickers")
        except Exception as e:
            logger.warning(f"Failed yfinance institutional fetch: {type(e).__name__}: {str(e)}")

        logger.info(f"Signal collection complete. Total tickers: {len(signals)}")
        return signals

    def generate_report(self) -> List[Dict]:
        """
        Generate a report of high-conviction stocks.

        Steps:
        1. Collect signals from SEC EDGAR (Form 4) and yfinance (institutional holders)
        2. Score and sort each stock
        3. Limit to top 20
        4. Enrich with price data and format display fields
        """
        logger.info("Starting report generation")

        signals = self.collect_signals()
        if not signals:
            logger.info("No signals collected. Returning empty report.")
            return []

        # Score and sort
        scored_stocks = []
        for ticker, signal_data in signals.items():
            score, reasons = self.scorer.score_ticker(
                ticker,
                insider_purchases=signal_data.get("insider_purchases", 0),
                num_institutional_holders=len(signal_data.get("institutional_holders", [])),
            )
            scored_stocks.append({
                "ticker": ticker,
                "score": score,
                "reasons": reasons,
                "data": signal_data,
            })

        logger.info(f"Scored {len(signals)} tickers total")
        scored_stocks.sort(key=lambda x: x["score"], reverse=True)
        top_stocks = scored_stocks[:20]
        logger.info(f"Selected top {len(top_stocks)} stocks for report")

        # Fetch current price and market cap for top stocks
        top_tickers = [s["ticker"] for s in top_stocks]
        stock_info = fetch_stock_info(top_tickers)

        # Enrich each stock with formatted display fields
        report_stocks = []
        for stock in top_stocks:
            data = stock.get("data", {})
            info = stock_info.get(stock["ticker"], {})

            stock["price"] = info.get("price")
            stock["market_cap"] = info.get("market_cap")

            stock["insiders"] = [
                self._format_insider(p) for p in data.get("sec_insiders", [])
            ]

            raw_holders = data.get("institutional_holders", [])
            stock["institutional_holders"] = [
                self._format_holder(h) for h in sorted(
                    raw_holders, key=lambda h: h.get("value_usd", 0), reverse=True
                )
            ]

            report_stocks.append(stock)

        logger.info(f"Report generation complete. {len(report_stocks)} stocks")

        # Step 5: AI stock tips — independent of signal pipeline
        tips_india, tips_us = self._collect_tips()
        return {"stocks": report_stocks, "tips_india": tips_india, "tips_us": tips_us}

    def _collect_tips(self):
        """Screen India + US watchlists and generate AI tips for top candidates."""
        try:
            logger.info("Screening India watchlist for AI tips")
            india_candidates = screen_stocks(INDIA_WATCHLIST, n=5, market="India")
        except Exception as e:
            logger.warning(f"India screener failed: {e}")
            india_candidates = []

        try:
            logger.info("Screening US watchlist for AI tips")
            us_candidates = screen_stocks(US_WATCHLIST, n=5, market="US")
        except Exception as e:
            logger.warning(f"US screener failed: {e}")
            us_candidates = []

        if not india_candidates and not us_candidates:
            return [], []

        logger.info(f"Generating AI tips for {len(india_candidates)} India + {len(us_candidates)} US stocks")
        all_tips = generate_tips(india_candidates, us_candidates)

        tips_india = [t for t in all_tips if t["market"] == "India"]
        tips_us = [t for t in all_tips if t["market"] == "US"]
        logger.info(f"AI tips generated: {len(tips_india)} India, {len(tips_us)} US")
        return tips_india, tips_us

    @staticmethod
    def _format_insider(p: dict) -> str:
        name = p.get("name", "Unknown")
        title = p.get("title", "")
        shares = int(p.get("shares", 0))
        price = p.get("price", 0.0)
        value = p.get("value", 0.0)
        date = p.get("date", "")
        label = name
        if title:
            label += f" ({title})"
        label += f" — {shares:,} shares"
        if price:
            label += f" @ ${price:,.2f}"
        if value:
            label += f" = ${value:,.0f}"
        if date:
            label += f" on {date}"
        return label

    @staticmethod
    def _format_holder(h: dict) -> str:
        investor = h.get("investor", "Unknown")
        value_usd = h.get("value_usd", 0)
        shares = h.get("shares", 0)
        pct_out = h.get("pct_out", 0)
        parts = [investor]
        if shares:
            parts.append(f"{shares:,} shares")
        if value_usd:
            parts.append(f"~${value_usd / 1_000_000:.1f}M position")
        if pct_out:
            parts.append(f"{pct_out:.2f}% of float")
        return " — ".join(parts)

    def send_report(self, report: Dict | List[Dict], recipient: str | None = None) -> bool:
        """
        Send the generated report via email.

        Args:
            report: Either the full report dict from generate_report()
                    {"stocks": [...], "tips_india": [...], "tips_us": [...]}
                    or a plain list of stocks (backwards-compatible).
        """
        recipient = recipient or settings.report_email

        if isinstance(report, list):
            stocks = report
            tips_india: List[Dict] = []
            tips_us: List[Dict] = []
        else:
            stocks = report.get("stocks", [])
            tips_india = report.get("tips_india", [])
            tips_us = report.get("tips_us", [])

        try:
            logger.info(f"Sending report to {recipient}")
            generated_at = datetime.now()
            html = self.renderer.render(stocks, generated_at, tips_india, tips_us)
            logger.info(f"Rendered email HTML ({len(html)} bytes)")

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

            try:
                self._log_email_history(
                    recipient=recipient,
                    generated_at=generated_at,
                    status="sent" if success else "failed",
                )
            except Exception as e:
                logger.error(f"Failed to log email history: {type(e).__name__}: {str(e)}")

            return success

        except Exception as e:
            logger.error(f"Failed to send report: {type(e).__name__}: {str(e)}")
            try:
                self._log_email_history(
                    recipient=recipient,
                    generated_at=datetime.now(),
                    status="failed",
                )
            except Exception as log_error:
                logger.error(f"Failed to log email failure: {type(log_error).__name__}: {str(log_error)}")
            return False

    def _log_email_history(
        self,
        recipient: str,
        generated_at: datetime,
        status: str,
    ) -> None:
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
            logger.info(f"Logged email history: {recipient}, status={status}")
        except Exception as e:
            logger.error(f"Error logging email history: {type(e).__name__}: {str(e)}")
            conn.rollback()
            raise
        finally:
            conn.close()
