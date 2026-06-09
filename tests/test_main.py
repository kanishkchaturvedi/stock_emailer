"""Tests for main entry point CLI."""

from unittest.mock import MagicMock, patch
import pytest
from smart_money_tracker.main import main


class TestMainEntryPoint:
    """Tests for main() function."""

    def test_main_with_dry_run(self):
        """Test main with --dry-run flag."""
        with patch("sys.argv", ["main.py", "--dry-run"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = [
                    {
                        "ticker": "AAPL",
                        "score": 85,
                        "reasons": ["New position", "Insider buying"],
                    }
                ]

                result = main()

                # Should not call send_report in dry-run mode
                mock_instance.send_report.assert_not_called()
                assert result == 0

    def test_main_with_min_score(self):
        """Test main with --min-score argument."""
        with patch("sys.argv", ["main.py", "--min-score", "75", "--dry-run"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = []

                result = main()

                # Check that min_score was passed
                mock_generator.assert_called_with(min_score=75)
                assert result == 0

    def test_main_with_custom_recipient(self):
        """Test main with --recipient argument."""
        with patch("sys.argv", ["main.py", "--recipient", "custom@example.com"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = [
                    {
                        "ticker": "MSFT",
                        "score": 72,
                        "reasons": ["Insider purchase"],
                    }
                ]
                mock_instance.send_report.return_value = True

                result = main()

                # Check that send_report was called with custom recipient
                mock_instance.send_report.assert_called_once()
                call_args = mock_instance.send_report.call_args
                assert call_args[0][1] == "custom@example.com"
                assert result == 0

    def test_main_no_stocks_found(self):
        """Test main when no stocks meet threshold."""
        with patch("sys.argv", ["main.py"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = []

                result = main()

                # Should return 0 when no stocks found
                assert result == 0

    def test_main_send_report_failure(self):
        """Test main when send_report fails."""
        with patch("sys.argv", ["main.py"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = [
                    {
                        "ticker": "GOOG",
                        "score": 80,
                        "reasons": ["New position"],
                    }
                ]
                mock_instance.send_report.return_value = False

                result = main()

                # Should return 1 on send failure
                assert result == 1

    def test_main_keyboard_interrupt(self):
        """Test main handles KeyboardInterrupt."""
        with patch("sys.argv", ["main.py"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.side_effect = KeyboardInterrupt()

                result = main()

                # Should return 1 on interrupt
                assert result == 1

    def test_main_exception_handling(self):
        """Test main handles exceptions gracefully."""
        with patch("sys.argv", ["main.py"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.side_effect = Exception(
                    "Test error"
                )

                result = main()

                # Should return 1 on exception
                assert result == 1

    def test_main_argument_parsing(self):
        """Test that arguments are parsed correctly."""
        with patch(
            "sys.argv",
            ["main.py", "--dry-run", "--min-score", "80", "--skip-fetch"],
        ):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = []

                result = main()

                # Verify min_score was parsed and used
                mock_generator.assert_called_with(min_score=80)
                assert result == 0

    def test_main_logs_summary(self):
        """Test that main logs stock summary."""
        with patch("sys.argv", ["main.py", "--dry-run"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                with patch(
                    "smart_money_tracker.main.logger"
                ) as mock_logger:
                    mock_instance = MagicMock()
                    mock_generator.return_value = mock_instance
                    mock_instance.generate_report.return_value = [
                        {
                            "ticker": "AAPL",
                            "score": 85,
                            "reasons": ["New position", "Insider buying"],
                        },
                        {
                            "ticker": "MSFT",
                            "score": 72,
                            "reasons": ["Position increase"],
                        },
                    ]

                    result = main()

                    # Should log summary
                    assert mock_logger.info.called
                    assert result == 0


class TestConftest:
    """Tests for conftest fixtures."""

    def test_temp_db_fixture(self, temp_db):
        """Test temp_db fixture creates database."""
        import os

        assert os.path.exists(temp_db)
        assert temp_db.endswith(".db")

    def test_mock_settings_fixture(self, mock_settings):
        """Test mock_settings fixture."""
        assert mock_settings["openai_api_key"] == "test-key-12345"
        assert mock_settings["report_email"] == "test@example.com"
        assert mock_settings["min_score_for_email"] == 60

    def test_cleanup_fixture(self, cleanup):
        """Test cleanup fixture."""
        # This should yield without error
        assert cleanup is None


class TestArgumentParser:
    """Tests for CLI argument parser."""

    def test_parser_accepts_dry_run(self):
        """Test parser accepts --dry-run."""
        with patch("sys.argv", ["main.py", "--dry-run"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = []

                result = main()

                assert result == 0

    def test_parser_accepts_recipient(self):
        """Test parser accepts --recipient."""
        with patch("sys.argv", ["main.py", "--recipient", "test@test.com"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = []

                result = main()

                assert result == 0

    def test_parser_accepts_min_score(self):
        """Test parser accepts --min-score."""
        with patch("sys.argv", ["main.py", "--min-score", "75"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = []

                result = main()

                assert result == 0

    def test_parser_accepts_skip_fetch(self):
        """Test parser accepts --skip-fetch."""
        with patch("sys.argv", ["main.py", "--skip-fetch", "--dry-run"]):
            with patch(
                "smart_money_tracker.main.ReportGenerator"
            ) as mock_generator:
                mock_instance = MagicMock()
                mock_generator.return_value = mock_instance
                mock_instance.generate_report.return_value = []

                result = main()

                assert result == 0
