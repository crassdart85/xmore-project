// API Base URL
const API_URL = '/api';

// ============================================
// BILINGUAL SUPPORT (English / Arabic)
// ============================================

// Current language (default: English)
let currentLang = localStorage.getItem('lang') || 'en';

// Translations
const TRANSLATIONS = {
    en: {
        // Header
        title: 'Stock Trading System',
        subtitle: 'Automated Prediction Dashboard',

        // Stats
        stocksTracked: 'Stocks Tracked',
        totalPredictions: 'Total Predictions',
        priceRecords: 'Price Records',
        latestData: 'Latest Data',

        // Section titles
        latestPredictions: 'Latest Predictions',
        agentPerformance: 'Agent Performance',
        predictionResults: 'Prediction Results',
        latestPrices: 'Latest Stock Prices',

        // Table headers
        stock: 'Stock',
        agent: 'Agent',
        prediction: 'Prediction',
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

        // Predictions
        up: 'UP',
        down: 'DOWN',
        hold: 'HOLD',

        // Sentiment
        sentiment: 'Sentiment',
        bullish: 'Bullish',
        neutral: 'Neutral',
        bearish: 'Bearish',
        noSentiment: 'N/A',

        // Messages
        noPredictions: 'No predictions available yet. New predictions are generated every Friday.',
        noPerformance: 'Performance tracking will begin once predictions have been evaluated. Check back soon!',
        noEvaluations: 'No prediction results yet. Results will appear after predictions are evaluated against actual prices.',
        noPrices: 'Price data is being collected. Please check back later.',
        errorPredictions: 'Unable to load predictions. Please try refreshing the page.',
        errorPerformance: 'Unable to load performance data. Please try refreshing the page.',
        errorEvaluations: 'Unable to load prediction results. Please try refreshing the page.',
        errorPrices: 'Unable to load price data. Please try refreshing the page.',

        // Buttons
        refreshData: 'Refresh Data',
        refreshing: 'Refreshing...',

        // Footer
        disclaimer: 'Not financial advice. For research purposes only.',

        // Search
        searchPlaceholder: 'Search by stock symbol or company name...',

        // Language
        switchLang: 'عربي'
    },
    ar: {
        // Header
        title: 'نظام تداول الأسهم',
        subtitle: 'لوحة التنبؤات الآلية',

        // Stats
        stocksTracked: 'الأسهم المتابعة',
        totalPredictions: 'إجمالي التنبؤات',
        priceRecords: 'سجلات الأسعار',
        latestData: 'آخر تحديث',

        // Section titles
        latestPredictions: 'أحدث التنبؤات',
        agentPerformance: 'أداء الوكلاء',
        predictionResults: 'نتائج التنبؤات',
        latestPrices: 'أحدث أسعار الأسهم',

        // Table headers
        stock: 'السهم',
        agent: 'الوكيل',
        prediction: 'التنبؤ',
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

        // Predictions
        up: 'صعود',
        down: 'هبوط',
        hold: 'احتفاظ',

        // Sentiment
        sentiment: 'المشاعر',
        bullish: 'إيجابي',
        neutral: 'محايد',
        bearish: 'سلبي',
        noSentiment: 'غ/م',

        // Messages
        noPredictions: 'لا توجد تنبؤات متاحة حالياً. يتم إنشاء تنبؤات جديدة كل يوم جمعة.',
        noPerformance: 'سيبدأ تتبع الأداء بمجرد تقييم التنبؤات. يرجى المراجعة لاحقاً!',
        noEvaluations: 'لا توجد نتائج تنبؤات بعد. ستظهر النتائج بعد مقارنة التنبؤات بالأسعار الفعلية.',
        noPrices: 'جاري جمع بيانات الأسعار. يرجى المراجعة لاحقاً.',
        errorPredictions: 'تعذر تحميل التنبؤات. يرجى تحديث الصفحة.',
        errorPerformance: 'تعذر تحميل بيانات الأداء. يرجى تحديث الصفحة.',
        errorEvaluations: 'تعذر تحميل نتائج التنبؤات. يرجى تحديث الصفحة.',
        errorPrices: 'تعذر تحميل بيانات الأسعار. يرجى تحديث الصفحة.',

        // Buttons
        refreshData: 'تحديث البيانات',
        refreshing: 'جاري التحديث...',

        // Footer
        disclaimer: 'ليست نصيحة مالية. لأغراض البحث فقط.',

        // Search
        searchPlaceholder: 'البحث برمز السهم أو اسم الشركة...',

        // Language
        switchLang: 'English'
    }
};

// Agent info with bilingual support
const AGENT_INFO = {
    'MA_Crossover_Agent': {
        en: { name: 'Moving Average Trend', description: 'Analyzes short and long-term moving average crossovers to identify trend changes' },
        ar: { name: 'اتجاه المتوسط المتحرك', description: 'يحلل تقاطعات المتوسطات المتحركة قصيرة وطويلة المدى لتحديد تغيرات الاتجاه' }
    },
    'ML_RandomForest': {
        en: { name: 'AI Price Predictor', description: 'Machine learning model using historical patterns to predict price movements' },
        ar: { name: 'متنبئ الأسعار الذكي', description: 'نموذج تعلم آلي يستخدم الأنماط التاريخية للتنبؤ بحركات الأسعار' }
    },
    'RSI_Agent': {
        en: { name: 'Momentum Indicator', description: 'Uses Relative Strength Index to detect overbought/oversold conditions' },
        ar: { name: 'مؤشر الزخم', description: 'يستخدم مؤشر القوة النسبية لاكتشاف حالات الشراء/البيع المفرط' }
    },
    'Volume_Spike_Agent': {
        en: { name: 'Volume Analysis', description: 'Monitors unusual volume activity to predict potential price movements' },
        ar: { name: 'تحليل الحجم', description: 'يراقب نشاط الحجم غير المعتاد للتنبؤ بتحركات الأسعار المحتملة' }
    },
};

// Get translation
function t(key) {
    return TRANSLATIONS[currentLang][key] || TRANSLATIONS['en'][key] || key;
}

// Get display name for an agent
function getAgentDisplayName(agentName) {
    return AGENT_INFO[agentName]?.[currentLang]?.name || AGENT_INFO[agentName]?.en?.name || agentName;
}

// Get agent description for tooltips
function getAgentDescription(agentName) {
    return AGENT_INFO[agentName]?.[currentLang]?.description || AGENT_INFO[agentName]?.en?.description || '';
}

// Switch language
async function switchLanguage() {
    currentLang = currentLang === 'en' ? 'ar' : 'en';
    localStorage.setItem('lang', currentLang);
    applyLanguage();
    // Reload all data to update dynamic content
    await loadSentiment();
    loadStats();
    loadPredictions();
    loadPerformance();
    loadEvaluations();
    loadPrices();
}

// Apply language to static elements
function applyLanguage() {
    const isArabic = currentLang === 'ar';

    // Set document direction
    document.documentElement.dir = isArabic ? 'rtl' : 'ltr';
    document.documentElement.lang = currentLang;
    document.body.classList.toggle('rtl', isArabic);

    // Update static text elements
    const title = document.querySelector('header h1');
    const subtitle = document.querySelector('.subtitle');
    if (title) title.textContent = t('title');
    if (subtitle) subtitle.textContent = t('subtitle');

    // Update stat labels
    document.querySelectorAll('.stat-label').forEach((el, index) => {
        const labels = ['stocksTracked', 'totalPredictions', 'priceRecords', 'latestData'];
        if (labels[index]) el.textContent = t(labels[index]);
    });

    // Update section titles
    const sectionTitles = document.querySelectorAll('.section h2');
    const titleKeys = ['latestPredictions', 'agentPerformance', 'latestPrices'];
    sectionTitles.forEach((el, index) => {
        if (titleKeys[index]) el.textContent = t(titleKeys[index]);
    });

    // Update search placeholder
    const searchInput = document.getElementById('predictionsSearch');
    if (searchInput) searchInput.placeholder = t('searchPlaceholder');

    // Update refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn && !refreshBtn.disabled) {
        refreshBtn.textContent = t('refreshData');
    }

    // Update disclaimer
    const disclaimer = document.querySelector('.disclaimer');
    if (disclaimer) disclaimer.textContent = t('disclaimer');

    // Update language switch button
    const langBtn = document.getElementById('langBtn');
    if (langBtn) langBtn.textContent = t('switchLang');
}

// Company Name Mapping with bilingual support (EGX and US stocks)
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

// Get company name for a symbol (bilingual)
function getCompanyName(symbol) {
    const company = COMPANY_NAMES[symbol];
    if (company) {
        return company[currentLang] || company.en;
    }
    return symbol.replace('.CA', '');
}

// Format datetime to short format (YYYY-MM-DD HH:MM)
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

        // If time is 00:00, just show date
        if (hours === '00' && minutes === '00') {
            return `${year}-${month}-${day}`;
        }
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    } catch (e) {
        return dateStr;
    }
}

// Store sentiment data globally for use in predictions display
let sentimentData = {};

// Load sentiment data
async function loadSentiment() {
    try {
        const response = await fetch(`${API_URL}/sentiment`);
        if (response.ok) {
            const data = await response.json();
            // Index by symbol for quick lookup
            sentimentData = {};
            data.forEach(item => {
                sentimentData[item.symbol] = item;
            });
        }
    } catch (error) {
        console.error('Error loading sentiment:', error);
    }
}

// Get sentiment badge HTML for a symbol
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

// Load all data on page load
window.addEventListener('load', async () => {
    applyLanguage();
    await loadSentiment(); // Load sentiment first
    loadStats();
    loadPredictions();
    loadPerformance();
    loadEvaluations();
    loadPrices();
});

// Initialize language switch button
document.getElementById('langBtn')?.addEventListener('click', switchLanguage);

// Refresh all data with loading state
async function refreshData() {
    const btn = document.getElementById('refreshBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = t('refreshing');
        btn.classList.add('loading-btn');
    }

    try {
        await loadSentiment(); // Load sentiment first
        await Promise.all([
            loadStats(),
            loadPredictions(),
            loadPerformance(),
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

// Load system stats
async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const data = await response.json();

        document.getElementById('stocksTracked').textContent = data.stocksTracked || '0';
        document.getElementById('totalPredictions').textContent = data.totalPredictions || '0';
        document.getElementById('totalPrices').textContent = data.totalPrices || '0';
        document.getElementById('latestDate').textContent = formatDate(data.latestDate);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load predictions (grouped by stock symbol)
async function loadPredictions() {
    const container = document.getElementById('predictions');

    try {
        const response = await fetch(`${API_URL}/predictions`);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const data = await response.json();

        if (!data || data.length === 0) {
            container.innerHTML = `<p class="no-data">${t('noPredictions')}</p>`;
            return;
        }

        // Group predictions by stock symbol
        const grouped = {};
        data.forEach(pred => {
            if (!grouped[pred.symbol]) {
                grouped[pred.symbol] = [];
            }
            grouped[pred.symbol].push(pred);
        });

        let html = `<table id="predictionsTable"><thead><tr><th>${t('stock')}</th><th>${t('sentiment')}</th><th>${t('agent')}</th><th>${t('prediction')}</th><th>${t('date')}</th></tr></thead><tbody>`;

        Object.keys(grouped).forEach(symbol => {
            const predictions = grouped[symbol];
            const companyName = getCompanyName(symbol);
            const searchText = `${symbol} ${companyName}`.toLowerCase();

            predictions.forEach((pred, index) => {
                const agentDisplayName = getAgentDisplayName(pred.agent_name);
                const agentDescription = getAgentDescription(pred.agent_name);

                html += `<tr data-search="${searchText}" class="${index === 0 ? 'group-start' : 'group-row'}">`;

                // Only show stock and sentiment cells on first row of group
                if (index === 0) {
                    html += `<td rowspan="${predictions.length}" class="stock-cell"><strong>${symbol}</strong><br><small class="company-name">${companyName}</small></td>`;
                    html += `<td rowspan="${predictions.length}" class="sentiment-cell">${getSentimentBadge(symbol)}</td>`;
                }

                const predictionText = t(pred.prediction.toLowerCase());
                html += `
                    <td><span class="agent-name" title="${agentDescription}">${agentDisplayName}</span></td>
                    <td><span class="prediction-${pred.prediction.toLowerCase()}">${predictionText}</span></td>
                    <td>${formatDate(pred.prediction_date)}</td>
                </tr>`;
            });
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading predictions:', error);
        document.getElementById('predictions').innerHTML = `<p class="error-message">${t('errorPredictions')}</p>`;
    }
}

// Filter predictions based on search input (by stock symbol or company name)
function filterPredictions() {
    const searchValue = document.getElementById('predictionsSearch').value.toLowerCase().trim();
    const table = document.getElementById('predictionsTable');

    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');
    let currentGroupVisible = false;

    rows.forEach(row => {
        const searchText = row.getAttribute('data-search') || '';
        const isGroupStart = row.classList.contains('group-start');

        // For group start rows, check if this group should be visible
        if (isGroupStart) {
            currentGroupVisible = searchText.includes(searchValue);
        }

        // Show/hide based on group visibility
        if (currentGroupVisible) {
            row.classList.remove('hidden-row');
        } else {
            row.classList.add('hidden-row');
        }
    });
}

// Load performance
async function loadPerformance() {
    const container = document.getElementById('performance');

    try {
        const response = await fetch(`${API_URL}/performance`);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const data = await response.json();

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

// Load prediction evaluations (actual vs predicted)
async function loadEvaluations() {
    const container = document.getElementById('evaluations');

    try {
        const response = await fetch(`${API_URL}/evaluations`);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

        const data = await response.json();

        if (!data || data.length === 0) {
            container.innerHTML = `<p class="no-data">${t('noEvaluations')}</p>`;
            return;
        }

        let html = `<table><thead><tr>
            <th>${t('stock')}</th>
            <th>${t('agent')}</th>
            <th>${t('prediction')}</th>
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
                    <td><span class="prediction-${item.prediction.toLowerCase()}">${predictionText}</span></td>
                    <td><span class="prediction-${item.actual_outcome.toLowerCase()}">${actualText}</span></td>
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

// Initialize refresh button event listener
document.getElementById('refreshBtn')?.addEventListener('click', refreshData);

// Load latest prices
async function loadPrices() {
    const container = document.getElementById('prices');

    try {
        const response = await fetch(`${API_URL}/prices`);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }

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