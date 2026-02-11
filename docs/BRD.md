# 📊 Business Requirements Document (BRD)
# Xmore Stock Prediction System

---

## Document Control

| Field | Details |
|-------|---------|
| **Document Title** | Xmore Stock Prediction System - BRD |
| **Version** | 1.1 |
| **Date** | February 11, 2026 |
| **Author** | Project Team |
| **Status** | Active Development |
| **Repository** | [github.com/crassdart85/xmore-project](https://github.com/crassdart85/xmore-project) |

---

## 1. Executive Summary

### 1.1 Project Overview

**Xmore** is an advanced AI-powered stock market prediction system designed to forecast price movements for stocks traded on the **Egyptian Exchange (EGX)** and optionally **US stock markets**. The system leverages ensemble machine learning techniques combined with sentiment analysis to provide actionable buy/sell/hold recommendations to traders and investors.

### 1.2 Business Objective

To provide retail and institutional investors with an intelligent, data-driven decision support system that:

- Predicts stock price movements with measurable accuracy
- Reduces emotional bias in trading decisions
- Automates data collection, analysis, and prediction workflows
- Delivers insights through an intuitive, bilingual (English/Arabic) web dashboard

### 1.3 Value Proposition

| Benefit | Description |
|---------|-------------|
| **Time Savings** | Automated data collection and analysis eliminates hours of manual research |
| **Enhanced Accuracy** | Multi-agent ensemble approach improves prediction reliability |
| **Sentiment Integration** | FinBERT-powered news analysis captures market sentiment |
| **Regional Focus** | Specialized support for EGX 30 index constituents |
| **Accessibility** | Bilingual interface serves both English and Arabic speaking users |

---

## 2. Business Context

### 2.1 Target Market

| Segment | Description |
|---------|-------------|
| **Primary** | Egyptian retail investors and traders seeking data-driven insights |
| **Secondary** | Investment advisors and portfolio managers in the MENA region |
| **Tertiary** | Quantitative trading enthusiasts and fintech developers |

### 2.2 Market Opportunity

- The Egyptian Exchange (EGX) represents one of the oldest and most active stock markets in the Middle East and Africa
- Growing demand for AI-powered trading tools in emerging markets
- Limited availability of localized trading prediction systems for Arabic-speaking investors
- Increasing retail investor participation in EGX following market digitization initiatives

### 2.3 Competitive Landscape

| Competitor Type | Xmore Differentiation |
|-----------------|----------------------|
| General Trading Platforms | Specialized ML prediction with sentiment analysis |
| US-Focused AI Tools | Native EGX support with regional market understanding |
| Basic Technical Analysis Tools | Ensemble ML agents combining multiple strategies |
| English-Only Platforms | Full Arabic/RTL language support |

---

## 3. Stakeholders

| Stakeholder | Role | Interest |
|-------------|------|----------|
| **End Users** | Traders/Investors | Accurate predictions, easy-to-use dashboard |
| **Product Owner** | Project Sponsor | System reliability, feature delivery |
| **Development Team** | Engineers | Code quality, maintainability |
| **Data Providers** | Yahoo Finance, Finnhub, NewsAPI | API usage compliance |
| **Hosting Providers** | Render, GitHub | Uptime, performance |

---

## 4. Functional Requirements

### 4.1 Data Collection & Management

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| **FR-DC-001** | System shall collect daily OHLCV (Open, High, Low, Close, Volume) price data from Yahoo Finance | High | ✅ Implemented |
| **FR-DC-002** | System shall fetch financial news from multiple sources (NewsAPI, Finnhub, RSS feeds) | High | ✅ Implemented |
| **FR-DC-003** | System shall support EGX stocks with `.CA` suffix notation | High | ✅ Implemented |
| **FR-DC-004** | System shall store all data in a relational database (SQLite local, PostgreSQL production) | High | ✅ Implemented |
| **FR-DC-005** | System shall maintain 90 days of historical price data for indicator calculations | Medium | ✅ Implemented |
| **FR-DC-006** | System shall handle market holidays and trading gaps gracefully | Medium | ✅ Implemented |

### 4.2 Sentiment Analysis

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| **FR-SA-001** | System shall analyze news headlines using FinBERT (financial BERT model) | High | ✅ Implemented |
| **FR-SA-002** | System shall classify sentiment as Bullish, Neutral, or Bearish | High | ✅ Implemented |
| **FR-SA-003** | System shall store sentiment scores (-1 to +1 scale) with article counts | High | ✅ Implemented |
| **FR-SA-004** | System shall integrate sentiment data into prediction models | High | ✅ Implemented |
| **FR-SA-005** | System shall display sentiment badges on the dashboard | Medium | ✅ Implemented |

### 4.3 Prediction Engine (AI Agents)

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| **FR-PE-001** | System shall implement multiple prediction agents with distinct strategies | High | ✅ Implemented |
| **FR-PE-002** | MA_Crossover_Agent: Analyze moving average crossovers (10-day/30-day) | High | ✅ Implemented |
| **FR-PE-003** | ML_RandomForest: Ensemble machine learning price predictor | High | ✅ Implemented |
| **FR-PE-004** | RSI_Agent: Relative Strength Index momentum analysis | High | ✅ Implemented |
| **FR-PE-005** | Volume_Spike_Agent: Volume anomaly detection | High | ✅ Implemented |
| **FR-PE-006** | System shall generate predictions for 5-7 day horizons | High | ✅ Implemented |
| **FR-PE-007** | System shall output confidence scores (0-100%) for each prediction | High | ✅ Implemented |
| **FR-PE-008** | System shall classify predictions as UP (Buy), DOWN (Sell), or FLAT (Hold) | High | ✅ Implemented |
| **FR-PE-009** | System shall provide a Consensus signal by aggregating agent predictions weighted by historical accuracy | High | ✅ Implemented |
| **FR-PE-010** | System shall calculate agreement confidence for consensus (0-100%) | Medium | ✅ Implemented |

### 4.4 Evaluation & Performance Tracking

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| **FR-EV-001** | System shall evaluate predictions against actual price movements | High | ✅ Implemented |
| **FR-EV-002** | System shall track accuracy metrics per agent | High | ✅ Implemented |
| **FR-EV-003** | System shall use 0.5% minimum move threshold for evaluation | Medium | ✅ Implemented |
| **FR-EV-004** | System shall display historical accuracy on dashboard | Medium | ✅ Implemented |
| **FR-EV-005** | System shall support TimeSeriesSplit validation for model training | Medium | ✅ Implemented |

### 4.5 Web Dashboard

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| **FR-UI-001** | System shall provide a web-based dashboard for prediction visualization | High | ✅ Implemented |
| **FR-UI-002** | Dashboard shall support bilingual interface (English/Arabic) | High | ✅ Implemented |
| **FR-UI-003** | Dashboard shall support RTL (Right-to-Left) text direction for Arabic | High | ✅ Implemented |
| **FR-UI-004** | Dashboard shall display grouped predictions by stock with agent details | High | ✅ Implemented |
| **FR-UI-005** | Dashboard shall show agent tooltips explaining each strategy | Medium | ✅ Implemented |
| **FR-UI-006** | Dashboard shall display company names in both English and Arabic | Medium | ✅ Implemented |
| **FR-UI-007** | Dashboard shall use color-coded accuracy indicators (Green/Yellow/Red) | Medium | ✅ Implemented |
| **FR-UI-008** | Dashboard shall be responsive (breakpoints: 1024px, 768px, 480px, 360px) | Medium | ✅ Implemented |
| **FR-UI-009** | Dashboard shall be touch-optimized (44px+ touch targets) | Medium | ✅ Implemented |
| **FR-UI-010** | Dashboard shall support print-friendly styles | Low | ✅ Implemented |
| **FR-UI-011** | Dashboard shall provide live price ticker and charts via TradingView integration | Medium | ✅ Implemented |
| **FR-UI-012** | Dashboard shall display legal disclaimers and link to Terms of Service | High | ✅ Implemented |

### 4.6 API Endpoints

| ID | Endpoint | Description | Status |
|----|----------|-------------|--------|
| **FR-API-001** | `/api/predictions` | Latest predictions from all agents | ✅ Implemented |
| **FR-API-002** | `/api/performance` | Agent accuracy statistics | ✅ Implemented |
| **FR-API-003** | `/api/performance/detailed` | Detailed metrics (per-stock, monthly trends) | ✅ Implemented |
| **FR-API-004** | `/api/evaluations` | Prediction results (predicted vs actual) | ✅ Implemented |
| **FR-API-005** | `/api/sentiment` | Latest sentiment scores per stock | ✅ Implemented |
| **FR-API-006** | `/api/prices` | Latest stock prices | ✅ Implemented |
| **FR-API-007** | `/api/stats` | System statistics | ✅ Implemented |
| **FR-API-008** | `/api/trades/today` | Active trade recommendations | ✅ Implemented |
| **FR-API-009** | `/api/portfolio` | Virtual portfolio positions & history | ✅ Implemented |

### 4.7 Automation & Scheduling

| ID | Requirement | Schedule | Status |
|----|-------------|----------|--------|
| **FR-AU-001** | Automated data collection + sentiment analysis | Mon-Fri 4:30 PM EST | ✅ Implemented |
| **FR-AU-002** | Automated prediction generation | Mon-Fri 5:00 PM EST | ✅ Fixed (removed broken `needs` dependency) |
| **FR-AU-003** | Automated evaluation of past predictions | Every hour | ✅ Implemented |
| **FR-AU-004** | GitHub Actions workflow orchestration | As scheduled | ✅ Implemented |

### 4.8 Trade Recommendations & Portfolio (Phase 2)

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| **FR-TR-001** | System shall generate actionable Buy/Sell/Watch trade signals | High | ✅ Implemented |
| **FR-TR-002** | System shall provide entry price, target price, and stop-loss levels | High | ✅ Implemented |
| **FR-TR-003** | System shall display "Trade Cards" with conviction, risk, and reasoning | High | ✅ Implemented |
| **FR-TR-004** | Dashboard shall include a "Trades" tab for active recommendations | High | ✅ Implemented |
| **FR-TR-005** | Dashboard shall include a "Portfolio" tab to track virtual positions | High | ✅ Implemented |
| **FR-TR-006** | System shall track simulated performance (P&L, win rate) of recommendations | High | ✅ Implemented |
| **FR-TR-007** | Trade reasoning shall be bilingual (English/Arabic) | High | ✅ Implemented |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| **NFR-P-001** | Dashboard page load time | < 3 seconds | Fixed: TDZ crash, parallel API calls, skeleton loader, cache-busting |
| **NFR-P-002** | API response time | < 500ms | Optimized: eliminated duplicate calls, SQL query tuning |
| **NFR-P-003** | Data collection cycle completion | < 15 minutes | |
| **NFR-P-004** | Prediction generation per stock | < 5 seconds | |

### 5.2 Availability & Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-A-001** | Dashboard uptime | 99.5% |
| **NFR-A-002** | Scheduled task success rate | 95% |
| **NFR-A-003** | Data freshness | Updated within 24 hours |
| **NFR-A-004** | Database backup frequency | Daily |

### 5.3 Security

| ID | Requirement | Implementation |
|----|-------------|----------------|
| **NFR-S-001** | API keys stored as environment secrets | GitHub Secrets / Render Env Vars |
| **NFR-S-002** | Database credentials encrypted | PostgreSQL SSL connection |
| **NFR-S-003** | No sensitive data exposed in frontend | Server-side API key handling |

### 5.4 Scalability

| ID | Requirement | Current | Future |
|----|-------------|---------|--------|
| **NFR-SC-001** | Number of tracked stocks | 30+ (EGX 30) | 100+ |
| **NFR-SC-002** | Prediction agents | 4 | 8+ |
| **NFR-SC-003** | Concurrent dashboard users | 50 | 500 |

### 5.5 Compatibility

| ID | Requirement | Supported |
|----|-------------|-----------|
| **NFR-C-001** | Browser support | Chrome, Firefox, Safari, Edge (latest 2 versions) |
| **NFR-C-002** | Mobile support | iOS Safari, Android Chrome |
| **NFR-C-003** | Database compatibility | SQLite (dev), PostgreSQL (prod) |

---

## 6. Technical Architecture

### 6.1 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        XMORE SYSTEM                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │   DATA      │    │  ANALYSIS   │    │   PRESENTATION      │ │
│  │   LAYER     │    │   LAYER     │    │   LAYER             │ │
│  │             │    │             │    │                     │ │
│  │ • Yahoo     │───▶│ • FinBERT   │───▶│ • Express.js API    │ │
│  │   Finance   │    │ • ML Model  │    │ • Web Dashboard     │ │
│  │ • Finnhub   │    │ • Agents    │    │ • REST Endpoints    │ │
│  │ • NewsAPI   │    │             │    │                     │ │
│  │ • RSS Feeds │    │             │    │                     │ │
│  └─────────────┘    └─────────────┘    └─────────────────────┘ │
│         │                  │                     │              │
│         └──────────────────┴─────────────────────┘              │
│                            │                                     │
│                   ┌────────┴────────┐                           │
│                   │   DATABASE      │                           │
│                   │  SQLite / Pg    │                           │
│                   └─────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend (Python)** | Python 3.10+ | Data collection, ML, sentiment analysis |
| **Backend (Web)** | Node.js/Express | API server, dashboard |
| **ML Framework** | scikit-learn | Random Forest classifier |
| **NLP** | Transformers (FinBERT) | Financial sentiment analysis |
| **Database** | SQLite (local), PostgreSQL (prod) | Data persistence |
| **Frontend** | Vanilla JS, CSS | Dashboard interface |
| **CI/CD** | GitHub Actions | Automation, scheduling |
| **Hosting** | Render.com | Production deployment |

### 6.3 External Dependencies

| Service | Purpose | API Key Required |
|---------|---------|------------------|
| Yahoo Finance (yfinance) | Stock price data | No |
| Finnhub | Financial news | Yes |
| NewsAPI | News aggregation | Yes |
| Hugging Face (FinBERT) | Sentiment model | No (cached locally) |
| TradingView | Embedded charts and ticker | No (Widgets) |

---

## 7. Data Model

### 7.1 Core Entities

| Table | Description | Key Fields |
|-------|-------------|------------|
| `prices` | Historical OHLCV data | symbol, date, open, high, low, close, volume |
| `news` | News articles with sentiment | symbol, headline, sentiment_score, published_at |
| `predictions` | Agent predictions | symbol, agent_name, prediction, confidence, target_date |
| `evaluations` | Prediction outcomes | prediction_id, actual_outcome, is_correct |
| `sentiment_scores` | Aggregated sentiment | symbol, avg_sentiment, label, article_count |

### 7.2 Data Flow

1. **Ingest**: Price/news data collected via APIs
2. **Process**: Technical indicators calculated, sentiment analyzed
3. **Predict**: ML agents generate predictions
4. **Store**: Results persisted to database
5. **Display**: Dashboard pulls data via API
6. **Evaluate**: Hourly job compares predictions to outcomes

---

## 8. User Stories

### 8.1 Investor Stories

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-001 | Retail investor | View daily buy/sell recommendations | I can make informed trading decisions |
| US-002 | Arabic-speaking user | Use the dashboard in Arabic | I can understand all information easily |
| US-003 | Mobile user | Access predictions on my phone | I can check recommendations anywhere |
| US-004 | Risk-aware trader | See confidence scores for predictions | I can assess the reliability of signals |
| US-005 | News-following investor | View market sentiment analysis | I can understand market mood |

### 8.2 System Administrator Stories

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-006 | Admin | Receive alerts on collection failures | I can address issues promptly |
| US-007 | Admin | View agent performance metrics | I can identify underperforming agents |
| US-008 | Admin | Configure stock watchlist | I can customize tracked securities |

---

## 9. Constraints & Assumptions

### 9.1 Constraints

| ID | Constraint | Impact |
|----|------------|--------|
| C-001 | EGX market data availability may have delays | Predictions based on previous day's close |
| C-002 | Free tier API rate limits | Limited news articles per day |
| C-003 | FinBERT model size (~500MB) | Requires adequate memory for inference |
| C-004 | EGX trading hours (Sun-Thu, 10:00-14:30 Cairo) | Scheduling aligned to Egyptian timezone |

### 9.2 Assumptions

| ID | Assumption |
|----|------------|
| A-001 | Yahoo Finance will continue providing free EGX data |
| A-002 | Users have reliable internet access |
| A-003 | Historical data is representative of future patterns |
| A-004 | News sentiment correlates with price movements |

---

## 10. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API provider discontinuation | Low | High | Implement backup data sources |
| Model accuracy degradation | Medium | Medium | Regular retraining, performance monitoring |
| Database corruption | Low | High | Daily backups, PostgreSQL reliability |
| Regulatory changes (EGX) | Low | Medium | Monitor compliance requirements |
| Security breach | Low | High | Environment secrets, secure hosting |

---

## 11. Success Metrics

### 11.1 Key Performance Indicators (KPIs)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Prediction accuracy | >55% | Automated evaluation job |
| Dashboard uptime | >99.5% | Render monitoring |
| Data freshness | <24 hours | Timestamp validation |
| User engagement | Daily active users | Analytics (future) |
| API response time | <500ms | Server logging |

### 11.2 Acceptance Criteria

| Criteria | Status |
|----------|--------|
| All 4 prediction agents operational | ✅ Met |
| Bilingual dashboard functional | ✅ Met |
| Automated scheduling working | ✅ Met |
| EGX 30 stocks tracked | ✅ Met |
| Sentiment analysis integrated | ✅ Met |

---

## 12. Future Roadmap

### Phase 2 (Planned)

| Feature | Description |
|---------|-------------|
| Trade Recommendations | Actionable signals with Entry/Target/Stop-loss | ✅ Implemented |
| Portfolio Tracker | Virtual portfolio tracking with P&L | ✅ Implemented |
| LSTM/Transformer Models | Deep learning for improved sequence modeling | Planned |
| Hyperparameter Tuning | GridSearch optimization for Random Forest | Planned |
| Social Media Integration | Twitter/X sentiment from Arabic fintwit | Planned |
| Macro-Economic Indicators | Fed rates, inflation data integration | Planned |

### Phase 3 (Future Vision)

| Feature | Description |
|---------|-------------|
| Paper Trading | Alpaca API integration for simulated trading |
| Portfolio Optimization | Multi-stock allocation recommendations |
| Mobile App | Native iOS/Android applications |
| Real-Time Streaming | WebSocket-based live updates |

---

## 13. Glossary

| Term | Definition |
|------|------------|
| **EGX** | Egyptian Exchange - Egypt's stock market |
| **EGX 30** | Index of top 30 most liquid stocks on EGX |
| **OHLCV** | Open, High, Low, Close, Volume - standard price data |
| **RSI** | Relative Strength Index - momentum indicator |
| **MACD** | Moving Average Convergence Divergence - trend indicator |
| **FinBERT** | BERT model fine-tuned for financial text sentiment |
| **Ensemble ML** | Combining multiple models for improved predictions |
| **RTL** | Right-to-Left text direction (for Arabic) |

---

## 14. Appendices

### Appendix A: EGX Market Hours

| Day | Trading Session |
|-----|-----------------|
| Sunday | 10:00 - 14:30 Cairo |
| Monday | 10:00 - 14:30 Cairo |
| Tuesday | 10:00 - 14:30 Cairo |
| Wednesday | 10:00 - 14:30 Cairo |
| Thursday | 10:00 - 14:30 Cairo |
| Friday | Closed |
| Saturday | Closed |

### Appendix B: Agent Strategy Summary

| Agent | Strategy | Signals |
|-------|----------|---------|
| MA_Crossover_Agent | 10/30-day MA crossover | Golden Cross = Buy, Death Cross = Sell |
| ML_RandomForest | Ensemble classification | Feature-based probability prediction |
| RSI_Agent | Momentum oscillator | <30 = Oversold (Buy), >70 = Overbought (Sell) |
| Volume_Spike_Agent | Volume anomaly detection | Unusual volume confirms trend strength |
| Consensus_Agent | Weighted Vote | Aggregates all agents based on historical accuracy |

---

*Document End*

**Last Updated**: February 11, 2026
**Next Review**: March 11, 2026
