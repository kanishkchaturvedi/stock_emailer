"""Tests for signal scoring engine."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from smart_money_tracker.config.scoring_config import SCORING_RULES
from smart_money_tracker.signals.scoring import ScoringEngine


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup - try multiple times to handle Windows file locking
    path = Path(db_path)
    if path.exists():
        try:
            path.unlink()
        except PermissionError:
            import time
            time.sleep(0.1)
            try:
                path.unlink()
            except PermissionError:
                # Ignore cleanup errors
                pass


@pytest.fixture
def scoring_engine():
    """Create a ScoringEngine instance for testing."""
    return ScoringEngine()


class TestScoringRulesConfig:
    """Tests for scoring rules configuration."""

    def test_scoring_rules_exist(self):
        """Test that all required scoring rules are defined."""
        required_rules = [
            "new_position",
            "position_increase_gt_25pct",
            "position_increase_gt_50pct",
            "insider_purchase",
            "multiple_insider_purchases",
            "congressional_buy",
            "congressional_multiple_buys",
        ]
        for rule in required_rules:
            assert rule in SCORING_RULES, f"Missing rule: {rule}"

    def test_scoring_rules_have_positive_values(self):
        """Test that all scoring rules have positive point values."""
        for rule, score in SCORING_RULES.items():
            assert isinstance(score, int), f"Rule {rule} is not an integer"
            assert score > 0, f"Rule {rule} has non-positive score: {score}"

    def test_scoring_rules_values(self):
        """Test that scoring rules have correct point values."""
        expected_values = {
            "new_position": 40,
            "position_increase_gt_25pct": 20,
            "position_increase_gt_50pct": 35,
            "insider_purchase": 30,
            "multiple_insider_purchases": 40,
            "congressional_buy": 10,
            "congressional_multiple_buys": 15,
        }
        for rule, expected_score in expected_values.items():
            assert SCORING_RULES[rule] == expected_score, (
                f"Rule {rule} has incorrect score: "
                f"expected {expected_score}, got {SCORING_RULES[rule]}"
            )


class TestScoringEngineBasic:
    """Tests for basic ScoringEngine functionality."""

    def test_scoring_engine_init(self, scoring_engine):
        """Test that ScoringEngine initializes correctly."""
        assert scoring_engine is not None
        assert scoring_engine.scoring_rules == SCORING_RULES

    def test_score_ticker_returns_tuple(self, scoring_engine):
        """Test that score_ticker returns a tuple of (int, List[str])."""
        score, reasons = scoring_engine.score_ticker("AAPL")
        assert isinstance(score, int)
        assert isinstance(reasons, list)

    def test_score_ticker_no_signals(self, scoring_engine):
        """Test scoring a ticker with no signals."""
        score, reasons = scoring_engine.score_ticker("AAPL")
        assert score == 0
        assert reasons == []

    def test_score_ticker_non_negative(self, scoring_engine):
        """Test that scores are always non-negative."""
        # Test various combinations
        test_cases = [
            (False, 0, 0, 0),
            (False, 5, 0, 0),
            (False, 0, 1, 0),
            (False, 0, 0, 1),
        ]
        for new_pos, pos_inc, insider, congress in test_cases:
            score, _ = scoring_engine.score_ticker(
                "AAPL",
                new_13f_position=new_pos,
                position_increase_pct=pos_inc,
                insider_purchases=insider,
                congressional_buys=congress,
            )
            assert score >= 0, f"Score is negative: {score}"


class TestNewPositionScoring:
    """Tests for new 13F position scoring."""

    def test_new_position_scoring(self, scoring_engine):
        """Test scoring for new 13F position."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", new_13f_position=True
        )
        assert score == SCORING_RULES["new_position"]
        assert len(reasons) == 1
        assert "New institutional position" in reasons[0]

    def test_new_position_reason_format(self, scoring_engine):
        """Test that new position reason is human-readable."""
        _, reasons = scoring_engine.score_ticker(
            "AAPL", new_13f_position=True
        )
        assert "New institutional position detected" in reasons[0]


class TestPositionIncreaseScoring:
    """Tests for position increase scoring."""

    def test_position_increase_gt_50pct(self, scoring_engine):
        """Test scoring for position increase > 50%."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=75.5
        )
        assert score == SCORING_RULES["position_increase_gt_50pct"]
        assert len(reasons) == 1
        assert "75.5%" in reasons[0]

    def test_position_increase_exactly_50pct(self, scoring_engine):
        """Test scoring for position increase exactly 50%."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=50.0
        )
        # At 50%, should use the >25% rule (not >50%)
        assert score == SCORING_RULES["position_increase_gt_25pct"]

    def test_position_increase_gt_25pct_but_not_50(self, scoring_engine):
        """Test scoring for position increase between 25% and 50%."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=35.2
        )
        assert score == SCORING_RULES["position_increase_gt_25pct"]
        assert len(reasons) == 1
        assert "35.2%" in reasons[0]

    def test_position_increase_exactly_25pct(self, scoring_engine):
        """Test scoring for position increase exactly 25%."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=25.0
        )
        # At 25%, should not trigger any rule
        assert score == 0
        assert len(reasons) == 0

    def test_position_increase_lt_25pct(self, scoring_engine):
        """Test scoring for position increase less than 25%."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=15.0
        )
        assert score == 0
        assert len(reasons) == 0

    def test_position_increase_zero(self, scoring_engine):
        """Test scoring with 0% position increase."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=0.0
        )
        assert score == 0
        assert len(reasons) == 0

    def test_position_increase_high_percentage(self, scoring_engine):
        """Test scoring with very high position increase."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=200.5
        )
        assert score == SCORING_RULES["position_increase_gt_50pct"]
        assert "200.5%" in reasons[0]


class TestInsiderPurchaseScoring:
    """Tests for insider purchase scoring."""

    def test_single_insider_purchase(self, scoring_engine):
        """Test scoring for single insider purchase."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", insider_purchases=1
        )
        assert score == SCORING_RULES["insider_purchase"]
        assert len(reasons) == 1
        assert "Insider purchase detected" in reasons[0]

    def test_multiple_insider_purchases(self, scoring_engine):
        """Test scoring for multiple insider purchases."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", insider_purchases=3
        )
        assert score == SCORING_RULES["multiple_insider_purchases"]
        assert len(reasons) == 1
        assert "3" in reasons[0]
        assert "Multiple insider purchases" in reasons[0]

    def test_multiple_insider_purchases_exactly_two(self, scoring_engine):
        """Test scoring for exactly two insider purchases."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", insider_purchases=2
        )
        assert score == SCORING_RULES["multiple_insider_purchases"]
        assert "2" in reasons[0]

    def test_zero_insider_purchases(self, scoring_engine):
        """Test scoring with zero insider purchases."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", insider_purchases=0
        )
        assert score == 0


class TestCongressionalBuyScoring:
    """Tests for congressional buy scoring."""

    def test_single_congressional_buy(self, scoring_engine):
        """Test scoring for single congressional buy."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", congressional_buys=1
        )
        assert score == SCORING_RULES["congressional_buy"]
        assert len(reasons) == 1
        assert "Congressional buy detected" in reasons[0]

    def test_multiple_congressional_buys(self, scoring_engine):
        """Test scoring for multiple congressional buys."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", congressional_buys=4
        )
        assert score == SCORING_RULES["congressional_multiple_buys"]
        assert len(reasons) == 1
        assert "4" in reasons[0]
        assert "Multiple congressional buys" in reasons[0]

    def test_multiple_congressional_buys_exactly_two(self, scoring_engine):
        """Test scoring for exactly two congressional buys."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", congressional_buys=2
        )
        assert score == SCORING_RULES["congressional_multiple_buys"]
        assert "2" in reasons[0]

    def test_zero_congressional_buys(self, scoring_engine):
        """Test scoring with zero congressional buys."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", congressional_buys=0
        )
        assert score == 0


class TestCombinedSignals:
    """Tests for combined signal scoring."""

    def test_new_position_and_insider(self, scoring_engine):
        """Test scoring with new position and insider purchase."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", new_13f_position=True, insider_purchases=1
        )
        expected_score = (
            SCORING_RULES["new_position"]
            + SCORING_RULES["insider_purchase"]
        )
        assert score == expected_score
        assert len(reasons) == 2

    def test_all_signals_combined(self, scoring_engine):
        """Test scoring with all signal types combined."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL",
            new_13f_position=True,
            position_increase_pct=60.0,
            insider_purchases=2,
            congressional_buys=3,
        )
        expected_score = (
            SCORING_RULES["new_position"]
            + SCORING_RULES["position_increase_gt_50pct"]
            + SCORING_RULES["multiple_insider_purchases"]
            + SCORING_RULES["congressional_multiple_buys"]
        )
        assert score == expected_score
        assert len(reasons) == 4

    def test_high_position_increase_with_congressional(self, scoring_engine):
        """Test scoring with high position increase and congressional buys."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL",
            position_increase_pct=75.0,
            congressional_buys=1,
        )
        expected_score = (
            SCORING_RULES["position_increase_gt_50pct"]
            + SCORING_RULES["congressional_buy"]
        )
        assert score == expected_score
        assert len(reasons) == 2

    def test_multiple_insiders_and_congressional(self, scoring_engine):
        """Test scoring with multiple insiders and multiple congressional."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL",
            insider_purchases=5,
            congressional_buys=2,
        )
        expected_score = (
            SCORING_RULES["multiple_insider_purchases"]
            + SCORING_RULES["congressional_multiple_buys"]
        )
        assert score == expected_score
        assert len(reasons) == 2

    def test_reason_order_13f_then_insider_then_congress(
        self, scoring_engine
    ):
        """Test that reasons appear in correct order: 13F, then insider, then congress."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL",
            new_13f_position=True,
            position_increase_pct=60.0,
            insider_purchases=2,
            congressional_buys=1,
        )
        # Should have reasons in order: new position, pos increase, insider, congress
        assert len(reasons) == 4
        assert "New institutional position" in reasons[0]
        assert "Position increased" in reasons[1]
        assert "Multiple insider purchases" in reasons[2]
        assert "Congressional buy" in reasons[3]


class TestHighConvictionStocks:
    """Tests for get_high_conviction_stocks method."""

    @patch("smart_money_tracker.signals.scoring.db_client")
    def test_get_high_conviction_stocks_empty(
        self, mock_db_client, scoring_engine
    ):
        """Test get_high_conviction_stocks with no results."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor
        mock_db_client.get_connection.return_value = mock_conn

        results = scoring_engine.get_high_conviction_stocks(min_score=60)
        assert results == []

    @patch("smart_money_tracker.signals.scoring.db_client")
    def test_get_high_conviction_stocks_single_result(
        self, mock_db_client, scoring_engine
    ):
        """Test get_high_conviction_stocks with one result."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("AAPL", 75, "New institutional position detected|Position increased 60.0%"),
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db_client.get_connection.return_value = mock_conn

        results = scoring_engine.get_high_conviction_stocks(min_score=60)
        assert len(results) == 1
        assert results[0]["ticker"] == "AAPL"
        assert results[0]["score"] == 75
        assert len(results[0]["reasons"]) == 2

    @patch("smart_money_tracker.signals.scoring.db_client")
    def test_get_high_conviction_stocks_multiple_results(
        self, mock_db_client, scoring_engine
    ):
        """Test get_high_conviction_stocks with multiple results."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("AAPL", 85, "New institutional position detected"),
            ("MSFT", 70, "Position increased 55.0%"),
            ("TSLA", 65, "Multiple insider purchases (2)"),
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db_client.get_connection.return_value = mock_conn

        results = scoring_engine.get_high_conviction_stocks(
            min_score=60, limit=10
        )
        assert len(results) == 3
        assert results[0]["ticker"] == "AAPL"
        assert results[1]["ticker"] == "MSFT"
        assert results[2]["ticker"] == "TSLA"

    @patch("smart_money_tracker.signals.scoring.db_client")
    def test_get_high_conviction_stocks_respects_min_score(
        self, mock_db_client, scoring_engine
    ):
        """Test that get_high_conviction_stocks respects min_score parameter."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_client.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Call with different min_score
        scoring_engine.get_high_conviction_stocks(min_score=80)

        # Verify the query used the correct min_score
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1][0] == 80

    @patch("smart_money_tracker.signals.scoring.db_client")
    def test_get_high_conviction_stocks_respects_limit(
        self, mock_db_client, scoring_engine
    ):
        """Test that get_high_conviction_stocks respects limit parameter."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_client.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Call with different limit
        scoring_engine.get_high_conviction_stocks(min_score=60, limit=5)

        # Verify the query used the correct limit
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1][1] == 5

    @patch("smart_money_tracker.signals.scoring.db_client")
    def test_get_high_conviction_stocks_empty_reasons(
        self, mock_db_client, scoring_engine
    ):
        """Test parsing of empty reasons string from database."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("AAPL", 50, ""),
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db_client.get_connection.return_value = mock_conn

        results = scoring_engine.get_high_conviction_stocks(min_score=50)
        assert len(results) == 1
        assert results[0]["reasons"] == []

    @patch("smart_money_tracker.signals.scoring.db_client")
    def test_get_high_conviction_stocks_pipe_delimited_reasons(
        self, mock_db_client, scoring_engine
    ):
        """Test proper parsing of pipe-delimited reasons."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (
                "AAPL",
                100,
                "Reason1|Reason2|Reason3",
            ),
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db_client.get_connection.return_value = mock_conn

        results = scoring_engine.get_high_conviction_stocks()
        assert len(results[0]["reasons"]) == 3
        assert results[0]["reasons"][0] == "Reason1"
        assert results[0]["reasons"][1] == "Reason2"
        assert results[0]["reasons"][2] == "Reason3"

    @patch("smart_money_tracker.signals.scoring.db_client")
    def test_get_high_conviction_stocks_handles_db_error(
        self, mock_db_client, scoring_engine
    ):
        """Test error handling when database query fails."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB Error")
        mock_conn.cursor.return_value = mock_cursor
        mock_db_client.get_connection.return_value = mock_conn

        with pytest.raises(Exception, match="DB Error"):
            scoring_engine.get_high_conviction_stocks()


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_negative_position_increase(self, scoring_engine):
        """Test handling of negative position increase (position closed)."""
        # This should be handled by data validation elsewhere,
        # but we should not crash
        score, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=-10.0
        )
        assert score == 0
        assert len(reasons) == 0

    def test_very_large_position_increase(self, scoring_engine):
        """Test with extremely large position increase."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=1000.0
        )
        assert score == SCORING_RULES["position_increase_gt_50pct"]
        assert "1000.0%" in reasons[0]

    def test_decimal_precision_in_reasons(self, scoring_engine):
        """Test that position increase shows one decimal place."""
        _, reasons = scoring_engine.score_ticker(
            "AAPL", position_increase_pct=33.456
        )
        assert "33.5%" in reasons[0]

    def test_large_insider_purchase_count(self, scoring_engine):
        """Test with large number of insider purchases."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", insider_purchases=50
        )
        assert score == SCORING_RULES["multiple_insider_purchases"]
        assert "50" in reasons[0]

    def test_large_congressional_buy_count(self, scoring_engine):
        """Test with large number of congressional buys."""
        score, reasons = scoring_engine.score_ticker(
            "AAPL", congressional_buys=25
        )
        assert score == SCORING_RULES["congressional_multiple_buys"]
        assert "25" in reasons[0]
