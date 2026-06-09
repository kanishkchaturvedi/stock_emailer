"""Configuration package for Smart Money Tracker."""

from smart_money_tracker.config.settings import settings
from smart_money_tracker.config.investors import TRACKED_INVESTORS, CIK_TO_INVESTOR
from smart_money_tracker.config.scoring_config import SCORING_RULES

__all__ = ["settings", "TRACKED_INVESTORS", "CIK_TO_INVESTOR", "SCORING_RULES"]
