# Xmore Project Memory

## Project Overview
Stock trading prediction system with web dashboard. Uses multiple AI agents to predict stock movements.

**Last Updated**: February 15, 2026

## Deployment Architecture
- **Render.com** - Hosts web dashboard + PostgreSQL database
- **GitHub Actions** - Runs scheduled automation tasks
- **GitHub** - Source code repository

## Key Files
- `engines/trade_recommender.py` - Daily trade signal generator (Phase 2)
- `engines/evaluate_performance.py` - **NEW** Performance evaluation engine (replaces `evaluate_trades.py`)
- `engines/performance_metrics.py` - **NEW** Professional financial metrics calculator (Sharpe, alpha, drawdown)
- `engines/briefing_generator.py` - Daily market briefing generator (now includes track record snippet)
- `engines/portfolio_config.py` - **NEW** Portfolio archetype configurations (Conservative/Balanced/Aggressive)
- `engines/portfolio_engine.py` - **NEW** Signal-to-allocation pipeline (5-step: collect ? filter ? score ? allocate ? publish)
- `engines/circuit_breaker.py` - **NEW** Drawdown circuit breaker (increases cash when drawdown exceeds threshold)
- `engines/generate_portfolios.py` - **NEW** Cron orchestrator for portfolio generation (runs after daily predictions)
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
- `web-ui/migrations/008_model_portfolios.sql` - **NEW** Portfolio tables migration (model_portfolios, portfolio_allocations, portfolio_performance)
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
- `tests/test_portfolio_engine.py` - **NEW** Portfolio engine unit tests (constraints, allocation math, edge cases)
- `stocks.db` - SQLite database (local only)

## GitHub Actions Schedule
| Task | Schedule | Script |
|------|----------|---------|
| EGX Data Collection | Sun-Thu 12:30 PM EST | `collect_data.py` (EGX live → yfinance) |
| US Data + Sentiment | Mon-Fri 4:30 PM EST | `collect_data.py` + `sentiment.py` |
| Predictions | Sun-Fri 5:00 PM EST (daily, 1-day) | `run_agents.py` (incl. Consensus, Trades, Performance Eval) |
| Portfolio Generation | Daily (after predictions) | `engines/generate_portfolios.py` (needs: daily-predictions) |
| Performance Eval | Daily (Step 8 in pipeline) | `engines/evaluate_performance.py` (called by `run_agents.py`) |
| Evaluation | Every hour | `evaluate.py` |

> **Note (Feb 2026):** Predictions changed from weekly (7-day) to daily (1-day) horizon for faster evaluation turnaround. GitHub Actions checkout upgraded to `actions/checkout@v4` with explicit `ref: main` and `fetch-depth: 1`.

## Environment Variables (Secrets)
- `DATABASE_URL` - PostgreSQL connection string (Render)
- `JWT_SECRET` - JWT signing secret for auth cookies (required for stable sessions in production)
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

### Portfolio Endpoints (Phase 2 � Planned)
- `GET /api/portfolios` - List portfolio types with latest snapshot
- `GET /api/portfolios/:type` - Full allocation detail for a portfolio type (preview: free / full: auth)
- `GET /api/portfolios/:type/performance` - Historical performance + metrics
- `GET /api/portfolios/:type/history` - All past snapshots and rebalances (auth)
- `GET /api/portfolios/:type/compare` - Side-by-side with EGX30
- `POST /api/portfolios/simulate` - Simulate allocation with custom amount (auth)
- `GET /api/portfolios/changes` - Latest rebalance changes (auth)

## Common Tasks
**Local Development:**
- Start server: `cd web-ui && npm install && node server.js`
- Run agents: `python run_agents.py` (includes performance evaluation as Step 8)
- Evaluate predictions: `python evaluate.py`
- Evaluate performance: `python -c "from engines.evaluate_performance import run_evaluation; run_evaluation()"`
- Generate portfolios: `python engines/generate_portfolios.py`
- Run portfolio tests: `python -m pytest tests/test_portfolio_engine.py -v`
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
| `model_portfolios` | **NEW** Portfolio snapshots per archetype (immutable once deactivated) |
| `portfolio_allocations` | **NEW** Per-stock allocation weights within a portfolio snapshot |
| `portfolio_performance` | **NEW** Daily performance tracking (return, alpha, Sharpe, drawdown) |

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
- **Portfolio immutability triggers**: PostgreSQL only (prevents UPDATE/DELETE on deactivated portfolio snapshots)
- **Auto-deactivation**: PostgreSQL trigger deactivates previous active portfolio of same type on new insert

## Notes
- EGX stocks use `.CA` suffix (e.g., `COMI.CA`)
- Language preference stored in localStorage
- Dark mode preference stored in localStorage (key: `theme`)
- Server runs on port 3000 locally
- Production uses Render's DATABASE_URL for PostgreSQL
- Dashboard auto-refreshes data on language switch
- Prediction horizon: 1 day (changed from 7 days for faster evaluation)

## Recent Changes (Feb 2026)
- **Auth + Deployment Hotfix (Feb 15, 2026)**:
  - Updated `web-ui/middleware/auth.js` startup behavior:
    - Production now auto-generates an ephemeral JWT secret if `JWT_SECRET` is missing (service can boot)
    - Logs explicit warning that sessions will be invalidated on restart until `JWT_SECRET` is configured
    - Local/dev still supports a fallback secret with warning
  - Updated `render.yaml` to include `JWT_SECRET` with `generateValue: true` for Render Blueprint provisioning
  - Deployment note: existing Render services may still require manual env var set/redeploy to apply new secret
- **Security + Reliability Hardening (Feb 14, 2026)**:
  - Enforced required `JWT_SECRET` in `web-ui/middleware/auth.js` (removed insecure default fallback)
  - Tightened CORS behavior in `web-ui/server.js` to support explicit allowlist via `CORS_ALLOWED_ORIGINS`
  - Fixed fragile SQLite placeholder conversion (`$1..$N` ? `?`) in `web-ui/routes/trades.js` and `web-ui/routes/briefing.js`
  - Added safe JSON parsing guard for trade reasons in `web-ui/routes/trades.js`
  - Reduced broad `SELECT *` usage in `web-ui/routes/performance.js` and `web-ui/server.js` consensus detail endpoint
- **Portfolio Engine Data Quality Improvements (Feb 14, 2026)**:
  - Deduplicated portfolio signal collection by symbol in `engines/portfolio_engine.py`
  - Updated `engines/generate_portfolios.py` to compute portfolio-specific daily performance snapshots using allocation-weighted returns (instead of copying global metrics)
- **Frontend Safety + UX Improvements (Feb 14, 2026)**:
  - Added HTML escaping helpers in `web-ui/public/trades.js` and `web-ui/public/watchlist.js` to reduce XSS risk from rendered dynamic values
  - Improved watchlist empty state with actionable "Add Stock" CTA
  - Added accessibility `aria-label` on watchlist remove button
  - Added lightweight loading placeholders for trades/portfolio views
- **Portfolio Engine Phase 1 (Feb 14, 2026)**:
  - Added migration `web-ui/migrations/008_model_portfolios.sql` with new tables:
    - `model_portfolios` (portfolio snapshots)
    - `portfolio_allocations` (per-stock weights)
    - `portfolio_performance` (daily performance tracking)
  - Added PostgreSQL trigger/function protections in migration:
    - Prevent UPDATE/DELETE for inactive portfolio snapshots (`is_active = FALSE`)
    - Auto-deactivate previous active portfolio of same `portfolio_type` when inserting a new active one
  - Added archetype configuration module `engines/portfolio_config.py`:
    - `CONSERVATIVE_CONFIG` (Al-Aman)
    - `BALANCED_CONFIG` (Al-Mizan)
    - `AGGRESSIVE_CONFIG` (Al-Numu)
  - Added signal-to-allocation engine `engines/portfolio_engine.py` with 5-step pipeline:
    - collect active signals
    - filter by archetype rules
    - score/rank
    - constrained weight allocation
    - validate/publish to portfolio tables
  - Added drawdown protection in `engines/circuit_breaker.py`:
    - Increases cash allocation when latest drawdown exceeds archetype threshold
  - Added cron orchestrator `engines/generate_portfolios.py`:
    - Rebalance cadence by archetype (30/14/7 days)
    - Runs full generation flow and writes daily `portfolio_performance` snapshots
  - Added test suite `tests/test_portfolio_engine.py`:
    - constraint enforcement
    - total allocation integrity
    - cash floor checks
    - edge cases (no signals, single signal)
  - Updated workflow `.github/workflows/scheduled-tasks.yml`:
    - Added `portfolio-generation` job
    - Runs after `daily-predictions` (`needs: daily-predictions`)
    - Executes `python engines/generate_portfolios.py`
- **Screen Briefs + Translation Coverage (Feb 12, 2026)**:
  - Added short novice-friendly "what this screen does" briefs across all major tabs in `web-ui/public/index.html`:
    - Predictions, Briefing, Trades, Portfolio, Watchlist, Consensus, Performance, Results, Prices
  - Added stable IDs for each brief line so copy can be language-switched dynamically
  - Added EN + AR translation keys in `web-ui/public/app.js`:
    - `predictionsBrief`, `briefingBrief`, `tradesBrief`, `portfolioBrief`, `watchlistBrief`, `consensusBrief`, `performanceBrief`, `resultsBrief`, `pricesBrief`
  - Updated `applyLanguage()` in `web-ui/public/app.js` to map all new brief keys to DOM on language toggle (EN/AR)
- **Results Tab UX Refresh (Feb 12, 2026)**:
  - Added a single centered Results tab heading (`resultsTitle`) for cleaner section framing
  - Reworked `/api/evaluations` rendering from one flat table to **stock-grouped cards** in `web-ui/public/app.js`
  - Each stock now has a distinct visual card (accent tone, symbol/company header) to avoid similar-looking rows
  - Kept per-agent evaluation details inside each stock card and sorted rows by **newest `target_date` first**
  - Added dedicated styles in `web-ui/public/style.css` for grouped Results layout and responsive table wrapping
- **Frontend Stability Guard (Feb 12, 2026)**:
  - Fixed critical browser stack overflow in `web-ui/public/briefing.js` caused by recursive global export (`window.loadBriefing` self-call loop)
  - Corrected export to direct binding: `window.loadBriefing = loadBriefing;`
  - Added `web-ui/scripts/check-frontend-exports.js` to fail builds on recursive `window.*` export wrappers
  - Added `npm run check` in `web-ui/package.json` to run recursion guard + `node --check` on frontend JS files
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





