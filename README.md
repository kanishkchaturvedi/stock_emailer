# Smart Money Tracker

**Automated insider trading signal emails powered by 13F filings, Form 4 transactions, and congressional trades.**

Smart Money Tracker monitors the portfolios of elite institutional investors, insider executives, and U.S. congresspeople. The system analyzes their trading activity daily, scores potential opportunities based on multi-source signals, and emails you actionable trading ideas. Data comes directly from SEC filings and congressional disclosure records. The tracker runs automatically via GitHub Actions with no manual intervention required.


## Quick Start

### Prerequisites

- Python 3.12 or later
- OpenAI API key (for signal analysis)
- Email delivery setup (SMTP or Resend)
- GitHub account (for Actions deployment)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/smart-money-tracker.git
cd smart-money-tracker
```

2. Create a Python virtual environment:
```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file with your configuration:
```bash
cp .env.example .env
# Edit .env with your API keys and email settings
```

5. Run manually (test before automation):
```bash
python -m smart_money_tracker.main --dry-run
```

6. Deploy to GitHub Actions:
   - Push code to GitHub
   - Go to Settings → Secrets and variables → Actions
   - Add secrets: `OPENAI_API_KEY`, `REPORT_EMAIL`, and email credentials
   - Actions runs daily at 8 AM UTC


## Configuration

### Required Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPENAI_API_KEY` | API key for GPT-4 signal analysis | `sk-proj-...` |
| `REPORT_EMAIL` | Email recipient for daily reports | `portfolio@example.com` |

### Optional Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_PATH` | Path to SQLite database | `smart_money.db` |
| `MIN_SCORE_FOR_EMAIL` | Minimum score threshold | `60` |
| `OPENAI_MODEL` | GPT model to use | `gpt-4o-mini` |

### Email Configuration

Choose one delivery method:

#### SMTP (Gmail, Outlook, etc.)

```env
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
```

For Gmail:
1. Enable 2-factor authentication
2. Generate app-specific password at https://myaccount.google.com/apppasswords
3. Use that password (not your login password)

#### Resend (Transactional Email)

```env
RESEND_API_KEY=re_your-resend-api-key-here
```

Get your API key from https://resend.com/api-keys

### Example `.env` File

```env
# OpenAI
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4o-mini

# Email - Choose one method
SMTP_EMAIL=portfolio@gmail.com
SMTP_PASSWORD=your-app-specific-password

# Reporting
REPORT_EMAIL=recipient@example.com

# Database
DATABASE_PATH=smart_money.db
MIN_SCORE_FOR_EMAIL=60
```


## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GitHub Actions                         │
│                    (Daily @ 8 AM UTC)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
   │  13F Data   │  │  Form 4     │  │ Congressional│
   │  Collection │  │ Transactions│  │   Trades    │
   └─────────────┘  └─────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                    ▼ (Normalized)
             ┌──────────────────────┐
             │   Position Signals   │
             │   & Comparisons      │
             └──────┬───────────────┘
                    │
                    ▼ (Scored)
            ┌────────────────────┐
            │  AI Analysis &     │
            │  Scoring Engine    │
            └──────┬─────────────┘
                   │
                   ▼ (Filtered)
            ┌────────────────────┐
            │  High-Conviction   │
            │  Signals (60+ pts) │
            └──────┬─────────────┘
                   │
                   ▼ (Rendered)
          ┌────────────────────────┐
          │  Email Report Generated│
          └──────┬─────────────────┘
                 │
                 ▼ (Sent)
          ┌────────────────────────┐
          │  SMTP or Resend Email  │
          └────────────────────────┘
```

### Pipeline Layers

1. **Data Collection**: Fetches filings from SEC EDGAR API (13F quarterly reports, insider Form 4s) and congressional trades from official records
2. **Position Signals**: Compares current holdings to previous quarters, identifies new positions, increases, and insider buying activity
3. **Scoring**: Rules-based point system evaluates signal strength across multiple sources
4. **AI Analysis**: OpenAI GPT-4 synthesizes signals into human-readable insights and confidence ratings
5. **Email Report**: Formats stocks above minimum threshold with reasons and sends via your email provider


## Scoring System

The scoring engine awards points for different signal types. A stock must score **60 or higher** to be included in email reports.

| Signal Type | Points | Description |
|-------------|--------|-------------|
| New position | 40 | Investor opened a new position this quarter |
| Position +25-50% | 20 | Holdings increased 25-50% |
| Position +50%+ | 35 | Holdings increased more than 50% |
| Insider purchase | 30 | Company insider(s) bought shares |
| Multiple insider purchases | 40 | 2+ insiders purchased in same period |
| Congressional buy | 10 | One senator/representative bought stock |
| Congressional multiple buys | 15 | 2+ members of Congress bought |

**Score = Sum of applicable signals**

### Scoring Example

Berkshire adds 500K AAPL shares (new position +40) + insider CEO purchased (+30) = **70 points** → **Email included**

### Adjusting Threshold

Override the default minimum score:

```bash
python -m smart_money_tracker.main --min-score 50
```


## Database Schema

Smart Money Tracker uses SQLite for data persistence. Database location: `smart_money.db`

| Table | Purpose |
|-------|---------|
| `investors` | Tracked institutional investors (CIK, name) |
| `filings_13f` | Quarterly 13F SEC filings with dates |
| `holdings` | Individual stock positions from each 13F filing |
| `insider_transactions` | Form 4 insider buy/sell activity |
| `congressional_trades` | Trades by U.S. senators and representatives |
| `signals` | Generated trading signals with scores and reasons |
| `email_history` | Log of sent reports and delivery status |


## Running Tests

### Unit Tests

```bash
pytest
```

Run specific test file:
```bash
pytest tests/test_scoring.py -v
```

### Code Quality

Format code with Black:
```bash
black smart_money_tracker/
```

Lint with Ruff:
```bash
ruff check smart_money_tracker/
```

Both checks run automatically in CI/CD.


## Tracked Investors

The system monitors these 8 elite institutional investors:

1. **Berkshire Hathaway** - Warren Buffett's conglomerate (CIK: 0000086882)
2. **Pershing Square Capital** - Bill Ackman's activist fund (CIK: 0001336528)
3. **Scion Asset Management** - Michael Burry's fund (CIK: 0001649337)
4. **Appaloosa Management** - David Tepper's fund (CIK: 0001022317)
5. **Baupost Group** - Seth Klarman's value fund (CIK: 0000814979)
6. **Duquesne Capital** - Stanley Druckenmiller's fund (CIK: 0001311786)
7. **Third Point** - Dan Loeb's hedge fund (CIK: 0001086239)
8. **Icahn Capital** - Carl Icahn's portfolio (CIK: 0000796422)

### Adding New Investors

Edit `smart_money_tracker/config/investors.py`:

```python
TRACKED_INVESTORS = {
    "Berkshire Hathaway": "0000086882",
    "Your Fund Name": "0001234567",  # Add here
    # ... other investors
}
```

Get CIK from https://www.sec.gov/cgi-bin/browse-edgar

### Removing Investors

Simply delete the line from the `TRACKED_INVESTORS` dictionary.


## Extending the System

### Add a New Data Source

1. Create new file in `smart_money_tracker/data_collection/`:

```python
# smart_money_tracker/data_collection/my_source.py
from smart_money_tracker.data_collection.base import BaseDataCollector

class MySourceCollector(BaseDataCollector):
    def collect(self) -> List[Signal]:
        """Fetch and parse data from your source."""
        pass
```

2. Integrate into `ReportGenerator`:

```python
# In smart_money_tracker/reports/generator.py
from smart_money_tracker.data_collection.my_source import MySourceCollector

my_collector = MySourceCollector()
signals.extend(my_collector.collect())
```

### Adjust Scoring Rules

Edit point values in `smart_money_tracker/config/scoring_config.py`:

```python
SCORING_RULES = {
    "new_position": 50,        # Increase from 40
    "position_increase_gt_25pct": 25,
    # ... adjust other scores
}
```

### Modify Email Template

Edit `smart_money_tracker/email/renderer.py` to change email layout, colors, or content format.


## Troubleshooting

### No stocks in email

**Problem**: Email sent but with no stock suggestions.

**Solutions**:
- Check if data was collected: `python -m smart_money_tracker.main --dry-run`
- Lower the threshold: `--min-score 50` (default is 60)
- Verify API keys in `.env` are correct
- Check logs: `DEBUG=true python -m smart_money_tracker.main`

### Email not sending

**SMTP Issues**:
- Verify app-specific password (not account password) for Gmail
- Enable "Less secure app access" if using corporate email
- Check firewall allows SMTP port 587

**Resend Issues**:
- Verify API key is active at https://resend.com
- Check Resend sender domain is verified

### Database locked error

Stop any other process accessing `smart_money.db` and retry.

### Rate limit errors

Reduce request frequency or wait for quota reset. The collector implements exponential backoff.

### Debug Mode

Enable verbose logging:

```bash
DEBUG=true python -m smart_money_tracker.main --dry-run
```

Check logs for:
- Data collection success/failures
- Signal generation
- Score calculations
- Email rendering and sending


## Disclaimer

**Smart Money Tracker is not financial advice.** This tool aggregates public information from SEC filings and congressional disclosure records. It does not predict future performance, and past trading activity does not guarantee future results. Use signals as research starting points only. Always conduct your own analysis and consult a qualified financial advisor before trading. The authors make no guarantees about accuracy or completeness of data. Use at your own risk.


## License & Support

Licensed under the MIT License - see LICENSE file for details.

### Getting Help

- Check the Troubleshooting section above
- Review GitHub Issues for similar problems
- Enable debug mode with `DEBUG=true` flag
- Test with `--dry-run` before scheduling automation
