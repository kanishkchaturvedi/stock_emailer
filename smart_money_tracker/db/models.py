"""Pydantic data models for Smart Money Tracker."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Holding(BaseModel):
    """Model representing a stock holding in a 13F filing."""

    ticker: str
    company_name: str
    shares: int
    market_value: float
    portfolio_weight: float


class Filing13F(BaseModel):
    """Model representing a 13F SEC filing."""

    investor_name: str
    cik: str
    filing_date: datetime
    holdings: List[Holding]


class FilingComparison(BaseModel):
    """Model representing changes in a position between filings."""

    ticker: str
    previous_shares: Optional[int] = None
    current_shares: int
    is_new_position: bool
    is_closed_position: bool
    position_increase_pct: Optional[float] = None
    position_decrease_pct: Optional[float] = None


class InsiderTransaction(BaseModel):
    """Model representing an insider transaction."""

    ticker: str
    insider_name: str
    role: str
    transaction_type: str
    shares_bought: int
    value_bought: float
    transaction_date: datetime


class CongressionalTrade(BaseModel):
    """Model representing a congressional trade."""

    politician: str
    ticker: str
    buy_or_sell: str
    disclosure_date: datetime
    estimated_amount: float


class Signal(BaseModel):
    """Model representing a trading signal for a stock."""

    ticker: str
    score: int
    reasons: List[str]
    has_13f_activity: bool = False
    has_insider_buying: bool = False
    has_congressional_activity: bool = False


class EmailReport(BaseModel):
    """Model representing a generated email report."""

    generated_at: datetime
    stocks: List[Signal]
    recipient: str
