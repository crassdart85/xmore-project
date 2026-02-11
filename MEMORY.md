# Xmore Project Memory

## Project Overview
Stock trading prediction system with web dashboard. Uses multiple AI agents to predict stock movements.

**Last Updated**: February 12, 2026

## Deployment Architecture
- **Render.com** - Hosts web dashboard + PostgreSQL database
- **GitHub Actions** - Runs scheduled automation tasks
- **GitHub** - Source code repository

## Key Files
- `engines/trade_recommender.py` - Daily trade signal generator (Phase 2)
- `engines/evaluate_performance.py` - **NEW** Performance evaluation engine (replaces `evaluate_trades.py`)
- `engines/performance_metrics.py` - **NEW** Professional financial metrics calculator (Sharpe, alpha, drawdown)
- `engines/briefing_generator.py` - Daily market briefing generator (now includes track record snippet)
- `evaluate_trades.py` - Trade recommendation accuracy tracker (legacy — superseded by `evaluate_performance.py`)
- `web-ui/routes/trades.js` - API routes for trades and portfolio
- `web-ui/routes/performance.js` - **NEW** Investor-grade performance API routes (`/api/performance-v2/*`)
- `web-ui/public/trades.js` - Frontend logic for trades dashboard
- `web-ui/public/performance-dashboard.js` - **NEW** Performance dashboard UI (canvas chart, agent table, audit modal)
- `web-ui/public/performance-dashboard.css` - **NEW** Performance dashboard styling (dark/light, RTL, responsive)
- `web-ui/public/app.js` - Frontend JavaScript (tabs, TradingView, bilingual)
- `web-ui/public/style.css` - Dashboard styling with tabs, RTL, responsive
- `web-ui/public/index.html` - Dashboard HTML (tabs, TradingView ticker, performance section)
- `web-ui/server.js` - Express API server (SQLite local, PostgreSQL production)
- `web-ui/migrations/007_performance_benchmark.sql` - **NEW** Performance schema migration
- `sentiment.py` - Finnhub news + FinBERT + VADER dual-engine sentiment
- `features.py` - 40+ TA-Lib technical indicators with pure Python fallback
- `data/egx_live_scraper.py` - EGX live feed scraper with yfinance fallback
- `data/egx_name_mapping.py` - Bilingual company name auto-generator
- `agents/agent_consensus.py` - Accuracy-weighted consensus voting agent
- `database.py` - Database connection + table creation (now includes performance tables)
- `TERMS.md` - Legal terms of service
- `docs/PERFORMANCE_SYSTEM.md` - **NEW** Performance system architecture document
- `render.yaml` - Render deployment configuration
- `.github/workflows/scheduled-tasks.yml` - GitHub Actions automation
- `stocks.db` - SQLite database (local only)

## GitHub Actions Schedule
| Task | Schedule | Script |
|------|----------|---------|
| EGX Data Collection | Sun-Thu 12:30 PM EST | `collect_data.py` (EGX live → yfinance) |
| US Data + Sentiment | Mon-Fri 4:30 PM EST | `collect_data.py` + `sentiment.py` |
| Predictions | Sun-Fri 5:00 PM EST (daily, 1-day) | `run_agents.py` (incl. Consensus, Trades, Performance Eval) |
| Performance Eval | Daily (Step 8 in pipeline) | `engines/evaluate_performance.py` (called by `run_agents.py`) |
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
- **Trade Recommendation Engine** - Generates actionable Buy/Sell signals with entry/exit targets (Phase 2)
- **Performance Evaluation Engine** - Resolves outcomes, calculates alpha vs EGX30 benchmark, agent accuracy snapshots (Phase 3)

## UI Features (Updated Feb 2026)
1. **Tab Navigation** - Predictions, Performance, Results, Prices tabs
2. **Performance Dashboard (v2)** - Investor-grade dashboard with key metrics cards, equity curve chart, agent accuracy table, best/worst stocks, recent predictions, rolling windows, integrity section, and audit log modal
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
20. **Trades Dashboard** - "Today's Recommendations" tab with actionable signals (Phase 2)
21. **Portfolio Tracker** - "Portfolio" tab showing open positions and history (Phase 2)
22. **Trade Cards** - detailed visual cards with Conviction, R/R ratio, and bilingual reasoning
23. **Portfolio Performance** - Real-time P&L tracking for virtual portfolio
24. **Equity Curve Chart** - Canvas-rendered cumulative return chart (Xmore vs EGX30 benchmark) with period selector
25. **Agent Accuracy Table** - Per-agent 30d/90d win rate, predictions count, avg confidence
26. **Audit Trail Modal** - View all prediction modification logs for full transparency
27. **Integrity Section** - Immutability status, audit trail, live-only indicator, minimum threshold progress

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
- `/api/performance` - Agent accuracy statistics (legacy)
- `/api/performance/detailed` - Full breakdown (per-agent, per-stock, monthly trend) (legacy)
- `/api/performance-v2/summary` - **NEW** Investor-grade overall performance + rolling metrics
- `/api/performance-v2/by-agent` - **NEW** Per-agent accuracy comparison (latest daily snapshot)
- `/api/performance-v2/by-stock?days=N` - **NEW** Per-stock performance breakdown
- `/api/performance-v2/equity-curve?days=N` - **NEW** Cumulative return series (Xmore vs EGX30)
- `/api/performance-v2/predictions/open` - **NEW** Currently open (unresolved) predictions
- `/api/performance-v2/predictions/history?page=N&limit=N` - **NEW** Auditable prediction history
- `/api/performance-v2/audit?limit=N` - **NEW** Prediction modification audit trail
- `/api/evaluations` - Prediction results (predicted vs actual)
- `/api/sentiment` - Latest sentiment scores per stock
- `/api/prices` - Latest stock prices
- `/api/trades/today` - Today's active trade recommendations
- `/api/trades/history` - Historical trade recommendations
- `/api/portfolio` - User portfolio (open positions, performance stats)
- `/api/stats` - System statistics

## Common Tasks
**Local Development:**
- Start server: `cd web-ui && npm install && node server.js`
- Run agents: `python run_agents.py` (includes performance evaluation as Step 8)
- Evaluate predictions: `python evaluate.py`
- Evaluate performance: `python -c "from engines.evaluate_performance import run_evaluation; run_evaluation()"`
- Evaluate trades (legacy): `python evaluate_trades.py`
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
- **Browser cache** - Hard refresh (Ctrl+Shift+R) after code changes; static assets use `?v=` cache-busting
- **GitHub Actions failing** - Check secrets: DATABASE_URL, NEWS_API_KEY, FINNHUB_API_KEY
- **Render not updating** - Wait 2-3 minutes after push for auto-deploy
- **Blank dashboard / no data** - Check browser console for JS errors; `window.onerror` handler shows errors on-page

## Database Tables

### Core Tables
| Table | Purpose |
|-------|---------|
| `prices` | Historical OHLCV data |
| `news` | News articles with sentiment |
| `predictions` | Per-agent predictions |
| `consensus_results` | Consensus engine output |
| `evaluations` | Prediction outcomes |
| `sentiment_scores` | Aggregated sentiment |
| `trade_recommendations` | Daily trade signals |
| `user_positions` | Virtual portfolio positions |
| `daily_briefings` | Generated daily briefings |
| `prediction_audit_log` | **NEW** Audit trail for outcome changes |
| `agent_performance_daily` | **NEW** Per-agent rolling accuracy snapshots |

### Performance Columns Added
- `trade_recommendations`: `benchmark_1d_return`, `alpha_1d`, `benchmark_5d_return`, `alpha_5d`, `is_live`
- `user_positions`: `benchmark_return_pct`, `alpha_pct`

## Database Compatibility
- **Boolean handling**: PostgreSQL uses `true/false`, SQLite uses `1/0`
- **Missing tables**: API returns empty array `[]` instead of 500 error
- **DISTINCT ON**: PostgreSQL-specific syntax for latest records per symbol (used in `/api/prices` and `/api/sentiment`)
- **Prices query**: PostgreSQL uses `DISTINCT ON`, SQLite uses `JOIN + GROUP BY MAX(date)`
- **Immutability triggers**: PostgreSQL only (prevents core prediction field mutations)
- **Materialized views**: PostgreSQL only (`mv_performance_global`); SQLite computes on-the-fly
- **FILTER clause**: PostgreSQL uses `FILTER (WHERE ...)`, SQLite uses `CASE WHEN` equivalent
- **ALTER TABLE**: Wrapped in try/except for safe column additions on both engines

## Notes
- EGX stocks use `.CA` suffix (e.g., `COMI.CA`)
- Language preference stored in localStorage
- Dark mode preference stored in localStorage (key: `theme`)
- Server runs on port 3000 locally
- Production uses Render's DATABASE_URL for PostgreSQL
- Dashboard auto-refreshes data on language switch
- Prediction horizon: 1 day (changed from 7 days for faster evaluation)

## Recent Changes (Feb 2026)
- **Institutional Dashboard UX Upgrade (Feb 12, 2026)**:
  - Added **Global Performance Snapshot Bar** under header with live-only badge, 30D alpha vs EGX30, 30D Sharpe, 30D max drawdown, 30D rolling win rate, and 100-trade progress bar
  - Refactored **Predictions tab** to be **stock-first** (consensus signal, agreement %, conviction, recent symbol accuracy) with expandable per-agent breakdown and structured "Why This Signal?" grid
  - Rebuilt **Performance tab** into institutional section flow:
    - Proof of Edge (alpha/sharpe/drawdown + upgraded equity curve)
    - Stability Metrics (30/60/90 + volatility + profit factor)
    - Agent Accountability (sortable comparison fields + mini weight visual)
    - Transparency & Integrity (immutable history table, audit modal, trade-threshold progress)
    - Since Inception summary block
  - Added **System Health badge** logic on Performance tab:
    - Stable: Sharpe > 1, positive alpha, drawdown controlled
    - Watch: borderline metrics
    - Degraded: weakening profile
  - Upgraded **equity curve chart** (canvas) with:
    - Hover tooltip (Xmore return, EGX30 return, alpha)
    - Toggle benchmark line on/off
    - Toggle drawdown shading on/off
    - Mobile-responsive interaction model
  - Expanded `/api/performance-v2/summary` output to include:
    - Global: `sharpe_ratio`, `max_drawdown`, `volatility`, `profit_factor`
    - Rolling: `30d`, `60d`, `90d` windows with risk and stability fields
  - Preserved bilingual support (EN/AR), RTL/LTR consistency, dark/light mode behavior, and responsive layout
- **Bug Fixes (Critical)**:
  - Fixed `init-db.js` missing `sentiment_scores` table creation (sync with `database.py`)
  - Fixed `agents/agent_ma.py` off-by-one error and "fresh crossover" logic flaw
  - Fixed `lxml` dependency for EGX live scraper
  - Added `finnhub-python` dependency for sentiment analysis
- **TDZ Fix**: `applyTheme()` crashed accessing `const TRANSLATIONS` before init; wrapped in try/catch
- **Predictions Workflow Fix**: Removed broken `needs: daily-collection` dependency that prevented `daily-predictions` from ever running on schedule
- **Dashboard Load Performance**: Parallelized API calls, eliminated duplicate fetch, optimized SQL, skeleton loader
- **Cache-Busting**: Static assets use `?v=` query params; `window.onerror` shows JS errors on-page
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

## Phase 3 Upgrade: Performance System (Feb 12, 2026)
- **Performance Evaluation Engine** (`engines/evaluate_performance.py`): Resolves 1d/5d outcomes, calculates EGX30 benchmark returns + alpha, updates agent accuracy snapshots, refreshes materialized views
- **Performance Metrics Calculator** (`engines/performance_metrics.py`): Sharpe ratio, Sortino ratio, max drawdown, profit factor, rolling windows, equity curve data, agent comparison
- **Investor-Grade API** (`web-ui/routes/performance.js`): 7 public endpoints under `/api/performance-v2/` — summary, by-agent, by-stock, equity-curve, predictions/open, predictions/history, audit
- **Performance Dashboard** (`web-ui/public/performance-dashboard.js` + `.css`): Premium dark/light dashboard with key metrics grid, canvas equity curve chart, agent accuracy table, stock chips, prediction history pagination, audit modal, integrity section, bilingual support
- **Database Schema** (`007_performance_benchmark.sql`, `database.py`): Immutability triggers, audit trail table, benchmark columns, agent performance table, materialized view
- **Pipeline Integration** (`run_agents.py`): Performance evaluation added as Step 8 after briefing generation
- **Briefing Track Record** (`engines/briefing_generator.py`): Daily briefing now includes 30-day rolling performance snippet
- **Data Integrity**: Core predictions immutable (PostgreSQL triggers), all outcome changes audited, live-only metrics, 100-trade minimum threshold
- **See**: `docs/PERFORMANCE_SYSTEM.md` for full architecture documentation
