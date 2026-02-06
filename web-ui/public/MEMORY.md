# Xmore Project Memory

## Project Overview
Stock trading prediction system with web dashboard. Uses multiple AI agents to predict stock movements.

## Deployment Architecture
- **Render.com** - Hosts web dashboard + PostgreSQL database
- **GitHub Actions** - Runs scheduled automation tasks
- **GitHub** - Source code repository

## Key Files
- `web-ui/public/app.js` - Frontend JavaScript (API calls, bilingual support, grouped predictions, sentiment badges)
- `web-ui/public/style.css` - Dashboard styling with RTL and responsive support
- `web-ui/public/index.html` - Dashboard HTML structure
- `web-ui/server.js` - Express API server (SQLite local, PostgreSQL production)
- `sentiment.py` - Finnhub news + FinBERT sentiment analysis
- `render.yaml` - Render deployment configuration
- `.github/workflows/scheduled-tasks.yml` - GitHub Actions automation
- `stocks.db` - SQLite database (local only)

## GitHub Actions Schedule
| Task | Schedule | Script |
|------|----------|--------|
| Data Collection + Sentiment | Mon-Fri 4:30 PM EST | `collect_data.py` + `sentiment.py` |
| Predictions | Friday 6 PM EST | `run_agents.py` |
| Evaluation | Every hour | `evaluate.py` |

## Environment Variables (Secrets)
- `DATABASE_URL` - PostgreSQL connection string (Render)
- `NEWS_API_KEY` - News API for news collection
- `FINNHUB_API_KEY` - Finnhub API for sentiment analysis news

## Tech Stack
- **Backend**: Node.js/Express (web-ui), Python (agents)
- **Database**: SQLite (local), PostgreSQL (production/Render)
- **Frontend**: Vanilla JS, CSS with animations
- **CI/CD**: GitHub Actions, Render auto-deploy

## Agents
- `MA_Crossover_Agent` - Moving average trend analysis
- `ML_RandomForest` - Machine learning price predictor
- `RSI_Agent` - Momentum indicator (RSI)
- `Volume_Spike_Agent` - Volume analysis

## UI Features (Feb 2025)
1. **Bilingual Support (EN/AR)** - Language switcher with RTL support
2. **Grouped Predictions** - Stock shown once with rowspan for multiple agents
3. **Agent Tooltips** - Hover descriptions explaining each agent (bilingual)
4. **Company Name Mapping** - US and EGX stocks with full names (bilingual)
5. **Color-coded Accuracy** - Green (60%+), Yellow (40-60%), Red (<40%)
6. **Responsive Design** - Breakpoints: 1024px, 768px, 480px, 360px
7. **Touch Optimized** - 44px+ touch targets, no hover on touch devices
8. **Print Styles** - Clean printing without buttons
9. **Sentiment Badges** - Bullish/Neutral/Bearish badges per stock (color-coded)
10. **User-Friendly Messages** - Friendly status messages instead of technical errors

## Sentiment Analysis (Feb 2025)
- **Source**: Finnhub API for company news
- **Model**: FinBERT (ProsusAI/finbert) for financial sentiment
- **Storage**: `sentiment_scores` table with avg_sentiment, label, article counts
- **Integration**: Agents receive sentiment data to confirm/adjust signals
- **Display**: Color-coded badges (green=Bullish, gray=Neutral, red=Bearish)
- **API**: `/api/sentiment` endpoint returns latest sentiment per stock

## Common Tasks
**Local Development:**
- Start server: `cd web-ui && npm install && node server.js`
- Run agents: `python run_agents.py`
- Evaluate predictions: `python evaluate.py`
- Collect data: `python collect_data.py`
- Collect sentiment: `python sentiment.py` (requires FINNHUB_API_KEY)

**Production (Render):**
- Auto-deploys on push to main branch
- Dashboard: trading-dashboard service
- Database: trading-db PostgreSQL

## Troubleshooting
- **"Performance tracking will begin..."** - Normal message when no evaluations exist yet. Wait for hourly GitHub Action
- **"N/A" sentiment badges** - Run `python sentiment.py` or check FINNHUB_API_KEY secret
- **Server errors** - Run `npm install` in web-ui folder, then restart server
- **Browser cache** - Hard refresh (Ctrl+Shift+R) after code changes
- **GitHub Actions failing** - Check secrets: DATABASE_URL, NEWS_API_KEY, FINNHUB_API_KEY
- **Render not updating** - Wait 2-3 minutes after push for auto-deploy

## Database Compatibility
- **Boolean handling**: PostgreSQL uses `true/false`, SQLite uses `1/0`
- **Missing tables**: API returns empty array `[]` instead of 500 error
- **DISTINCT ON**: PostgreSQL-specific syntax for latest records per symbol

## Notes
- EGX stocks use `.CA` suffix (e.g., `COMI.CA`)
- Language preference stored in localStorage
- Server runs on port 3000 locally
- Production uses Render's DATABASE_URL for PostgreSQL
- Dashboard auto-refreshes data on language switch
