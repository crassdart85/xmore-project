// ============================================
// Xmore — Performance Dashboard (Investor-Grade)
// ============================================

// Performance-specific translations
const PERF_TRANSLATIONS = {
    en: {
        perfTitle: '📈 XMORE PERFORMANCE — Live Track Record',
        perfTitleAr: '',
        perfDisclaimer: 'All metrics are from LIVE predictions only. No backtested or backfilled data is included. Predictions are immutable — see Audit Log for proof.',
        keyMetrics: '📊 Key Metrics',
        trades: 'Trades',
        winRate: 'Win Rate',
        avgAlpha: 'Avg α',
        sharpe: 'Sharpe',
        vsEgx: 'vs EGX30',
        maxDD: 'Max DD',
        sortino: 'Sortino',
        profitF: 'Profit F',
        beatMkt: 'Beat Mkt',
        equityCurve: '📈 Equity Curve',
        agentAccuracy: '🤖 Agent Accuracy',
        bestWorst: '🏆 Best & Worst Stocks',
        recentPreds: '📜 Recent Predictions (Auditable)',
        rollingWindows: '📋 Rolling Windows',
        integrity: 'Integrity',
        integrityImmutable: '🔒 Predictions are IMMUTABLE — cannot be modified after creation.',
        integrityAudit: '📜 All outcome updates are logged in the audit trail.',
        integrityLive: '📊 Only live predictions are included. No backtests in public stats.',
        integrityMin: '✅ Minimum 100-trade threshold met for statistical credibility.',
        integrityMinNot: '⏳ Track record in progress — {n}/100 live trades resolved.',
        liveSince: '📅 Live trading since:',
        disclaimer: '⚠️ Disclaimer',
        disclaimerText: 'Past performance does not guarantee future results. Xmore is an AI-generated analysis tool, not a licensed financial advisor.',
        disclaimerTextAr: 'الأداء السابق لا يضمن النتائج المستقبلية.',
        showMore: 'Show More →',
        viewAudit: 'View Full Audit Log →',
        agent: 'Agent',
        thirtyWin: '30d Win%',
        ninetyWin: '90d Win%',
        signals: 'Signals',
        avgConf: 'Avg Conf',
        window: 'Window',
        avgA: 'Avg α',
        bestAlpha: 'Best Alpha',
        worstAlpha: 'Worst Alpha',
        date: 'Date',
        symbol: 'Symbol',
        signal: 'Signal',
        conf: 'Conf',
        action: 'Action',
        actual: 'Actual',
        alpha: 'α',
        noData: 'Performance tracking will begin once predictions have been evaluated.',
        loading: 'Loading performance data...',
        resolved: 'predictions resolved',
        '30d': '30d',
        '60d': '60d',
        '90d': '90d',
        '180d': '180d',
    },
    ar: {
        perfTitle: '📈 أداء إكسمور — السجل الحي',
        perfTitleAr: '',
        perfDisclaimer: 'جميع المقاييس من التنبؤات الحية فقط. لا بيانات مختبرة أو معبأة. التنبؤات غير قابلة للتعديل — راجع سجل التدقيق.',
        keyMetrics: '📊 المقاييس الرئيسية',
        trades: 'صفقات',
        winRate: 'نسبة الفوز',
        avgAlpha: 'متوسط α',
        sharpe: 'شارب',
        vsEgx: 'مقابل EGX30',
        maxDD: 'أقصى تراجع',
        sortino: 'سورتينو',
        profitF: 'معامل الربح',
        beatMkt: 'تفوق على السوق',
        equityCurve: '📈 منحنى الأرباح',
        agentAccuracy: '🤖 دقة الوكلاء',
        bestWorst: '🏆 أفضل وأسوأ الأسهم',
        recentPreds: '📜 التنبؤات الأخيرة (قابلة للتدقيق)',
        rollingWindows: '📋 النوافذ المتحركة',
        integrity: 'النزاهة',
        integrityImmutable: '🔒 التنبؤات غير قابلة للتعديل بعد الإنشاء.',
        integrityAudit: '📜 جميع تحديثات النتائج مسجلة في سجل التدقيق.',
        integrityLive: '📊 التنبؤات الحية فقط. لا اختبارات خلفية في الإحصائيات العامة.',
        integrityMin: '✅ تم استيفاء حد 100 صفقة كحد أدنى للمصداقية الإحصائية.',
        integrityMinNot: '⏳ سجل الأداء قيد التكوين — {n}/100 تنبؤ محللة.',
        liveSince: '📅 التداول الحي منذ:',
        disclaimer: '⚠️ إخلاء المسؤولية',
        disclaimerText: 'الأداء السابق لا يضمن النتائج المستقبلية. إكسمور أداة تحليل بالذكاء الاصطناعي وليس مستشاراً مالياً مرخصاً.',
        disclaimerTextAr: '',
        showMore: 'عرض المزيد →',
        viewAudit: 'عرض سجل التدقيق الكامل →',
        agent: 'الوكيل',
        thirtyWin: 'فوز 30 يوم%',
        ninetyWin: 'فوز 90 يوم%',
        signals: 'إشارات',
        avgConf: 'متوسط الثقة',
        window: 'النافذة',
        avgA: 'متوسط α',
        bestAlpha: 'أفضل ألفا',
        worstAlpha: 'أسوأ ألفا',
        date: 'التاريخ',
        symbol: 'الرمز',
        signal: 'الإشارة',
        conf: 'الثقة',
        action: 'الإجراء',
        actual: 'الفعلي',
        alpha: 'α',
        noData: 'سيبدأ تتبع الأداء بمجرد تقييم التنبؤات.',
        loading: 'جاري تحميل بيانات الأداء...',
        resolved: 'تنبؤ تم تحليله',
        '30d': '30 يوم',
        '60d': '60 يوم',
        '90d': '90 يوم',
        '180d': '180 يوم',
    }
};

function pt(key) {
    return PERF_TRANSLATIONS[currentLang]?.[key] || PERF_TRANSLATIONS['en']?.[key] || key;
}

// State
let perfEquityCurveDays = 90;
let perfHistoryPage = 1;
let perfChartInstance = null;

// ─── MAIN LOAD FUNCTION ──────────────────────────────────────

async function loadPerformanceDashboard() {
    const container = document.getElementById('perfDashboard');
    if (!container) return;

    container.innerHTML = `<p class="loading">${pt('loading')}</p>`;

    try {
        // Fetch all data in parallel
        const [summaryRes, agentsRes, stocksRes, equityRes, historyRes] = await Promise.all([
            fetch('/api/performance-v2/summary').then(r => r.json()).catch(() => ({ available: false })),
            fetch('/api/performance-v2/by-agent').then(r => r.json()).catch(() => ({ agents: [] })),
            fetch('/api/performance-v2/by-stock?days=90').then(r => r.json()).catch(() => ({ stocks: [] })),
            fetch(`/api/performance-v2/equity-curve?days=${perfEquityCurveDays}`).then(r => r.json()).catch(() => ({ series: [] })),
            fetch(`/api/performance-v2/predictions/history?page=${perfHistoryPage}&limit=10`).then(r => r.json()).catch(() => ({ predictions: [] }))
        ]);

        container.innerHTML = '';

        // Build dashboard sections
        container.appendChild(buildHeader(summaryRes));
        container.appendChild(buildKeyMetrics(summaryRes));
        container.appendChild(buildEquityCurve(equityRes));
        container.appendChild(buildAgentTable(agentsRes));
        container.appendChild(buildBestWorstStocks(stocksRes));
        container.appendChild(buildRecentPredictions(historyRes));
        container.appendChild(buildRollingWindows(summaryRes));
        container.appendChild(buildIntegrity(summaryRes));
        container.appendChild(buildDisclaimerSection());

        // Render equity curve chart
        renderEquityCurveChart(equityRes);

    } catch (err) {
        console.error('Performance dashboard error:', err);
        container.innerHTML = `<p class="error-message">Failed to load performance data.</p>`;
    }
}

// ─── HEADER ──────────────────────────────────────────────────

function buildHeader(data) {
    const section = document.createElement('div');
    section.className = 'perf-header';
    section.innerHTML = `
        <h2 class="perf-main-title">${pt('perfTitle')}</h2>
        <div class="perf-disclaimer-banner">
            <p>${pt('perfDisclaimer')}</p>
        </div>
    `;
    return section;
}

// ─── KEY METRICS CARDS ───────────────────────────────────────

function buildKeyMetrics(data) {
    const section = document.createElement('div');
    section.className = 'perf-section';

    if (!data.available) {
        section.innerHTML = `<h3>${pt('keyMetrics')}</h3><p class="no-data">${pt('noData')}</p>`;
        return section;
    }

    const g = data.global;
    const r30 = data.rolling?.['30d'] || {};

    section.innerHTML = `
        <h3>${pt('keyMetrics')}</h3>
        <div class="perf-metrics-grid">
            <div class="perf-metric-card">
                <div class="perf-metric-value">${g.total_predictions || 0}</div>
                <div class="perf-metric-label">${pt('trades')}</div>
            </div>
            <div class="perf-metric-card ${g.win_rate >= 55 ? 'positive' : g.win_rate < 45 ? 'negative' : ''}">
                <div class="perf-metric-value">${g.win_rate || 0}%</div>
                <div class="perf-metric-label">${pt('winRate')}</div>
            </div>
            <div class="perf-metric-card ${g.avg_alpha_1d > 0 ? 'positive' : g.avg_alpha_1d < 0 ? 'negative' : ''}">
                <div class="perf-metric-value">${g.avg_alpha_1d > 0 ? '+' : ''}${g.avg_alpha_1d || 0}%</div>
                <div class="perf-metric-label">${pt('avgAlpha')}</div>
            </div>
            <div class="perf-metric-card ${g.beat_benchmark_pct > 50 ? 'positive' : 'negative'}">
                <div class="perf-metric-value">${g.beat_benchmark_pct || 0}%</div>
                <div class="perf-metric-label">${pt('beatMkt')}</div>
            </div>
        </div>
        ${!g.meets_minimum ? `
            <div class="perf-min-banner">
                ${pt('integrityMinNot').replace('{n}', g.total_predictions)}
            </div>
        ` : ''}
    `;
    return section;
}

// ─── EQUITY CURVE ────────────────────────────────────────────

function buildEquityCurve(data) {
    const section = document.createElement('div');
    section.className = 'perf-section';

    section.innerHTML = `
        <h3>${pt('equityCurve')}</h3>
        <div class="perf-period-tabs">
            <button class="perf-period-btn ${perfEquityCurveDays === 30 ? 'active' : ''}" onclick="changeEquityCurvePeriod(30)">${pt('30d')}</button>
            <button class="perf-period-btn ${perfEquityCurveDays === 60 ? 'active' : ''}" onclick="changeEquityCurvePeriod(60)">${pt('60d')}</button>
            <button class="perf-period-btn ${perfEquityCurveDays === 90 ? 'active' : ''}" onclick="changeEquityCurvePeriod(90)">${pt('90d')}</button>
            <button class="perf-period-btn ${perfEquityCurveDays === 180 ? 'active' : ''}" onclick="changeEquityCurvePeriod(180)">${pt('180d')}</button>
        </div>
        <div class="perf-chart-container">
            <canvas id="equityCurveCanvas" width="800" height="350"></canvas>
        </div>
        <div class="perf-chart-legend">
            <span class="legend-item legend-xmore">🟢 Xmore: ${data.total_xmore > 0 ? '+' : ''}${data.total_xmore}%</span>
            <span class="legend-item legend-egx">⬜ EGX30: ${data.total_egx30 > 0 ? '+' : ''}${data.total_egx30}%</span>
            <span class="legend-item legend-alpha">α: ${data.total_alpha > 0 ? '+' : ''}${data.total_alpha}%</span>
        </div>
    `;
    return section;
}

async function changeEquityCurvePeriod(days) {
    perfEquityCurveDays = days;
    // Re-fetch equity curve with new period
    try {
        const res = await fetch(`/api/performance-v2/equity-curve?days=${days}`);
        const data = await res.json();

        // Update buttons
        document.querySelectorAll('.perf-period-btn').forEach(btn => {
            btn.classList.toggle('active', parseInt(btn.textContent) === days || btn.textContent === pt(`${days}d`));
        });

        // Update legend
        const legend = document.querySelector('.perf-chart-legend');
        if (legend) {
            legend.innerHTML = `
                <span class="legend-item legend-xmore">🟢 Xmore: ${data.total_xmore > 0 ? '+' : ''}${data.total_xmore}%</span>
                <span class="legend-item legend-egx">⬜ EGX30: ${data.total_egx30 > 0 ? '+' : ''}${data.total_egx30}%</span>
                <span class="legend-item legend-alpha">α: ${data.total_alpha > 0 ? '+' : ''}${data.total_alpha}%</span>
            `;
        }

        renderEquityCurveChart(data);
    } catch (e) {
        console.error('Failed to update equity curve:', e);
    }
}

function renderEquityCurveChart(data) {
    const canvas = document.getElementById('equityCurveCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const series = data.series || [];

    // Responsive canvas
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width || 800;
    canvas.height = 350;

    const W = canvas.width;
    const H = canvas.height;
    const padding = { top: 30, right: 20, bottom: 40, left: 60 };
    const chartW = W - padding.left - padding.right;
    const chartH = H - padding.top - padding.bottom;

    ctx.clearRect(0, 0, W, H);

    if (series.length < 2) {
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary') || '#999';
        ctx.font = '14px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Not enough data to display chart.', W / 2, H / 2);
        return;
    }

    // Get data ranges
    const allValues = series.flatMap(s => [s.xmore, s.egx30]);
    const minVal = Math.min(0, ...allValues) - 1;
    const maxVal = Math.max(0, ...allValues) + 1;
    const range = maxVal - minVal || 1;

    const toX = (i) => padding.left + (i / (series.length - 1)) * chartW;
    const toY = (val) => padding.top + (1 - (val - minVal) / range) * chartH;

    // Grid lines
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    ctx.strokeStyle = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';
    ctx.lineWidth = 1;
    const gridSteps = 5;
    for (let i = 0; i <= gridSteps; i++) {
        const val = minVal + (range * i / gridSteps);
        const y = toY(val);
        ctx.beginPath();
        ctx.moveTo(padding.left, y);
        ctx.lineTo(W - padding.right, y);
        ctx.stroke();

        // Y-axis labels
        ctx.fillStyle = isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(`${val.toFixed(1)}%`, padding.left - 8, y + 4);
    }

    // Zero line
    const zeroY = toY(0);
    ctx.strokeStyle = isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.15)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padding.left, zeroY);
    ctx.lineTo(W - padding.right, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw EGX30 line (gray dashed)
    ctx.strokeStyle = isDark ? 'rgba(255,255,255,0.35)' : 'rgba(100,100,100,0.5)';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    series.forEach((s, i) => {
        const x = toX(i);
        const y = toY(s.egx30);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw Xmore line (green, solid, thick)
    const gradient = ctx.createLinearGradient(0, padding.top, 0, H - padding.bottom);
    gradient.addColorStop(0, '#00e676');
    gradient.addColorStop(1, '#00c853');
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 3;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.beginPath();
    series.forEach((s, i) => {
        const x = toX(i);
        const y = toY(s.xmore);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Area fill under Xmore line
    ctx.globalAlpha = 0.08;
    ctx.fillStyle = '#00e676';
    ctx.beginPath();
    series.forEach((s, i) => {
        const x = toX(i);
        const y = toY(s.xmore);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.lineTo(toX(series.length - 1), toY(minVal));
    ctx.lineTo(toX(0), toY(minVal));
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 1.0;

    // X-axis date labels (show 5-6 dates)
    ctx.fillStyle = isDark ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.5)';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'center';
    const labelInterval = Math.max(1, Math.floor(series.length / 6));
    series.forEach((s, i) => {
        if (i % labelInterval === 0 || i === series.length - 1) {
            const dateStr = s.date ? s.date.substring(5) : '';  // MM-DD
            ctx.fillText(dateStr, toX(i), H - padding.bottom + 20);
        }
    });
}

// ─── AGENT TABLE ─────────────────────────────────────────────

function buildAgentTable(data) {
    const section = document.createElement('div');
    section.className = 'perf-section';

    const agents = data.agents || [];

    if (!agents.length) {
        section.innerHTML = `<h3>${pt('agentAccuracy')}</h3><p class="no-data">Agent accuracy data not yet available.</p>`;
        return section;
    }

    let tableRows = agents.map(a => {
        const agentDisplayName = typeof getAgentDisplayName === 'function' ? getAgentDisplayName(a.agent) : a.agent;
        return `
            <tr>
                <td class="agent-name-cell">${agentDisplayName}</td>
                <td><span class="perf-badge ${a.win_rate_30d >= 60 ? 'positive' : a.win_rate_30d < 50 ? 'negative' : ''}">${a.win_rate_30d || 0}%</span></td>
                <td><span class="perf-badge ${a.win_rate_90d >= 60 ? 'positive' : a.win_rate_90d < 50 ? 'negative' : ''}">${a.win_rate_90d || 0}%</span></td>
                <td>${a.predictions_30d || 0}</td>
                <td>${a.avg_confidence_30d || 0}%</td>
            </tr>
        `;
    }).join('');

    section.innerHTML = `
        <h3>${pt('agentAccuracy')}</h3>
        <div class="perf-table-wrapper">
            <table class="perf-table">
                <thead>
                    <tr>
                        <th>${pt('agent')}</th>
                        <th>${pt('thirtyWin')}</th>
                        <th>${pt('ninetyWin')}</th>
                        <th>${pt('signals')}</th>
                        <th>${pt('avgConf')}</th>
                    </tr>
                </thead>
                <tbody>${tableRows}</tbody>
            </table>
        </div>
    `;
    return section;
}

// ─── BEST & WORST STOCKS ─────────────────────────────────────

function buildBestWorstStocks(data) {
    const section = document.createElement('div');
    section.className = 'perf-section';

    const stocks = data.stocks || [];
    if (!stocks.length) {
        section.innerHTML = `<h3>${pt('bestWorst')}</h3><p class="no-data">No stock-level data available yet.</p>`;
        return section;
    }

    const best = stocks.filter(s => parseFloat(s.avg_alpha) > 0).slice(0, 3);
    const worst = stocks.filter(s => parseFloat(s.avg_alpha) <= 0).slice(-3).reverse();

    const formatStock = (s, emoji) => {
        const alpha = parseFloat(s.avg_alpha) || 0;
        const name = s.name_en || s.symbol;
        return `<span class="stock-chip ${alpha > 0 ? 'positive' : 'negative'}">${emoji} ${s.symbol} <strong>${alpha > 0 ? '+' : ''}${alpha}%</strong> avg α</span>`;
    };

    section.innerHTML = `
        <h3>${pt('bestWorst')}</h3>
        <div class="perf-best-worst">
            <div class="perf-best">
                <h4>${pt('bestAlpha')}:</h4>
                <div class="stock-chips">
                    ${best.map(s => formatStock(s, '🟢')).join('')}
                </div>
            </div>
            <div class="perf-worst">
                <h4>${pt('worstAlpha')}:</h4>
                <div class="stock-chips">
                    ${worst.map(s => formatStock(s, '🔴')).join('')}
                </div>
            </div>
        </div>
    `;
    return section;
}

// ─── RECENT PREDICTIONS TABLE ────────────────────────────────

function buildRecentPredictions(data) {
    const section = document.createElement('div');
    section.className = 'perf-section';

    const preds = data.predictions || [];

    if (!preds.length) {
        section.innerHTML = `<h3>${pt('recentPreds')}</h3><p class="no-data">No prediction history yet.</p>`;
        return section;
    }

    let tableRows = preds.map(p => {
        const date = p.prediction_date ? String(p.prediction_date).substring(5) : 'N/A';
        const actual = p.actual_next_day_return != null ? `${p.actual_next_day_return > 0 ? '+' : ''}${p.actual_next_day_return}%` : '—';
        const correct = p.was_correct === true ? '✅' : p.was_correct === false ? '❌' : '';
        const alpha = p.alpha_1d != null ? `${p.alpha_1d > 0 ? '+' : ''}${p.alpha_1d}%` : '—';
        const signalClass = (p.final_signal || '').toLowerCase();

        return `
            <tr>
                <td>${date}</td>
                <td><strong>${p.symbol}</strong></td>
                <td><span class="signal-badge signal-${signalClass}">${p.final_signal || '—'}</span></td>
                <td>${p.consensus_confidence || '—'}%</td>
                <td>${p.action || '—'}</td>
                <td>${actual} ${correct}</td>
                <td class="${p.alpha_1d > 0 ? 'text-positive' : p.alpha_1d < 0 ? 'text-negative' : ''}">${alpha}</td>
            </tr>
        `;
    }).join('');

    section.innerHTML = `
        <h3>${pt('recentPreds')}</h3>
        <div class="perf-table-wrapper">
            <table class="perf-table">
                <thead>
                    <tr>
                        <th>${pt('date')}</th>
                        <th>${pt('symbol')}</th>
                        <th>${pt('signal')}</th>
                        <th>${pt('conf')}</th>
                        <th>${pt('action')}</th>
                        <th>${pt('actual')}</th>
                        <th>${pt('alpha')}</th>
                    </tr>
                </thead>
                <tbody>${tableRows}</tbody>
            </table>
        </div>
        <div class="perf-table-actions">
            <button class="perf-action-btn" onclick="loadMorePredictions()">${pt('showMore')}</button>
            <button class="perf-action-btn secondary" onclick="showAuditLog()">${pt('viewAudit')}</button>
        </div>
    `;
    return section;
}

async function loadMorePredictions() {
    perfHistoryPage++;
    try {
        const res = await fetch(`/api/performance-v2/predictions/history?page=${perfHistoryPage}&limit=10`);
        const data = await res.json();
        const preds = data.predictions || [];
        if (!preds.length) {
            perfHistoryPage--;
            return;
        }

        const tbody = document.querySelector('.perf-section .perf-table tbody');
        if (!tbody) return;

        preds.forEach(p => {
            const date = p.prediction_date ? String(p.prediction_date).substring(5) : 'N/A';
            const actual = p.actual_next_day_return != null ? `${p.actual_next_day_return > 0 ? '+' : ''}${p.actual_next_day_return}%` : '—';
            const correct = p.was_correct === true ? '✅' : p.was_correct === false ? '❌' : '';
            const alpha = p.alpha_1d != null ? `${p.alpha_1d > 0 ? '+' : ''}${p.alpha_1d}%` : '—';
            const signalClass = (p.final_signal || '').toLowerCase();

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${date}</td>
                <td><strong>${p.symbol}</strong></td>
                <td><span class="signal-badge signal-${signalClass}">${p.final_signal || '—'}</span></td>
                <td>${p.consensus_confidence || '—'}%</td>
                <td>${p.action || '—'}</td>
                <td>${actual} ${correct}</td>
                <td class="${p.alpha_1d > 0 ? 'text-positive' : p.alpha_1d < 0 ? 'text-negative' : ''}">${alpha}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('Failed to load more predictions:', e);
        perfHistoryPage--;
    }
}

async function showAuditLog() {
    try {
        const res = await fetch('/api/performance-v2/audit');
        const data = await res.json();
        const entries = data.audit_entries || [];

        const modal = document.createElement('div');
        modal.className = 'perf-modal-overlay';
        modal.onclick = (e) => { if (e.target === modal) modal.remove(); };

        const rows = entries.map(e => `
            <tr>
                <td>${e.changed_at ? new Date(e.changed_at).toLocaleString() : '—'}</td>
                <td>${e.table_name}</td>
                <td>#${e.record_id}</td>
                <td>${e.field_changed}</td>
                <td>${e.old_value || '—'}</td>
                <td>${e.new_value || '—'}</td>
            </tr>
        `).join('');

        modal.innerHTML = `
            <div class="perf-modal">
                <button class="perf-modal-close" onclick="this.closest('.perf-modal-overlay').remove()">×</button>
                <h3>📜 Audit Log</h3>
                <p>${data.message}</p>
                <div class="perf-table-wrapper" style="max-height:400px;overflow-y:auto;">
                    <table class="perf-table">
                        <thead>
                            <tr>
                                <th>When</th>
                                <th>Table</th>
                                <th>Record</th>
                                <th>Field</th>
                                <th>Old Value</th>
                                <th>New Value</th>
                            </tr>
                        </thead>
                        <tbody>${rows || '<tr><td colspan="6">No audit entries yet.</td></tr>'}</tbody>
                    </table>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    } catch (e) {
        console.error('Failed to show audit log:', e);
    }
}

// ─── ROLLING WINDOWS ────────────────────────────────────────

function buildRollingWindows(data) {
    const section = document.createElement('div');
    section.className = 'perf-section';

    if (!data.available || !data.rolling) {
        section.innerHTML = `<h3>${pt('rollingWindows')}</h3><p class="no-data">Rolling window data not yet available.</p>`;
        return section;
    }

    const r = data.rolling;
    const windows = ['30d', '90d'];

    let rows = windows.map(w => {
        const d = r[w] || {};
        return `
            <tr>
                <td><strong>${w === '30d' ? '30 days' : '90 days'}</strong></td>
                <td>${d.trades || 0}</td>
                <td><span class="perf-badge ${d.win_rate >= 55 ? 'positive' : d.win_rate < 45 ? 'negative' : ''}">${d.win_rate || 0}%</span></td>
                <td class="${d.alpha > 0 ? 'text-positive' : d.alpha < 0 ? 'text-negative' : ''}">${d.alpha > 0 ? '+' : ''}${d.alpha || 0}%</td>
            </tr>
        `;
    }).join('');

    section.innerHTML = `
        <h3>${pt('rollingWindows')}</h3>
        <div class="perf-table-wrapper">
            <table class="perf-table">
                <thead>
                    <tr>
                        <th>${pt('window')}</th>
                        <th>${pt('trades')}</th>
                        <th>${pt('winRate')}</th>
                        <th>${pt('avgA')}</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
    return section;
}

// ─── INTEGRITY SECTION ───────────────────────────────────────

function buildIntegrity(data) {
    const section = document.createElement('div');
    section.className = 'perf-section perf-integrity';

    const g = data.available ? data.global : {};
    const meetsMin = g.meets_minimum;
    const total = g.total_predictions || 0;
    const firstDate = g.first_prediction ? new Date(g.first_prediction).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A';

    section.innerHTML = `
        <h3>🔐 ${pt('integrity')}</h3>
        <div class="integrity-items">
            <p>${pt('integrityImmutable')}</p>
            <p>${pt('integrityAudit')}</p>
            <p>${pt('integrityLive')}</p>
            <p>${meetsMin ? pt('integrityMin') : pt('integrityMinNot').replace('{n}', total)}</p>
            <p>${pt('liveSince')} ${firstDate} — ${total} ${pt('resolved')}.</p>
        </div>
    `;
    return section;
}

// ─── DISCLAIMER ──────────────────────────────────────────────

function buildDisclaimerSection() {
    const section = document.createElement('div');
    section.className = 'perf-section perf-disclaimer-section';
    section.innerHTML = `
        <h3>${pt('disclaimer')}</h3>
        <p>${pt('disclaimerText')}</p>
        ${currentLang === 'en' ? `<p class="disclaimer-ar">${pt('disclaimerTextAr') || PERF_TRANSLATIONS.ar.disclaimerText}</p>` : ''}
    `;
    return section;
}

// ─── HOOK INTO TAB SYSTEM ────────────────────────────────────

// Override the existing performance tab behavior
const _origInitTabs = typeof initTabs === 'function' ? initTabs : null;

// We'll hook into the tab click in the tab navigation
document.addEventListener('DOMContentLoaded', () => {
    // Listen for the performance tab activation
    const perfTab = document.querySelector('[data-tab="performance"]');
    if (perfTab) {
        perfTab.addEventListener('click', () => {
            // Small delay to let tab content show
            setTimeout(() => loadPerformanceDashboard(), 50);
        });
    }
});

// Also load if performance tab is already visible on page load
window.addEventListener('load', () => {
    const perfContent = document.getElementById('tab-performance');
    if (perfContent && perfContent.classList.contains('active')) {
        loadPerformanceDashboard();
    }
});
