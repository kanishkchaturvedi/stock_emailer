# Alternative Data Sources for Smart Money Tracking

## APIs That Actually Work

### 1. **Finnhub API** ✅ (FREE TIER AVAILABLE)
- Insider transactions (real-time)
- Company filings (13F, Form 4, 8-K)
- CEO/Director trades
- Free tier: 60 API calls/minute
- Website: https://finnhub.io
```
GET /stock/insider-transactions?symbol=AAPL
GET /stock/insider-sentiment?symbol=AAPL
```

### 2. **MarketWatch Insider Trading** ✅ (WEB SCRAPING)
- Real-time insider buys/sells
- Director and officer transactions
- Forms 3, 4, 5
- Website: https://www.marketwatch.com/tools/insider-trades
- Can be scraped with BeautifulSoup

### 3. **GuruFocus API** ✅ (FREE TIER)
- Track what famous investors are buying
- Portfolio holdings
- Transaction history
- Website: https://www.gurufocus.com
- Free API available

### 4. **SEC.report** ✅ (NO RATE LIMITING)
- Alternative SEC data aggregator
- Insider transactions
- 13F holdings
- 8-K filings
- Website: https://www.sec.report
- Can be scraped or use their unofficial API

### 5. **Seeking Alpha** ✅ (WEB SCRAPING)
- Insider holdings
- CEO buys/sells
- Analyst ratings
- Can be scraped

## Social/Sentiment Sources

### 6. **Twitter/X API** ✅ (PAID)
- Track investor accounts
- Monitor #stocks #trading #insider
- Real-time sentiment

### 7. **Reddit** ✅ (FREE)
- r/investing, r/stocks, r/SecurityAnalysis
- Community discussion of insider activity
- Can use PRAW library to scrape

### 8. **News APIs** ✅ (FREE TIER)
- NewsAPI, GNews
- Monitor "insider buying" "insider transaction" articles
- Real-time news alerts

## Which is Best?

**Quick Ranking:**
1. **Finnhub** - Best balance of free tier + good data
2. **MarketWatch** - Web scraping (no auth needed)
3. **SEC.report** - Good aggregator, no rate limits
4. **GuruFocus** - Specific investor tracking
5. **News APIs** - Supplementary data

## Recommendation

**Use Finnhub + MarketWatch Scraping:**
- Finnhub handles programmatic API calls
- MarketWatch scraping for recent insider trades
- Both free/low-cost
- No authentication blocking
