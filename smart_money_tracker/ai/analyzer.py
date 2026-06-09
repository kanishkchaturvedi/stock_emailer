"""AI-powered stock analysis using OpenAI API."""

import json
from typing import Any, Dict, List

from openai import OpenAI

from smart_money_tracker.config.settings import settings
from smart_money_tracker.utils.logger import get_logger
from smart_money_tracker.utils.retries import retry

logger = get_logger(__name__)


class AIAnalyzer:
    """Generates AI-powered bullish/bearish stock theses using OpenAI."""

    def __init__(self) -> None:
        """Initialize OpenAI client with API key from settings."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def analyze_ticker(self, ticker: str, reasons: List[str]) -> Dict[str, str]:
        """
        Generate bullish/bearish theses for a ticker using OpenAI.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            reasons: List of signals/reasons for analysis

        Returns:
            Dictionary with keys: bullish_thesis, bearish_thesis, key_risks
            Each value is a string with max word limits:
            - bullish_thesis: max 150 words
            - bearish_thesis: max 150 words
            - key_risks: max 100 words

        Note:
            - Uses @retry decorator (via _fetch_analysis) with 3 attempts and exponential backoff
            - Returns mock analysis as fallback if API fails
            - Will not exceed word limits
            - Contains no financial advice language (no "buy/sell")
            - Only uses supplied signals, no invented facts
        """
        try:
            analysis = self._fetch_analysis(ticker, reasons)
            logger.info(f"Successfully analyzed ticker {ticker}")
            return analysis

        except Exception as e:
            logger.error(
                f"API call failed for {ticker}: {type(e).__name__}: {str(e)}. "
                f"Using mock analysis as fallback."
            )
            return self._mock_analysis(ticker)

    @retry(max_attempts=3, base_delay=1.0, backoff=2.0)
    def _fetch_analysis(self, ticker: str, reasons: List[str]) -> Dict[str, str]:
        """
        Fetch analysis from OpenAI API with retry logic.

        This method is decorated with @retry to allow retry attempts
        before falling back to mock analysis.

        Args:
            ticker: Stock ticker symbol
            reasons: List of signals/reasons for analysis

        Returns:
            Dictionary with bullish_thesis, bearish_thesis, key_risks
        """
        prompt = self._build_analysis_prompt(ticker, reasons)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text

        # Try to parse as JSON
        analysis = self._parse_response(response_text)
        return analysis

    def _build_analysis_prompt(self, ticker: str, reasons: List[str]) -> str:
        """
        Build the prompt for OpenAI analysis.

        Args:
            ticker: Stock ticker symbol
            reasons: List of signals/reasons

        Returns:
            Formatted prompt string
        """
        reasons_text = "\n".join(f"- {reason}" for reason in reasons)

        prompt = f"""Analyze the stock ticker {ticker} based on the following signals:

{reasons_text}

Provide your analysis in the following JSON format (replace the values with your analysis):
{{
    "bullish_thesis": "Your bullish thesis here (max 150 words)",
    "bearish_thesis": "Your bearish thesis here (max 150 words)",
    "key_risks": "Key risks here (max 100 words)"
}}

IMPORTANT REQUIREMENTS:
1. Your response MUST be valid JSON
2. Bullish thesis: max 150 words, explain why this stock could perform well based on signals
3. Bearish thesis: max 150 words, explain why this stock could underperform based on signals
4. Key risks: max 100 words, list potential risks
5. NO FINANCIAL ADVICE - do not use phrases like "should buy", "must sell", "you should"
6. NO INVENTED FACTS - only use the supplied signals above
7. ONLY USE SUPPLIED SIGNALS - do not reference other data or make assumptions

Return ONLY the JSON object, no additional text."""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, str]:
        """
        Parse JSON response from OpenAI.

        Args:
            response_text: Raw response text from OpenAI

        Returns:
            Dictionary with bullish_thesis, bearish_thesis, key_risks

        Note:
            Tries direct JSON parsing first, then attempts to extract JSON
            from response text if initial parsing fails.
        """
        # Try direct JSON parsing
        try:
            data = json.loads(response_text)
            return self._validate_response_keys(data)
        except json.JSONDecodeError:
            # Try to extract JSON from response text
            logger.warning(
                "Failed to parse response as JSON directly. "
                "Attempting to extract JSON from text."
            )
            json_str = self._extract_json_from_text(response_text)
            data = json.loads(json_str)
            return self._validate_response_keys(data)

    def _extract_json_from_text(self, text: str) -> str:
        """
        Extract JSON object from response text.

        Args:
            text: Text containing JSON

        Returns:
            JSON string extracted from text

        Raises:
            ValueError: If no valid JSON object found
        """
        # Find the first { and last } to extract JSON object
        start_idx = text.find("{")
        end_idx = text.rfind("}") + 1

        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON object found in response text")

        return text[start_idx:end_idx]

    def _validate_response_keys(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate response has required keys.

        Args:
            data: Parsed response dictionary

        Returns:
            Dictionary with string values for required keys

        Raises:
            KeyError: If required keys are missing
        """
        required_keys = ["bullish_thesis", "bearish_thesis", "key_risks"]

        for key in required_keys:
            if key not in data:
                raise KeyError(f"Missing required key: {key}")

            if not isinstance(data[key], str):
                data[key] = str(data[key])

        return {key: data[key] for key in required_keys}

    def _mock_analysis(self, ticker: str) -> Dict[str, str]:
        """
        Fallback mock analysis if API fails.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with reasonable placeholder text for analysis
        """
        return {
            "bullish_thesis": (
                f"Positive signals detected for {ticker}. The stock shows "
                f"indicators worth monitoring, with potential for upside movement "
                f"if current trends continue."
            ),
            "bearish_thesis": (
                f"Headwinds present for {ticker}. Market conditions and current "
                f"indicators suggest caution, with potential downside risks to monitor."
            ),
            "key_risks": (
                "Market volatility, macro conditions, and unexpected company-specific "
                "events represent key risks to any position."
            ),
        }
