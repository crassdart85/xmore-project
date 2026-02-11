const PERF_TRANSLATIONS = {
    en: {
        perfTitle: 'Xmore Performance',
        proof: 'Proof of Edge',
        stability: 'Stability Metrics',
        accountability: 'Agent Accountability',
        transparency: 'Transparency & Integrity',
        equity: 'Equity Curve',
        alpha: 'Alpha',
        sharpe: 'Sharpe',
        maxDd: 'Max Drawdown',
        volatility: 'Volatility',
        profitFactor: 'Profit Factor',
        winRate: 'Win Rate',
        trades: 'Trades',
        systemHealth: 'System Health',
        stable: 'Stable',
        watch: 'Watch',
        degraded: 'Degraded',
        sinceInception: 'Since Inception',
        liveOnly: 'Live-only immutable logs',
        showBenchmark: 'Benchmark',
        showDrawdown: 'Drawdown',
        noData: 'Performance tracking will appear after live evaluations.',
        openAudit: 'Open Audit Trail',
        showMore: 'Show More'
    },
    ar: {
        perfTitle: 'أداء إكسمور',
        proof: 'إثبات التفوق',
        stability: 'مقاييس الاستقرار',
        accountability: 'مساءلة الوكلاء',
        transparency: 'الشفافية والنزاهة',
        equity: 'منحنى الأداء',
        alpha: 'ألفا',
        sharpe: 'شارب',
        maxDd: 'أقصى تراجع',
        volatility: 'التذبذب',
        profitFactor: 'معامل الربح',
        winRate: 'نسبة الفوز',
        trades: 'الصفقات',
        systemHealth: 'حالة النظام',
        stable: 'مستقر',
        watch: 'مراقبة',
        degraded: 'متراجع',
        sinceInception: 'منذ الانطلاق',
        liveOnly: 'سجل حي غير قابل للتعديل',
        showBenchmark: 'المعيار',
        showDrawdown: 'الهبوط',
        noData: 'سيظهر تتبع الأداء بعد توفر تقييمات حية.',
        openAudit: 'فتح سجل التدقيق',
        showMore: 'عرض المزيد'
    }
};

function pt(key) {
    return PERF_TRANSLATIONS[currentLang]?.[key] || PERF_TRANSLATIONS.en[key] || key;
}

let perfHistoryPage = 1;
let perfEquityCurveDays = 90;
let perfChartState = { showBenchmark: true, showDrawdown: true, points: [] };

async function loadPerformanceDashboard() {
    const container = document.getElementById('perfDashboard');
    if (!container) return;
    container.innerHTML = '<p class="loading">Loading performance...</p>';

    try {
        const [summary, agents, equity, history] = await Promise.all([
            fetch('/api/performance-v2/summary').then(r => r.json()).catch(() => ({ available: false })),
            fetch('/api/performance-v2/by-agent').then(r => r.json()).catch(() => ({ agents: [] })),
            fetch(`/api/performance-v2/equity-curve?days=${perfEquityCurveDays}`).then(r => r.json()).catch(() => ({ series: [] })),
            fetch(`/api/performance-v2/predictions/history?page=${perfHistoryPage}&limit=10`).then(r => r.json()).catch(() => ({ predictions: [] }))
        ]);

        if (!summary.available) {
            container.innerHTML = `<p class="no-data">${pt('noData')}</p>`;
            return;
        }

        container.innerHTML = '';
        container.appendChild(buildHealth(summary));
        container.appendChild(buildProofOfEdge(summary, equity));
        container.appendChild(buildStability(summary));
        container.appendChild(buildAgentAccountability(agents));
        container.appendChild(buildTransparency(summary, history));
        container.appendChild(buildSinceInception(summary));
        renderEquityCurveChart(equity);
    } catch (e) {
        container.innerHTML = '<p class="error-message">Failed to load performance dashboard.</p>';
        console.error(e);
    }
}

function metricCard(label, value, cls = '', tip = '') {
    return `<div class="perf-metric-card ${cls}" title="${tip}"><div class="perf-metric-label">${label}</div><div class="perf-metric-value">${value}</div></div>`;
}

function buildHealth(summary) {
    const g = summary.global || {};
    const r30 = summary.rolling?.['30d'] || {};
    const sharpe = r30.sharpe_ratio ?? g.sharpe_ratio ?? 0;
    const alpha = r30.alpha ?? g.avg_alpha_1d ?? 0;
    const dd = r30.max_drawdown ?? g.max_drawdown ?? 0;
    let state = 'degraded';
    if (sharpe > 1 && alpha > 0 && dd <= 8) state = 'stable';
    else if (sharpe > 0.6 && alpha >= 0 && dd <= 12) state = 'watch';

    return createSection(`
        <div class="perf-health ${state}">
            <div class="perf-health-title">${pt('systemHealth')}</div>
            <div class="perf-health-state">${pt(state)}</div>
            <div class="perf-health-note">${pt('liveOnly')}</div>
        </div>
    `);
}

function buildProofOfEdge(summary, equity) {
    const g = summary.global || {};
    const r30 = summary.rolling?.['30d'] || {};
    const alpha = r30.alpha ?? 0;
    const sharpe = r30.sharpe_ratio ?? g.sharpe_ratio ?? 0;
    const maxDd = r30.max_drawdown ?? g.max_drawdown ?? 0;

    return createSection(`
        <h3>${pt('proof')}</h3>
        <div class="perf-proof-grid">
            ${metricCard(pt('alpha'), `${alpha > 0 ? '+' : ''}${alpha.toFixed(2)}%`, alpha > 0 ? 'positive' : 'negative', '30-day alpha versus EGX30')}
            ${metricCard(pt('sharpe'), Number(sharpe).toFixed(2), sharpe >= 1 ? 'positive' : 'neutral', '30-day risk-adjusted return')}
            ${metricCard(pt('maxDd'), `${Number(maxDd).toFixed(2)}%`, maxDd <= 8 ? 'positive' : 'negative', '30-day maximum drawdown')}
        </div>
        <div class="perf-section-head">
            <h3>${pt('equity')}</h3>
            <div class="perf-chart-controls">
                <button class="perf-period-btn ${perfEquityCurveDays === 30 ? 'active' : ''}" onclick="changeEquityCurvePeriod(30)">30d</button>
                <button class="perf-period-btn ${perfEquityCurveDays === 60 ? 'active' : ''}" onclick="changeEquityCurvePeriod(60)">60d</button>
                <button class="perf-period-btn ${perfEquityCurveDays === 90 ? 'active' : ''}" onclick="changeEquityCurvePeriod(90)">90d</button>
                <button class="perf-period-btn ${perfEquityCurveDays === 180 ? 'active' : ''}" onclick="changeEquityCurvePeriod(180)">180d</button>
                <label><input type="checkbox" ${perfChartState.showBenchmark ? 'checked' : ''} onchange="toggleBenchmarkLine(this.checked)"> ${pt('showBenchmark')}</label>
                <label><input type="checkbox" ${perfChartState.showDrawdown ? 'checked' : ''} onchange="toggleDrawdownShading(this.checked)"> ${pt('showDrawdown')}</label>
            </div>
        </div>
        <div class="perf-chart-wrap">
            <canvas id="equityCurveCanvas"></canvas>
            <div id="perfChartTooltip" class="perf-chart-tooltip"></div>
        </div>
        <div class="perf-chart-legend">
            <span>Xmore ${equity.total_xmore > 0 ? '+' : ''}${Number(equity.total_xmore || 0).toFixed(2)}%</span>
            <span>EGX30 ${equity.total_egx30 > 0 ? '+' : ''}${Number(equity.total_egx30 || 0).toFixed(2)}%</span>
            <span>Alpha ${equity.total_alpha > 0 ? '+' : ''}${Number(equity.total_alpha || 0).toFixed(2)}%</span>
        </div>
    `);
}

function buildStability(summary) {
    const rows = ['30d', '60d', '90d'].map(k => {
        const d = summary.rolling?.[k] || {};
        return `<tr>
            <td>${k}</td>
            <td>${Number(d.win_rate || 0).toFixed(1)}%</td>
            <td>${Number(d.volatility || 0).toFixed(2)}%</td>
            <td>${Number(d.profit_factor || 0).toFixed(2)}</td>
            <td>${Number(d.trades || 0)}</td>
        </tr>`;
    }).join('');
    return createSection(`
        <h3>${pt('stability')}</h3>
        <div class="perf-table-wrapper">
            <table class="perf-table">
                <thead><tr><th>Window</th><th>${pt('winRate')}</th><th>${pt('volatility')}</th><th>${pt('profitFactor')}</th><th>${pt('trades')}</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `);
}

function buildAgentAccountability(data) {
    const agents = (data.agents || []).slice().sort((a, b) => (b.win_rate_30d || 0) - (a.win_rate_30d || 0));
    const rows = agents.map(a => {
        const n = typeof getAgentDisplayName === 'function' ? getAgentDisplayName(a.agent) : a.agent;
        return `<tr>
            <td>${n}</td>
            <td>${Number(a.win_rate_30d || 0).toFixed(1)}%</td>
            <td>${Number(a.win_rate_90d || 0).toFixed(1)}%</td>
            <td>${Number(a.avg_confidence_30d || 0).toFixed(1)}%</td>
            <td>${a.predictions_30d || 0}</td>
            <td><div class="mini-weight"><span style="width:${Math.min(100, Number(a.win_rate_30d || 0))}%"></span></div></td>
        </tr>`;
    }).join('');
    return createSection(`
        <h3>${pt('accountability')}</h3>
        <div class="perf-table-wrapper">
            <table class="perf-table">
                <thead><tr><th>Agent</th><th>30d Win</th><th>90d Win</th><th>Confidence</th><th>Predictions</th><th>Weight</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="6">No data</td></tr>'}</tbody>
            </table>
        </div>
    `);
}

function buildTransparency(summary, history) {
    const g = summary.global || {};
    const preds = history.predictions || [];
    const rows = preds.map(p => `<tr>
        <td>${String(p.prediction_date || '').slice(0, 10)}</td>
        <td>${p.symbol || '-'}</td>
        <td>${p.final_signal || '-'}</td>
        <td>${p.consensus_confidence == null ? '-' : `${Number(p.consensus_confidence).toFixed(1)}%`}</td>
        <td>${p.alpha_1d == null ? '-' : `${p.alpha_1d > 0 ? '+' : ''}${Number(p.alpha_1d).toFixed(2)}%`}</td>
    </tr>`).join('');
    const progress = Math.min(100, Math.round(((g.total_predictions || 0) / 100) * 100));
    return createSection(`
        <h3>${pt('transparency')}</h3>
        <div class="perf-integrity-banner">${pt('liveOnly')}</div>
        <div class="perf-table-wrapper">
            <table class="perf-table">
                <thead><tr><th>Date</th><th>Symbol</th><th>Signal</th><th>Confidence</th><th>Alpha</th></tr></thead>
                <tbody>${rows || '<tr><td colspan="5">No data</td></tr>'}</tbody>
            </table>
        </div>
        <div class="perf-actions">
            <button class="perf-action-btn secondary" onclick="showAuditLog()">${pt('openAudit')}</button>
            <button class="perf-action-btn" onclick="loadMorePredictions()">${pt('showMore')}</button>
        </div>
        <div class="integrity-progress"><span style="width:${progress}%"></span><em>${g.total_predictions || 0}/100</em></div>
    `);
}

function buildSinceInception(summary) {
    const g = summary.global || {};
    return createSection(`
        <h3>${pt('sinceInception')}</h3>
        <div class="perf-proof-grid">
            ${metricCard(pt('alpha'), `${g.avg_alpha_1d > 0 ? '+' : ''}${Number(g.avg_alpha_1d || 0).toFixed(2)}%`)}
            ${metricCard(pt('sharpe'), Number(g.sharpe_ratio || 0).toFixed(2))}
            ${metricCard('First Live', g.first_prediction ? String(g.first_prediction).slice(0, 10) : 'N/A')}
            ${metricCard('Total Live', `${g.total_predictions || 0}`)}
        </div>
    `);
}

function createSection(html) {
    const el = document.createElement('div');
    el.className = 'perf-section';
    el.innerHTML = html;
    return el;
}

async function changeEquityCurvePeriod(days) {
    perfEquityCurveDays = days;
    await loadPerformanceDashboard();
}

function toggleBenchmarkLine(v) {
    perfChartState.showBenchmark = !!v;
    const chartData = { series: perfChartState.points };
    renderEquityCurveChart(chartData);
}

function toggleDrawdownShading(v) {
    perfChartState.showDrawdown = !!v;
    const chartData = { series: perfChartState.points };
    renderEquityCurveChart(chartData);
}

function renderEquityCurveChart(data) {
    const canvas = document.getElementById('equityCurveCanvas');
    const tip = document.getElementById('perfChartTooltip');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const points = data.series || [];
    perfChartState.points = points;

    const wrap = canvas.parentElement;
    const w = Math.max(320, Math.floor((wrap?.clientWidth || 860) - 12));
    const h = 330;
    canvas.width = w;
    canvas.height = h;
    ctx.clearRect(0, 0, w, h);
    if (points.length < 2) return;

    const pad = { top: 20, left: 54, right: 18, bottom: 28 };
    const cW = w - pad.left - pad.right;
    const cH = h - pad.top - pad.bottom;
    const values = points.flatMap(p => [Number(p.xmore || 0), Number(p.egx30 || 0)]);
    const min = Math.min(...values, 0) - 0.8;
    const max = Math.max(...values, 0) + 0.8;
    const range = Math.max(1, max - min);
    const toX = i => pad.left + (i / (points.length - 1)) * cW;
    const toY = v => pad.top + (1 - ((v - min) / range)) * cH;

    ctx.strokeStyle = 'rgba(127,127,127,0.25)';
    for (let i = 0; i < 5; i++) {
        const y = pad.top + (i / 4) * cH;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
    }

    if (perfChartState.showDrawdown) {
        let peak = -Infinity;
        ctx.fillStyle = 'rgba(220, 38, 38, 0.08)';
        for (let i = 0; i < points.length; i++) {
            const cur = Number(points[i].xmore || 0);
            if (cur > peak) peak = cur;
            if (cur < peak) {
                const x = toX(i);
                const y1 = toY(peak);
                const y2 = toY(cur);
                ctx.fillRect(x - 1, Math.min(y1, y2), 2, Math.abs(y2 - y1));
            }
        }
    }

    if (perfChartState.showBenchmark) {
        ctx.strokeStyle = '#9ca3af';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 4]);
        ctx.beginPath();
        points.forEach((p, i) => i ? ctx.lineTo(toX(i), toY(Number(p.egx30 || 0))) : ctx.moveTo(toX(i), toY(Number(p.egx30 || 0))));
        ctx.stroke();
        ctx.setLineDash([]);
    }

    ctx.strokeStyle = '#16a34a';
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    points.forEach((p, i) => i ? ctx.lineTo(toX(i), toY(Number(p.xmore || 0))) : ctx.moveTo(toX(i), toY(Number(p.xmore || 0))));
    ctx.stroke();

    const move = (ev) => {
        const rect = canvas.getBoundingClientRect();
        const mx = ev.clientX - rect.left;
        let idx = Math.round(((mx - pad.left) / cW) * (points.length - 1));
        idx = Math.max(0, Math.min(points.length - 1, idx));
        const p = points[idx];
        if (!tip || !p) return;
        tip.style.display = 'block';
        tip.style.left = `${Math.min(w - 170, Math.max(8, mx + 10))}px`;
        tip.style.top = '10px';
        tip.innerHTML = `Xmore: ${Number(p.xmore).toFixed(2)}%<br>EGX30: ${Number(p.egx30).toFixed(2)}%<br>Alpha: ${Number(p.alpha).toFixed(2)}%`;
    };
    canvas.onmousemove = move;
    canvas.onmouseleave = () => { if (tip) tip.style.display = 'none'; };
}

async function loadMorePredictions() {
    perfHistoryPage += 1;
    await loadPerformanceDashboard();
}

async function showAuditLog() {
    const data = await fetch('/api/performance-v2/audit?limit=80').then(r => r.json()).catch(() => ({ audit_entries: [] }));
    const modal = document.createElement('div');
    modal.className = 'perf-modal-overlay';
    modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
    modal.innerHTML = `<div class="perf-modal">
        <button class="perf-modal-close" onclick="this.closest('.perf-modal-overlay').remove()">x</button>
        <h3>Audit Trail</h3>
        <div class="perf-table-wrapper"><table class="perf-table"><thead><tr><th>When</th><th>Table</th><th>Record</th><th>Field</th><th>Old</th><th>New</th></tr></thead>
        <tbody>${(data.audit_entries || []).map(e => `<tr><td>${e.changed_at || '-'}</td><td>${e.table_name || '-'}</td><td>${e.record_id || '-'}</td><td>${e.field_changed || '-'}</td><td>${e.old_value || '-'}</td><td>${e.new_value || '-'}</td></tr>`).join('') || '<tr><td colspan="6">No entries</td></tr>'}</tbody></table></div>
    </div>`;
    document.body.appendChild(modal);
}

document.addEventListener('DOMContentLoaded', () => {
    const perfTab = document.querySelector('[data-tab="performance"]');
    if (perfTab) perfTab.addEventListener('click', () => setTimeout(loadPerformanceDashboard, 60));
});

