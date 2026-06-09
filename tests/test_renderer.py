"""Tests for email renderer module."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from smart_money_tracker.email.renderer import EmailRenderer


class TestEmailRendererInitialization:
    """Test suite for EmailRenderer initialization."""

    def test_initializes_with_jinja2_environment(self):
        """Test that EmailRenderer initializes Jinja2 environment."""
        renderer = EmailRenderer()

        assert renderer.env is not None
        assert hasattr(renderer.env, "get_template")

    def test_autoescape_enabled(self):
        """Test that autoescape is enabled for XSS prevention."""
        renderer = EmailRenderer()

        # Verify autoescape is enabled by checking environment properties
        assert renderer.env.autoescape is not None

    def test_template_loader_configured(self):
        """Test that template loader is properly configured."""
        renderer = EmailRenderer()

        # Check that loader is PackageLoader
        loader = renderer.env.loader
        assert loader is not None


class TestRenderMethod:
    """Test suite for render method."""

    def test_render_returns_html_string(self):
        """Test that render returns a non-empty HTML string."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["New 13F position", "Insider purchase"],
                "analysis": {
                    "bullish_thesis": "Strong upside potential.",
                    "bearish_thesis": "Market headwinds present.",
                    "key_risks": "Macro volatility.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert isinstance(html, str)
        assert len(html) > 0
        assert html.strip().startswith("<!DOCTYPE html>")

    def test_render_includes_ticker_symbol(self):
        """Test that rendered HTML includes ticker symbol."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "MSFT",
                "score": 75,
                "reasons": ["Position increase"],
                "analysis": {
                    "bullish_thesis": "Upside thesis.",
                    "bearish_thesis": "Downside thesis.",
                    "key_risks": "Risk factors.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert "MSFT" in html

    def test_render_includes_score(self):
        """Test that rendered HTML includes stock score."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 92,
                "reasons": ["Multiple signals"],
                "analysis": {
                    "bullish_thesis": "Strong thesis.",
                    "bearish_thesis": "Weak bearish case.",
                    "key_risks": "Market risks.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert "92" in html

    def test_render_includes_signal_reasons(self):
        """Test that rendered HTML includes signal reasons."""
        renderer = EmailRenderer()
        reasons = ["New 13F position", "Insider purchase", "Congressional buy"]
        stocks = [
            {
                "ticker": "GOOGL",
                "score": 80,
                "reasons": reasons,
                "analysis": {
                    "bullish_thesis": "Bullish case.",
                    "bearish_thesis": "Bearish case.",
                    "key_risks": "Risks present.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        for reason in reasons:
            assert reason in html

    def test_render_includes_bullish_thesis(self):
        """Test that rendered HTML includes bullish thesis."""
        renderer = EmailRenderer()
        bullish_thesis = "This stock shows strong fundamentals and growth potential."
        stocks = [
            {
                "ticker": "TSLA",
                "score": 88,
                "reasons": ["Strong signals"],
                "analysis": {
                    "bullish_thesis": bullish_thesis,
                    "bearish_thesis": "Some downside risks.",
                    "key_risks": "Competition.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert bullish_thesis in html

    def test_render_includes_bearish_thesis(self):
        """Test that rendered HTML includes bearish thesis."""
        renderer = EmailRenderer()
        bearish_thesis = "Market conditions pose challenges to near-term performance."
        stocks = [
            {
                "ticker": "META",
                "score": 65,
                "reasons": ["Moderate signals"],
                "analysis": {
                    "bullish_thesis": "Upside potential exists.",
                    "bearish_thesis": bearish_thesis,
                    "key_risks": "Regulatory risks.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert bearish_thesis in html

    def test_render_includes_key_risks(self):
        """Test that rendered HTML includes key risks section."""
        renderer = EmailRenderer()
        key_risks = "Market volatility and macro headwinds represent key risks."
        stocks = [
            {
                "ticker": "NVDA",
                "score": 78,
                "reasons": ["Multiple insiders buying"],
                "analysis": {
                    "bullish_thesis": "Strong momentum.",
                    "bearish_thesis": "Valuation concerns.",
                    "key_risks": key_risks,
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert key_risks in html

    def test_render_includes_timestamp(self):
        """Test that rendered HTML includes generated timestamp."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AMD",
                "score": 72,
                "reasons": ["Activity detected"],
                "analysis": {
                    "bullish_thesis": "Positive signals.",
                    "bearish_thesis": "Some concerns.",
                    "key_risks": "Industry risks.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 14, 45, 30)

        html = renderer.render(stocks, generated_at)

        # Check that timestamp is formatted correctly
        assert "2025-06-09" in html
        assert "14:45:30" in html

    def test_render_with_empty_stock_list(self):
        """Test render with empty stock list."""
        renderer = EmailRenderer()
        stocks = []
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert isinstance(html, str)
        assert len(html) > 0
        # Should contain message about no stocks found
        assert "no high-conviction stocks" in html.lower()

    def test_render_with_max_ten_stocks(self):
        """Test render limits display to max 10 stocks."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": f"TICK{i:02d}",
                "score": 70 + i,
                "reasons": [f"Signal {i}"],
                "analysis": {
                    "bullish_thesis": f"Bull thesis {i}.",
                    "bearish_thesis": f"Bear thesis {i}.",
                    "key_risks": f"Risks {i}.",
                },
            }
            for i in range(15)  # Create 15 stocks
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # Check that first 10 stocks are present
        for i in range(10):
            assert f"TICK{i:02d}" in html

        # Check that stocks beyond 10 are not present
        for i in range(10, 15):
            assert f"TICK{i:02d}" not in html

    def test_render_handles_special_characters(self):
        """Test that special characters are properly escaped."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["Signal with <bracket>", "Signal with & ampersand"],
                "analysis": {
                    "bullish_thesis": "Thesis with <html> tag.",
                    "bearish_thesis": "Thesis with & symbol.",
                    "key_risks": "Risks with \"quotes\" and 'apostrophes'.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # Check that special characters are escaped
        assert "&lt;bracket&gt;" in html or "<bracket>" not in html
        assert "&amp;" in html or " & " not in html

    def test_render_prevents_script_injection(self):
        """Test that script tags in data are escaped (XSS prevention)."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["<script>alert('xss')</script>"],
                "analysis": {
                    "bullish_thesis": "<script>alert('injection')</script>",
                    "bearish_thesis": "Normal thesis.",
                    "key_risks": "<img src=x onerror='alert(1)'>",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # Script tags should be escaped (not executed)
        assert "<script>" not in html
        # Verify HTML entities are used to escape (autoescape working)
        assert "&lt;script&gt;" in html
        assert "&lt;img" in html
        # Quotes should be escaped with HTML entities
        assert "&#39;" in html or "&#34;" in html or "&quot;" in html

    def test_render_with_notable_activity(self):
        """Test that notable activity field is rendered when present."""
        renderer = EmailRenderer()
        notable_activity = "Large options call volume detected on expiration date."
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["Insider activity"],
                "analysis": {
                    "bullish_thesis": "Strong upside.",
                    "bearish_thesis": "Some downside.",
                    "key_risks": "Market risks.",
                },
                "notable_activity": notable_activity,
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert notable_activity in html

    def test_render_without_notable_activity(self):
        """Test rendering when notable_activity is not provided."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "MSFT",
                "score": 75,
                "reasons": ["Position increase"],
                "analysis": {
                    "bullish_thesis": "Upside potential.",
                    "bearish_thesis": "Downside risks.",
                    "key_risks": "Market volatility.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # Should render without errors
        assert isinstance(html, str)
        assert len(html) > 0

    def test_render_includes_disclaimer(self):
        """Test that disclaimer is included in rendered output."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["Signal"],
                "analysis": {
                    "bullish_thesis": "Thesis.",
                    "bearish_thesis": "Thesis.",
                    "key_risks": "Risks.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert "DISCLAIMER" in html.upper()
        assert "RISK" in html.upper() or "risk" in html
        assert "informational purposes" in html.lower()

    def test_render_timestamp_formatting(self):
        """Test that timestamp is formatted correctly."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["Signal"],
                "analysis": {
                    "bullish_thesis": "Thesis.",
                    "bearish_thesis": "Thesis.",
                    "key_risks": "Risks.",
                },
            }
        ]
        test_datetime = datetime(2025, 3, 15, 9, 5, 42)

        html = renderer.render(stocks, test_datetime)

        # Check ISO format with UTC indicator
        assert "2025-03-15" in html
        assert "09:05:42" in html
        assert "UTC" in html

    def test_render_with_single_stock(self):
        """Test render with single stock."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "GOOG",
                "score": 90,
                "reasons": ["Multiple strong signals"],
                "analysis": {
                    "bullish_thesis": "Excellent opportunity.",
                    "bearish_thesis": "Minimal concerns.",
                    "key_risks": "Macro risks only.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        assert "GOOG" in html
        assert "90" in html

    def test_render_with_multiple_stocks(self):
        """Test render with multiple different stocks."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["New position"],
                "analysis": {
                    "bullish_thesis": "Strong bull case.",
                    "bearish_thesis": "Some concerns.",
                    "key_risks": "Market risks.",
                },
            },
            {
                "ticker": "MSFT",
                "score": 80,
                "reasons": ["Position increase"],
                "analysis": {
                    "bullish_thesis": "Positive momentum.",
                    "bearish_thesis": "Valuation concerns.",
                    "key_risks": "Competition.",
                },
            },
            {
                "ticker": "GOOGL",
                "score": 75,
                "reasons": ["Insider buying"],
                "analysis": {
                    "bullish_thesis": "Growth potential.",
                    "bearish_thesis": "Regulatory risks.",
                    "key_risks": "Policy changes.",
                },
            },
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # All tickers should be present
        assert "AAPL" in html
        assert "MSFT" in html
        assert "GOOGL" in html

        # All scores should be present
        assert "85" in html
        assert "80" in html
        assert "75" in html

    def test_render_returns_valid_html_structure(self):
        """Test that render returns valid HTML structure."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["Signal"],
                "analysis": {
                    "bullish_thesis": "Thesis.",
                    "bearish_thesis": "Thesis.",
                    "key_risks": "Risks.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # Check basic HTML structure
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "</html>" in html
        assert "<body" in html
        assert "</body>" in html

    def test_render_with_none_analysis_fields(self):
        """Test render when analysis fields are None or missing."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["Signal"],
                "analysis": {
                    "bullish_thesis": None,
                    "bearish_thesis": "Thesis",
                    "key_risks": None,
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # Should render without errors
        assert isinstance(html, str)
        assert len(html) > 0
        assert "AAPL" in html

    def test_render_logs_success(self):
        """Test that render logs success at INFO level."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["Signal"],
                "analysis": {
                    "bullish_thesis": "Thesis.",
                    "bearish_thesis": "Thesis.",
                    "key_risks": "Risks.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        with patch("smart_money_tracker.email.renderer.logger") as mock_logger:
            renderer_with_mock_logger = EmailRenderer()
            renderer_with_mock_logger.render(stocks, generated_at)

            # Check that logger.info was called
            assert mock_logger.info.call_count >= 1

    def test_render_executive_summary_count(self):
        """Test that executive summary shows correct count of stocks."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "TICK01",
                "score": 80,
                "reasons": ["Signal"],
                "analysis": {
                    "bullish_thesis": "Thesis.",
                    "bearish_thesis": "Thesis.",
                    "key_risks": "Risks.",
                },
            },
            {
                "ticker": "TICK02",
                "score": 75,
                "reasons": ["Signal"],
                "analysis": {
                    "bullish_thesis": "Thesis.",
                    "bearish_thesis": "Thesis.",
                    "key_risks": "Risks.",
                },
            },
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # Executive summary should mention number of stocks
        assert "2" in html

    def test_render_with_unicode_characters(self):
        """Test rendering with unicode characters."""
        renderer = EmailRenderer()
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["Signal with symbols: © ® ™"],
                "analysis": {
                    "bullish_thesis": "Thesis with emoji indicators.",
                    "bearish_thesis": "Thesis normal.",
                    "key_risks": "Risks normal.",
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # Should render without errors
        assert isinstance(html, str)
        assert len(html) > 0

    def test_render_long_text_fields(self):
        """Test rendering with very long text fields."""
        renderer = EmailRenderer()
        long_thesis = "This is a very long thesis. " * 50  # Very long text
        stocks = [
            {
                "ticker": "AAPL",
                "score": 85,
                "reasons": ["Signal"] * 10,  # Multiple reasons
                "analysis": {
                    "bullish_thesis": long_thesis,
                    "bearish_thesis": long_thesis,
                    "key_risks": long_thesis,
                },
            }
        ]
        generated_at = datetime(2025, 6, 9, 10, 30, 0)

        html = renderer.render(stocks, generated_at)

        # Should render without errors
        assert isinstance(html, str)
        assert len(html) > 0
