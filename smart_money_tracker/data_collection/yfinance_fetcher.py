"""Institutional holders and stock info via yfinance (Yahoo Finance)."""

from typing import Dict, List

import yfinance as yf

from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


def fetch_institutional_holders(tickers: List[str]) -> Dict[str, List[dict]]:
    """
    Return top institutional holders for each ticker.

    Data is aggregated by Yahoo Finance from 13F filings — no SEC parsing needed.

    Returns:
        {ticker: [{"investor": str, "shares": int, "value_usd": float, "pct_out": float}]}
    """
    result: Dict[str, List[dict]] = {}
    for ticker in tickers:
        try:
            ih = yf.Ticker(ticker).institutional_holders
            if ih is None or ih.empty:
                continue
            holders = []
            for _, row in ih.iterrows():
                name = str(row.get("Holder", "Unknown"))
                shares = int(row.get("Shares", 0) or 0)
                value = float(row.get("Value", 0) or 0)
                pct = float(row.get("% Out", 0) or 0)
                holders.append({
                    "investor": name,
                    "shares": shares,
                    "value_usd": value,
                    "pct_out": round(pct * 100, 2),  # fraction → percent
                })
            if holders:
                result[ticker] = holders
                logger.info(f"{ticker}: {len(holders)} institutional holders")
        except Exception as e:
            logger.warning(f"yfinance holders error for {ticker}: {e}")
    return result


def fetch_stock_info(tickers: List[str]) -> Dict[str, dict]:
    """
    Return price and market cap info for each ticker.

    Returns:
        {ticker: {"price": float, "market_cap": float, "week52_high": float, "week52_low": float}}
    """
    result: Dict[str, dict] = {}
    for ticker in tickers:
        try:
            fi = yf.Ticker(ticker).fast_info
            result[ticker] = {
                "price": getattr(fi, "last_price", None),
                "market_cap": getattr(fi, "market_cap", None),
                "week52_high": getattr(fi, "year_high", None),
                "week52_low": getattr(fi, "year_low", None),
            }
        except Exception as e:
            logger.warning(f"yfinance info error for {ticker}: {e}")
    return result
