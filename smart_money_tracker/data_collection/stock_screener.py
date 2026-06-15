"""Stock screener for AI tips — India (NSE) and US markets via yfinance."""

from typing import Dict, List

import yfinance as yf

from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)

# Nifty 50 coverage across major sectors
INDIA_WATCHLIST = [
    # IT
    {"ticker": "TCS.NS",       "name": "Tata Consultancy Services", "sector": "IT"},
    {"ticker": "INFY.NS",      "name": "Infosys",                   "sector": "IT"},
    {"ticker": "WIPRO.NS",     "name": "Wipro",                     "sector": "IT"},
    {"ticker": "HCLTECH.NS",   "name": "HCL Technologies",          "sector": "IT"},
    {"ticker": "TECHM.NS",     "name": "Tech Mahindra",             "sector": "IT"},
    # Banking / Finance
    {"ticker": "HDFCBANK.NS",  "name": "HDFC Bank",                 "sector": "Banking"},
    {"ticker": "ICICIBANK.NS", "name": "ICICI Bank",                "sector": "Banking"},
    {"ticker": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank",       "sector": "Banking"},
    {"ticker": "AXISBANK.NS",  "name": "Axis Bank",                 "sector": "Banking"},
    {"ticker": "SBIN.NS",      "name": "State Bank of India",       "sector": "Banking"},
    {"ticker": "BAJFINANCE.NS","name": "Bajaj Finance",             "sector": "Finance"},
    # Consumer
    {"ticker": "HINDUNILVR.NS","name": "Hindustan Unilever",        "sector": "Consumer"},
    {"ticker": "ITC.NS",       "name": "ITC",                       "sector": "Consumer"},
    {"ticker": "NESTLEIND.NS", "name": "Nestle India",              "sector": "Consumer"},
    {"ticker": "TITAN.NS",     "name": "Titan Company",             "sector": "Consumer"},
    # Auto
    {"ticker": "MARUTI.NS",    "name": "Maruti Suzuki",             "sector": "Auto"},
    {"ticker": "M&M.NS",       "name": "Mahindra & Mahindra",       "sector": "Auto"},
    {"ticker": "BAJAJ-AUTO.NS","name": "Bajaj Auto",                "sector": "Auto"},
    {"ticker": "HEROMOTOCO.NS","name": "Hero MotoCorp",             "sector": "Auto"},
    # Pharma
    {"ticker": "SUNPHARMA.NS", "name": "Sun Pharmaceutical",        "sector": "Pharma"},
    {"ticker": "DRREDDY.NS",   "name": "Dr. Reddy's Laboratories",  "sector": "Pharma"},
    {"ticker": "CIPLA.NS",     "name": "Cipla",                     "sector": "Pharma"},
    # Energy / Conglomerate
    {"ticker": "RELIANCE.NS",  "name": "Reliance Industries",       "sector": "Energy"},
    {"ticker": "ONGC.NS",      "name": "ONGC",                      "sector": "Energy"},
    {"ticker": "NTPC.NS",      "name": "NTPC",                      "sector": "Energy"},
    # Infra / Industrials
    {"ticker": "LT.NS",        "name": "Larsen & Toubro",           "sector": "Industrials"},
    {"ticker": "POWERGRID.NS", "name": "Power Grid Corp",           "sector": "Industrials"},
    # Metals
    {"ticker": "TATASTEEL.NS", "name": "Tata Steel",                "sector": "Metals"},
    {"ticker": "JSWSTEEL.NS",  "name": "JSW Steel",                 "sector": "Metals"},
]

US_WATCHLIST = [
    {"ticker": "AAPL",  "name": "Apple",             "sector": "Technology"},
    {"ticker": "MSFT",  "name": "Microsoft",         "sector": "Technology"},
    {"ticker": "NVDA",  "name": "NVIDIA",            "sector": "Semiconductors"},
    {"ticker": "GOOGL", "name": "Alphabet",          "sector": "Technology"},
    {"ticker": "AMZN",  "name": "Amazon",            "sector": "Consumer/Cloud"},
    {"ticker": "META",  "name": "Meta Platforms",    "sector": "Technology"},
    {"ticker": "TSLA",  "name": "Tesla",             "sector": "Auto/EV"},
    {"ticker": "JPM",   "name": "JPMorgan Chase",    "sector": "Banking"},
    {"ticker": "GS",    "name": "Goldman Sachs",     "sector": "Banking"},
    {"ticker": "JNJ",   "name": "Johnson & Johnson", "sector": "Healthcare"},
    {"ticker": "UNH",   "name": "UnitedHealth",      "sector": "Healthcare"},
    {"ticker": "PFE",   "name": "Pfizer",            "sector": "Pharma"},
    {"ticker": "LLY",   "name": "Eli Lilly",         "sector": "Pharma"},
    {"ticker": "XOM",   "name": "ExxonMobil",        "sector": "Energy"},
    {"ticker": "CVX",   "name": "Chevron",           "sector": "Energy"},
    {"ticker": "KO",    "name": "Coca-Cola",         "sector": "Consumer"},
    {"ticker": "MCD",   "name": "McDonald's",        "sector": "Consumer"},
    {"ticker": "NKE",   "name": "Nike",              "sector": "Consumer"},
    {"ticker": "BAC",   "name": "Bank of America",   "sector": "Banking"},
    {"ticker": "AVGO",  "name": "Broadcom",          "sector": "Semiconductors"},
    {"ticker": "AMD",   "name": "AMD",               "sector": "Semiconductors"},
    {"ticker": "NFLX",  "name": "Netflix",           "sector": "Media"},
    {"ticker": "COST",  "name": "Costco",            "sector": "Retail"},
    {"ticker": "CAT",   "name": "Caterpillar",       "sector": "Industrials"},
    {"ticker": "BA",    "name": "Boeing",            "sector": "Industrials"},
]


def screen_stocks(watchlist: List[Dict], n: int = 5, market: str = "US") -> List[Dict]:
    """
    Screen a watchlist and return the top n candidates for AI analysis.

    Scoring: prefers stocks that have pulled back 5–50% from their 52-week high
    (beaten-down quality names) while ensuring sector diversity.

    Returns list of dicts with price, range, sector, and score data.
    """
    results = []

    for item in watchlist:
        ticker = item["ticker"]
        try:
            fi = yf.Ticker(ticker).fast_info
            price = fi.last_price
            year_high = fi.year_high
            year_low = fi.year_low

            if not price or not year_high or not year_low or price <= 0:
                continue

            pct_from_high = (price - year_high) / year_high * 100  # negative
            pct_from_low = (price - year_low) / year_low * 100      # positive
            from_high_abs = abs(pct_from_high)

            # Favour 5–50% pullback; ignore stocks in freefall (>50%) or near ATH (<5%)
            score = from_high_abs if 5 <= from_high_abs <= 50 else 0

            currency = "INR" if (".NS" in ticker or ".BO" in ticker) else "USD"

            results.append({
                "ticker": ticker,
                "name": item["name"],
                "sector": item["sector"],
                "market": market,
                "currency": currency,
                "price": round(price, 2),
                "year_high": round(year_high, 2),
                "year_low": round(year_low, 2),
                "pct_from_high": round(pct_from_high, 1),
                "pct_from_low": round(pct_from_low, 1),
                "score": round(score, 1),
            })
            logger.debug(f"{ticker}: price={price:.2f}, from_high={pct_from_high:.1f}%")

        except Exception as e:
            logger.warning(f"Screener error for {ticker}: {e}")
            continue

    # Sort by score descending (biggest quality pullbacks first)
    results.sort(key=lambda x: x["score"], reverse=True)

    # Pick top n with sector diversity
    seen_sectors: set = set()
    diverse: List[Dict] = []
    remaining: List[Dict] = []

    for r in results:
        if r["sector"] not in seen_sectors:
            diverse.append(r)
            seen_sectors.add(r["sector"])
        else:
            remaining.append(r)
        if len(diverse) >= n:
            break

    # Top up with non-diverse picks if needed
    if len(diverse) < n:
        diverse.extend(remaining[: n - len(diverse)])

    logger.info(f"{market}: screened {len(results)} stocks, selected {len(diverse[:n])}")
    return diverse[:n]
