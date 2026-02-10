// ============================================
// Xmore — AI Stock Prediction Dashboard
// Phase 1 Upgrade: Performance Dashboard, TradingView, Consensus, Compliance
// ============================================

// Global error handler — surface JS errors visibly for debugging
window.onerror = function(msg, url, line, col, error) {
    console.error('Global error:', msg, url, line, col, error);
    const el = document.getElementById('predictions');
    if (el) el.innerHTML = `<p class="error-message">JS Error: ${msg} (line ${line})</p>`;
};

const API_URL = '/api';

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
        tabPerformance: 'Performance',
        tabResults: 'Results',
        tabPrices: 'Prices',

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

        // Language
        switchLang: 'عربي',

        // Theme
        lightMode: 'Switch to light mode',
        darkMode: 'Switch to dark mode',

        // Terms
        termsOfService: 'Terms of Service'
    },
    ar: {
        title: 'إكسمور',
        subtitle: 'لوحة التنبؤات الذكية للأسهم',

        stocksTracked: 'الأسهم المتابعة',
        totalPredictions: 'إجمالي التنبؤات',
        overallAccuracy: 'الدقة',
        latestData: 'آخر تحديث',

        tabPredictions: 'التنبؤات',
        tabPerformance: 'الأداء',
        tabResults: 'النتائج',
        tabPrices: 'الأسعار',

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

        switchLang: 'English',

        lightMode: 'التبديل إلى الوضع الفاتح',
        darkMode: 'التبديل إلى الوضع الداكن',

        termsOfService: 'شروط الخدمة'
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
// LANGUAGE SWITCH
// ============================================

async function switchLanguage() {
    currentLang = currentLang === 'en' ? 'ar' : 'en';
    localStorage.setItem('lang', currentLang);
    applyLanguage();
    await loadSentiment();
    loadStats();
    loadPredictions();
    loadPerformance();
    loadPerformanceDetailed();
    loadEvaluations();
    loadPrices();
    loadTradingViewTicker();
}

function applyLanguage() {
    const isArabic = currentLang === 'ar';

    document.documentElement.dir = isArabic ? 'rtl' : 'ltr';
    document.documentElement.lang = currentLang;
    document.body.classList.toggle('rtl', isArabic);

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
    const tabs = ['tabPredictions', 'tabPerformance', 'tabResults', 'tabPrices'];
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

    updateThemeButton();
}

// ============================================
// TAB NAVIGATION
// ============================================

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');

            // Toggle active tab button
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Toggle active tab content
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            const content = document.getElementById(`tab-${tabId}`);
            if (content) content.classList.add('active');
        });
    });
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

// ============================================
// LOAD DATA ON PAGE LOAD
// ============================================

window.addEventListener('load', () => {
    try {
        applyLanguage();
        initTabs();
        loadTradingViewTicker();

        // Load all independent data in parallel
        loadStats();
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
                if (el) el.innerHTML = `<p class="error-message">Failed to load: ${err.message}</p>`;
            });
    } catch (err) {
        console.error('Load handler error:', err);
        const el = document.getElementById('predictions');
        if (el) el.innerHTML = `<p class="error-message">Init error: ${err.message}</p>`;
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
        await loadSentiment();
        await Promise.all([
            loadStats(),
            loadPredictions(),
            loadPerformance(),
            loadPerformanceDetailed(),
            loadEvaluations(),
            loadPrices()
        ]);
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

        document.getElementById('stocksTracked').textContent = data.stocksTracked || '0';
        document.getElementById('totalPredictions').textContent = data.totalPredictions || '0';
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
        const response = await fetch(`${API_URL}/predictions`);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);

        const result = await response.json();
        // Handle new API format with disclaimer wrapper
        const data = Array.isArray(result) ? result : (result.predictions || []);

        if (!data || data.length === 0) {
            container.innerHTML = `<p class="no-data">${t('noPredictions')}</p>`;
            return;
        }

        // Group predictions by stock symbol
        const grouped = {};
        data.forEach(pred => {
            if (!grouped[pred.symbol]) grouped[pred.symbol] = [];
            grouped[pred.symbol].push(pred);
        });

        let html = `<table id="predictionsTable"><thead><tr><th>${t('stock')}</th><th>${t('sentiment')}</th><th>${t('agent')}</th><th>${t('signal')}</th><th>${t('date')}</th></tr></thead><tbody>`;

        Object.keys(grouped).forEach(symbol => {
            const predictions = grouped[symbol];
            const companyName = getCompanyName(symbol);
            const searchText = `${symbol} ${companyName}`.toLowerCase();
            const chartContainerId = `tv-chart-${symbol.replace('.', '-')}`;

            predictions.forEach((pred, index) => {
                const agentDisplayName = getAgentDisplayName(pred.agent_name);
                const agentDescription = getAgentDescription(pred.agent_name);
                // Task 6: Signal instead of prediction
                const signalKey = pred.prediction.toLowerCase();
                const signalText = t(signalKey);
                // Agent accuracy badge
                const agentAcc = agentPerformanceData[pred.agent_name];
                const accBadge = agentAcc
                    ? `<span class="agent-accuracy-badge" title="${agentAcc.accuracy}% ${t('agentHistoryBadge')}">${agentAcc.accuracy}%</span>`
                    : '';

                html += `<tr data-search="${searchText}" class="${index === 0 ? 'group-start' : 'group-row'}">`;

                if (index === 0) {
                    html += `<td rowspan="${predictions.length}" class="stock-cell">
                        <strong>${symbol}</strong><br>
                        <small class="company-name">${companyName}</small>
                        <div class="tv-chart-mini" id="${chartContainerId}" data-symbol="${symbol}" onclick="loadTradingViewChart('${symbol}', '${chartContainerId}')">
                            <small class="chart-hint">📊 ${currentLang === 'ar' ? 'اضغط للرسم البياني' : 'Click for chart'}</small>
                        </div>
                    </td>`;
                    html += `<td rowspan="${predictions.length}" class="sentiment-cell">${getSentimentBadge(symbol)}</td>`;
                }

                html += `
                    <td><span class="agent-name" title="${agentDescription}">${agentDisplayName}</span> ${accBadge}</td>
                    <td><span class="signal-${signalKey}">${signalText}</span></td>
                    <td>${formatDate(pred.prediction_date)}</td>
                </tr>`;
            });
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading predictions:', error);
        container.innerHTML = `<p class="error-message">${t('errorPredictions')}</p>`;
    }
}

// ============================================
// FILTER PREDICTIONS
// ============================================

function filterPredictions() {
    const searchValue = document.getElementById('predictionsSearch').value.toLowerCase().trim();
    const table = document.getElementById('predictionsTable');
    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');
    let currentGroupVisible = false;

    rows.forEach(row => {
        const searchText = row.getAttribute('data-search') || '';
        const isGroupStart = row.classList.contains('group-start');
        if (isGroupStart) currentGroupVisible = searchText.includes(searchValue);
        row.classList.toggle('hidden-row', !currentGroupVisible);
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
        const accEl = document.getElementById('overallAccuracy');
        if (accEl) accEl.textContent = acc ? `${acc}%` : '-';

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
                <div class="perf-stat-value">${overall.directional_accuracy || 0}%</div>
                <div class="perf-stat-label">${t('directionalAccuracy')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value">${overall.total_predictions || 0}</div>
                <div class="perf-stat-label">${t('totalSignals')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value">${overall.win_rate_buy || 0}%</div>
                <div class="perf-stat-label">${t('winRateBuy')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value">${overall.win_rate_sell || 0}%</div>
                <div class="perf-stat-label">${t('winRateSell')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value">${(overall.avg_return_per_signal * 100).toFixed(2)}%</div>
                <div class="perf-stat-label">${t('avgReturnPerSignal')}</div>
            </div>
            <div class="perf-stat-card">
                <div class="perf-stat-value">${((overall.max_drawdown || 0) * 100).toFixed(1)}%</div>
                <div class="perf-stat-label">${t('maxDrawdown')}</div>
            </div>
        </div>
    `;
}

function renderPerStockTable(perStock) {
    const container = document.getElementById('perfStocks');
    if (!container) return;

    const entries = Object.entries(perStock || {});
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

        if (!data || data.length === 0) {
            container.innerHTML = `<p class="no-data">${t('noEvaluations')}</p>`;
            return;
        }

        let html = `<table><thead><tr>
            <th>${t('stock')}</th>
            <th>${t('agent')}</th>
            <th>${t('signal')}</th>
            <th>${t('actualOutcome')}</th>
            <th>${t('priceChange')}</th>
            <th>${t('result')}</th>
            <th>${t('targetDate')}</th>
        </tr></thead><tbody>`;

        data.forEach(item => {
            const companyName = getCompanyName(item.symbol);
            const agentDisplayName = getAgentDisplayName(item.agent_name);
            const predictionText = t(item.prediction.toLowerCase());
            const actualText = t(item.actual_outcome.toLowerCase());
            const changePercent = item.actual_change_pct ? item.actual_change_pct.toFixed(2) : '0.00';
            const changeClass = parseFloat(changePercent) >= 0 ? 'positive-change' : 'negative-change';
            const resultClass = item.was_correct ? 'result-correct' : 'result-wrong';
            const resultIcon = item.was_correct ? '✓' : '✗';

            html += `
                <tr>
                    <td><strong>${item.symbol}</strong><br><small class="company-name">${companyName}</small></td>
                    <td>${agentDisplayName}</td>
                    <td><span class="signal-${item.prediction.toLowerCase()}">${predictionText}</span></td>
                    <td><span class="signal-${item.actual_outcome.toLowerCase()}">${actualText}</span></td>
                    <td class="${changeClass}">${changePercent}%</td>
                    <td><span class="${resultClass}">${resultIcon}</span></td>
                    <td>${formatDate(item.target_date)}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
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

        if (!data || data.length === 0) {
            container.innerHTML = `<p class="no-data">${t('noPrices')}</p>`;
            return;
        }

        let html = `<table><thead><tr><th>${t('stock')}</th><th>${t('date')}</th><th>${t('closePrice')}</th><th>${t('volume')}</th></tr></thead><tbody>`;

        data.forEach(stock => {
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