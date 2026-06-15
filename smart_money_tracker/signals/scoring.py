"""Scoring engine for trading signals."""

from typing import List, Tuple

from smart_money_tracker.config.scoring_config import SCORING_RULES
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class ScoringEngine:
    """Engine for scoring stocks based on collected signals."""

    def __init__(self):
        self.scoring_rules = SCORING_RULES

    def score_ticker(
        self,
        ticker: str,
        insider_purchases: int = 0,
        num_institutional_holders: int = 0,
    ) -> Tuple[int, List[str]]:
        """
        Score a ticker based on collected signals.

        Args:
            ticker: Stock ticker symbol
            insider_purchases: Number of open-market insider purchases (Form 4)
            num_institutional_holders: Number of tracked institutions holding this stock

        Returns:
            Tuple of (score: int, reasons: List[str])
        """
        score = 0
        reasons = []

        if insider_purchases >= 6:
            score += self.scoring_rules["very_high_insider_purchases"]
            reasons.append(f"Very high insider buying ({insider_purchases} purchases)")
        elif insider_purchases >= 4:
            score += self.scoring_rules["high_insider_purchases"]
            reasons.append(f"High insider buying ({insider_purchases} purchases)")
        elif insider_purchases >= 2:
            score += self.scoring_rules["multiple_insider_purchases"]
            reasons.append(f"Multiple insider purchases ({insider_purchases})")
        elif insider_purchases == 1:
            score += self.scoring_rules["insider_purchase"]
            reasons.append("Insider purchase detected")

        if num_institutional_holders >= 2:
            score += self.scoring_rules["multiple_tracked_funds"]
            reasons.append(f"Held by {num_institutional_holders} tracked major funds")
        elif num_institutional_holders == 1:
            score += self.scoring_rules["tracked_fund_holder"]
            reasons.append("Held by tracked major fund")

        logger.info(f"{ticker}: score={score}, signals={len(reasons)}")
        return score, reasons
