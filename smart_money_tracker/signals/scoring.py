"""Scoring engine for trading signals."""

from typing import List, Tuple

from smart_money_tracker.config.scoring_config import SCORING_RULES
from smart_money_tracker.db.client import db_client
from smart_money_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class ScoringEngine:
    """Engine for scoring stocks based on collected signals."""

    def __init__(self):
        """Initialize the scoring engine."""
        self.scoring_rules = SCORING_RULES

    def score_ticker(
        self,
        ticker: str,
        new_13f_position: bool = False,
        position_increase_pct: float = 0.0,
        insider_purchases: int = 0,
        congressional_buys: int = 0,
    ) -> Tuple[int, List[str]]:
        """
        Score a ticker based on collected signals.

        Args:
            ticker: Stock ticker symbol
            new_13f_position: Whether this is a new 13F position
            position_increase_pct: Percentage increase in position (0-100+)
            insider_purchases: Number of insider purchases
            congressional_buys: Number of congressional buys

        Returns:
            Tuple of (score: int, reasons: List[str])
        """
        score = 0
        reasons = []

        # 13F signals
        if new_13f_position:
            score += self.scoring_rules["new_position"]
            reasons.append("New institutional position detected")

        if position_increase_pct > 50:
            score += self.scoring_rules["position_increase_gt_50pct"]
            reasons.append(f"Position increased {position_increase_pct:.1f}%")
        elif position_increase_pct > 25:
            score += self.scoring_rules["position_increase_gt_25pct"]
            reasons.append(f"Position increased {position_increase_pct:.1f}%")

        # Insider signals
        if insider_purchases > 1:
            score += self.scoring_rules["multiple_insider_purchases"]
            reasons.append(f"Multiple insider purchases ({insider_purchases})")
        elif insider_purchases == 1:
            score += self.scoring_rules["insider_purchase"]
            reasons.append("Insider purchase detected")

        # Congressional signals
        if congressional_buys > 1:
            score += self.scoring_rules["congressional_multiple_buys"]
            reasons.append(f"Multiple congressional buys ({congressional_buys})")
        elif congressional_buys == 1:
            score += self.scoring_rules["congressional_buy"]
            reasons.append("Congressional buy detected")

        # Log the signal
        logger.info(
            f"{ticker}: score={score}, signals={len(reasons)}"
        )

        return score, reasons

    def get_high_conviction_stocks(
        self, min_score: int = 60, limit: int = 10
    ) -> List[dict]:
        """
        Get stocks with high conviction scores.

        Queries the signals table for scores >= min_score, ordered by
        score in descending order.

        Args:
            min_score: Minimum score threshold (default 60)
            limit: Maximum number of results to return (default 10)

        Returns:
            List of dicts with structure: {ticker, score, reasons}
        """
        conn = db_client.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT ticker, score, reasons
                FROM signals
                WHERE score >= ?
                ORDER BY score DESC
                LIMIT ?
                """,
                (min_score, limit),
            )

            results = []
            for row in cursor.fetchall():
                ticker, score, reasons_str = row
                # Split pipe-delimited reasons from database
                reasons = (
                    reasons_str.split("|") if reasons_str else []
                )
                results.append({
                    "ticker": ticker,
                    "score": score,
                    "reasons": reasons,
                })

            logger.info(
                f"Retrieved {len(results)} high conviction stocks "
                f"(min_score={min_score})"
            )
            return results

        except Exception as e:
            logger.error(
                f"Error querying high conviction stocks: {e}"
            )
            raise
        finally:
            conn.close()
