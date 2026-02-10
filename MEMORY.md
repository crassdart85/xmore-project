# Xmore Project Memory

## Project Overview
Stock trading prediction system with web dashboard. Uses multiple AI agents to predict stock movements.

**Last Updated**: February 10, 2026

## Deployment Architecture
- **Render.com** - Hosts web dashboard + PostgreSQL database
- **GitHub Actions** - Runs scheduled automation tasks
- **GitHub** - Source code repository

## Key Files
- `web-ui/public/app.js` - Frontend JavaScript (tabs, performance dashboard, TradingView, bilingual)
- `web-ui/public/style.css` - Dashboard styling with tabs, perf dashboard, RTL, responsive
- `web-ui/public/index.html` - Dashboard HTML (tabs, TradingView ticker, performance section)
- `web-ui/server.js` - Express API server (SQLite local, PostgreSQL production)
- `sentiment.py` - Finnhub news + FinBERT + VADER dual-engine sentiment
- `features.py` - 40+ TA-Lib technical indicators with pure Python fallback
- `data/egx_live_scraper.py` - EGX live feed scraper with yfinance fallback
- `data/egx_name_mapping.py` - Bilingual company name auto-generator
- `agents/agent_consensus.py` - Accuracy-weighted consensus voting agent
- `TERMS.md` - Legal terms of service
- `render.yaml` - Render deployment configuration
- `.github/workflows/scheduled-tasks.yml` - GitHub Actions automation
- `stocks.db` - SQLite database (local only)

## GitHub Actions Schedule
| Task | Schedule | Script |
|------|----------|---------|
| EGX Data Collection | Sun-Thu 12:30 PM EST | `collect_data.py` (EGX live → yfinance) |
| US Data + Sentiment | Mon-Fri 4:30 PM EST | `collect_data.py` + `sentiment.py` |
| Predictions | Mon-Fri 5:00 PM EST (daily, 1-day horizon) | `run_agents.py` (incl. Consensus) |
| Evaluation | Every hour | `evaluate.py` |

> **Note (Feb 2026):** Predictions changed from weekly (7-day) to daily (1-day) horizon for faster evaluation turnaround. GitHub Actions checkout upgraded to `actions/checkout@v4` with explicit `ref: main` and `fetch-depth: 1`.

## Environment Variables (Secrets)
- `DATABASE_URL` - PostgreSQL connection string (Render)
- `NEWS_API_KEY` - News API for news collection
- `FINNHUB_API_KEY` - Finnhub API for sentiment analysis news

## Tech Stack
- **Backend**: Node.js/Express (web-ui), Python (agents)
- **Database**: SQLite (local), PostgreSQL (production/Render)
- **Frontend**: Vanilla JS, CSS with animations
- **CI/CD**: GitHub Actions (`actions/checkout@v4`), Render auto-deploy

## Agents
- `MA_Crossover_Agent` - Moving average trend analysis
- `ML_RandomForest` - Machine learning with 40+ TA-Lib features, walk-forward validation
- `RSI_Agent` - Momentum indicator (RSI)
- `Volume_Spike_Agent` - Volume analysis
- `Consensus` - Accuracy-weighted vote across all agents (Phase 1)

## UI Features (Updated Feb 2026 — Phase 1)
1. **Tab Navigation** - Predictions, Performance, Results, Prices tabs
2. **Performance Dashboard** - Overall stats cards, per-stock table, monthly accuracy canvas chart
3. **TradingView Ticker Tape** - Live EGX30 + major stocks at top
4. **TradingView Mini Charts** - Lazy-loaded per-stock charts (click to load)
5. **Signal Terminology** - "Bullish/Bearish/Neutral" instead of "UP/DOWN/HOLD"
6. **Agent Accuracy Badges** - Per-agent accuracy shown on prediction cards
7. **Consensus Signal** - Weighted vote with agreement indicator
8. **Bilingual Disclaimers** - EN + AR legal disclaimers in footer, Terms link
9. **Dark Mode** - Toggle via header button, system preference detection
10. **Bilingual Support (EN/AR)** - Language switcher with RTL support
11. **Grouped Predictions** - Stock shown once with rowspan for multiple agents
12. **Agent Tooltips** - Hover descriptions explaining each agent (bilingual)
13. **Company Name Mapping** - US and EGX stocks with full names (bilingual)
14. **Color-coded Accuracy** - Green (60%+), Yellow (40-60%), Red (<40%)
15. **Responsive Design** - Breakpoints: 1024px, 768px, 480px, 360px
16. **Sentiment Badges** - Bullish/Neutral/Bearish badges per stock
17. **Print Styles** - Clean printing without TradingView/tabs/buttons
18. **Skeleton Loader** - Animated placeholder rows while predictions load
19. **Parallel Data Loading** - All API calls fire simultaneously on page load

## Sentiment Analysis (Phase 1 Upgrade)
- **Dual Engine**: VADER (fast, 1000+ headlines/sec) + FinBERT (deep accuracy)
- **Auto Mode**: VADER for >50 headlines, FinBERT for smaller batches
- **Source Weighting**: Bloomberg/Reuters prioritized over generic news
- **Source**: Finnhub API for company news
- **Storage**: `sentiment_scores` table with avg_sentiment, label, article counts
- **Integration**: Agents receive sentiment data to confirm/adjust signals
- **Display**: Color-coded badges (green=Bullish, gray=Neutral, red=Bearish)
- **API**: `/api/sentiment` endpoint returns latest sentiment per stock

## API Endpoints
- `/api/predictions` - Latest predictions from all agents (includes disclaimer)
- `/api/performance` - Agent accuracy statistics
- `/api/performance/detailed` - Full breakdown (per-agent, per-stock, monthly trend)
- `/api/evaluations` - Prediction results (predicted vs actual)
- `/api/sentiment` - Latest sentiment scores per stock
- `/api/prices` - Latest stock prices
- `/api/stats` - System statistics

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
- **DISTINCT ON**: PostgreSQL-specific syntax for latest records per symbol (used in `/api/prices` and `/api/sentiment`)
- **Prices query**: PostgreSQL uses `DISTINCT ON`, SQLite uses `JOIN + GROUP BY MAX(date)`

## Notes
- EGX stocks use `.CA` suffix (e.g., `COMI.CA`)
- Language preference stored in localStorage
- Dark mode preference stored in localStorage (key: `theme`)
- Server runs on port 3000 locally
- Production uses Render's DATABASE_URL for PostgreSQL
- Dashboard auto-refreshes data on language switch
- Prediction horizon: 1 day (changed from 7 days for faster evaluation)

## Recent Changes (Feb 2026)
- **Dashboard Load Performance**: Parallelized API calls, eliminated duplicate fetch, optimized SQL, skeleton loader
- **Dark Mode Toggle**: Added `.theme-btn` with sun/moon icons, CSS custom properties, system preference detection
- **Daily Predictions**: 1-day horizon for faster evaluation turnaround
- **GitHub Actions Upgraded**: All jobs now use `actions/checkout@v4`

## Phase 1 Upgrade (Feb 2026)
- **EGX Live Scraper**: `data/egx_live_scraper.py` scrapes live EGX feed with yfinance fallback
- **TA-Lib Integration**: `features.py` rewritten with 40+ indicators, pure Python fallback
- **VADER Sentiment**: Dual-engine (VADER fast + FinBERT deep) with auto mode and source weighting
- **Performance Dashboard**: Tabbed UI, per-agent/per-stock stats, monthly accuracy chart (canvas)
- **TradingView Widgets**: Ticker tape + lazy-loaded mini charts, locale-aware
- **Compliance**: Signal terminology → Bullish/Bearish, bilingual disclaimers, `TERMS.md`
- **Consensus Agent**: `agents/agent_consensus.py` — accuracy-weighted voting across all agents
- **Dependencies Added**: `lxml`, `vaderSentiment`, `quantstats`, `TA-Lib`
