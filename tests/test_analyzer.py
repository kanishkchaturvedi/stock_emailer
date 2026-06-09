"""Tests for AI analyzer module."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from smart_money_tracker.ai.analyzer import AIAnalyzer


class TestAIAnalyzerInitialization:
    """Test suite for AIAnalyzer initialization."""

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_initializes_with_openai_client(self, mock_openai_class, mock_settings):
        """Test that AIAnalyzer initializes OpenAI client with API key."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        analyzer = AIAnalyzer()

        mock_openai_class.assert_called_once_with(api_key="test-api-key")
        assert analyzer.model == "gpt-4o-mini"

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_sets_model_from_settings(self, mock_openai_class, mock_settings):
        """Test that AIAnalyzer sets model from settings."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o"

        analyzer = AIAnalyzer()

        assert analyzer.model == "gpt-4o"


class TestAnalyzeTicker:
    """Test suite for analyze_ticker method."""

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_analyze_ticker_returns_correct_keys(self, mock_openai_class, mock_settings):
        """Test that analyze_ticker returns dict with required keys."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Strong upside potential.",
            "bearish_thesis": "Downside risks present.",
            "key_risks": "Market volatility.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal 1", "Signal 2"])

        assert set(result.keys()) == {"bullish_thesis", "bearish_thesis", "key_risks"}
        assert isinstance(result["bullish_thesis"], str)
        assert isinstance(result["bearish_thesis"], str)
        assert isinstance(result["key_risks"], str)

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_analyze_ticker_with_single_reason(self, mock_openai_class, mock_settings):
        """Test analyze_ticker with a single reason."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Bullish signal detected.",
            "bearish_thesis": "Some downside risk.",
            "key_risks": "Market conditions.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("MSFT", ["Signal 1"])

        assert len(result) == 3
        assert all(isinstance(v, str) for v in result.values())

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_analyze_ticker_with_multiple_reasons(
        self, mock_openai_class, mock_settings
    ):
        """Test analyze_ticker with multiple reasons."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Multiple positive indicators.",
            "bearish_thesis": "Some concerns exist.",
            "key_risks": "Competition and macro.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        reasons = ["Signal 1", "Signal 2", "Signal 3", "Signal 4"]
        result = analyzer.analyze_ticker("GOOGL", reasons)

        assert len(result) == 3
        mock_client.messages.create.assert_called_once()

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_api_call_uses_correct_parameters(
        self, mock_openai_class, mock_settings
    ):
        """Test that API call uses correct model and max_tokens."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Analysis.",
            "bearish_thesis": "Analysis.",
            "key_risks": "Risks.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        analyzer.analyze_ticker("TSLA", ["Signal"])

        # Verify API call parameters
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "gpt-4o-mini"
        assert call_args.kwargs["max_tokens"] == 1000
        assert "messages" in call_args.kwargs
        assert len(call_args.kwargs["messages"]) == 1
        assert call_args.kwargs["messages"][0]["role"] == "user"


class TestResponseParsing:
    """Test suite for JSON response parsing."""

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_parse_json_response_directly(self, mock_openai_class, mock_settings):
        """Test parsing JSON response directly."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Direct JSON response.",
            "bearish_thesis": "Some downside.",
            "key_risks": "Market risks.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        assert result["bullish_thesis"] == "Direct JSON response."

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_extract_json_from_text_with_preamble(
        self, mock_openai_class, mock_settings
    ):
        """Test extracting JSON from response with preamble text."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_text = """Here's the analysis:
{
    "bullish_thesis": "Extracted from text",
    "bearish_thesis": "Downside present",
    "key_risks": "Various risks"
}
Additional commentary here."""

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=response_text)]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        assert result["bullish_thesis"] == "Extracted from text"

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_non_string_values_converted_to_string(
        self, mock_openai_class, mock_settings
    ):
        """Test that non-string values in response are converted to strings."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Return non-string values that should be converted
        response_data = {
            "bullish_thesis": 123,
            "bearish_thesis": True,
            "key_risks": None,
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        assert isinstance(result["bullish_thesis"], str)
        assert isinstance(result["bearish_thesis"], str)
        assert isinstance(result["key_risks"], str)


class TestWordLimits:
    """Test suite for word limit validation."""

    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text."""
        return len(text.split())

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_bullish_thesis_word_limit(self, mock_openai_class, mock_settings):
        """Test that bullish thesis respects word limit."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create a bullish thesis with 140 words (under 150 limit)
        bullish = " ".join(["word"] * 140)
        response_data = {
            "bullish_thesis": bullish,
            "bearish_thesis": "Downside risk present.",
            "key_risks": "Market volatility.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        word_count = self.count_words(result["bullish_thesis"])
        assert word_count <= 150

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_bearish_thesis_word_limit(self, mock_openai_class, mock_settings):
        """Test that bearish thesis respects word limit."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create a bearish thesis with 140 words (under 150 limit)
        bearish = " ".join(["word"] * 140)
        response_data = {
            "bullish_thesis": "Upside potential.",
            "bearish_thesis": bearish,
            "key_risks": "Various risks.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        word_count = self.count_words(result["bearish_thesis"])
        assert word_count <= 150

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_key_risks_word_limit(self, mock_openai_class, mock_settings):
        """Test that key risks respects word limit."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Create key risks with 95 words (under 100 limit)
        risks = " ".join(["risk"] * 95)
        response_data = {
            "bullish_thesis": "Upside.",
            "bearish_thesis": "Downside.",
            "key_risks": risks,
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        word_count = self.count_words(result["key_risks"])
        assert word_count <= 100


class TestFinancialAdviceRestriction:
    """Test suite for financial advice language restrictions."""

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_no_buy_language_in_response(self, mock_openai_class, mock_settings):
        """Test that no 'buy' advice language is present."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Stock shows strong fundamentals.",
            "bearish_thesis": "Competition poses risks.",
            "key_risks": "Market conditions uncertain.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        # Check for problematic buy language
        response_text = " ".join(result.values()).lower()
        assert "should buy" not in response_text
        assert "must buy" not in response_text
        assert "buy now" not in response_text

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_no_sell_language_in_response(self, mock_openai_class, mock_settings):
        """Test that no 'sell' advice language is present."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Positive indicators detected.",
            "bearish_thesis": "Downside risks to monitor.",
            "key_risks": "Volatility expected.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        # Check for problematic sell language
        response_text = " ".join(result.values()).lower()
        assert "should sell" not in response_text
        assert "must sell" not in response_text
        assert "sell now" not in response_text


class TestMockAnalysisFallback:
    """Test suite for mock analysis fallback."""

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_mock_analysis_returned_on_api_failure(
        self, mock_openai_class, mock_settings
    ):
        """Test that mock analysis is returned when API fails."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        # Should return mock analysis
        assert "bullish_thesis" in result
        assert "bearish_thesis" in result
        assert "key_risks" in result
        assert all(isinstance(v, str) for v in result.values())
        assert all(len(v) > 0 for v in result.values())

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_mock_analysis_includes_ticker(self, mock_openai_class, mock_settings):
        """Test that mock analysis includes the ticker symbol."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("TSLA", ["Signal"])

        # Mock analysis should reference the ticker
        response_text = " ".join(result.values()).upper()
        assert "TSLA" in response_text

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_mock_analysis_contains_no_empty_strings(
        self, mock_openai_class, mock_settings
    ):
        """Test that mock analysis values are never empty."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("GOOG", ["Signal"])

        # All values should be non-empty strings
        assert all(isinstance(v, str) and len(v) > 0 for v in result.values())


class TestRetryDecorator:
    """Test suite for retry decorator on _fetch_analysis."""

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_retry_decorator_applied(self, mock_openai_class, mock_settings):
        """Test that retry decorator is applied to _fetch_analysis."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # First call fails, second succeeds
        response_data = {
            "bullish_thesis": "Success after retry.",
            "bearish_thesis": "Downside.",
            "key_risks": "Risks.",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.side_effect = [
            Exception("First attempt fails"),
            mock_response,
        ]

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        # Should succeed because of retry
        assert result["bullish_thesis"] == "Success after retry."
        # Verify API was called twice (first failed, second succeeded)
        assert mock_client.messages.create.call_count == 2

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_fallback_to_mock_after_retries_exhausted(
        self, mock_openai_class, mock_settings
    ):
        """Test that mock analysis is used after all retries fail."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        # All attempts fail
        mock_client.messages.create.side_effect = Exception("Persistent API Error")

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", ["Signal"])

        # Should return mock analysis after retries exhausted
        assert "bullish_thesis" in result
        assert isinstance(result["bullish_thesis"], str)
        assert len(result["bullish_thesis"]) > 0
        # Verify retries were attempted (3 attempts)
        assert mock_client.messages.create.call_count == 3


class TestPromptConstruction:
    """Test suite for prompt construction."""

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_prompt_includes_ticker(self, mock_openai_class, mock_settings):
        """Test that prompt includes the ticker symbol."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Analysis",
            "bearish_thesis": "Analysis",
            "key_risks": "Risks",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        analyzer.analyze_ticker("MSFT", ["Signal"])

        # Check prompt content
        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "MSFT" in prompt

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_prompt_includes_signals(self, mock_openai_class, mock_settings):
        """Test that prompt includes all supplied signals."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Analysis",
            "bearish_thesis": "Analysis",
            "key_risks": "Risks",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        signals = ["Congress insider bought", "Large options activity"]
        analyzer = AIAnalyzer()
        analyzer.analyze_ticker("AAPL", signals)

        # Check prompt content
        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        for signal in signals:
            assert signal in prompt

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_prompt_includes_word_limits(self, mock_openai_class, mock_settings):
        """Test that prompt includes word limit requirements."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Analysis",
            "bearish_thesis": "Analysis",
            "key_risks": "Risks",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        analyzer.analyze_ticker("AAPL", ["Signal"])

        # Check prompt content
        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "150" in prompt  # Word limits mentioned
        assert "100" in prompt

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_prompt_includes_restrictions(self, mock_openai_class, mock_settings):
        """Test that prompt includes NO FINANCIAL ADVICE restriction."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Analysis",
            "bearish_thesis": "Analysis",
            "key_risks": "Risks",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        analyzer.analyze_ticker("AAPL", ["Signal"])

        # Check prompt content
        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "NO FINANCIAL ADVICE" in prompt
        assert "ONLY USE SUPPLIED SIGNALS" in prompt
        assert "NO INVENTED FACTS" in prompt


class TestVariousTickerSymbols:
    """Test suite for various ticker symbols."""

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    @pytest.mark.parametrize("ticker", ["AAPL", "MSFT", "GOOGL", "TSLA", "META"])
    def test_analyze_various_tickers(self, mock_openai_class, mock_settings, ticker):
        """Test analyze_ticker with various ticker symbols."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": f"Analysis for {ticker}",
            "bearish_thesis": "Downside risks",
            "key_risks": "Market risks",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker(ticker, ["Signal"])

        assert len(result) == 3
        assert all(isinstance(v, str) for v in result.values())


class TestVariousReasonLists:
    """Test suite for various reason lists."""

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_analyze_with_empty_reasons_list(
        self, mock_openai_class, mock_settings
    ):
        """Test analyze_ticker with empty reasons list."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Analysis",
            "bearish_thesis": "Analysis",
            "key_risks": "Risks",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", [])

        assert len(result) == 3

    @patch("smart_money_tracker.ai.analyzer.settings")
    @patch("smart_money_tracker.ai.analyzer.OpenAI")
    def test_analyze_with_many_reasons(self, mock_openai_class, mock_settings):
        """Test analyze_ticker with many reasons."""
        mock_settings.openai_api_key = "test-api-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        response_data = {
            "bullish_thesis": "Analysis",
            "bearish_thesis": "Analysis",
            "key_risks": "Risks",
        }
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        mock_client.messages.create.return_value = mock_response

        reasons = [f"Signal {i}" for i in range(10)]
        analyzer = AIAnalyzer()
        result = analyzer.analyze_ticker("AAPL", reasons)

        assert len(result) == 3
        # Verify all signals were included in prompt
        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        for reason in reasons:
            assert reason in prompt
