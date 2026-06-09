"""Tracked investors registry with CIK mappings."""

TRACKED_INVESTORS = {
    "Berkshire Hathaway": "0000086882",
    "Pershing Square Capital": "0001336528",
    "Scion Asset Management": "0001649337",
    "Appaloosa Management": "0001022317",
    "Baupost Group": "0000814979",
    "Duquesne Capital": "0001311786",
    "Third Point": "0001086239",
    "Icahn Capital": "0000796422",
}

# Reverse mapping for quick lookup by CIK
CIK_TO_INVESTOR = {cik: investor for investor, cik in TRACKED_INVESTORS.items()}
