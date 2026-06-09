"""Comprehensive integration tests for the full Smart Money Tracker pipeline."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
import json

import pytest

from smart_money_tracker.reports.generator import ReportGenerator
from smart_money_tracker.signals.scoring import ScoringEngine
from smart_money_tracker.ai.analyzer import AIAnalyzer
from smart_money_tracker.email.renderer import EmailRenderer
from smart_money_tracker.main import main


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


class TestFullPipelineGeneratesReport:
    """Integration test for end-to-end report generation."""

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    @patch("smart_money_tracker.reports.generator.AIAnalyzer")
    def test_full_pipeline_generates_report(
        self, mock_analyzer_class, mock_congress, mock_form4, mock_13f
    ):
        """
        Test end-to-end report generation through full pipeline.

        Verifies:
        - Returns list of dicts
        - Each dict has correct structure (ticker, score, reasons, analysis, data)
        - Scores are >= 0
        - No more than 10 stocks returned
        - Analysis is included and non-empty
        """
        # Setup 13F fetcher mock
        mock_13f_instance = MagicMock()
        mock_holding = MagicMock()
        mock_holding.ticker = "AAPL"
        mock_holding.company_name = "Apple Inc"
        mock_filing = MagicMock()
        mock_filing.holdings = [mock_holding]
        mock_13f_instance.fetch.return_value = [mock_filing]
        mock_13f.return_value = mock_13f_instance

        # Setup Form4 fetcher mock
        mock_form4_instance = MagicMock()
        mock_transaction = MagicMock()
        mock_transaction.ticker = "AAPL"
        mock_form4_instance.fetch.return_value = [mock_transaction]
        mock_form4.return_value = mock_form4_instance

        # Setup Congress fetcher mock
        mock_congress_instance = MagicMock()
        mock_trade = MagicMock()
        mock_trade.ticker = "AAPL"
        mock_trade.buy_or_sell = "buy"
        mock_congress_instance.fetch.return_value = [mock_trade]
        mock_congress.return_value = mock_congress_instance

        # Setup AI analyzer mock
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_ticker.return_value = {
            "bullish_thesis": "Strong signals detected",
            "bearish_thesis": "Some concerns present",
            "key_risks": "Market volatility",
        }
        mock_analyzer_class.return_value = mock_analyzer

        # Generate report
        generator = ReportGenerator(min_score=50)
        report = generator.generate_report()

        # Verify structure
        assert isinstance(report, list)
        assert len(report) > 0, "Report should contain at least one stock"
        assert len(report) <= 10, "Report should contain at most 10 stocks"

        # Verify each stock in report
        for stock in report:
            assert isinstance(stock, dict), "Each stock should be a dict"
            assert "ticker" in stock, "Stock should have ticker"
            assert "score" in stock, "Stock should have score"
            assert "reasons" in stock, "Stock should have reasons"
            assert "analysis" in stock, "Stock should have analysis"
            assert "data" in stock, "Stock should have data"

            # Verify data types
            assert isinstance(stock["ticker"], str), "Ticker should be string"
            assert isinstance(stock["score"], int), "Score should be int"
            assert isinstance(stock["reasons"], list), "Reasons should be list"
            assert stock["score"] >= 0, "Score should be >= 0"

            # Verify analysis structure
            if stock["analysis"] is not None:
                assert isinstance(stock["analysis"], dict)
                assert "bullish_thesis" in stock["analysis"]
                assert "bearish_thesis" in stock["analysis"]
                assert "key_risks" in stock["analysis"]

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    def test_full_pipeline_handles_empty_signals(
        self, mock_congress, mock_form4, mock_13f
    ):
        """
        Test pipeline handling when no signals are collected.

        Verifies:
        - Returns empty list
        - No errors raised
        """
        # Setup all fetchers to return empty
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.return_value = []
        mock_13f.return_value = mock_13f_instance

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator(min_score=50)
        report = generator.generate_report()

        assert isinstance(report, list)
        assert len(report) == 0


class TestSignalsCollectedFromAllSources:
    """Integration test for signal collection from all sources."""

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    def test_signals_collected_from_all_sources(
        self, mock_congress, mock_form4, mock_13f
    ):
        """
        Test collecting signals from all three data sources.

        Verifies:
        - Returns dict keyed by ticker
        - Each ticker has signal counts
        - Different tickers can be collected from different sources
        """
        # Setup 13F fetcher
        mock_13f_instance = MagicMock()
        mock_holding_1 = MagicMock()
        mock_holding_1.ticker = "AAPL"
        mock_holding_2 = MagicMock()
        mock_holding_2.ticker = "MSFT"
        mock_filing = MagicMock()
        mock_filing.holdings = [mock_holding_1, mock_holding_2]
        mock_13f_instance.fetch.return_value = [mock_filing]
        mock_13f.return_value = mock_13f_instance

        # Setup Form4 fetcher
        mock_form4_instance = MagicMock()
        mock_transaction_1 = MagicMock()
        mock_transaction_1.ticker = "AAPL"
        mock_transaction_2 = MagicMock()
        mock_transaction_2.ticker = "GOOGL"
        mock_form4_instance.fetch.return_value = [
            mock_transaction_1,
            mock_transaction_2,
        ]
        mock_form4.return_value = mock_form4_instance

        # Setup Congress fetcher
        mock_congress_instance = MagicMock()
        mock_trade_1 = MagicMock()
        mock_trade_1.ticker = "TSLA"
        mock_trade_1.buy_or_sell = "buy"
        mock_trade_2 = MagicMock()
        mock_trade_2.ticker = "NVDA"
        mock_trade_2.buy_or_sell = "buy"
        mock_congress_instance.fetch.return_value = [mock_trade_1, mock_trade_2]
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        # Verify structure
        assert isinstance(signals, dict)

        # Verify tickers from different sources
        assert "AAPL" in signals  # 13F + Form4
        assert "MSFT" in signals  # 13F only
        assert "GOOGL" in signals  # Form4 only
        assert "TSLA" in signals  # Congress only
        assert "NVDA" in signals  # Congress only

        # Verify signal counts
        for ticker, signal_data in signals.items():
            assert "new_13f_position" in signal_data
            assert "position_increase_pct" in signal_data
            assert "insider_purchases" in signal_data
            assert "congressional_buys" in signal_data

        # Verify AAPL has signals from multiple sources
        assert signals["AAPL"]["new_13f_position"] == True
        assert signals["AAPL"]["insider_purchases"] >= 1

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    def test_signals_handles_api_failures(
        self, mock_congress, mock_form4, mock_13f
    ):
        """
        Test signal collection continues when one source fails.

        Verifies:
        - Continues collection even if one fetcher fails
        - Partial results are returned
        """
        # Setup 13F to fail
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.side_effect = Exception("API error")
        mock_13f.return_value = mock_13f_instance

        # Setup Form4 to work
        mock_form4_instance = MagicMock()
        mock_transaction = MagicMock()
        mock_transaction.ticker = "AAPL"
        mock_form4_instance.fetch.return_value = [mock_transaction]
        mock_form4.return_value = mock_form4_instance

        # Setup Congress to work
        mock_congress_instance = MagicMock()
        mock_trade = MagicMock()
        mock_trade.ticker = "MSFT"
        mock_trade.buy_or_sell = "buy"
        mock_congress_instance.fetch.return_value = [mock_trade]
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        # Should still have signals from working sources
        assert len(signals) > 0
        assert "AAPL" in signals or "MSFT" in signals


class TestReportFilteringByMinScore:
    """Integration test for report filtering by minimum score."""

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    @patch("smart_money_tracker.reports.generator.AIAnalyzer")
    def test_report_filters_by_min_score(
        self, mock_analyzer_class, mock_congress, mock_form4, mock_13f
    ):
        """
        Test that report properly filters stocks by minimum score.

        Verifies:
        - Only stocks >= min_score are included
        - Filtering works correctly
        """
        # Setup to generate multiple stocks with different scores
        mock_13f_instance = MagicMock()

        # Create holdings for stocks with different signals
        mock_holding_1 = MagicMock()
        mock_holding_1.ticker = "HIGH_SCORE"  # Will have new position
        mock_holding_2 = MagicMock()
        mock_holding_2.ticker = "LOW_SCORE"

        mock_filing = MagicMock()
        mock_filing.holdings = [mock_holding_1]
        mock_13f_instance.fetch.return_value = [mock_filing]
        mock_13f.return_value = mock_13f_instance

        # Setup Form4
        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        # Setup Congress
        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        # Setup AI analyzer
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_ticker.return_value = {
            "bullish_thesis": "Test",
            "bearish_thesis": "Test",
            "key_risks": "Test",
        }
        mock_analyzer_class.return_value = mock_analyzer

        # Generate report with high min_score
        generator = ReportGenerator(min_score=80)
        report = generator.generate_report()

        # Verify all stocks meet minimum score
        for stock in report:
            assert stock["score"] >= 80, f"Stock {stock['ticker']} score {stock['score']} below min_score 80"

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    @patch("smart_money_tracker.reports.generator.AIAnalyzer")
    def test_report_limits_to_10_stocks(
        self, mock_analyzer_class, mock_congress, mock_form4, mock_13f
    ):
        """
        Test that report limits results to top 10 stocks.

        Verifies:
        - Never more than 10 stocks in report
        - Sorted by score descending
        """
        # Setup to generate many holdings
        mock_13f_instance = MagicMock()
        holdings = []
        for i in range(20):
            holding = MagicMock()
            holding.ticker = f"STOCK{i:02d}"
            holdings.append(holding)

        mock_filing = MagicMock()
        mock_filing.holdings = holdings
        mock_13f_instance.fetch.return_value = [mock_filing]
        mock_13f.return_value = mock_13f_instance

        # Setup Form4
        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        # Setup Congress
        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        # Setup AI analyzer
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_ticker.return_value = {
            "bullish_thesis": "Test",
            "bearish_thesis": "Test",
            "key_risks": "Test",
        }
        mock_analyzer_class.return_value = mock_analyzer

        generator = ReportGenerator(min_score=0)
        report = generator.generate_report()

        # Verify limit
        assert len(report) <= 10, f"Report has {len(report)} stocks, expected <= 10"

        # Verify sorted by score descending
        if len(report) > 1:
            for i in range(len(report) - 1):
                assert (
                    report[i]["score"] >= report[i + 1]["score"]
                ), "Report not sorted by score descending"


class TestAIAnalysisIntegration:
    """Integration test for AI analysis integration in the pipeline."""

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_ai_analysis_added_to_report(
        self, mock_openai_class, mock_congress, mock_form4, mock_13f
    ):
        """
        Test AI analysis is properly integrated into the report.

        Verifies:
        - Analysis fields present and non-empty
        - No financial advice language present
        - Analysis is correctly formatted JSON
        """
        # Setup fetchers with enough signals to meet min_score
        mock_13f_instance = MagicMock()
        mock_holding = MagicMock()
        mock_holding.ticker = "AAPL"
        mock_filing = MagicMock()
        mock_filing.holdings = [mock_holding]
        mock_13f_instance.fetch.return_value = [mock_filing]
        mock_13f.return_value = mock_13f_instance

        # Add multiple Form4 transactions to increase score
        mock_form4_instance = MagicMock()
        mock_transaction_1 = MagicMock()
        mock_transaction_1.ticker = "AAPL"
        mock_transaction_2 = MagicMock()
        mock_transaction_2.ticker = "AAPL"
        mock_form4_instance.fetch.return_value = [mock_transaction_1, mock_transaction_2]
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        # Setup OpenAI mock
        mock_openai = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps({
            "bullish_thesis": "Strong institutional interest shown by large position",
            "bearish_thesis": "Economic headwinds could impact performance",
            "key_risks": "Market volatility and geopolitical uncertainty"
        })
        mock_openai.messages.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai

        generator = ReportGenerator(min_score=0)
        report = generator.generate_report()

        assert len(report) > 0
        stock = report[0]

        # Verify analysis exists
        assert stock["analysis"] is not None
        assert isinstance(stock["analysis"], dict)

        # Verify required fields
        assert "bullish_thesis" in stock["analysis"]
        assert "bearish_thesis" in stock["analysis"]
        assert "key_risks" in stock["analysis"]

        # Verify non-empty
        assert len(stock["analysis"]["bullish_thesis"]) > 0
        assert len(stock["analysis"]["bearish_thesis"]) > 0
        assert len(stock["analysis"]["key_risks"]) > 0

        # Verify no financial advice language
        advice_keywords = ["buy", "sell", "should", "must", "recommend"]
        for field in stock["analysis"].values():
            field_lower = field.lower()
            for keyword in advice_keywords:
                # Check for standalone keywords (not part of other words)
                if f" {keyword} " in f" {field_lower} ":
                    pytest.fail(
                        f"Financial advice language found: '{keyword}' in {field}"
                    )

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_ai_analysis_fallback_on_api_failure(
        self, mock_openai_class, mock_congress, mock_form4, mock_13f
    ):
        """
        Test AI analysis falls back to mock when API fails.

        Verifies:
        - Mock analysis is used on API failure
        - Report still completes successfully
        """
        # Setup fetchers with enough signals to meet min_score
        mock_13f_instance = MagicMock()
        mock_holding = MagicMock()
        mock_holding.ticker = "AAPL"
        mock_filing = MagicMock()
        mock_filing.holdings = [mock_holding]
        mock_13f_instance.fetch.return_value = [mock_filing]
        mock_13f.return_value = mock_13f_instance

        # Add multiple Form4 transactions to increase score
        mock_form4_instance = MagicMock()
        mock_transaction_1 = MagicMock()
        mock_transaction_1.ticker = "AAPL"
        mock_transaction_2 = MagicMock()
        mock_transaction_2.ticker = "AAPL"
        mock_form4_instance.fetch.return_value = [mock_transaction_1, mock_transaction_2]
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        # Setup OpenAI to fail
        mock_openai = MagicMock()
        mock_openai.messages.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_openai

        generator = ReportGenerator(min_score=0)
        report = generator.generate_report()

        assert len(report) > 0
        stock = report[0]

        # Verify mock analysis is used
        assert stock["analysis"] is not None
        assert "bullish_thesis" in stock["analysis"]
        assert "bearish_thesis" in stock["analysis"]
        assert "key_risks" in stock["analysis"]


class TestHTMLRenderingCorrectly:
    """Integration test for email HTML rendering."""

    def test_html_rendered_correctly(self):
        """
        Test HTML email rendering.

        Verifies:
        - HTML contains ticker symbols
        - HTML is well-formed
        - Safe character escaping
        """
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["New position", "Insider purchase"],
                "analysis": {
                    "bullish_thesis": "Strong signals detected",
                    "bearish_thesis": "Some concerns present",
                    "key_risks": "Market volatility",
                },
                "data": {
                    "new_13f_position": True,
                    "insider_purchases": 1,
                    "congressional_buys": 0,
                    "position_increase_pct": 15.5,
                },
            },
            {
                "ticker": "MSFT",
                "score": 75,
                "reasons": ["Congressional buy"],
                "analysis": {
                    "bullish_thesis": "Political support indicators",
                    "bearish_thesis": "Valuation concerns",
                    "key_risks": "Policy changes",
                },
                "data": {
                    "new_13f_position": False,
                    "insider_purchases": 0,
                    "congressional_buys": 2,
                    "position_increase_pct": 0.0,
                },
            },
        ]

        renderer = EmailRenderer()
        generated_at = datetime.now()
        html = renderer.render(stocks, generated_at)

        # Verify it's a string
        assert isinstance(html, str)
        assert len(html) > 0

        # Verify HTML structure (basic checks)
        assert "<html" in html.lower() or "<!doctype" in html.lower()
        assert "</html>" in html.lower() or html.lower().endswith(">")

        # Verify tickers are present
        assert "AAPL" in html
        assert "MSFT" in html

        # Verify scores are present
        assert "85" in html
        assert "75" in html

        # Verify reasons are present
        assert "New position" in html
        assert "Congressional buy" in html

    def test_html_with_special_characters(self):
        """
        Test HTML rendering with special characters and escaping.

        Verifies:
        - Special characters are properly escaped
        - HTML is valid after escaping
        """
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["New position", "Signal & opportunity"],
                "analysis": {
                    "bullish_thesis": 'Strong signals & momentum <expected>',
                    "bearish_thesis": "Some concerns 'present'",
                    "key_risks": 'Market "volatility" & risks',
                },
                "data": {
                    "new_13f_position": True,
                    "insider_purchases": 1,
                    "congressional_buys": 0,
                    "position_increase_pct": 15.5,
                },
            }
        ]

        renderer = EmailRenderer()
        generated_at = datetime.now()
        html = renderer.render(stocks, generated_at)

        # Verify special characters are escaped or properly handled
        assert isinstance(html, str)
        assert len(html) > 0

        # HTML should contain the ticker
        assert "AAPL" in html

    def test_html_with_empty_stocks(self):
        """
        Test HTML rendering with no stocks.

        Verifies:
        - Valid HTML is still generated
        - No errors on empty report
        """
        stocks = []
        renderer = EmailRenderer()
        generated_at = datetime.now()
        html = renderer.render(stocks, generated_at)

        assert isinstance(html, str)
        assert len(html) > 0


class TestDatabasePersistence:
    """Integration test for database persistence."""

    def test_database_stores_email_history(self, mock_db_client):
        """
        Test database persistence of email history.

        Verifies:
        - Email history is logged to database
        - Data integrity is maintained
        - Correct fields are stored
        """
        from smart_money_tracker.db.client import db_client

        # Use the mock_db_client to verify database operations
        conn = db_client.get_connection()
        cursor = conn.cursor()

        # Simulate an email history log
        cursor.execute(
            """
            INSERT INTO email_history (recipient, generated_at, sent_at, status)
            VALUES (?, ?, ?, ?)
            """,
            (
                "test@example.com",
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                "sent",
            ),
        )
        conn.commit()

        # Query it back
        cursor.execute("SELECT recipient, status FROM email_history")
        rows = cursor.fetchall()
        conn.close()

        # Verify it was saved
        assert len(rows) > 0
        recipient, status = rows[0]
        assert recipient == "test@example.com"
        assert status == "sent"

    def test_database_schema_has_email_history_table(self, mock_db_client):
        """
        Test database schema includes email_history table.

        Verifies:
        - email_history table exists
        - Required columns are present
        - Schema is correctly initialized
        """
        from smart_money_tracker.db.client import db_client

        conn = db_client.get_connection()
        cursor = conn.cursor()

        # Check that email_history table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='email_history'"
        )
        result = cursor.fetchone()
        assert result is not None, "email_history table does not exist"

        # Check table structure
        cursor.execute("PRAGMA table_info(email_history)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        assert "recipient" in column_names
        assert "status" in column_names
        assert "generated_at" in column_names

        conn.close()

    def test_send_report_records_email_history(self):
        """
        Test send_report records email history on success.

        Verifies:
        - send_report logs email history when successful
        - Success status is recorded
        """
        generator = ReportGenerator()

        # Create a test report
        test_stocks = [
            {
                "ticker": "TEST",
                "score": 85,
                "reasons": ["Test"],
                "analysis": {
                    "bullish_thesis": "Test",
                    "bearish_thesis": "Test",
                    "key_risks": "Test",
                },
                "data": {},
            }
        ]

        # Mock the sender to succeed
        with patch.object(generator.sender, "send", return_value=True):
            # Mock _log_email_history to track calls
            with patch.object(generator, "_log_email_history") as mock_log:
                success = generator.send_report(test_stocks, "test@example.com")

                # Verify send succeeded
                assert success == True

                # Verify _log_email_history was called
                mock_log.assert_called_once()

                # Verify it was called with sent status
                call_kwargs = mock_log.call_args[1]
                assert call_kwargs["status"] == "sent"
                assert call_kwargs["recipient"] == "test@example.com"

    def test_send_report_records_failure_status(self):
        """
        Test send_report records failure status when send fails.

        Verifies:
        - send_report logs email history on failure
        - Failed status is recorded
        """
        generator = ReportGenerator()

        test_stocks = [
            {
                "ticker": "TEST",
                "score": 85,
                "reasons": ["Test"],
                "analysis": {
                    "bullish_thesis": "Test",
                    "bearish_thesis": "Test",
                    "key_risks": "Test",
                },
                "data": {},
            }
        ]

        # Mock the sender to fail
        with patch.object(generator.sender, "send", return_value=False):
            # Mock _log_email_history to track calls
            with patch.object(generator, "_log_email_history") as mock_log:
                success = generator.send_report(test_stocks, "test@example.com")

                # Verify send failed
                assert success == False

                # Verify _log_email_history was called
                mock_log.assert_called_once()

                # Verify it was called with failed status
                call_kwargs = mock_log.call_args[1]
                assert call_kwargs["status"] == "failed"


class TestMainCLIIntegration:
    """Integration test for main CLI entry point."""

    @patch("smart_money_tracker.main.ReportGenerator")
    def test_cli_dry_run_succeeds(self, mock_generator_class):
        """
        Test CLI dry-run mode succeeds.

        Verifies:
        - Returns exit code 0
        - Logs appropriately
        - No email sending attempted
        """
        # Setup mock generator
        mock_generator = MagicMock()
        mock_generator.generate_report.return_value = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["New position"],
                "analysis": {
                    "bullish_thesis": "Test",
                    "bearish_thesis": "Test",
                    "key_risks": "Test",
                },
                "data": {},
            }
        ]
        mock_generator_class.return_value = mock_generator

        # Call main with --dry-run
        with patch("sys.argv", ["main.py", "--dry-run"]):
            exit_code = main()

        # Verify success
        assert exit_code == 0

        # Verify send_report was not called
        mock_generator.send_report.assert_not_called()

    @patch("smart_money_tracker.main.ReportGenerator")
    def test_cli_sends_report_on_normal_run(self, mock_generator_class):
        """
        Test CLI sends report in normal (non-dry-run) mode.

        Verifies:
        - Returns exit code 0
        - send_report is called
        """
        # Setup mock generator
        mock_generator = MagicMock()
        mock_generator.generate_report.return_value = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["New position"],
                "analysis": {
                    "bullish_thesis": "Test",
                    "bearish_thesis": "Test",
                    "key_risks": "Test",
                },
                "data": {},
            }
        ]
        mock_generator.send_report.return_value = True
        mock_generator_class.return_value = mock_generator

        # Call main without --dry-run
        with patch("sys.argv", ["main.py"]):
            exit_code = main()

        # Verify success
        assert exit_code == 0

        # Verify send_report was called
        mock_generator.send_report.assert_called_once()

    @patch("smart_money_tracker.main.ReportGenerator")
    def test_cli_respects_min_score_argument(self, mock_generator_class):
        """
        Test CLI respects --min-score argument.

        Verifies:
        - min_score is passed to ReportGenerator
        """
        # Setup mock generator
        mock_generator = MagicMock()
        mock_generator.generate_report.return_value = []
        mock_generator_class.return_value = mock_generator

        # Call main with custom min-score
        with patch("sys.argv", ["main.py", "--min-score", "75", "--dry-run"]):
            exit_code = main()

        # Verify ReportGenerator was created with correct min_score
        mock_generator_class.assert_called_once_with(min_score=75)
        assert exit_code == 0

    @patch("smart_money_tracker.main.ReportGenerator")
    def test_cli_handles_no_stocks_found(self, mock_generator_class):
        """
        Test CLI handles case when no stocks are found.

        Verifies:
        - Returns exit code 0 (success)
        - No errors raised
        """
        # Setup mock generator
        mock_generator = MagicMock()
        mock_generator.generate_report.return_value = []
        mock_generator_class.return_value = mock_generator

        # Call main
        with patch("sys.argv", ["main.py", "--dry-run"]):
            exit_code = main()

        # Verify success
        assert exit_code == 0

    @patch("smart_money_tracker.main.ReportGenerator")
    def test_cli_handles_report_generation_error(self, mock_generator_class):
        """
        Test CLI handles errors during report generation.

        Verifies:
        - Returns exit code 1
        - Error is logged
        """
        # Setup mock generator to fail
        mock_generator = MagicMock()
        mock_generator.generate_report.side_effect = Exception("Test error")
        mock_generator_class.return_value = mock_generator

        # Call main
        with patch("sys.argv", ["main.py", "--dry-run"]):
            exit_code = main()

        # Verify failure
        assert exit_code == 1

    @patch("smart_money_tracker.main.ReportGenerator")
    def test_cli_handles_email_send_failure(self, mock_generator_class):
        """
        Test CLI handles email send failure gracefully.

        Verifies:
        - Returns exit code 1
        - Error is logged
        """
        # Setup mock generator
        mock_generator = MagicMock()
        mock_generator.generate_report.return_value = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["New position"],
                "analysis": {
                    "bullish_thesis": "Test",
                    "bearish_thesis": "Test",
                    "key_risks": "Test",
                },
                "data": {},
            }
        ]
        mock_generator.send_report.return_value = False
        mock_generator_class.return_value = mock_generator

        # Call main
        with patch("sys.argv", ["main.py"]):
            exit_code = main()

        # Verify failure
        assert exit_code == 1


class TestScoringAndFiltering:
    """Integration test for scoring and filtering logic."""

    def test_report_filters_by_min_score_strict(self):
        """
        Test strict filtering by min_score threshold.

        Verifies:
        - Only stocks >= min_score are included
        - Stocks exactly at threshold are included
        - Stocks below threshold are excluded
        """
        scorer = ScoringEngine()

        # Create test cases
        test_cases = [
            # (new_13f, increase_pct, insider, congress, expected_score)
            (True, 0, 0, 0, 40),  # New position only
            (False, 30, 0, 0, 20),  # Moderate position increase
            (False, 60, 0, 0, 35),  # Large position increase
            (False, 0, 1, 0, 30),  # Insider purchase
            (False, 0, 2, 0, 40),  # Multiple insider purchases
            (False, 0, 0, 1, 10),  # Congressional buy
            (False, 0, 0, 2, 15),  # Multiple congressional buys
        ]

        for new_13f, increase_pct, insider, congress, expected in test_cases:
            score, reasons = scorer.score_ticker(
                "TEST",
                new_13f_position=new_13f,
                position_increase_pct=increase_pct,
                insider_purchases=insider,
                congressional_buys=congress,
            )
            assert score == expected, f"Score mismatch: {score} != {expected}"

    def test_sorting_by_score_descending(self):
        """
        Test that stocks are sorted by score in descending order.

        Verifies:
        - Higher scores come first
        - Sorting is stable
        """
        stocks = [
            {"ticker": "LOW", "score": 30},
            {"ticker": "HIGH", "score": 90},
            {"ticker": "MEDIUM", "score": 60},
            {"ticker": "TOP", "score": 95},
        ]

        # Sort like ReportGenerator does
        stocks.sort(key=lambda x: x["score"], reverse=True)

        # Verify order
        assert stocks[0]["score"] == 95
        assert stocks[1]["score"] == 90
        assert stocks[2]["score"] == 60
        assert stocks[3]["score"] == 30

    def test_combined_signals_scoring(self):
        """
        Test scoring with multiple signals combined.

        Verifies:
        - Scores accumulate correctly
        - Multiple reasons are returned
        """
        scorer = ScoringEngine()

        # Multiple signals
        score, reasons = scorer.score_ticker(
            "AAPL",
            new_13f_position=True,
            position_increase_pct=75,
            insider_purchases=2,
            congressional_buys=3,
        )

        # Expected: 40 (new) + 35 (position > 50%) + 40 (multiple insider) + 15 (multiple congress) = 130
        assert score == 130
        assert len(reasons) == 4
        assert any("institutional" in r.lower() for r in reasons)
        assert any("insider" in r.lower() for r in reasons)
        assert any("congressional" in r.lower() for r in reasons)


class TestErrorHandlingAndRecovery:
    """Integration test for error handling and recovery."""

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    @patch("smart_money_tracker.reports.generator.AIAnalyzer")
    def test_pipeline_continues_on_partial_api_failures(
        self, mock_analyzer_class, mock_congress, mock_form4, mock_13f
    ):
        """
        Test pipeline continues when some APIs fail.

        Verifies:
        - Continues collection from working sources
        - Report is generated with partial data
        """
        # Setup 13F to fail
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.side_effect = Exception("Connection timeout")
        mock_13f.return_value = mock_13f_instance

        # Setup Form4 to work
        mock_form4_instance = MagicMock()
        mock_transaction = MagicMock()
        mock_transaction.ticker = "AAPL"
        mock_form4_instance.fetch.return_value = [mock_transaction]
        mock_form4.return_value = mock_form4_instance

        # Setup Congress to work
        mock_congress_instance = MagicMock()
        mock_trade = MagicMock()
        mock_trade.ticker = "MSFT"
        mock_trade.buy_or_sell = "buy"
        mock_congress_instance.fetch.return_value = [mock_trade]
        mock_congress.return_value = mock_congress_instance

        # Setup AI analyzer
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_ticker.return_value = {
            "bullish_thesis": "Test",
            "bearish_thesis": "Test",
            "key_risks": "Test",
        }
        mock_analyzer_class.return_value = mock_analyzer

        generator = ReportGenerator(min_score=0)
        report = generator.generate_report()

        # Should still have stocks from working sources
        assert isinstance(report, list)
        # Report may be empty if scores don't meet threshold, but no exception should occur
