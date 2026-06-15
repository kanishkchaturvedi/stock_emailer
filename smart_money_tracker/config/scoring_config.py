"""Scoring configuration for signal evaluation."""

# Scoring rules with point values for different signal types
SCORING_RULES = {
    "insider_purchase": 20,           # 1 purchase
    "multiple_insider_purchases": 35,  # 2-3 purchases
    "high_insider_purchases": 55,      # 4-5 purchases
    "very_high_insider_purchases": 70, # 6+ purchases
    "tracked_fund_holder": 10,        # held by 1 tracked institution
    "multiple_tracked_funds": 20,     # held by 2+ tracked institutions
}
