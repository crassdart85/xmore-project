// ============================================
// Xmore — AI Stock Prediction Dashboard
// Phase 1 Upgrade: Performance Dashboard, TradingView, Consensus, Compliance
// ============================================

// Global error handler — surface JS errors visibly for debugging
window.onerror = function (msg, url, line, col, error) {
    console.error('Global error:', msg, url, line, col, error);
    const el = document.getElementById('predictions');
    if (el) {
        const p = document.createElement('p');
        p.className = 'error-message';
        p.textContent = `JS Error: ${msg} (line ${line})`;
        el.innerHTML = '';
        el.appendChild(p);
    }
};

const API_URL = '/api';

// Shared HTML escaping utility
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ============================================
// UPGRADE 1: ANIMATED NUMBER COUNTERS (CountUp.js)
// ============================================

function animateValue(elementId, endVal, options = {}) {
    const el = document.getElementById(elementId);
    if (!el) return;
    // Skip if already animated with same value
    if (el.getAttribute('data-animated') === String(endVal)) return;

    const defaults = {
        duration: 1.8,
        useGrouping: true,
        decimal: '.',
        separator: ',',
        ...options
    };
    if (typeof countUp !== 'undefined' && countUp.CountUp) {
        const counter = new countUp.CountUp(elementId, endVal, defaults);
        if (!counter.error) {
            counter.start();
        } else {
            el.textContent = formatAnimatedValue(endVal, defaults);
        }
    } else {
        el.textContent = formatAnimatedValue(endVal, defaults);
    }
    el.setAttribute('data-animated', String(endVal));
}

function formatAnimatedValue(val, opts) {
    let str = Number(val).toFixed(opts.decimalPlaces || 0);
    if (opts.prefix) str = opts.prefix + str;
    if (opts.suffix) str = str + opts.suffix;
    return str;
}

function pulseMetric(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.classList.remove('updated');
        void el.offsetWidth; // force reflow
        el.classList.add('updated');
    }
}

// ============================================
// UPGRADE 2: TOAST NOTIFICATION SYSTEM (Notyf)
// ============================================

let notyf = null;

function initNotyf() {
    if (typeof Notyf === 'undefined') return;
    notyf = new Notyf({
        duration: 4000,
        position: { x: 'right', y: 'top' },
        dismissible: true,
        ripple: true,
        types: [
            {
                type: 'info',
                background: 'var(--accent, #667eea)',
                icon: { className: 'notyf-info-icon', tagName: 'span', text: '\u2139' }
            },
            {
                type: 'warning',
                background: '#f59e0b',
                icon: { className: 'notyf-warn-icon', tagName: 'span', text: '\u26A0' }
            }
        ]
    });
}

function showToast(type, message) {
    if (!notyf) initNotyf();
    if (!notyf) { console.log(`[Toast ${type}] ${message}`); return; }
    if (type === 'success') notyf.success(message);
    else if (type === 'error') notyf.error(message);
    else notyf.open({ type: type, message: message });
}

// ============================================
// UPGRADE 4: IMPROVED SKELETON LOADING
// ============================================

const SKELETON_TEMPLATES = {
    predictions: `
        <div class="skeleton-shimmer skeleton-text long"></div>
        ${'<div class="skeleton-shimmer skeleton-card"></div>'.repeat(5)}
    `,
    performance: `
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
            ${'<div class="skeleton-shimmer skeleton-metric"></div>'.repeat(4)}
        </div>
        <div class="skeleton-shimmer skeleton-chart"></div>
        ${'<div class="skeleton-shimmer skeleton-row"></div>'.repeat(4)}
    `,
    trades: `${'<div class="skeleton-shimmer skeleton-card"></div>'.repeat(3)}`,
    results: `${('<div class="skeleton-shimmer skeleton-text short"></div><div class="skeleton-shimmer skeleton-row"></div><div class="skeleton-shimmer skeleton-row"></div>').repeat(4)}`,
    prices: `${'<div class="skeleton-shimmer skeleton-row"></div>'.repeat(6)}`,
    consensus: `
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px">
            ${'<div class="skeleton-shimmer skeleton-metric"></div>'.repeat(4)}
        </div>
        ${'<div class="skeleton-shimmer skeleton-card"></div>'.repeat(3)}
    `,
    briefing: `
        <div class="skeleton-shimmer skeleton-card"></div>
        <div class="skeleton-shimmer skeleton-card"></div>
        <div class="skeleton-shimmer skeleton-card"></div>
    `,
};

function showSkeleton(containerId, type) {
    const el = document.getElementById(containerId);
    if (el && SKELETON_TEMPLATES[type]) {
        el.innerHTML = SKELETON_TEMPLATES[type];
        el.setAttribute('aria-busy', 'true');
    }
}

function clearSkeleton(containerId) {
    const el = document.getElementById(containerId);
    if (el) el.setAttribute('aria-busy', 'false');
}

// ============================================
// UPGRADE 6: EMPTY STATE ILLUSTRATIONS
// ============================================

function renderEmptyState(containerId, icon, titleKey, subtitleKey, ctaKey, ctaAction) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">${icon}</div>
            <h3 data-i18n="${titleKey}">${t(titleKey)}</h3>
            <p class="empty-state-desc" data-i18n="${subtitleKey}">${t(subtitleKey)}</p>
            ${ctaKey ? `<button class="btn btn-primary empty-state-cta" onclick="${ctaAction}" data-i18n="${ctaKey}">${t(ctaKey)}</button>` : ''}
        </div>
    `;
}

// ============================================
// DARK MODE SUPPORT
// ============================================

let currentTheme = localStorage.getItem('theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

function applyTheme() {
    document.documentElement.setAttribute('data-theme', currentTheme);
    try { updateThemeButton(); } catch (e) { /* TRANSLATIONS not ready yet */ }
}

function updateThemeButton() {
    const themeBtn = document.getElementById('themeBtn');
    if (themeBtn) {
        const tooltipKey = currentTheme === 'dark' ? 'lightMode' : 'darkMode';
        const tooltip = (typeof t === 'function') ? t(tooltipKey) :
            (currentTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
        themeBtn.title = tooltip;
    }
}

function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', currentTheme);
    applyTheme();
    // Rebuild TradingView widgets with new theme
    loadTradingViewTicker();
    // Update Lightweight Charts theme (Upgrade 3)
    const chartContainer = document.getElementById('equityCurveChartContainer');
    if (chartContainer && chartContainer._chartInstance) {
        const isDark = currentTheme === 'dark';
        chartContainer._chartInstance.applyOptions({
            layout: {
                background: { type: 'solid', color: isDark ? '#1a1a2e' : '#ffffff' },
                textColor: isDark ? '#d1d5db' : '#374151',
            },
            grid: {
                vertLines: { color: isDark ? '#2d2d44' : '#f0f0f0' },
                horzLines: { color: isDark ? '#2d2d44' : '#f0f0f0' },
            },
        });
    }
}

// Apply theme CSS immediately (prevents flash); button tooltip set later in applyLanguage()
applyTheme();

// ============================================
// BILINGUAL SUPPORT (English / Arabic)
// ============================================

let currentLang = localStorage.getItem('lang') || 'en';

const TRANSLATIONS = {
    en: {
        // Header
        title: 'Xmore',
        subtitle: 'AI Stock Prediction Dashboard',

        // Stats
        stocksTracked: 'Stocks Tracked',
        totalPredictions: 'Total Predictions',
        overallAccuracy: 'Accuracy',
        latestData: 'Latest Data',

        // Tabs
        tabPredictions: 'Predictions',
        tabBriefing: 'Briefing',
        tabTrades: 'Trades',
        tabPortfolio: 'Portfolio',
        tabWatchlist: 'Watchlist',
        tabPerformance: 'Performance',
        tabResults: 'Results',
        tabPrices: 'Prices',
        predictionsBrief: "Start here: see today's AI signals by stock and scan for bullish, bearish, or neutral direction.",
        watchlistBrief: 'Track the stocks you care about so the app can personalize signals, briefing, and performance for you.',
        performanceBrief: 'Review strategy quality over time, including win rate, drawdown, and benchmark-relative performance.',
        consensusBrief: 'See where multiple agents agree, plus risk filters, to spot the strongest shared setup.',
        resultsBrief: 'Compare past predictions with real outcomes to understand what the model got right or wrong.',
        pricesBrief: 'Check the latest market prices and volume for each tracked stock in one quick table.',
        briefingBrief: 'Use this as your daily summary: key market context, priority signals, and suggested next actions.',
        tradesBrief: 'View executable trade ideas with direction and rationale for the current session.',
        portfolioBrief: 'Monitor open positions, recent trade history, and high-level portfolio health in one place.',

        // Section titles
        latestPredictions: 'Latest Predictions',
        agentPerformance: 'Agent Performance',
        predictionResults: 'Prediction Results',
        latestPrices: 'Latest Stock Prices',
        performanceOverview: 'Performance Overview',
        agentAccuracy: 'Agent Accuracy',
        stockPerformance: 'Stock Performance',
        monthlyTrend: 'Monthly Accuracy Trend',

        // Table headers
        stock: 'Stock',
        agent: 'Agent',
        signal: 'Signal',
        prediction: 'Signal',
        date: 'Date',
        totalPreds: 'Total Predictions',
        correct: 'Correct',
        accuracy: 'Accuracy',
        closePrice: 'Close Price',
        volume: 'Volume',
        actualOutcome: 'Actual',
        priceChange: 'Change %',
        result: 'Result',
        targetDate: 'Target Date',
        avgReturn: 'Avg Return',

        // Signals (Task 6: from predictions to signals)
        up: 'Bullish',
        down: 'Bearish',
        hold: 'Neutral',
        flat: 'Neutral',

        // Sentiment
        sentiment: 'Sentiment',
        bullish: 'Bullish',
        neutral: 'Neutral',
        bearish: 'Bearish',
        noSentiment: 'N/A',

        // Consensus
        consensus: 'Consensus',
        agentsAgree: 'agents agree',
        unanimous: 'Unanimous',

        // Performance
        directionalAccuracy: 'Directional Accuracy',
        totalSignals: 'Total Signals',
        winRateBuy: 'Win Rate (Buy)',
        winRateSell: 'Win Rate (Sell)',
        avgReturnPerSignal: 'Avg Return/Signal',
        maxDrawdown: 'Max Drawdown',
        accuracyDefinition: 'Directional Accuracy: Percentage of predictions where the predicted direction (UP/DOWN) matched the actual 5-day price movement exceeding ±0.5% threshold.',
        agentHistoryBadge: 'correct historically',

        // Messages
        noPredictions: 'No predictions available yet. Signals are generated daily after market close.',
        noPerformance: 'Performance tracking will begin once predictions have been evaluated.',
        noEvaluations: 'No prediction results yet. Results will appear after predictions are evaluated.',
        noPrices: 'Price data is being collected. Please check back later.',
        errorPredictions: 'Unable to load predictions. Please try refreshing.',
        errorPerformance: 'Unable to load performance data.',
        errorEvaluations: 'Unable to load prediction results.',
        errorPrices: 'Unable to load price data.',
        noDetailedPerformance: 'Detailed performance data will be available after prediction evaluation.',

        // Buttons
        refreshData: 'Refresh Data',
        refreshing: 'Refreshing...',

        // Search
        searchPlaceholder: 'Search by stock symbol or company name...',
        liveOnlyData: 'Live-Only Data',
        snapshotAlpha30d: '30-Day Alpha vs EGX30',
        snapshotSharpe30d: 'Sharpe Ratio (30D)',
        snapshotMaxDd30d: 'Max Drawdown (30D)',
        snapshotWinRate30d: 'Rolling Win Rate (30D)',
        snapshotTrades: 'Total Live Trades',
        consensusSignal: 'Consensus Signal',
        agreement: 'Agreement',
        recentAccuracySymbol: 'Recent Accuracy',
        whySignal: 'Why This Signal?',
        expandDetails: 'Details',
        conf: 'Confidence',
        trend: 'Trend',
        momentum: 'Momentum',
        volumeState: 'Volume',
        sentimentState: 'Sentiment',
        agentAgreement: 'Agent agreement',
        tooltipAlpha: 'Average 1-day alpha in the latest 30-day live window versus EGX30.',
        tooltipSharpe: 'Risk-adjusted return quality in the latest 30-day live window.',
        tooltipMaxDd: 'Largest peak-to-trough decline in cumulative returns over 30 days.',
        tooltipWinRate: 'Share of correct resolved live predictions over the latest 30 days.',
        tooltipTrades: 'Resolved live predictions included in public metrics. Target: 100+.',

        // Language
        switchLang: 'عربي',

        // Theme
        lightMode: 'Switch to light mode',
        darkMode: 'Switch to dark mode',

        // Terms
        termsOfService: 'Terms of Service',

        // Consensus tab
        tabConsensus: 'Consensus',
        consensusTitle: 'Signal Consensus',
        bullCase: 'Bull Case',
        bearCase: 'Bear Case',
        riskAction: 'Risk',
        conviction: 'Conviction',
        riskPassed: 'Passed',
        riskFlagged: 'Flagged',
        riskBlocked: 'Blocked',
        riskDowngraded: 'Downgraded',
        totalStocks: 'Total Stocks',
        avgRisk: 'Avg Risk',
        noConsensus: 'No consensus data available yet. Run the prediction pipeline first.',
        errorConsensus: 'Unable to load consensus data.',
        convictionVeryHigh: 'Very High',
        convictionHigh: 'High',
        convictionModerate: 'Moderate',
        convictionLow: 'Low',
        convictionBlocked: 'Blocked',
        riskWarnings: 'Risk Warnings',
        agentSignals: 'Agent Signals',
        yourWatchlist: 'Your Watchlist',
        allPredictions: 'All EGX Predictions',
        followStocksPrompt: 'Follow stocks from the Watchlist tab to see personalized data here.',
        noWatchlistLogin: 'Login to see personalized data for your followed stocks.',

        // Toast notifications (Upgrade 2)
        stockAdded: 'Stock added to watchlist',
        stockRemoved: 'Stock removed from watchlist',
        watchlistFull: 'Watchlist is full (max 30 stocks)',
        loadError: 'Failed to load data. Please try again.',
        dataRefreshed: 'Data updated successfully',
        minTradesWarning: 'Performance tracking begins after 100 trades',
        langSwitched: 'Switched to English',

        // Empty states (Upgrade 6)
        emptyPredictions: 'No Predictions Yet',
        emptyPredictionsDesc: 'Signals are generated daily after market close. Check back soon.',
        emptyTrades: 'No Trade History',
        emptyTradesDesc: 'Trade recommendations will appear here once the system generates them.',
        emptyPortfolio: 'No Open Positions',
        emptyPortfolioDesc: 'Open positions will show here after executing trade recommendations.',
        viewTrades: 'View Trades',
        emptyResults: 'No Results Yet',
        emptyResultsDesc: 'Results will appear after predictions have been evaluated against actual outcomes.',

        // Accessibility (Upgrade 7)
        skipToContent: 'Skip to content',

        // Time Machine
        tabTimeMachine: 'Time Machine',
        timemachineBrief: "Enter an amount and a past date to see what your investment would be worth today if you had followed Xmore's recommendations.",
        tmTitle: 'What If You Had Invested?',
        tmSubtitle: "See how much your money would be worth if you had followed Xmore's best recommendations.",
        tmAmountLabel: 'Investment Amount (EGP)',
        tmDateLabel: 'Starting From',
        tm3Months: '3 months ago',
        tm6Months: '6 months ago',
        tm12Months: '1 year ago',
        tmMaxRange: 'Max (2 years)',
        tmSimulate: 'Simulate',
        tmYouInvested: 'You invested',
        tmWouldBeWorth: 'Would be worth today',
        tmAlpha: 'Alpha vs EGX30',
        tmVsEGX30: 'outperformance',
        tmAnnualized: 'Annualized Return',
        tmTotalTrades: 'Total Trades',
        tmWinRate: 'Win Rate',
        tmMaxDrawdown: 'Max Drawdown',
        tmSharpe: 'Sharpe Ratio',
        tmEquityCurve: 'Your Money Over Time',
        tmMonthlyBreakdown: 'Monthly Returns',
        tmMonth: 'Month',
        tmTopTrades: 'Best Trades',
        tmWorstTrades: 'Worst Trades',
        tmTimeline: 'Investment Timeline',
        tmCalculating: 'Traveling through time...',
        tmAnalyzing: 'Fetching live market data & running simulation',
        tmLoadingWarning: 'This may take 30–60 seconds.',
        tmDisclaimer: "This simulation uses real EGX price data from Yahoo Finance and applies Xmore's signal logic retroactively. Past performance does not guarantee future results. This is not financial advice.",
        tmProfit: 'Profit',
        tmLoss: 'Loss',
        tmBought: 'Bought',
        tmSold: 'Sold',
        tmHeldFor: 'Held for',
        tmDays: 'days',
        tmInvalidAmount: 'Amount must be between 5,000 and 10,000,000 EGP',
        tmSelectDate: 'Please select a start date',
        tmErrorGeneric: 'Simulation failed. Please try again.',
        tmTryDifferent: 'Try a different date range or amount.',
        tmNoDataHint: 'Could not complete the simulation. Try a different date range.',
        // Future tab
        tmSubPastLabel: '⏮ Past',
        tmSubFutureLabel: '⏭ Future',
        fcTitle: 'Future Forecast',
        fcSubtitle: 'AI picks the best EGX30 stock for your horizon. 5,000 Monte Carlo paths.',
        fcModeAuto: '🤖 AI picks for me',
        fcModeManual: '🔍 I pick manually',
        fcEndDateLabel: 'Target Date',
        fcEndDateHint: 'Up to 30 days from today — AI picks the best EGX30 stock for you',
        fcSymbolLabel: 'Stock Symbol',
        fcHorizonLabel: 'Time Horizon',
        fc3Months: '3 months',
        fc6Months: '6 months',
        fc1Year: '1 year',
        fc2Years: '2 years',
        fcRunBtnManual: 'Run Forecast',
        fcSelectSymbol: 'Please select a stock.',
        fcScenarioLabel: 'Scenario',
        fcBase: 'Base',
        fcBaseHint: 'Historical drift',
        fcBull: 'Bull',
        fcBullHint: '+2% drift boost',
        fcBear: 'Bear',
        fcBearHint: '−2% drift drag',
        fcRunBtn: 'Find Best Stock & Forecast',
        fcSelectDate: 'Please pick a target date.',
        fcChosenBy: 'AI Best Pick',
        fcSeeRanking: 'See ranking ▼',
        fcHideRanking: 'Hide ▲',
        fcExpectedValue: 'Expected Value',
        fcProbProfit: 'Probability of Profit',
        fcVolatility: 'Annual Volatility',
        fcWorstCase: 'Worst Case (5th pct)',
        fcMedian: 'Median',
        fcBestCase: 'Best Case (95th pct)',
        fcBandChartTitle: 'Projected Portfolio Value',
        fcHistTitle: 'Distribution of Final Values',
        fcHistSub: '5,000 simulated outcomes. Green = profit, Red = loss.',
        fcDrift: 'Historical Drift',
        fcScenarioUsed: 'Scenario Adj.',
        fcDataPoints: 'Data Points',
        fcSimCount: 'Simulations',
        fcCalculating: 'Scanning EGX30 stocks & running 5,000 Monte Carlo paths…',
        fcAnalyzing: 'Computing GBM parameters — this takes ~30s',
        fcDisclaimer: 'This projection is model-based and does not constitute financial advice. Results depend on historical statistical assumptions and market conditions.',
    },
    ar: {
        title: 'إكسمور',
        subtitle: 'لوحة التنبؤات الذكية للأسهم',

        stocksTracked: 'الأسهم المتابعة',
        totalPredictions: 'إجمالي التنبؤات',
        overallAccuracy: 'الدقة',
        latestData: 'آخر تحديث',

        tabPredictions: 'التنبؤات',
        tabBriefing: 'النشرة',
        tabTrades: 'التداول',
        tabPortfolio: 'المحفظة',
        tabWatchlist: 'المتابعة',
        tabPerformance: 'الأداء',
        tabResults: 'النتائج',
        tabPrices: 'الأسعار',
        predictionsBrief: 'ابدأ من هنا: راجع إشارات الذكاء الاصطناعي اليومية لكل سهم (صاعد/هابط/محايد).',
        watchlistBrief: 'تابع الأسهم التي تهمك ليخصص النظام الإشارات والنشرة والأداء لك.',
        performanceBrief: 'تابع جودة الاستراتيجية عبر الوقت، بما في ذلك نسبة الفوز والسحب الأقصى والأداء مقابل المؤشر.',
        consensusBrief: 'اطلع على الأسهم التي يتفق عليها عدة وكلاء مع فلاتر المخاطر لتحديد أقوى الفرص.',
        resultsBrief: 'قارن التوقعات السابقة بالنتائج الفعلية لفهم ما أصابه النظام وما أخطأ فيه.',
        pricesBrief: 'راجع أحدث الأسعار وأحجام التداول للأسهم المتابعة في جدول واحد.',
        briefingBrief: 'استخدمها كملخص يومي: سياق السوق، أولويات الإشارات، والخطوات المقترحة.',
        tradesBrief: 'اطلع على أفكار تداول قابلة للتنفيذ مع الاتجاه والمبرر خلال جلسة اليوم.',
        portfolioBrief: 'راقب المراكز المفتوحة وتاريخ الصفقات ومؤشرات صحة المحفظة في مكان واحد.',

        latestPredictions: 'أحدث التنبؤات',
        agentPerformance: 'أداء الوكلاء',
        predictionResults: 'نتائج التنبؤات',
        latestPrices: 'أحدث أسعار الأسهم',
        performanceOverview: 'نظرة عامة على الأداء',
        agentAccuracy: 'دقة الوكلاء',
        stockPerformance: 'أداء الأسهم',
        monthlyTrend: 'اتجاه الدقة الشهري',

        stock: 'السهم',
        agent: 'الوكيل',
        signal: 'الإشارة',
        prediction: 'الإشارة',
        date: 'التاريخ',
        totalPreds: 'إجمالي التنبؤات',
        correct: 'الصحيحة',
        accuracy: 'الدقة',
        closePrice: 'سعر الإغلاق',
        volume: 'الحجم',
        actualOutcome: 'الفعلي',
        priceChange: 'التغير %',
        result: 'النتيجة',
        targetDate: 'تاريخ الهدف',
        avgReturn: 'متوسط العائد',

        up: 'صاعد',
        down: 'هابط',
        hold: 'محايد',
        flat: 'محايد',

        sentiment: 'المشاعر',
        bullish: 'إيجابي',
        neutral: 'محايد',
        bearish: 'سلبي',
        noSentiment: 'غ/م',

        consensus: 'الإجماع',
        agentsAgree: 'وكلاء يتفقون',
        unanimous: 'إجماع تام',

        directionalAccuracy: 'الدقة الاتجاهية',
        totalSignals: 'إجمالي الإشارات',
        winRateBuy: 'نسبة النجاح (شراء)',
        winRateSell: 'نسبة النجاح (بيع)',
        avgReturnPerSignal: 'متوسط العائد/إشارة',
        maxDrawdown: 'أقصى تراجع',
        accuracyDefinition: 'الدقة الاتجاهية: نسبة التنبؤات التي تطابق فيها الاتجاه المتوقع (صعود/هبوط) مع حركة السعر الفعلية خلال 5 أيام بتجاوز عتبة ±0.5%.',
        agentHistoryBadge: 'صحيح تاريخياً',

        noPredictions: 'لا توجد تنبؤات متاحة. يتم إنشاء الإشارات يومياً بعد إغلاق السوق.',
        noPerformance: 'سيبدأ تتبع الأداء بمجرد تقييم التنبؤات.',
        noEvaluations: 'لا توجد نتائج تنبؤات بعد.',
        noPrices: 'جاري جمع بيانات الأسعار.',
        errorPredictions: 'تعذر تحميل التنبؤات.',
        errorPerformance: 'تعذر تحميل بيانات الأداء.',
        errorEvaluations: 'تعذر تحميل النتائج.',
        errorPrices: 'تعذر تحميل الأسعار.',
        noDetailedPerformance: 'ستتوفر بيانات الأداء التفصيلية بعد تقييم التنبؤات.',

        refreshData: 'تحديث البيانات',
        refreshing: 'جاري التحديث...',

        searchPlaceholder: 'البحث برمز السهم أو اسم الشركة...',
        liveOnlyData: 'بيانات حية فقط',
        snapshotAlpha30d: 'ألفا 30 يوم مقابل EGX30',
        snapshotSharpe30d: 'نسبة شارب (30 يوم)',
        snapshotMaxDd30d: 'أقصى تراجع (30 يوم)',
        snapshotWinRate30d: 'نسبة الفوز المتحركة (30 يوم)',
        snapshotTrades: 'إجمالي الصفقات الحية',
        consensusSignal: 'إشارة الإجماع',
        agreement: 'نسبة الاتفاق',
        recentAccuracySymbol: 'الدقة الحديثة',
        whySignal: 'لماذا هذه الإشارة؟',
        expandDetails: 'التفاصيل',
        conf: 'الثقة',
        trend: 'الاتجاه',
        momentum: 'الزخم',
        volumeState: 'الحجم',
        sentimentState: 'المشاعر',
        agentAgreement: 'اتفاق الوكلاء',
        tooltipAlpha: 'متوسط ألفا يومي خلال آخر 30 يوما حيا مقابل EGX30.',
        tooltipSharpe: 'جودة العائد المعدل بالمخاطر خلال آخر 30 يوما حيا.',
        tooltipMaxDd: 'أكبر هبوط من قمة إلى قاع في العائد التراكمي خلال 30 يوما.',
        tooltipWinRate: 'نسبة الإشارات الحية الصحيحة خلال آخر 30 يوما.',
        tooltipTrades: 'التنبؤات الحية المحللة ضمن الإحصاءات العامة. الهدف: 100+.',

        switchLang: 'English',

        lightMode: 'التبديل إلى الوضع الفاتح',
        darkMode: 'التبديل إلى الوضع الداكن',

        termsOfService: 'شروط الخدمة',

        // Consensus tab
        tabConsensus: 'الإجماع',
        consensusTitle: 'إجماع الإشارات',
        bullCase: 'حالة الثور',
        bearCase: 'حالة الدب',
        riskAction: 'المخاطر',
        conviction: 'القناعة',
        riskPassed: 'أُجيز',
        riskFlagged: 'مُعلّم',
        riskBlocked: 'محظور',
        riskDowngraded: 'مُخفّض',
        totalStocks: 'إجمالي الأسهم',
        avgRisk: 'متوسط المخاطر',
        noConsensus: 'لا توجد بيانات إجماع بعد. شغّل خط التنبؤات أولاً.',
        errorConsensus: 'تعذر تحميل بيانات الإجماع.',
        convictionVeryHigh: 'عالية جداً',
        convictionHigh: 'عالية',
        convictionModerate: 'متوسطة',
        convictionLow: 'منخفضة',
        convictionBlocked: 'محظور',
        riskWarnings: 'تحذيرات المخاطر',
        agentSignals: 'إشارات الوكلاء',
        yourWatchlist: 'أسهمك المتابعة',
        allPredictions: 'جميع تنبؤات البورصة',
        followStocksPrompt: 'تابع أسهمك من تبويب المتابعة لعرض البيانات المخصصة هنا.',
        noWatchlistLogin: 'سجّل دخولك لعرض بيانات الأسهم التي تتابعها.',

        // Toast notifications (Upgrade 2)
        stockAdded: 'تمت إضافة السهم للمتابعة',
        stockRemoved: 'تم إزالة السهم من المتابعة',
        watchlistFull: 'قائمة المتابعة ممتلئة (الحد الأقصى ٣٠ سهم)',
        loadError: 'فشل تحميل البيانات. حاول مرة أخرى.',
        dataRefreshed: 'تم تحديث البيانات بنجاح',
        minTradesWarning: 'يبدأ تتبع الأداء بعد ١٠٠ توصية',
        langSwitched: 'تم التبديل للعربية',

        // Empty states (Upgrade 6)
        emptyPredictions: 'لا توجد تنبؤات بعد',
        emptyPredictionsDesc: 'يتم إنشاء الإشارات يومياً بعد إغلاق السوق. تحقق مجدداً قريباً.',
        emptyTrades: 'لا يوجد سجل تداول',
        emptyTradesDesc: 'ستظهر توصيات التداول هنا بعد إنشائها بواسطة النظام.',
        emptyPortfolio: 'لا توجد مراكز مفتوحة',
        emptyPortfolioDesc: 'ستظهر المراكز المفتوحة هنا بعد تنفيذ توصيات التداول.',
        viewTrades: 'عرض التوصيات',
        emptyResults: 'لا توجد نتائج بعد',
        emptyResultsDesc: 'ستظهر النتائج بعد تقييم التنبؤات مقابل النتائج الفعلية.',

        // Accessibility (Upgrade 7)
        skipToContent: 'الانتقال إلى المحتوى',

        // Time Machine
        tabTimeMachine: 'آلة الزمن',
        timemachineBrief: 'أدخل مبلغاً وتاريخاً سابقاً لمعرفة قيمة استثمارك اليوم لو اتبعت توصيات Xmore.',
        tmTitle: 'ماذا لو كنت استثمرت؟',
        tmSubtitle: 'شاهد كم ستكون قيمة أموالك لو اتبعت أفضل توصيات Xmore.',
        tmAmountLabel: 'مبلغ الاستثمار (جنيه)',
        tmDateLabel: 'بدءاً من',
        tm3Months: 'منذ ٣ أشهر',
        tm6Months: 'منذ ٦ أشهر',
        tm12Months: 'منذ سنة',
        tmMaxRange: 'الحد الأقصى (سنتان)',
        tmSimulate: 'محاكاة',
        tmYouInvested: 'لو استثمرت',
        tmWouldBeWorth: 'ستصبح قيمتها اليوم',
        tmAlpha: 'ألفا مقابل EGX30',
        tmVsEGX30: 'تفوق على المؤشر',
        tmAnnualized: 'العائد السنوي',
        tmTotalTrades: 'إجمالي الصفقات',
        tmWinRate: 'نسبة الفوز',
        tmMaxDrawdown: 'أقصى تراجع',
        tmSharpe: 'نسبة شارب',
        tmEquityCurve: 'أموالك عبر الزمن',
        tmMonthlyBreakdown: 'العوائد الشهرية',
        tmMonth: 'الشهر',
        tmTopTrades: 'أفضل الصفقات',
        tmWorstTrades: 'أسوأ الصفقات',
        tmTimeline: 'الجدول الزمني للاستثمار',
        tmCalculating: '...نسافر عبر الزمن',
        tmAnalyzing: 'جلب بيانات السوق الحية وتشغيل المحاكاة',
        tmLoadingWarning: 'قد يستغرق هذا ٣٠ إلى ٦٠ ثانية.',
        tmDisclaimer: 'تستخدم هذه المحاكاة بيانات أسعار البورصة المصرية الحقيقية من Yahoo Finance وتطبق منطق إشارات Xmore بأثر رجعي. الأداء السابق لا يضمن النتائج المستقبلية. هذا ليس نصيحة مالية.',
        tmProfit: 'ربح',
        tmLoss: 'خسارة',
        tmBought: 'شراء',
        tmSold: 'بيع',
        tmHeldFor: 'مدة الاحتفاظ',
        tmDays: 'يوم',
        tmInvalidAmount: 'يجب أن يكون المبلغ بين ٥٬٠٠٠ و ١٠٬٠٠٠٬٠٠٠ جنيه',
        tmSelectDate: 'يرجى تحديد تاريخ البداية',
        tmErrorGeneric: 'فشلت المحاكاة. يرجى المحاولة مرة أخرى.',
        tmTryDifferent: 'جرّب نطاق تاريخ أو مبلغ مختلف.',
        tmNoDataHint: 'تعذّر إكمال المحاكاة. جرّب نطاق تاريخ مختلف.',
        // Future tab
        tmSubPastLabel: '⏮ الماضي',
        tmSubFutureLabel: '⏭ المستقبل',
        fcTitle: 'التوقع المستقبلي',
        fcSubtitle: 'الذكاء الاصطناعي يختار أفضل سهم EGX30 لأفقك الزمني. ٥٬٠٠٠ مسار مونتي كارلو.',
        fcModeAuto: '🤖 الذكاء الاصطناعي يختار لي',
        fcModeManual: '🔍 أختار بنفسي',
        fcEndDateLabel: 'التاريخ المستهدف',
        fcEndDateHint: 'حتى ٣٠ يوماً من اليوم — الذكاء الاصطناعي يختار أفضل سهم لك',
        fcSymbolLabel: 'رمز السهم',
        fcHorizonLabel: 'الأفق الزمني',
        fc3Months: '٣ أشهر',
        fc6Months: '٦ أشهر',
        fc1Year: 'سنة',
        fc2Years: 'سنتان',
        fcRunBtnManual: 'تشغيل التوقع',
        fcSelectSymbol: 'يرجى اختيار سهم.',
        fcScenarioLabel: 'السيناريو',
        fcBase: 'قاعدي',
        fcBaseHint: 'الانجراف التاريخي',
        fcBull: 'صاعد',
        fcBullHint: '+٢٪ تعزيز',
        fcBear: 'هابط',
        fcBearHint: '−٢٪ ضغط',
        fcRunBtn: 'اختر أفضل سهم وابدأ التوقع',
        fcSelectDate: 'يرجى اختيار تاريخ مستهدف.',
        fcChosenBy: 'اختيار الذكاء الاصطناعي',
        fcSeeRanking: 'رؤية الترتيب ▼',
        fcHideRanking: 'إخفاء ▲',
        fcExpectedValue: 'القيمة المتوقعة',
        fcProbProfit: 'احتمالية الربح',
        fcVolatility: 'التقلب السنوي',
        fcWorstCase: 'أسوأ حالة (الخامس٪)',
        fcMedian: 'الوسيط',
        fcBestCase: 'أفضل حالة (٩٥٪)',
        fcBandChartTitle: 'القيمة المتوقعة للمحفظة',
        fcHistTitle: 'توزيع القيم النهائية',
        fcHistSub: '٥٬٠٠٠ نتيجة محاكاة. أخضر = ربح، أحمر = خسارة.',
        fcDrift: 'الانجراف التاريخي',
        fcScenarioUsed: 'تعديل السيناريو',
        fcDataPoints: 'نقاط البيانات',
        fcSimCount: 'عدد المحاكاة',
        fcCalculating: '...فحص أسهم EGX30 وتشغيل ٥٬٠٠٠ مسار مونتي كارلو',
        fcAnalyzing: 'حساب معاملات GBM — قد يستغرق ~٣٠ ثانية',
        fcDisclaimer: 'هذا التوقع قائم على نموذج رياضي ولا يمثل نصيحة مالية. تعتمد النتائج على افتراضات إحصائية تاريخية وظروف السوق.',
    }
};

// Agent info with bilingual support
const AGENT_INFO = {
    'MA_Crossover_Agent': {
        en: { name: 'Moving Average Trend', description: 'Analyzes short and long-term moving average crossovers to identify trend changes.' },
        ar: { name: 'اتجاه المتوسط المتحرك', description: 'يحلل تقاطعات المتوسطات المتحركة لتحديد تغيرات الاتجاه.' }
    },
    'ML_RandomForest': {
        en: { name: 'AI Price Predictor', description: 'Machine learning model using 40+ technical indicators to predict price movements.' },
        ar: { name: 'متنبئ الأسعار الذكي', description: 'نموذج تعلم آلي يستخدم 40+ مؤشر فني للتنبؤ بحركات الأسعار.' }
    },
    'RSI_Agent': {
        en: { name: 'Momentum Indicator', description: 'Uses Relative Strength Index to detect overbought/oversold conditions.' },
        ar: { name: 'مؤشر الزخم', description: 'يستخدم مؤشر القوة النسبية لاكتشاف حالات الشراء/البيع المفرط.' }
    },
    'Volume_Spike_Agent': {
        en: { name: 'Volume Analysis', description: 'Monitors unusual volume activity to predict potential price movements.' },
        ar: { name: 'تحليل الحجم', description: 'يراقب نشاط الحجم غير المعتاد للتنبؤ بتحركات الأسعار.' }
    },
    'Consensus': {
        en: { name: 'Consensus Signal', description: 'Weighted vote across all agents based on historical accuracy.' },
        ar: { name: 'إشارة الإجماع', description: 'تصويت مرجح عبر جميع الوكلاء بناءً على الدقة التاريخية.' }
    },
};

// Get translation
function t(key) {
    return TRANSLATIONS[currentLang]?.[key] || TRANSLATIONS['en']?.[key] || key;
}

function getAgentDisplayName(agentName) {
    return AGENT_INFO[agentName]?.[currentLang]?.name || AGENT_INFO[agentName]?.en?.name || agentName;
}

function getAgentDescription(agentName) {
    return AGENT_INFO[agentName]?.[currentLang]?.description || AGENT_INFO[agentName]?.en?.description || '';
}

// ============================================
// WATCHLIST FILTER CACHE
// ============================================

let userWatchlistSymbols = new Set();
let watchlistCacheFetched = false;

async function fetchUserWatchlistSymbols() {
    if (typeof currentUser === 'undefined' || !currentUser) {
        userWatchlistSymbols = new Set();
        watchlistCacheFetched = false;
        return;
    }
    if (watchlistCacheFetched) return;
    try {
        const res = await fetch('/api/watchlist', { credentials: 'include' });
        if (res.ok) {
            const data = await res.json();
            userWatchlistSymbols = new Set((data.watchlist || []).map(w => w.symbol));
        }
    } catch (e) {
        console.warn('Failed to fetch watchlist for filtering:', e);
    }
    watchlistCacheFetched = true;
}

function resetWatchlistCache() {
    watchlistCacheFetched = false;
    userWatchlistSymbols = new Set();
}

function isLoggedIn() {
    return typeof currentUser !== 'undefined' && currentUser;
}

function getWatchlistEmptyHtml() {
    if (!isLoggedIn()) {
        return `<p class="no-data">${t('noWatchlistLogin')}</p>`;
    }
    return `<div class="no-data watchlist-prompt">
        <p>${t('followStocksPrompt')}</p>
        <button class="wl-add-btn" onclick="document.querySelector('[data-tab=watchlist]').click()">${t('tabWatchlist')}</button>
    </div>`;
}

// ============================================
// LANGUAGE SWITCH
// ============================================

async function switchLanguage() {
    currentLang = currentLang === 'en' ? 'ar' : 'en';
    localStorage.setItem('lang', currentLang);
    applyLanguage();
    showToast('info', t('langSwitched'));
    await loadSentiment();
    loadStats();
    loadPredictions();
    loadConsensus();
    loadPerformance();
    loadPerformanceDetailed();
    loadEvaluations();
    loadPrices();
    loadGlobalSnapshotBar();
}

function applyLanguage() {
    const isArabic = currentLang === 'ar';

    document.documentElement.dir = isArabic ? 'rtl' : 'ltr';
    document.documentElement.lang = currentLang;
    document.body.classList.toggle('rtl', isArabic);

    // Update page title
    document.title = isArabic ? 'إكسمور — لوحة التنبؤات الذكية للأسهم' : 'Xmore — AI Stock Prediction Dashboard';

    const title = document.querySelector('header h1');
    const subtitle = document.querySelector('.subtitle');
    if (title) title.textContent = t('title');
    if (subtitle) subtitle.textContent = t('subtitle');

    // Stat labels
    document.querySelectorAll('.stat-label').forEach((el, index) => {
        const labels = ['stocksTracked', 'totalPredictions', 'overallAccuracy', 'latestData'];
        if (labels[index]) el.textContent = t(labels[index]);
    });

    // Tab buttons
    const tabs = ['tabPredictions', 'tabBriefing', 'tabTrades', 'tabPortfolio', 'tabWatchlist', 'tabConsensus', 'tabPerformance', 'tabResults', 'tabPrices', 'tabTimeMachine'];
    tabs.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.textContent = t(id);
    });

    // Performance section titles
    const perfAgentTitle = document.getElementById('perfAgentTitle');
    if (perfAgentTitle) perfAgentTitle.textContent = t('agentAccuracy');
    const perfStockTitle = document.getElementById('perfStockTitle');
    if (perfStockTitle) perfStockTitle.textContent = t('stockPerformance');
    const perfMonthlyTitle = document.getElementById('perfMonthlyTitle');
    if (perfMonthlyTitle) perfMonthlyTitle.textContent = t('monthlyTrend');
    const resultsTitle = document.getElementById('resultsTitle');
    if (resultsTitle) resultsTitle.textContent = t('tabResults');
    const briefIds = ['predictionsBrief', 'watchlistBrief', 'performanceBrief', 'consensusBrief', 'resultsBrief', 'pricesBrief', 'briefingBrief', 'tradesBrief', 'portfolioBrief', 'timemachineBrief'];
    briefIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = t(id);
    });

    // Accuracy definition tooltip
    const accDef = document.getElementById('accuracyDefinition');
    if (accDef) accDef.textContent = t('accuracyDefinition');

    // Search placeholder
    const searchInput = document.getElementById('predictionsSearch');
    if (searchInput) searchInput.placeholder = t('searchPlaceholder');

    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn && !refreshBtn.disabled) refreshBtn.textContent = t('refreshData');

    // Disclaimer visibility
    const enDisclaimer = document.getElementById('disclaimerEN');
    const arDisclaimer = document.getElementById('disclaimerAR');
    if (enDisclaimer) enDisclaimer.style.display = isArabic ? 'none' : 'block';
    if (arDisclaimer) arDisclaimer.style.display = isArabic ? 'block' : 'none';

    // Terms link
    const termsLink = document.getElementById('termsLink');
    if (termsLink) termsLink.textContent = t('termsOfService');

    // Language button
    const langBtn = document.getElementById('langBtn');
    if (langBtn) langBtn.textContent = t('switchLang');

    // Skip link (Upgrade 7)
    const skipLink = document.querySelector('.skip-link');
    if (skipLink) skipLink.textContent = t('skipToContent');

    updateThemeButton();

    // Update auth and watchlist text
    if (typeof updateAuthLanguage === 'function') updateAuthLanguage();
    if (typeof updateWatchlistLanguage === 'function') updateWatchlistLanguage();
    if (typeof updateTradesLanguage === 'function') updateTradesLanguage();
    if (typeof updateBriefingLanguage === 'function') updateBriefingLanguage();
    if (typeof updateTimeMachineLanguage === 'function') updateTimeMachineLanguage();
}

// ============================================
// TAB NAVIGATION
// ============================================

function switchToTab(tabId, updateHash) {
    const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    if (!btn) return;

    // Guard: watchlist tab requires login
    if (tabId === 'watchlist' && typeof currentUser !== 'undefined' && !currentUser) {
        if (typeof showAuthModal === 'function') showAuthModal('login');
        return;
    }

    // Toggle active tab button + ARIA
    document.querySelectorAll('.tab-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
    });
    btn.classList.add('active');
    btn.setAttribute('aria-selected', 'true');

    // Toggle active tab content
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    const content = document.getElementById(`tab-${tabId}`);
    if (content) {
        content.classList.add('active');
        // Re-trigger tab entrance animation (Upgrade 5)
        content.style.animation = 'none';
        void content.offsetWidth;
        content.style.animation = '';
    }

    // Update URL hash
    if (updateHash !== false) {
        history.pushState({ tab: tabId }, '', `#${tabId}`);
    }

    // Lazy-load data
    if (tabId === 'watchlist' && typeof loadWatchlist === 'function') loadWatchlist();
    if (tabId === 'briefing' && typeof loadBriefing === 'function') loadBriefing();
    if (tabId === 'trades' && typeof loadTrades === 'function') loadTrades();
    if (tabId === 'portfolio' && typeof loadPortfolio === 'function') loadPortfolio();
    if (tabId === 'performance' && typeof loadPerformanceDashboard === 'function') loadPerformanceDashboard();
    if (tabId === 'timemachine' && typeof loadTimeMachine === 'function') loadTimeMachine();
}

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.setAttribute('tabindex', '0');
        btn.addEventListener('click', () => {
            switchToTab(btn.getAttribute('data-tab'));
        });
        // Keyboard navigation (Upgrade 7)
        btn.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                btn.click();
            }
            if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                const tabs = [...document.querySelectorAll('.tab-btn')];
                const idx = tabs.indexOf(btn);
                const dir = e.key === 'ArrowRight' ? 1 : -1;
                const next = tabs[(idx + dir + tabs.length) % tabs.length];
                next.focus();
                next.click();
            }
        });
    });

    // Handle browser back/forward
    window.addEventListener('popstate', (e) => {
        const tabId = (e.state && e.state.tab) || window.location.hash.slice(1) || 'predictions';
        switchToTab(tabId, false);
    });

    // Load initial tab from URL hash
    const initialTab = window.location.hash.slice(1) || 'predictions';
    if (initialTab !== 'predictions') {
        switchToTab(initialTab, false);
    }
}

// ============================================
// COMPANY NAMES
// ============================================

const COMPANY_NAMES = {
    // US Stocks
    'AAPL': { en: 'Apple Inc.', ar: 'شركة أبل' },
    'GOOGL': { en: 'Alphabet Inc. (Google)', ar: 'ألفابت (جوجل)' },
    'MSFT': { en: 'Microsoft Corporation', ar: 'شركة مايكروسوفت' },
    'AMZN': { en: 'Amazon.com Inc.', ar: 'شركة أمازون' },
    'META': { en: 'Meta Platforms Inc.', ar: 'شركة ميتا' },
    'TSLA': { en: 'Tesla Inc.', ar: 'شركة تسلا' },
    'NVDA': { en: 'NVIDIA Corporation', ar: 'شركة إنفيديا' },
    'JPM': { en: 'JPMorgan Chase & Co.', ar: 'جي بي مورغان' },
    'V': { en: 'Visa Inc.', ar: 'شركة فيزا' },
    'JNJ': { en: 'Johnson & Johnson', ar: 'جونسون آند جونسون' },
    'WMT': { en: 'Walmart Inc.', ar: 'شركة وولمارت' },
    'XOM': { en: 'Exxon Mobil Corporation', ar: 'إكسون موبيل' },
    'BAC': { en: 'Bank of America Corp.', ar: 'بنك أوف أمريكا' },
    'PG': { en: 'Procter & Gamble Co.', ar: 'بروكتر آند غامبل' },
    'HD': { en: 'The Home Depot Inc.', ar: 'هوم ديبوت' },
    // EGX Stocks (Egyptian Exchange)
    'COMI.CA': { en: 'Commercial International Bank CIB', ar: 'البنك التجاري الدولي' },
    'HRHO.CA': { en: 'EFG Holding Hermes', ar: 'هيرميس القابضة' },
    'FWRY.CA': { en: 'Fawry Banking Technology', ar: 'فوري لتكنولوجيا البنوك' },
    'TMGH.CA': { en: 'Talaat Moustafa Group', ar: 'مجموعة طلعت مصطفى' },
    'ORAS.CA': { en: 'Orascom Construction', ar: 'أوراسكوم للإنشاءات' },
    'PHDC.CA': { en: 'Palm Hills Development', ar: 'بالم هيلز للتعمير' },
    'MNHD.CA': { en: 'Madinet Nasr Housing', ar: 'مدينة نصر للإسكان' },
    'OCDI.CA': { en: 'Orascom Development', ar: 'أوراسكوم للتنمية' },
    'SWDY.CA': { en: 'El Sewedy Electric', ar: 'السويدي إليكتريك' },
    'EAST.CA': { en: 'Eastern Company Tobacco', ar: 'الشرقية للدخان' },
    'EFIH.CA': { en: 'Egyptian Financial Industrial', ar: 'المصرية المالية الصناعية' },
    'ESRS.CA': { en: 'Ezz Steel', ar: 'حديد عز' },
    'ETEL.CA': { en: 'Telecom Egypt', ar: 'المصرية للاتصالات' },
    'EMFD.CA': { en: 'E-Finance Digital', ar: 'إي فاينانس' },
    'ALCN.CA': { en: 'Alexandria Container Cargo', ar: 'الإسكندرية للحاويات' },
    'ABUK.CA': { en: 'Abu Qir Fertilizers', ar: 'أبو قير للأسمدة' },
    'MFPC.CA': { en: 'Misr Fertilizers MOPCO', ar: 'موبكو للأسمدة' },
    'SKPC.CA': { en: 'Sidi Kerir Petrochemicals', ar: 'سيدي كرير للبتروكيماويات' },
    'JUFO.CA': { en: 'Juhayna Food Industries', ar: 'جهينة للصناعات الغذائية' },
    'CCAP.CA': { en: 'Cleopatra Hospital', ar: 'مستشفى كليوباترا' },
    'ORWE.CA': { en: 'Oriental Weavers', ar: 'السجاد الشرقي' },
    'AMOC.CA': { en: 'Alexandria Mineral Oils', ar: 'أموك للزيوت المعدنية' },
};

function getCompanyName(symbol) {
    const company = COMPANY_NAMES[symbol];
    if (company) return company[currentLang] || company.en;
    return symbol.replace('.CA', '');
}

// ============================================
// UTILITIES
// ============================================

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        if (hours === '00' && minutes === '00') return `${year}-${month}-${day}`;
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    } catch (e) {
        return dateStr;
    }
}

// Map symbol to TradingView format
function mapToTradingViewSymbol(symbol) {
    if (symbol.endsWith('.CA')) {
        return 'EGX:' + symbol.replace('.CA', '');
    }
    return symbol; // US stocks use plain symbol
}

// ============================================
// SENTIMENT
// ============================================

let sentimentData = {};

async function loadSentiment() {
    try {
        const response = await fetch(`${API_URL}/sentiment`);
        if (response.ok) {
            const data = await response.json();
            sentimentData = {};
            data.forEach(item => { sentimentData[item.symbol] = item; });
        }
    } catch (error) {
        console.error('Error loading sentiment:', error);
    }
}

function getSentimentBadge(symbol) {
    const sentiment = sentimentData[symbol];
    if (!sentiment || !sentiment.sentiment_label) {
        return `<span class="sentiment-badge sentiment-none">${t('noSentiment')}</span>`;
    }
    const label = sentiment.sentiment_label.toLowerCase();
    const displayLabel = t(label) || sentiment.sentiment_label;
    const score = sentiment.avg_sentiment ? sentiment.avg_sentiment.toFixed(2) : '0.00';
    return `<span class="sentiment-badge sentiment-${label}" title="Score: ${score}">${displayLabel}</span>`;
}

// ============================================
// TRADINGVIEW WIDGETS (Task 5)
// ============================================

function loadTradingViewTicker() {
    const container = document.getElementById('tv-ticker-tape');
    if (!container) return;

    const locale = currentLang === 'ar' ? 'ar_AE' : 'en';
    const colorTheme = currentTheme;

    container.innerHTML = '';
    const widgetDiv = document.createElement('div');
    widgetDiv.className = 'tradingview-widget-container__widget';
    container.appendChild(widgetDiv);

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js';
    script.async = true;
    script.textContent = JSON.stringify({
        symbols: [
            { proName: 'EGX:EGX30', title: 'EGX 30' },
            { proName: 'EGX:COMI', title: 'CIB' },
            { proName: 'EGX:HRHO', title: 'Hermes' },
            { proName: 'NASDAQ:AAPL', title: 'Apple' },
            { proName: 'NASDAQ:MSFT', title: 'Microsoft' },
            { proName: 'NASDAQ:NVDA', title: 'NVIDIA' },
        ],
        showSymbolLogo: true,
        colorTheme: colorTheme,
        isTransparent: true,
        displayMode: 'adaptive',
        locale: locale
    });
    container.appendChild(script);
}

// Lazy-load TradingView mini chart for a stock card
function loadTradingViewChart(symbol, containerId) {
    const container = document.getElementById(containerId);
    if (!container || container.dataset.loaded === 'true') return;

    const tvSymbol = mapToTradingViewSymbol(symbol);
    const locale = currentLang === 'ar' ? 'ar_AE' : 'en';

    container.innerHTML = '';
    container.dataset.loaded = 'true';

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js';
    script.async = true;
    script.textContent = JSON.stringify({
        symbol: tvSymbol,
        width: '100%',
        height: '180',
        locale: locale,
        dateRange: '1M',
        colorTheme: currentTheme,
        isTransparent: true,
        autosize: true
    });
    container.appendChild(script);
}

// ============================================
// PERFORMANCE DATA (stored globally for badges)
// ============================================

let agentPerformanceData = {};
let stockPerformanceMap = {};

function trendFromSignal(signalKey) {
    if (signalKey === 'up' || signalKey === 'bullish' || signalKey === 'buy') return t('bullish');
    if (signalKey === 'down' || signalKey === 'bearish' || signalKey === 'sell') return t('bearish');
    return t('neutral');
}

function parsePredictionMetadata(metaRaw) {
    let meta = {};
    if (typeof metaRaw === 'string') {
        try { meta = JSON.parse(metaRaw); } catch (e) { meta = {}; }
    } else if (metaRaw && typeof metaRaw === 'object') {
        meta = metaRaw;
    }

    const rsi = meta.rsi || meta.RSI || meta.rsi_value || null;
    const volume = meta.volume_signal || meta.volume || meta.volume_state || null;
    const sentiment = meta.sentiment_label || meta.sentiment || null;
    const momentum = rsi != null ? `RSI ${Number(rsi).toFixed(1)}` : (meta.momentum || 'N/A');

    return {
        trendPct: meta.trend_score || meta.trend_pct || meta.trend || null,
        sentiment: sentiment || 'N/A',
        volume: volume || 'N/A',
        momentum,
        reasoning: `Trend ${meta.trend_score ?? meta.trend_pct ?? 'N/A'} | Sentiment ${sentiment || 'N/A'} | Volume ${volume || 'N/A'} | Momentum ${momentum}`
    };
}

async function loadGlobalSnapshotBar() {
    const el = document.getElementById('globalPerfSnapshot');
    if (!el) return;

    try {
        const response = await fetch('/api/performance-v2/summary');
        const data = await response.json();
        if (!data || !data.available) {
            el.innerHTML = `<div class="global-snapshot-empty">${t('noPerformance')}</div>`;
            return;
        }

        const g = data.global || {};
        const r30 = data.rolling?.['30d'] || {};
        const trades = g.total_predictions || 0;
        const progressPct = Math.min(100, Math.round((trades / 100) * 100));
        const sharpe = (r30.sharpe_ratio ?? g.sharpe_ratio ?? 0);
        const maxDd = (r30.max_drawdown ?? g.max_drawdown ?? 0);
        const alpha30 = (r30.alpha ?? 0);
        const win30 = (r30.win_rate ?? 0);

        const card = (id, label, cls, tooltip) => `
            <div class="global-snapshot-card ${cls}" title="${tooltip}">
                <div class="global-snapshot-label">${label}</div>
                <div class="global-snapshot-value metric-value" id="${id}">-</div>
            </div>
        `;

        el.innerHTML = `
            <div class="global-snapshot-head">
                <span class="live-only-pill">${t('liveOnlyData')}</span>
            </div>
            <div class="global-snapshot-grid">
                ${card('gsAlpha30', t('snapshotAlpha30d'), alpha30 > 0 ? 'positive' : alpha30 < 0 ? 'negative' : 'neutral', t('tooltipAlpha'))}
                ${card('gsSharpe30', t('snapshotSharpe30d'), sharpe >= 1 ? 'positive' : sharpe > 0 ? 'neutral' : 'negative', t('tooltipSharpe'))}
                ${card('gsMaxDd30', t('snapshotMaxDd30d'), maxDd <= 4 ? 'positive' : maxDd <= 8 ? 'neutral' : 'negative', t('tooltipMaxDd'))}
                ${card('gsWinRate30', t('snapshotWinRate30d'), win30 >= 55 ? 'positive' : win30 >= 45 ? 'neutral' : 'negative', t('tooltipWinRate'))}
                <div class="global-snapshot-card span-2" title="${t('tooltipTrades')}">
                    <div class="global-snapshot-label">${t('snapshotTrades')}</div>
                    <div class="global-snapshot-value metric-value" id="gsTrades">-</div>
                    <div class="global-progress-track"><span class="global-progress-fill progress-fill" style="width:${progressPct}%"></span></div>
                </div>
            </div>
        `;

        // Animate the values (Upgrade 1)
        animateValue('gsAlpha30', alpha30, { decimalPlaces: 2, suffix: '%', prefix: alpha30 > 0 ? '+' : '' });
        animateValue('gsSharpe30', sharpe, { decimalPlaces: 2, prefix: sharpe > 0 ? '+' : '' });
        animateValue('gsMaxDd30', maxDd, { decimalPlaces: 2, suffix: '%' });
        animateValue('gsWinRate30', win30, { decimalPlaces: 1, suffix: '%' });
        animateValue('gsTrades', trades, { decimalPlaces: 0 });
    } catch (error) {
        console.error('Error loading global snapshot bar:', error);
        el.innerHTML = `<div class="global-snapshot-empty">${t('errorPerformance')}</div>`;
    }
}

// ============================================
// LOAD DATA ON PAGE LOAD
// ============================================

window.addEventListener('load', async () => {
    try {
        initNotyf();
        applyLanguage();
        initTabs();
        loadTradingViewTicker();
        loadGlobalSnapshotBar();

        // Show skeletons before data loads (Upgrade 4)
        showSkeleton('predictions', 'predictions');
        showSkeleton('evaluations', 'results');
        showSkeleton('prices', 'prices');
        showSkeleton('consensusCards', 'consensus');

        // Set aria-live on dynamic containers (Upgrade 7)
        ['predictions', 'evaluations', 'prices', 'consensusCards'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.setAttribute('aria-live', 'polite');
        });

        // Fetch watchlist symbols first (needed for filtering all tabs)
        await fetchUserWatchlistSymbols();

        // Load all independent data in parallel
        loadStats();
        loadConsensus();
        loadPerformance();
        loadPerformanceDetailed();
        loadEvaluations();
        loadPrices();

        // Predictions need sentiment data for badges, so chain them
        loadSentiment()
            .then(() => loadPredictions())
            .catch(err => {
                console.error('Failed loading predictions chain:', err);
                const el = document.getElementById('predictions');
                if (el) el.innerHTML = `<p class="error-message">Failed to load: ${escapeHtml(err.message)}</p>`;
            });
    } catch (err) {
        console.error('Load handler error:', err);
        const el = document.getElementById('predictions');
        if (el) el.innerHTML = `<p class="error-message">Init error: ${escapeHtml(err.message)}</p>`;
    }
});

document.getElementById('langBtn')?.addEventListener('click', switchLanguage);
document.getElementById('themeBtn')?.addEventListener('click', toggleTheme);

// ============================================
// REFRESH
// ============================================

async function refreshData() {
    const btn = document.getElementById('refreshBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = t('refreshing');
        btn.classList.add('loading-btn');
    }

    try {
        // Re-fetch watchlist cache in case user followed/unfollowed stocks
        resetWatchlistCache();
        await fetchUserWatchlistSymbols();

        await loadSentiment();
        await Promise.all([
            loadStats(),
            loadGlobalSnapshotBar(),
            loadPredictions(),
            loadConsensus(),
            loadPerformance(),
            loadPerformanceDetailed(),
            loadEvaluations(),
            loadPrices()
        ]);

        // Load trades if functions exist
        if (typeof loadTrades === 'function') loadTrades();
        if (typeof loadPortfolio === 'function') loadPortfolio();
        showToast('success', t('dataRefreshed'));
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = t('refreshData');
            btn.classList.remove('loading-btn');
        }
    }
}

document.getElementById('refreshBtn')?.addEventListener('click', refreshData);

// ============================================
// LOAD STATS
// ============================================

async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const data = await response.json();

        animateValue('stocksTracked', data.stocksTracked || 0, { decimalPlaces: 0 });
        animateValue('totalPredictions', data.totalPredictions || 0, { decimalPlaces: 0 });
        document.getElementById('latestDate').textContent = formatDate(data.latestDate);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// ============================================
// LOAD PREDICTIONS (Task 6: Signal terminology)
// ============================================

async function loadPredictions() {
    const container = document.getElementById('predictions');

    try {
        const [predRes, stockPerfRes] = await Promise.all([
            fetch(`${API_URL}/predictions`),
            fetch('/api/performance-v2/by-stock?days=90').catch(() => null)
        ]);
        if (!predRes.ok) throw new Error(`HTTP error: ${predRes.status}`);

        const result = await predRes.json();
        const data = Array.isArray(result) ? result : (result.predictions || []);
        const stockPerfData = stockPerfRes && stockPerfRes.ok ? await stockPerfRes.json() : { stocks: [] };
        stockPerformanceMap = {};
        (stockPerfData.stocks || []).forEach(s => { stockPerformanceMap[s.symbol] = s; });

        clearSkeleton('predictions');
        if (!data || data.length === 0) {
            renderEmptyState('predictions', '\uD83D\uDCCA', 'emptyPredictions', 'emptyPredictionsDesc', null, null);
            return;
        }

        const grouped = {};
        data.forEach(pred => {
            if (!grouped[pred.symbol]) grouped[pred.symbol] = [];
            grouped[pred.symbol].push(pred);
        });

        const allSymbols = Object.keys(grouped);

        if (isLoggedIn()) {
            const watchlistSymbols = allSymbols.filter(s => userWatchlistSymbols.has(s));
            if (userWatchlistSymbols.size === 0) {
                container.innerHTML = getWatchlistEmptyHtml();
                return;
            }
            if (watchlistSymbols.length === 0) {
                container.innerHTML = `<p class="no-data">${t('noPredictions')}</p>`;
                return;
            }
            container.innerHTML = renderPredictionTable(grouped, watchlistSymbols, 'predictionsTable');
        } else {
            container.innerHTML = renderPredictionTable(grouped, allSymbols, 'predictionsTable');
        }
    } catch (error) {
        console.error('Error loading predictions:', error);
        clearSkeleton('predictions');
        container.innerHTML = `<p class="error-message">${t('errorPredictions')}</p>`;
        showToast('error', t('loadError'));
    }
}

function renderPredictionTable(grouped, symbols, tableId) {
    if (symbols.length === 0) return '';

    let html = `<table id="${tableId}" class="predictions-v2-table"><thead><tr><th>${t('stock')}</th><th>${t('consensusSignal')}</th><th>${t('agreement')}</th><th>${t('conviction')}</th><th>${t('recentAccuracySymbol')}</th><th>${t('expandDetails')}</th></tr></thead><tbody>`;

    symbols.forEach(symbol => {
        const predictions = grouped[symbol];
        const companyName = getCompanyName(symbol);
        const searchText = `${symbol} ${companyName}`.toLowerCase();
        const tally = { up: 0, down: 0, hold: 0 };
        let confidenceSum = 0;

        const agentDetails = predictions.map(pred => {
            const signalKey = (pred.prediction || 'hold').toLowerCase();
            if (tally[signalKey] == null) tally[signalKey] = 0;
            tally[signalKey] += 1;
            const confidence = Number(pred.confidence || 0);
            confidenceSum += confidence;
            return {
                agentDisplayName: getAgentDisplayName(pred.agent_name),
                agentDescription: getAgentDescription(pred.agent_name),
                signalKey,
                signalText: t(signalKey),
                confidence,
                metadata: parsePredictionMetadata(pred.metadata)
            };
        });

        const consensusKey = Object.keys(tally).sort((a, b) => (tally[b] || 0) - (tally[a] || 0))[0] || 'hold';
        const agreeCount = tally[consensusKey] || 0;
        const agreementPct = predictions.length ? Math.round((agreeCount / predictions.length) * 100) : 0;
        const convictionValue = predictions.length ? confidenceSum / predictions.length : 0;
        const recentAcc = stockPerformanceMap[symbol]?.win_rate;
        const detailsId = `pred-details-${symbol.replace('.', '-')}`;

        html += `
            <tr data-search="${searchText}" class="group-start pred-stock-row">
                <td class="stock-cell"><strong>${symbol}</strong><br><small class="company-name">${companyName}</small></td>
                <td><span class="signal-${consensusKey}">${t(consensusKey)}</span></td>
                <td>${agreeCount}/${predictions.length} (${agreementPct}%)</td>
                <td>${convictionValue.toFixed(1)}%</td>
                <td>${recentAcc == null ? 'N/A' : `${Number(recentAcc).toFixed(1)}%`}</td>
                <td><button class="perf-action-btn secondary" onclick="togglePredictionDetails('${detailsId}')">${t('expandDetails')}</button></td>
            </tr>
            <tr data-search="${searchText}" class="group-row hidden-row pred-detail-row" id="${detailsId}">
                <td colspan="6">
                    <div class="signal-why-grid">
                        <div class="signal-why-title">${t('whySignal')}</div>
                        <div class="signal-why-item"><span>${t('trend')}</span><strong>${trendFromSignal(consensusKey)}</strong></div>
                        <div class="signal-why-item"><span>${t('momentum')}</span><strong>${agentDetails[0]?.metadata?.momentum || 'N/A'}</strong></div>
                        <div class="signal-why-item"><span>${t('volumeState')}</span><strong>${agentDetails[0]?.metadata?.volume || 'N/A'}</strong></div>
                        <div class="signal-why-item"><span>${t('sentimentState')}</span><strong>${agentDetails[0]?.metadata?.sentiment || 'N/A'}</strong></div>
                        <div class="signal-why-item"><span>${t('agentAgreement')}</span><strong>${agreementPct}%</strong></div>
                    </div>
                    <div class="pred-agent-breakdown">
                        ${agentDetails.map(d => `
                            <div class="pred-agent-row">
                                <div><span class="agent-name" title="${d.agentDescription}">${d.agentDisplayName}</span> <span class="signal-${d.signalKey}">${d.signalText}</span></div>
                                <div>${t('conf')}: ${d.confidence.toFixed(1)}%</div>
                                <div class="pred-reason">${d.metadata.reasoning}</div>
                            </div>
                        `).join('')}
                    </div>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    return html;
}

function togglePredictionDetails(id) {
    const row = document.getElementById(id);
    if (!row) return;
    row.classList.toggle('hidden-row');
}

// ============================================
// FILTER PREDICTIONS
// ============================================

function filterPredictions() {
    const searchValue = document.getElementById('predictionsSearch').value.toLowerCase().trim();

    ['predictionsTable', 'watchlistPredictionsTable'].forEach(tableId => {
        const table = document.getElementById(tableId);
        if (!table) return;

        const rows = table.querySelectorAll('tbody tr');
        let currentGroupVisible = false;

        rows.forEach(row => {
            const searchText = row.getAttribute('data-search') || '';
            const isGroupStart = row.classList.contains('group-start');
            if (isGroupStart) {
                currentGroupVisible = searchText.includes(searchValue);
                row.classList.toggle('hidden-row', !currentGroupVisible);
                return;
            }
            if (row.classList.contains('pred-detail-row')) {
                if (!currentGroupVisible) row.classList.add('hidden-row');
                return;
            }
            row.classList.toggle('hidden-row', !currentGroupVisible);
        });
    });
}

// ============================================
// LOAD PERFORMANCE (basic — existing endpoint)
// ============================================

async function loadPerformance() {
    const container = document.getElementById('perfAgents');
    if (!container) return;

    try {
        const response = await fetch(`${API_URL}/performance`);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        const data = await response.json();

        // Store for agent accuracy badges
        data.forEach(agent => {
            agentPerformanceData[agent.agent_name] = agent;
        });

        if (!data || data.length === 0) {
            container.innerHTML = `<p class="no-data">${t('noPerformance')}</p>`;
            return;
        }

        let html = `<table><thead><tr><th>${t('agent')}</th><th>${t('totalPreds')}</th><th>${t('correct')}</th><th>${t('accuracy')}</th></tr></thead><tbody>`;

        data.forEach(agent => {
            const agentDisplayName = getAgentDisplayName(agent.agent_name);
            const agentDescription = getAgentDescription(agent.agent_name);
            const accuracyClass = agent.accuracy >= 60 ? 'high' : agent.accuracy >= 40 ? 'medium' : 'low';
            html += `
                <tr>
                    <td><strong class="agent-name" title="${agentDescription}">${agentDisplayName}</strong></td>
                    <td>${agent.total_predictions}</td>
                    <td>${agent.correct_predictions}</td>
                    <td>
                        <div class="accuracy-bar">
                            <div class="accuracy-fill accuracy-${accuracyClass}" style="width: ${agent.accuracy}%">
                                ${agent.accuracy}%
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading performance:', error);
        container.innerHTML = `<p class="error-message">${t('errorPerformance')}</p>`;
    }
}

// ============================================
// LOAD DETAILED PERFORMANCE (Task 4)
// ============================================

async function loadPerformanceDetailed() {
    try {
        const response = await fetch(`${API_URL}/performance/detailed`);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        const data = await response.json();

        // Update overall accuracy in stats bar (avoids duplicate API call)
        const acc = data?.overall?.directional_accuracy;
        if (acc) {
            animateValue('overallAccuracy', acc, { decimalPlaces: 1, suffix: '%' });
        }

        // Render overall stats
        renderOverallStats(data.overall);

        // Render per-stock table
        renderPerStockTable(data.per_stock);

        // Render monthly chart
        renderMonthlyChart(data.monthly);

    } catch (error) {
        console.error('Error loading detailed performance:', error);
        const container = document.getElementById('perfOverall');
        if (container) container.innerHTML = `<p class="no-data">${t('noDetailedPerformance')}</p>`;
    }
}

function renderOverallStats(overall) {
    const container = document.getElementById('perfOverall');
    if (!container || !overall) return;

    if (!overall.total_predictions) {
        container.innerHTML = `<p class="no-data">${t('noDetailedPerformance')}</p>`;
        return;
    }

    container.innerHTML = `
        <div class="perf-stats-grid">
            <div class="perf-stat-card">
                <div class="perf-stat-value metric-value" id="perfDirAcc">-</div>
                <div class="perf-stat-label">${t('directionalAccuracy')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value metric-value" id="perfTotalSig">-</div>
                <div class="perf-stat-label">${t('totalSignals')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value metric-value" id="perfWinBuy">-</div>
                <div class="perf-stat-label">${t('winRateBuy')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value metric-value" id="perfWinSell">-</div>
                <div class="perf-stat-label">${t('winRateSell')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value metric-value" id="perfAvgRet">-</div>
                <div class="perf-stat-label">${t('avgReturnPerSignal')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value metric-value" id="perfMaxDd">-</div>
                <div class="perf-stat-label">${t('maxDrawdown')}</div>
            </div>
        </div>
    `;
    animateValue('perfDirAcc', overall.directional_accuracy || 0, { decimalPlaces: 1, suffix: '%' });
    animateValue('perfTotalSig', overall.total_predictions || 0, { decimalPlaces: 0 });
    animateValue('perfWinBuy', overall.win_rate_buy || 0, { decimalPlaces: 1, suffix: '%' });
    animateValue('perfWinSell', overall.win_rate_sell || 0, { decimalPlaces: 1, suffix: '%' });
    animateValue('perfAvgRet', (overall.avg_return_per_signal * 100), { decimalPlaces: 2, suffix: '%' });
    animateValue('perfMaxDd', ((overall.max_drawdown || 0) * 100), { decimalPlaces: 1, suffix: '%' });
}

function renderPerStockTable(perStock) {
    const container = document.getElementById('perfStocks');
    if (!container) return;

    let entries = Object.entries(perStock || {});

    // Filter to watchlist stocks for logged-in users
    if (isLoggedIn() && userWatchlistSymbols.size > 0) {
        entries = entries.filter(([symbol]) => userWatchlistSymbols.has(symbol));
    }

    if (entries.length === 0) {
        container.innerHTML = `<p class="no-data">${t('noDetailedPerformance')}</p>`;
        return;
    }

    let html = `<table><thead><tr><th>${t('stock')}</th><th>${t('accuracy')}</th><th>${t('avgReturn')}</th><th>${t('totalPreds')}</th></tr></thead><tbody>`;

    entries.forEach(([symbol, stats]) => {
        const companyName = getCompanyName(symbol);
        const accuracyClass = stats.accuracy >= 60 ? 'high' : stats.accuracy >= 40 ? 'medium' : 'low';
        html += `
            <tr>
                <td><strong>${symbol}</strong><br><small class="company-name">${companyName}</small></td>
                <td>
                    <div class="accuracy-bar">
                        <div class="accuracy-fill accuracy-${accuracyClass}" style="width: ${stats.accuracy}%">${stats.accuracy}%</div>
                    </div>
                </td>
                <td class="${stats.avg_return >= 0 ? 'positive-change' : 'negative-change'}">${(stats.avg_return * 100).toFixed(2)}%</td>
                <td>${stats.predictions}</td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderMonthlyChart(monthly) {
    const canvas = document.getElementById('monthlyChart');
    if (!canvas || !monthly || monthly.length === 0) return;

    const ctx = canvas.getContext('2d');
    const padding = 50;
    const width = canvas.width;
    const height = canvas.height;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Sort by month
    monthly.sort((a, b) => a.month.localeCompare(b.month));

    const maxAcc = Math.max(...monthly.map(m => m.accuracy), 100);
    const barWidth = Math.min(chartWidth / monthly.length - 4, 40);

    // Style
    const isDark = currentTheme === 'dark';
    ctx.fillStyle = isDark ? '#e0e0e0' : '#333';
    ctx.font = '12px -apple-system, sans-serif';
    ctx.textAlign = 'center';

    // Y-axis label
    ctx.save();
    ctx.translate(15, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(t('accuracy') + ' (%)', 0, 0);
    ctx.restore();

    // Draw bars
    monthly.forEach((m, i) => {
        const x = padding + (i * (chartWidth / monthly.length)) + (chartWidth / monthly.length - barWidth) / 2;
        const barHeight = (m.accuracy / maxAcc) * chartHeight;
        const y = padding + chartHeight - barHeight;

        // Bar gradient
        const gradient = ctx.createLinearGradient(x, y, x, y + barHeight);
        if (m.accuracy >= 60) {
            gradient.addColorStop(0, '#22c55e');
            gradient.addColorStop(1, '#16a34a');
        } else if (m.accuracy >= 40) {
            gradient.addColorStop(0, '#f59e0b');
            gradient.addColorStop(1, '#d97706');
        } else {
            gradient.addColorStop(0, '#ef4444');
            gradient.addColorStop(1, '#dc2626');
        }
        ctx.fillStyle = gradient;

        // Rounded top corners
        const radius = 4;
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + barWidth - radius, y);
        ctx.arcTo(x + barWidth, y, x + barWidth, y + radius, radius);
        ctx.lineTo(x + barWidth, y + barHeight);
        ctx.lineTo(x, y + barHeight);
        ctx.lineTo(x, y + radius);
        ctx.arcTo(x, y, x + radius, y, radius);
        ctx.fill();

        // Value on top
        ctx.fillStyle = isDark ? '#e0e0e0' : '#333';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(`${m.accuracy}%`, x + barWidth / 2, y - 6);

        // Month label
        ctx.fillText(m.month.slice(5), x + barWidth / 2, padding + chartHeight + 18);
    });

    // 50% baseline
    const baselineY = padding + chartHeight - (50 / maxAcc) * chartHeight;
    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = isDark ? '#666' : '#ccc';
    ctx.beginPath();
    ctx.moveTo(padding, baselineY);
    ctx.lineTo(width - padding, baselineY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = isDark ? '#888' : '#999';
    ctx.font = '10px -apple-system, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('50%', padding - 30, baselineY + 4);
}

// ============================================
// LOAD EVALUATIONS
// ============================================

async function loadEvaluations() {
    const container = document.getElementById('evaluations');

    try {
        const response = await fetch(`${API_URL}/evaluations`);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        const data = await response.json();

        clearSkeleton('evaluations');
        if (!data || data.length === 0) {
            renderEmptyState('evaluations', '\uD83D\uDCC8', 'emptyResults', 'emptyResultsDesc', null, null);
            return;
        }

        // Filter to watchlist stocks for logged-in users
        let filteredData = data;
        if (isLoggedIn()) {
            if (userWatchlistSymbols.size === 0) {
                container.innerHTML = getWatchlistEmptyHtml();
                return;
            }
            filteredData = data.filter(item => userWatchlistSymbols.has(item.symbol));
            if (filteredData.length === 0) {
                renderEmptyState('evaluations', '\uD83D\uDCC8', 'emptyResults', 'emptyResultsDesc', null, null);
                return;
            }
        }

        const groupedBySymbol = {};
        filteredData.forEach(item => {
            if (!groupedBySymbol[item.symbol]) groupedBySymbol[item.symbol] = [];
            groupedBySymbol[item.symbol].push(item);
        });

        const symbols = Object.keys(groupedBySymbol).sort((a, b) => a.localeCompare(b));
        let html = '<div class="results-stock-list">';

        symbols.forEach((symbol, index) => {
            const rows = groupedBySymbol[symbol].slice().sort((a, b) => {
                return new Date(b.target_date) - new Date(a.target_date);
            });
            const companyName = getCompanyName(symbol);
            const toneClass = `tone-${(index % 3) + 1}`;

            html += `
                <article class="result-stock-card ${toneClass}">
                    <div class="result-stock-header">
                        <div class="result-stock-symbol">${symbol}</div>
                        <div class="result-stock-company">${companyName}</div>
                    </div>
                    <div class="result-stock-table-wrap">
                        <table class="result-stock-table">
                            <thead>
                                <tr>
                                    <th>${t('agent')}</th>
                                    <th>${t('signal')}</th>
                                    <th>${t('actualOutcome')}</th>
                                    <th>${t('priceChange')}</th>
                                    <th>${t('result')}</th>
                                    <th>${t('targetDate')}</th>
                                </tr>
                            </thead>
                            <tbody>
            `;

            rows.forEach(item => {
                const agentDisplayName = getAgentDisplayName(item.agent_name);
                const predictionText = t(item.prediction.toLowerCase());
                const actualText = t(item.actual_outcome.toLowerCase());
                const changePercent = item.actual_change_pct ? item.actual_change_pct.toFixed(2) : '0.00';
                const changeClass = parseFloat(changePercent) >= 0 ? 'positive-change' : 'negative-change';
                const resultClass = item.was_correct ? 'result-correct' : 'result-wrong';
                const resultIcon = item.was_correct ? '&#10003;' : '&#10007;';

                html += `
                    <tr>
                        <td>${agentDisplayName}</td>
                        <td><span class="signal-${item.prediction.toLowerCase()}">${predictionText}</span></td>
                        <td><span class="signal-${item.actual_outcome.toLowerCase()}">${actualText}</span></td>
                        <td class="${changeClass}">${changePercent}%</td>
                        <td><span class="${resultClass}">${resultIcon}</span></td>
                        <td>${formatDate(item.target_date)}</td>
                    </tr>
                `;
            });

            html += `
                            </tbody>
                        </table>
                    </div>
                </article>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading evaluations:', error);
        container.innerHTML = `<p class="error-message">${t('errorEvaluations')}</p>`;
    }
}

// ============================================
// LOAD PRICES
// ============================================

async function loadPrices() {
    const container = document.getElementById('prices');

    try {
        const response = await fetch(`${API_URL}/prices`);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        const data = await response.json();

        clearSkeleton('prices');
        if (!data || data.length === 0) {
            container.innerHTML = `<p class="no-data">${t('noPrices')}</p>`;
            return;
        }

        // Filter to watchlist stocks for logged-in users
        let filteredData = data;
        if (isLoggedIn()) {
            if (userWatchlistSymbols.size === 0) {
                container.innerHTML = getWatchlistEmptyHtml();
                return;
            }
            filteredData = data.filter(stock => userWatchlistSymbols.has(stock.symbol));
            if (filteredData.length === 0) {
                container.innerHTML = `<p class="no-data">${t('noPrices')}</p>`;
                return;
            }
        }

        let html = `<table><thead><tr><th>${t('stock')}</th><th>${t('date')}</th><th>${t('closePrice')}</th><th>${t('volume')}</th></tr></thead><tbody>`;

        filteredData.forEach(stock => {
            const companyName = getCompanyName(stock.symbol);
            html += `
                <tr>
                    <td><strong>${stock.symbol}</strong><br><small class="company-name">${companyName}</small></td>
                    <td>${formatDate(stock.date)}</td>
                    <td class="price-cell">${parseFloat(stock.close).toFixed(2)}</td>
                    <td class="volume-cell">${parseInt(stock.volume).toLocaleString()}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading prices:', error);
        container.innerHTML = `<p class="error-message">${t('errorPrices')}</p>`;
    }
}

// ============================================
// LOAD CONSENSUS DATA (3-Layer Pipeline)
// ============================================

async function loadConsensus() {
    const cardsContainer = document.getElementById('consensusCards');
    if (!cardsContainer) return;

    try {
        // Fetch consensus data and risk overview in parallel
        const [consensusRes, riskRes] = await Promise.all([
            fetch(`${API_URL}/consensus`),
            fetch(`${API_URL}/risk/overview`)
        ]);

        const consensusData = consensusRes.ok ? await consensusRes.json() : [];
        const riskData = riskRes.ok ? await riskRes.json() : { stocks: [], summary: {} };

        // Update risk overview stats
        const summary = riskData.summary || {};
        const elTotal = document.getElementById('riskStocksTotal');
        const elPassed = document.getElementById('riskPassed');
        const elFlagged = document.getElementById('riskFlagged');
        const elBlocked = document.getElementById('riskBlocked');
        if (elTotal) elTotal.textContent = summary.total || 0;
        if (elPassed) elPassed.textContent = summary.passed || 0;
        if (elFlagged) elFlagged.textContent = (summary.flagged || 0) + (summary.downgraded || 0);
        if (elBlocked) elBlocked.textContent = summary.blocked || 0;

        // Update i18n labels
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (key) el.textContent = t(key);
        });

        clearSkeleton('consensusCards');
        if (!consensusData || consensusData.length === 0) {
            cardsContainer.innerHTML = `<p class="no-data">${t('noConsensus')}</p>`;
            return;
        }

        // Filter to watchlist stocks for logged-in users
        let filteredConsensus = consensusData;
        if (isLoggedIn()) {
            if (userWatchlistSymbols.size === 0) {
                cardsContainer.innerHTML = getWatchlistEmptyHtml();
                return;
            }
            filteredConsensus = consensusData.filter(item => userWatchlistSymbols.has(item.symbol));
            if (filteredConsensus.length === 0) {
                cardsContainer.innerHTML = `<p class="no-data">${t('noConsensus')}</p>`;
                return;
            }
        }

        // Render consensus cards
        let html = '';
        filteredConsensus.forEach(item => {
            html += renderConsensusCard(item);
        });
        cardsContainer.innerHTML = html;

    } catch (error) {
        console.error('Error loading consensus:', error);
        cardsContainer.innerHTML = `<p class="error-message">${t('errorConsensus')}</p>`;
    }
}

function renderConsensusCard(item) {
    const isArabic = currentLang === 'ar';
    const companyName = getCompanyName(item.symbol);

    // Signal display
    const display = item.display || {};
    const signalText = isArabic ? (display.signal_text_ar || display.signal_text || item.final_signal) : (display.signal_text || item.final_signal);
    const signalKey = (item.final_signal || 'HOLD').toLowerCase();

    // Conviction
    const convictionText = isArabic ? (display.conviction_text_ar || item.conviction) : (display.conviction_text || item.conviction);
    const convictionClass = (item.conviction || 'LOW').toLowerCase().replace('_', '-');

    // Summary
    const summaryText = isArabic ? (display.summary_ar || display.summary || '') : (display.summary || '');

    // Bull/Bear scores
    const bullScore = item.bull_score || 0;
    const bearScore = item.bear_score || 0;

    // Risk action
    const riskAction = item.risk_action || 'PASS';
    const riskScore = item.risk_score || 0;
    const riskAdjusted = item.risk_adjusted;

    // Risk warnings from risk_assessment
    const riskAssessment = item.risk_assessment || {};
    const riskFlags = isArabic ? (riskAssessment.risk_flags_ar || []) : (riskAssessment.risk_flags || []);

    // Agreement
    const agreementPct = Math.round((item.agent_agreement || 0) * 100);
    const agentsAgreeing = item.agents_agreeing || 0;
    const agentsTotal = item.agents_total || 0;

    // Risk action badge class
    let riskBadgeClass = 'risk-badge-pass';
    let riskBadgeText = '✓ PASS';
    if (riskAction === 'BLOCK') {
        riskBadgeClass = 'risk-badge-block';
        riskBadgeText = '🚫 BLOCK';
    } else if (riskAction === 'DOWNGRADE') {
        riskBadgeClass = 'risk-badge-downgrade';
        riskBadgeText = '⬇ DOWNGRADE';
    } else if (riskAction === 'FLAG') {
        riskBadgeClass = 'risk-badge-flag';
        riskBadgeText = '⚠️ FLAG';
    }

    return `
    <div class="consensus-card ${riskAction === 'BLOCK' ? 'consensus-card-blocked' : ''}">
        <div class="consensus-card-header">
            <div class="consensus-card-stock">
                <strong>${item.symbol}</strong>
                <small class="company-name">${companyName}</small>
            </div>
            <div class="consensus-card-signal">
                <span class="consensus-signal-badge signal-${signalKey}">${signalText}</span>
                ${riskAdjusted ? '<span class="risk-adjusted-badge" title="Risk-adjusted">⚠️</span>' : ''}
            </div>
        </div>

        <div class="consensus-card-body">
            <!-- Conviction & Agreement -->
            <div class="consensus-meta-row">
                <div class="consensus-meta-item">
                    <span class="meta-label">${t('conviction')}:</span>
                    <span class="conviction-badge conviction-${convictionClass}">${convictionText}</span>
                </div>
                <div class="consensus-meta-item">
                    <span class="meta-label">${t('consensus')}:</span>
                    <span class="agreement-text">${agentsAgreeing}/${agentsTotal} (${agreementPct}%)</span>
                </div>
            </div>

            <!-- Bull/Bear Bars -->
            <div class="bull-bear-section">
                <div class="bull-bear-row">
                    <span class="bb-label">🐂 ${t('bullCase')}</span>
                    <div class="bb-bar-container">
                        <div class="bb-bar bb-bull" style="width: ${bullScore}%"></div>
                    </div>
                    <span class="bb-score">${bullScore}</span>
                </div>
                <div class="bull-bear-row">
                    <span class="bb-label">🐻 ${t('bearCase')}</span>
                    <div class="bb-bar-container">
                        <div class="bb-bar bb-bear" style="width: ${bearScore}%"></div>
                    </div>
                    <span class="bb-score">${bearScore}</span>
                </div>
            </div>

            <!-- Risk Badge -->
            <div class="consensus-risk-row">
                <span class="${riskBadgeClass}">${riskBadgeText}</span>
                <span class="risk-score-text">${t('riskAction')}: ${riskScore}/100</span>
            </div>

            <!-- Summary -->
            <div class="consensus-summary">${summaryText}</div>

            ${riskFlags.length > 0 ? `
            <details class="risk-warnings-details">
                <summary>${t('riskWarnings')} (${riskFlags.length})</summary>
                <ul class="risk-warnings-list">
                    ${riskFlags.map(f => `<li>${f}</li>`).join('')}
                </ul>
            </details>` : ''}
        </div>
    </div>`;
}

