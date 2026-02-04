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

        // Predictions
        up: 'UP',
        down: 'DOWN',
        hold: 'HOLD',

        // Messages
        noPredictions: 'No predictions yet. Run python run_agents.py to generate predictions.',
        noPerformance: 'No performance data yet. Run evaluate.py after predictions are made to see agent accuracy.',
        noPrices: 'No price data available yet.',
        errorPredictions: 'Could not load predictions. Check if the server is running.',
        errorPerformance: 'Could not load performance data. Check if the server is running.',
        errorPrices: 'Could not load price data. Check if the server is running.',

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

        // Predictions
        up: 'صعود',
        down: 'هبوط',
        hold: 'احتفاظ',

        // Messages
        noPredictions: 'لا توجد تنبؤات بعد. قم بتشغيل run_agents.py لإنشاء التنبؤات.',
        noPerformance: 'لا توجد بيانات أداء بعد. قم بتشغيل evaluate.py بعد إنشاء التنبؤات.',
        noPrices: 'لا توجد بيانات أسعار متاحة بعد.',
        errorPredictions: 'تعذر تحميل التنبؤات. تأكد من تشغيل الخادم.',
        errorPerformance: 'تعذر تحميل بيانات الأداء. تأكد من تشغيل الخادم.',
        errorPrices: 'تعذر تحميل بيانات الأسعار. تأكد من تشغيل الخادم.',

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
function switchLanguage() {
    currentLang = currentLang === 'en' ? 'ar' : 'en';
    localStorage.setItem('lang', currentLang);
    applyLanguage();
    // Reload all data to update dynamic content
    loadStats();
    loadPredictions();
    loadPerformance();
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

// Company Name Mapping for search (EGX and US stocks)
const COMPANY_NAMES = {
    // US Stocks
    'AAPL': 'Apple Inc.',
    'GOOGL': 'Alphabet Inc. (Google)',
    'MSFT': 'Microsoft Corporation',
    'AMZN': 'Amazon.com Inc.',
    'META': 'Meta Platforms Inc.',
    'TSLA': 'Tesla Inc.',
    'NVDA': 'NVIDIA Corporation',
    'JPM': 'JPMorgan Chase & Co.',
    'V': 'Visa Inc.',
    'JNJ': 'Johnson & Johnson',
    'WMT': 'Walmart Inc.',
    'XOM': 'Exxon Mobil Corporation',
    'BAC': 'Bank of America Corp.',
    'PG': 'Procter & Gamble Co.',
    'HD': 'The Home Depot Inc.',
    // EGX Stocks (Egyptian Exchange)
    'COMI.CA': 'Commercial International Bank CIB',
    'HRHO.CA': 'EFG Holding Hermes',
    'FWRY.CA': 'Fawry Banking Technology',
    'TMGH.CA': 'Talaat Moustafa Group',
    'ORAS.CA': 'Orascom Construction',
    'PHDC.CA': 'Palm Hills Development',
    'MNHD.CA': 'Madinet Nasr Housing',
    'OCDI.CA': 'Orascom Development',
    'SWDY.CA': 'El Sewedy Electric',
    'EAST.CA': 'Eastern Company Tobacco',
    'EFIH.CA': 'Egyptian Financial Industrial',
    'ESRS.CA': 'Ezz Steel',
    'ETEL.CA': 'Telecom Egypt',
    'EMFD.CA': 'E-Finance Digital',
    'ALCN.CA': 'Alexandria Container Cargo',
    'ABUK.CA': 'Abu Qir Fertilizers',
    'MFPC.CA': 'Misr Fertilizers MOPCO',
    'SKPC.CA': 'Sidi Kerir Petrochemicals',
    'JUFO.CA': 'Juhayna Food Industries',
    'CCAP.CA': 'Cleopatra Hospital',
    'ORWE.CA': 'Oriental Weavers',
    'AMOC.CA': 'Alexandria Mineral Oils',
};

// Get company name for a symbol
function getCompanyName(symbol) {
    return COMPANY_NAMES[symbol] || symbol.replace('.CA', '');
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

// Load all data on page load
window.addEventListener('load', () => {
    applyLanguage();
    loadStats();
    loadPredictions();
    loadPerformance();
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
        await Promise.all([
            loadStats(),
            loadPredictions(),
            loadPerformance(),
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

        let html = `<table id="predictionsTable"><thead><tr><th>${t('stock')}</th><th>${t('agent')}</th><th>${t('prediction')}</th><th>${t('date')}</th></tr></thead><tbody>`;

        Object.keys(grouped).forEach(symbol => {
            const predictions = grouped[symbol];
            const companyName = getCompanyName(symbol);
            const searchText = `${symbol} ${companyName}`.toLowerCase();

            predictions.forEach((pred, index) => {
                const agentDisplayName = getAgentDisplayName(pred.agent_name);
                const agentDescription = getAgentDescription(pred.agent_name);

                html += `<tr data-search="${searchText}" class="${index === 0 ? 'group-start' : 'group-row'}">`;

                // Only show stock cell on first row of group
                if (index === 0) {
                    html += `<td rowspan="${predictions.length}" class="stock-cell"><strong>${symbol}</strong><br><small class="company-name">${companyName}</small></td>`;
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