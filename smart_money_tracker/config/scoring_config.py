"""Scoring configuration for signal evaluation."""

# Scoring rules with point values for different signal types
SCORING_RULES = {
    "new_position": 40,
    "position_increase_gt_25pct": 20,
    "position_increase_gt_50pct": 35,
    "insider_purchase": 30,
    "multiple_insider_purchases": 40,
    "congressional_buy": 10,
    "congressional_multiple_buys": 15,
}
