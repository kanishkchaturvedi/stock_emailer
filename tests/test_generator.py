"""Tests for report generator module."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from smart_money_tracker.reports.generator import ReportGenerator


class TestReportGeneratorInitialization:
    """Tests for ReportGenerator initialization."""

    def test_initialize_with_default_min_score(self):
        """Test initialization with default min_score from settings."""
        with patch(
            "smart_money_tracker.reports.generator.settings.min_score_for_email",
            60,
        ):
            generator = ReportGenerator()
            assert generator.min_score == 60

    def test_initialize_with_custom_min_score(self):
        """Test initialization with custom min_score."""
        generator = ReportGenerator(min_score=75)
        assert generator.min_score == 75

    def test_initialize_creates_scorer(self):
        """Test that initialization creates ScoringEngine instance."""
        generator = ReportGenerator()
        assert generator.scorer is not None

    def test_initialize_creates_analyzer(self):
        """Test that initialization creates AIAnalyzer instance."""
        generator = ReportGenerator()
        assert generator.analyzer is not None

    def test_initialize_creates_renderer(self):
        """Test that initialization creates EmailRenderer instance."""
        generator = ReportGenerator()
        assert generator.renderer is not None

    def test_initialize_creates_sender(self):
        """Test that initialization creates EmailSender instance."""
        generator = ReportGenerator()
        assert generator.sender is not None


class TestCollectSignals:
    """Tests for collect_signals method."""

    @patch(
        "smart_money_tracker.reports.generator.Fetcher13F"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherForm4"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherCongress"
    )
    def test_collect_signals_returns_dict(
        self, mock_congress, mock_form4, mock_13f
    ):
        """Test that collect_signals returns a dictionary."""
        # Setup mocks
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.return_value = []
        mock_13f.return_value = mock_13f_instance

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        assert isinstance(signals, dict)

    @patch(
        "smart_money_tracker.reports.generator.Fetcher13F"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherForm4"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherCongress"
    )
    def test_collect_signals_with_13f_holdings(
        self, mock_congress, mock_form4, mock_13f
    ):
        """Test signal collection with 13F holdings."""
        # Create mock holding and filing
        mock_holding = MagicMock()
        mock_holding.ticker = "AAPL"
        mock_holding.company_name = "Apple Inc"

        mock_filing = MagicMock()
        mock_filing.holdings = [mock_holding]

        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.return_value = [mock_filing]
        mock_13f.return_value = mock_13f_instance

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        assert "AAPL" in signals
        assert signals["AAPL"]["new_13f_position"] is True

    @patch(
        "smart_money_tracker.reports.generator.Fetcher13F"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherForm4"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherCongress"
    )
    def test_collect_signals_with_insider_purchases(
        self, mock_congress, mock_form4, mock_13f
    ):
        """Test signal collection with insider purchases."""
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.return_value = []
        mock_13f.return_value = mock_13f_instance

        # Create mock transactions
        mock_transaction = MagicMock()
        mock_transaction.ticker = "MSFT"
        mock_transaction.transaction_type = "purchase"

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = [
            mock_transaction,
            mock_transaction,
        ]
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        assert "MSFT" in signals
        assert signals["MSFT"]["insider_purchases"] == 2

    @patch(
        "smart_money_tracker.reports.generator.Fetcher13F"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherForm4"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherCongress"
    )
    def test_collect_signals_with_congressional_buys(
        self, mock_congress, mock_form4, mock_13f
    ):
        """Test signal collection with congressional buys."""
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.return_value = []
        mock_13f.return_value = mock_13f_instance

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        # Create mock trades
        mock_trade = MagicMock()
        mock_trade.ticker = "TSLA"
        mock_trade.buy_or_sell = "buy"

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = [mock_trade]
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        assert "TSLA" in signals
        assert signals["TSLA"]["congressional_buys"] == 1

    @patch(
        "smart_money_tracker.reports.generator.Fetcher13F"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherForm4"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherCongress"
    )
    def test_collect_signals_ignores_congressional_sells(
        self, mock_congress, mock_form4, mock_13f
    ):
        """Test that congressional sells are ignored."""
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.return_value = []
        mock_13f.return_value = mock_13f_instance

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        # Create mock sell trade
        mock_trade = MagicMock()
        mock_trade.ticker = "GOOG"
        mock_trade.buy_or_sell = "sell"

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = [mock_trade]
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        assert "GOOG" not in signals

    @patch(
        "smart_money_tracker.reports.generator.Fetcher13F"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherForm4"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherCongress"
    )
    def test_collect_signals_handles_13f_failure(
        self, mock_congress, mock_form4, mock_13f
    ):
        """Test graceful handling of 13F fetcher failure."""
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.side_effect = Exception("13F API Error")
        mock_13f.return_value = mock_13f_instance

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        # Should return empty dict but not crash
        assert isinstance(signals, dict)

    @patch(
        "smart_money_tracker.reports.generator.Fetcher13F"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherForm4"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherCongress"
    )
    def test_collect_signals_handles_form4_failure(
        self, mock_congress, mock_form4, mock_13f
    ):
        """Test graceful handling of Form 4 fetcher failure."""
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.return_value = []
        mock_13f.return_value = mock_13f_instance

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.side_effect = Exception("Form 4 API Error")
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        # Should return empty dict but not crash
        assert isinstance(signals, dict)

    @patch(
        "smart_money_tracker.reports.generator.Fetcher13F"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherForm4"
    )
    @patch(
        "smart_money_tracker.reports.generator.FetcherCongress"
    )
    def test_collect_signals_handles_congress_failure(
        self, mock_congress, mock_form4, mock_13f
    ):
        """Test graceful handling of congressional fetcher failure."""
        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.return_value = []
        mock_13f.return_value = mock_13f_instance

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.side_effect = Exception(
            "Congress API Error"
        )
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator()
        signals = generator.collect_signals()

        # Should return empty dict but not crash
        assert isinstance(signals, dict)


class TestGenerateReport:
    """Tests for generate_report method."""

    @patch("smart_money_tracker.reports.generator.ReportGenerator.collect_signals")
    def test_generate_report_returns_list(self, mock_collect):
        """Test that generate_report returns a list."""
        mock_collect.return_value = {}

        generator = ReportGenerator()
        report = generator.generate_report()

        assert isinstance(report, list)

    @patch("smart_money_tracker.reports.generator.ReportGenerator.collect_signals")
    def test_generate_report_empty_signals_returns_empty_list(
        self, mock_collect
    ):
        """Test that empty signals result in empty report."""
        mock_collect.return_value = {}

        generator = ReportGenerator()
        report = generator.generate_report()

        assert report == []

    @patch("smart_money_tracker.reports.generator.ReportGenerator.collect_signals")
    def test_generate_report_filters_by_min_score(self, mock_collect):
        """Test that generate_report filters by min_score."""
        mock_collect.return_value = {
            "AAPL": {
                "new_13f_position": True,
                "position_increase_pct": 60,
                "insider_purchases": 0,
                "congressional_buys": 0,
            },  # Score: 40 + 35 = 75 (new position + pos increase >50%)
            "MSFT": {
                "new_13f_position": False,
                "position_increase_pct": 0,
                "insider_purchases": 0,
                "congressional_buys": 0,
            },  # Score: 0
        }

        generator = ReportGenerator(min_score=50)
        report = generator.generate_report()

        # Only AAPL should be included
        assert len(report) == 1
        assert report[0]["ticker"] == "AAPL"

    @patch("smart_money_tracker.reports.generator.ReportGenerator.collect_signals")
    def test_generate_report_sorts_by_score_descending(self, mock_collect):
        """Test that report is sorted by score descending."""
        mock_collect.return_value = {
            "AAPL": {
                "new_13f_position": True,
                "position_increase_pct": 0,
                "insider_purchases": 0,
                "congressional_buys": 0,
            },  # Score: 40
            "MSFT": {
                "new_13f_position": True,
                "position_increase_pct": 60,
                "insider_purchases": 0,
                "congressional_buys": 0,
            },  # Score: 40 + 35 = 75
        }

        generator = ReportGenerator(min_score=30)
        report = generator.generate_report()

        assert len(report) == 2
        assert report[0]["ticker"] == "MSFT"
        assert report[0]["score"] == 75
        assert report[1]["ticker"] == "AAPL"
        assert report[1]["score"] == 40

    @patch("smart_money_tracker.reports.generator.ReportGenerator.collect_signals")
    def test_generate_report_limits_to_10_stocks(self, mock_collect):
        """Test that report is limited to 10 stocks."""
        signals = {}
        for i in range(15):
            ticker = f"TICK{i:02d}"
            signals[ticker] = {
                "new_13f_position": True,
                "position_increase_pct": 0,
                "insider_purchases": 0,
                "congressional_buys": 0,
            }

        mock_collect.return_value = signals

        generator = ReportGenerator(min_score=30)
        report = generator.generate_report()

        assert len(report) <= 10

    @patch("smart_money_tracker.reports.generator.ReportGenerator.collect_signals")
    def test_generate_report_includes_stock_structure(self, mock_collect):
        """Test that report includes required stock fields."""
        mock_collect.return_value = {
            "AAPL": {
                "new_13f_position": True,
                "position_increase_pct": 0,
                "insider_purchases": 0,
                "congressional_buys": 0,
            },
        }

        generator = ReportGenerator(min_score=30)
        report = generator.generate_report()

        assert len(report) == 1
        stock = report[0]
        assert "ticker" in stock
        assert "score" in stock
        assert "reasons" in stock
        assert "analysis" in stock
        assert "data" in stock

    @patch("smart_money_tracker.reports.generator.ReportGenerator.collect_signals")
    def test_generate_report_calls_analyzer(self, mock_collect):
        """Test that generate_report calls analyzer for each stock."""
        mock_collect.return_value = {
            "AAPL": {
                "new_13f_position": True,
                "position_increase_pct": 0,
                "insider_purchases": 0,
                "congressional_buys": 0,
            },
        }

        generator = ReportGenerator(min_score=30)
        generator.analyzer = MagicMock()
        generator.analyzer.analyze_ticker.return_value = {
            "bullish_thesis": "Bullish",
            "bearish_thesis": "Bearish",
            "key_risks": "Risks",
        }

        report = generator.generate_report()

        generator.analyzer.analyze_ticker.assert_called_once()
        assert report[0]["analysis"] is not None

    @patch("smart_money_tracker.reports.generator.ReportGenerator.collect_signals")
    def test_generate_report_handles_analyzer_failure(self, mock_collect):
        """Test that analyzer failure is handled gracefully."""
        mock_collect.return_value = {
            "AAPL": {
                "new_13f_position": True,
                "position_increase_pct": 0,
                "insider_purchases": 0,
                "congressional_buys": 0,
            },
        }

        generator = ReportGenerator(min_score=30)
        generator.analyzer = MagicMock()
        generator.analyzer.analyze_ticker.side_effect = Exception(
            "Analysis failed"
        )

        report = generator.generate_report()

        assert len(report) == 1
        assert report[0]["analysis"] is None


class TestSendReport:
    """Tests for send_report method."""

    @patch("smart_money_tracker.reports.generator.settings.report_email", "test@example.com")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_send_report_calls_renderer(self, mock_log, ):
        """Test that send_report calls renderer."""
        generator = ReportGenerator()
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.return_value = True

        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["New position"],
                "analysis": {
                    "bullish_thesis": "Bullish",
                    "bearish_thesis": "Bearish",
                    "key_risks": "Risks",
                },
            }
        ]

        generator.send_report(stocks)

        generator.renderer.render.assert_called_once()

    @patch("smart_money_tracker.reports.generator.settings.report_email", "test@example.com")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_send_report_calls_sender(self, mock_log):
        """Test that send_report calls sender."""
        generator = ReportGenerator()
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.return_value = True

        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["New position"],
                "analysis": {
                    "bullish_thesis": "Bullish",
                    "bearish_thesis": "Bearish",
                    "key_risks": "Risks",
                },
            }
        ]

        generator.send_report(stocks)

        generator.sender.send.assert_called_once()

    @patch("smart_money_tracker.reports.generator.settings.report_email", "test@example.com")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_send_report_returns_true_on_success(self, mock_log):
        """Test that send_report returns True on success."""
        generator = ReportGenerator()
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.return_value = True

        stocks = []

        result = generator.send_report(stocks)

        assert result is True

    @patch("smart_money_tracker.reports.generator.settings.report_email", "test@example.com")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_send_report_returns_false_on_failure(self, mock_log):
        """Test that send_report returns False on failure."""
        generator = ReportGenerator()
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.side_effect = Exception("Send failed")

        stocks = []

        result = generator.send_report(stocks)

        assert result is False

    @patch("smart_money_tracker.reports.generator.settings.report_email", "test@example.com")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_send_report_uses_default_recipient(self, mock_log):
        """Test that send_report uses default recipient from settings."""
        generator = ReportGenerator()
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.return_value = True

        stocks = []

        generator.send_report(stocks)

        call_args = generator.sender.send.call_args
        assert call_args.kwargs["to_email"] == "test@example.com"

    @patch("smart_money_tracker.reports.generator.settings.report_email", "test@example.com")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_send_report_uses_custom_recipient(self, mock_log):
        """Test that send_report uses custom recipient when provided."""
        generator = ReportGenerator()
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.return_value = True

        stocks = []

        generator.send_report(stocks, recipient="custom@example.com")

        call_args = generator.sender.send.call_args
        assert call_args.kwargs["to_email"] == "custom@example.com"

    @patch("smart_money_tracker.reports.generator.settings.report_email", "test@example.com")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_send_report_logs_to_database(self, mock_log):
        """Test that send_report logs email history."""
        generator = ReportGenerator()
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.return_value = True

        stocks = []

        generator.send_report(stocks, recipient="test@example.com")

        mock_log.assert_called_once()
        call_args = mock_log.call_args
        assert call_args.kwargs["recipient"] == "test@example.com"
        assert call_args.kwargs["status"] == "sent"

    @patch("smart_money_tracker.reports.generator.settings.report_email", "test@example.com")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_send_report_logs_failure_to_database(self, mock_log):
        """Test that send_report logs failures to database."""
        generator = ReportGenerator()
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.side_effect = Exception("Send failed")

        stocks = []

        generator.send_report(stocks)

        mock_log.assert_called_once()
        call_args = mock_log.call_args
        assert call_args.kwargs["status"] == "failed"


class TestLogEmailHistory:
    """Tests for _log_email_history method."""

    @patch("smart_money_tracker.reports.generator.db_client")
    def test_log_email_history_success(self, mock_db):
        """Test logging successful email send."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        generator = ReportGenerator()
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        generator._log_email_history(
            recipient="test@example.com",
            generated_at=generated_at,
            status="sent",
        )

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("smart_money_tracker.reports.generator.db_client")
    def test_log_email_history_failure(self, mock_db):
        """Test logging failed email send."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        generator = ReportGenerator()
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        generator._log_email_history(
            recipient="test@example.com",
            generated_at=generated_at,
            status="failed",
        )

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("smart_money_tracker.reports.generator.db_client")
    def test_log_email_history_error_handling(self, mock_db):
        """Test that database errors in logging are handled."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB Error")
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        generator = ReportGenerator()
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        with pytest.raises(Exception):
            generator._log_email_history(
                recipient="test@example.com",
                generated_at=generated_at,
                status="sent",
            )

        mock_conn.rollback.assert_called_once()


class TestIntegration:
    """Integration tests for the full workflow."""

    @patch("smart_money_tracker.reports.generator.Fetcher13F")
    @patch("smart_money_tracker.reports.generator.FetcherForm4")
    @patch("smart_money_tracker.reports.generator.FetcherCongress")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_full_workflow_from_signals_to_report(
        self, mock_log, mock_congress, mock_form4, mock_13f
    ):
        """Test complete workflow from signal collection to report generation."""
        # Setup mocks
        mock_holding = MagicMock()
        mock_holding.ticker = "AAPL"

        mock_filing = MagicMock()
        mock_filing.holdings = [mock_holding]

        mock_13f_instance = MagicMock()
        mock_13f_instance.fetch.return_value = [mock_filing]
        mock_13f.return_value = mock_13f_instance

        mock_form4_instance = MagicMock()
        mock_form4_instance.fetch.return_value = []
        mock_form4.return_value = mock_form4_instance

        mock_congress_instance = MagicMock()
        mock_congress_instance.fetch.return_value = []
        mock_congress.return_value = mock_congress_instance

        generator = ReportGenerator(min_score=30)
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.return_value = True

        # Generate report
        report = generator.generate_report()

        assert len(report) > 0
        assert report[0]["ticker"] == "AAPL"

        # Send report
        success = generator.send_report(report)

        assert success is True
        generator.sender.send.assert_called_once()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("smart_money_tracker.reports.generator.ReportGenerator.collect_signals")
    def test_generate_report_with_mixed_score_threshold(self, mock_collect):
        """Test filtering with various score thresholds."""
        mock_collect.return_value = {
            "AAPL": {
                "new_13f_position": True,
                "position_increase_pct": 60,
                "insider_purchases": 1,
                "congressional_buys": 0,
            },  # Score: 40 + 35 + 30 = 105
            "MSFT": {
                "new_13f_position": False,
                "position_increase_pct": 0,
                "insider_purchases": 0,
                "congressional_buys": 0,
            },  # Score: 0
            "GOOG": {
                "new_13f_position": False,
                "position_increase_pct": 30,
                "insider_purchases": 0,
                "congressional_buys": 0,
            },  # Score: 20
        }

        generator = ReportGenerator(min_score=50)
        report = generator.generate_report()

        # Only AAPL should be included
        assert len(report) == 1
        assert report[0]["ticker"] == "AAPL"

    @patch("smart_money_tracker.reports.generator.settings.report_email", "test@example.com")
    @patch("smart_money_tracker.reports.generator.ReportGenerator._log_email_history")
    def test_send_report_with_empty_stocks_list(self, mock_log):
        """Test sending report with no stocks."""
        generator = ReportGenerator()
        generator.renderer = MagicMock()
        generator.renderer.render.return_value = "<html></html>"
        generator.sender = MagicMock()
        generator.sender.send.return_value = True

        success = generator.send_report([])

        assert success is True
        generator.sender.send.assert_called_once()
