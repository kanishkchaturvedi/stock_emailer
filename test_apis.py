#!/usr/bin/env python3
"""
Test which external APIs are actually working
"""
import requests
from datetime import datetime, timedelta

print("=" * 60)
print("Testing External APIs")
print("=" * 60)

# Test 1: SEC EDGAR 13F API
print("\n[1] Testing SEC EDGAR 13F API...")
try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0'}
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000086882&type=13F-HR&dateb=&owner=exclude&count=1&output=json"
    response = requests.get(url, headers=headers, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   [OK] SEC EDGAR 13F API WORKS")
    else:
        print(f"   [FAIL] SEC EDGAR returned {response.status_code}")
except Exception as e:
    print(f"   [FAIL] Error: {str(e)[:80]}")

# Test 2: SEC Form 4 API
print("\n[2] Testing SEC EDGAR Form 4 API...")
try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0'}
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=4&dateb=&owner=exclude&count=10&search_text="
    response = requests.get(url, headers=headers, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   [OK] SEC EDGAR Form 4 API WORKS")
    else:
        print(f"   [FAIL] SEC EDGAR returned {response.status_code}")
except Exception as e:
    print(f"   [FAIL] Error: {str(e)[:80]}")

# Test 3: Senate Stock Watcher API
print("\n[3] Testing Senate Stock Watcher API...")
try:
    url = "https://senatestockwatcher.com/api/trades"
    response = requests.get(url, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   [OK] Senate Stock Watcher API WORKS ({len(data)} trades)")
    else:
        print(f"   [FAIL] Status {response.status_code}")
except requests.exceptions.ConnectionError as e:
    print(f"   [FAIL] Connection Error: {str(e)[:80]}")
except Exception as e:
    print(f"   [FAIL] Error: {str(e)[:80]}")

# Test 4: Alpha Vantage (for technical data)
print("\n[4] Testing Alpha Vantage API (for price data)...")
try:
    url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey=demo"
    response = requests.get(url, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   [OK] Alpha Vantage API WORKS (demo key)")
    else:
        print(f"   [FAIL] Status {response.status_code}")
except Exception as e:
    print(f"   [FAIL] Error: {str(e)[:80]}")

# Test 5: Yahoo Finance (alternative for price data)
print("\n[5] Testing Yahoo Finance API...")
try:
    url = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=price"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0'}
    response = requests.get(url, headers=headers, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   [OK] Yahoo Finance API WORKS")
    else:
        print(f"   [FAIL] Status {response.status_code}")
except Exception as e:
    print(f"   [FAIL] Error: {str(e)[:80]}")

print("\n" + "=" * 60)
print("Summary: Check which APIs returned [OK] above")
print("=" * 60)
