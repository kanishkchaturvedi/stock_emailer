"""AI-generated stock tips via OpenAI for India and US markets."""

import json
from typing import Dict, List

from smart_money_tracker.config.settings import settings
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a concise financial analyst writing stock tips for retail investors.
For each stock, provide a signal and a 2-3 sentence thesis based on the price data given.
Be specific — mention the pullback magnitude, sector dynamics, or valuation context.
Do NOT give generic advice. Do NOT add disclaimers inside the thesis.
Valid signals: STRONG BUY, BUY, WATCH, AVOID."""


def _build_stock_block(s: dict) -> str:
    symbol = s["ticker"].replace(".NS", "").replace(".BO", "")
    currency = s["currency"]
    price_str = f"{currency} {s['price']:,.2f}"
    high_str = f"{currency} {s['year_high']:,.2f}"
    low_str = f"{currency} {s['year_low']:,.2f}"
    return (
        f"Ticker: {s['ticker']} — {s['name']}\n"
        f"Sector: {s['sector']} | Market: {s['market']}\n"
        f"Price: {price_str}  |  52w range: {low_str} – {high_str}\n"
        f"Down {abs(s['pct_from_high']):.1f}% from 52w high  |  "
        f"Up {s['pct_from_low']:.1f}% from 52w low"
    )


def generate_tips(india_stocks: List[Dict], us_stocks: List[Dict]) -> List[Dict]:
    """
    Call OpenAI to generate signal + thesis for each screened stock.

    Returns list of tip dicts:
        [{"ticker", "name", "sector", "market", "currency", "price",
          "pct_from_high", "signal", "thesis"}, ...]

    Returns [] if OpenAI is not configured or the call fails.
    """
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — skipping AI tips")
        return []

    all_stocks = india_stocks + us_stocks
    if not all_stocks:
        return []

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
    except ImportError:
        logger.warning("openai package not installed — skipping AI tips")
        return []

    # Build user message
    blocks = []
    for i, s in enumerate(all_stocks, 1):
        blocks.append(f"--- Stock {i} ---\n{_build_stock_block(s)}")

    user_msg = (
        "Generate tips for the following stocks.\n\n"
        + "\n\n".join(blocks)
        + "\n\nRespond with a JSON object in this exact format:\n"
        '{"tips": [{"ticker": "...", "signal": "...", "thesis": "..."}, ...]}\n'
        "Include one entry per stock in the same order. "
        "thesis must be 2-3 sentences."
    )

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_completion_tokens=1500,
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
        ai_tips = data.get("tips", [])
    except Exception as e:
        logger.error(f"OpenAI tips call failed: {type(e).__name__}: {e}")
        return []

    # Merge AI output back with screened stock metadata
    results = []
    for stock, tip in zip(all_stocks, ai_tips):
        signal = tip.get("signal", "WATCH").upper().strip()
        # Normalise any unexpected values
        if signal not in ("STRONG BUY", "BUY", "WATCH", "AVOID"):
            signal = "WATCH"
        results.append({
            "ticker": stock["ticker"],
            "name": stock["name"],
            "sector": stock["sector"],
            "market": stock["market"],
            "currency": stock["currency"],
            "price": stock["price"],
            "pct_from_high": stock["pct_from_high"],
            "year_high": stock["year_high"],
            "year_low": stock["year_low"],
            "signal": signal,
            "thesis": tip.get("thesis", ""),
        })
        logger.info(f"AI tip: {stock['ticker']} -> {signal}")

    return results
