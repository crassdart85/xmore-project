'use strict';

// ============================================
// TIME MACHINE — Frontend Module
// ============================================

(function () {
    let tmDateRange = null;
    let tmChart = null;       // Lightweight Charts instance
    let tmCanvasCtx = null;   // Canvas fallback

    // ─── Public entry point (called by switchToTab) ───────────
    window.loadTimeMachine = function () {
        initTimeMachineForm();
    };

    window.updateTimeMachineLanguage = function () {
        // Translate static elements via data-translate
        document.querySelectorAll('#tab-timemachine [data-translate]').forEach(el => {
            const key = el.getAttribute('data-translate');
            if (typeof t === 'function') el.textContent = t(key);
        });
        // Update brief
        const brief = document.getElementById('timemachineBrief');
        if (brief && typeof t === 'function') brief.textContent = t('timemachineBrief');
    };

    // ─── Form initialisation ─────────────────────────────────
    async function initTimeMachineForm() {
        const dateInput = document.getElementById('tmStartDate');
        const amountInput = document.getElementById('tmAmount');
        const slider = document.getElementById('tmAmountSlider');
        const display = document.getElementById('tmAmountDisplay');
        const simulateBtn = document.getElementById('tmSimulateBtn');

        if (!dateInput || !amountInput) return;

        // Fetch date range
        if (!tmDateRange) {
            try {
                const res = await fetch('/api/timemachine/date-range');
                if (res.ok) tmDateRange = await res.json();
            } catch (e) {
                console.warn('Failed to fetch date range:', e);
            }
        }

        if (tmDateRange && tmDateRange.min_date) {
            dateInput.min = tmDateRange.min_date;
            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);
            dateInput.max = yesterday.toISOString().split('T')[0];
            if (!dateInput.value) {
                // Default to 6 months ago
                const sixMonths = new Date();
                sixMonths.setMonth(sixMonths.getMonth() - 6);
                const defaultDate = sixMonths.toISOString().split('T')[0];
                dateInput.value = defaultDate >= tmDateRange.min_date ? defaultDate : tmDateRange.min_date;
            }
        }

        // Amount ↔ slider sync
        function syncDisplay() {
            const val = parseInt(amountInput.value) || 50000;
            if (display) display.textContent = formatEGP(val);
        }

        if (slider) {
            slider.addEventListener('input', () => {
                amountInput.value = slider.value;
                syncDisplay();
            });
        }
        amountInput.addEventListener('input', () => {
            if (slider) slider.value = Math.min(Math.max(amountInput.value, 5000), 500000);
            syncDisplay();
        });
        syncDisplay();

        // Date presets
        document.querySelectorAll('.tm-preset').forEach(btn => {
            btn.addEventListener('click', () => {
                const months = parseInt(btn.getAttribute('data-months'));
                if (months === 0 && tmDateRange && tmDateRange.min_date) {
                    dateInput.value = tmDateRange.min_date;
                } else {
                    const d = new Date();
                    d.setMonth(d.getMonth() - months);
                    const str = d.toISOString().split('T')[0];
                    dateInput.value = (tmDateRange && str < tmDateRange.min_date) ? tmDateRange.min_date : str;
                }
                // Visual feedback
                document.querySelectorAll('.tm-preset').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });

        // Simulate button
        if (simulateBtn && !simulateBtn._tmBound) {
            simulateBtn._tmBound = true;
            simulateBtn.addEventListener('click', runSimulation);
        }
    }

    // ─── Run simulation ──────────────────────────────────────
    async function runSimulation() {
        const amountInput = document.getElementById('tmAmount');
        const dateInput = document.getElementById('tmStartDate');
        const resultsDiv = document.getElementById('tmResults');
        const loadingDiv = document.getElementById('tmLoading');
        const simulateBtn = document.getElementById('tmSimulateBtn');

        const amount = parseFloat(amountInput.value);
        const startDate = dateInput.value;

        // Validate
        if (!amount || amount < 5000 || amount > 10000000) {
            if (typeof showToast === 'function') showToast('error', typeof t === 'function' ? t('tmInvalidAmount') || 'Amount must be between 5,000 and 10,000,000 EGP' : 'Invalid amount');
            return;
        }
        if (!startDate) {
            if (typeof showToast === 'function') showToast('error', 'Please select a start date');
            return;
        }

        // Show loading
        if (resultsDiv) resultsDiv.style.display = 'none';
        if (loadingDiv) loadingDiv.style.display = 'flex';
        if (simulateBtn) simulateBtn.disabled = true;

        try {
            const res = await fetch('/api/timemachine/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount, start_date: startDate })
            });

            const data = await res.json();

            if (!res.ok || data.error) {
                // Use friendly message, fall back to error code
                const msg = data.message || data.error || 'Simulation failed';
                throw new Error(msg);
            }

            renderResults(data.simulation || data);
        } catch (err) {
            console.error('Simulation error:', err);
            const _t = typeof t === 'function' ? t : (k) => k;
            const esc = typeof escapeHtml === 'function' ? escapeHtml : (s) => s;
            if (resultsDiv) {
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = `
                    <div class="tm-empty-state">
                        <div class="tm-empty-icon">📭</div>
                        <h3>${esc(err.message)}</h3>
                        <p class="tm-empty-hint">${esc(_t('tmNoDataHint'))}</p>
                    </div>`;
            }
        } finally {
            if (loadingDiv) loadingDiv.style.display = 'none';
            if (simulateBtn) simulateBtn.disabled = false;
        }
    }

    // ─── Render results ──────────────────────────────────────
    function renderResults(sim) {
        const resultsDiv = document.getElementById('tmResults');
        if (!resultsDiv) return;
        resultsDiv.style.display = 'block';

        const isProfit = sim.total_return_pct >= 0;
        const lang = (typeof currentLang !== 'undefined') ? currentLang : 'en';
        const _t = typeof t === 'function' ? t : (k) => k;

        // Hero card
        const invested = document.getElementById('tmInvestedAmount');
        const final = document.getElementById('tmFinalAmount');
        const badge = document.getElementById('tmReturnBadge');

        if (invested) invested.textContent = formatEGP(sim.input_amount);
        if (final) {
            // Animate with CountUp if available
            if (typeof countUp !== 'undefined' || typeof CountUp !== 'undefined') {
                animateCounter(final, sim.input_amount, sim.final_value);
            } else {
                final.textContent = formatEGP(sim.final_value);
            }
            final.className = 'tm-final ' + (isProfit ? 'tm-profit' : 'tm-loss');
        }
        if (badge) {
            const sign = isProfit ? '+' : '';
            badge.textContent = `${sign}${sim.total_return_pct}% (${sign}${formatEGP(sim.total_return_egp)})`;
            badge.className = 'tm-hero-return ' + (isProfit ? 'tm-badge-profit' : 'tm-badge-loss');
        }

        // Hero arrow direction for RTL
        const arrow = document.querySelector('.tm-hero-arrow');
        if (arrow) arrow.textContent = document.documentElement.dir === 'rtl' ? '\u2190' : '\u2192';

        // Key metrics
        setMetric('tmAlpha', sim.benchmark.alpha_pct !== null ? `${sim.benchmark.alpha_pct >= 0 ? '+' : ''}${sim.benchmark.alpha_pct}%` : 'N/A',
            sim.benchmark.alpha_pct >= 0);
        setMetric('tmTotalTrades', sim.risk_metrics.total_trades);
        setMetric('tmWinRate', `${sim.risk_metrics.win_rate_pct}%`);
        setMetric('tmMaxDrawdown', `${sim.risk_metrics.max_drawdown_pct}%`, false);

        // Duration info
        const durationEl = document.getElementById('tmDuration');
        if (durationEl) durationEl.textContent = sim.duration_display;

        // Equity curve
        renderEquityCurve(sim.equity_curve);

        // Monthly breakdown
        renderMonthlyTable(sim.monthly_breakdown, lang);

        // Top trades
        renderTradeCards('tmTopTrades', sim.top_trades, lang, true);
        renderTradeCards('tmWorstTrades', sim.worst_trades || [], lang, false);

        // Timeline
        renderTimeline(sim.allocation_timeline, lang);

        // Scroll to results
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ─── Equity Curve ────────────────────────────────────────
    function renderEquityCurve(curve) {
        if (!curve || curve.length < 2) return;

        const container = document.getElementById('tmEquityChart');
        if (!container) return;

        // Try Lightweight Charts first
        if (typeof LightweightCharts !== 'undefined') {
            renderEquityCurveLW(container, curve);
        } else {
            renderEquityCurveCanvas(container, curve);
        }
    }

    function renderEquityCurveLW(container, curve) {
        // Clear previous
        container.innerHTML = '';

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const bgColor = isDark ? '#1e1e2e' : '#ffffff';
        const textColor = isDark ? '#e4e4e7' : '#333333';
        const gridColor = isDark ? '#3f3f46' : '#e5e7eb';

        const chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 300,
            layout: { background: { color: bgColor }, textColor },
            grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
            rightPriceScale: { borderColor: gridColor },
            timeScale: { borderColor: gridColor }
        });

        // Xmore series (green area)
        const xmoreSeries = chart.addAreaSeries({
            topColor: 'rgba(102, 126, 234, 0.4)',
            bottomColor: 'rgba(102, 126, 234, 0.05)',
            lineColor: '#667eea',
            lineWidth: 2
        });
        xmoreSeries.setData(curve.map(p => ({ time: p.date, value: p.value })));

        // EGX30 series (gray dashed)
        const hasEgx = curve.some(p => p.egx30_value !== null);
        if (hasEgx) {
            const egxSeries = chart.addLineSeries({
                color: '#9ca3af',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed
            });
            egxSeries.setData(
                curve.filter(p => p.egx30_value !== null).map(p => ({ time: p.date, value: p.egx30_value }))
            );
        }

        chart.timeScale().fitContent();
        tmChart = chart;

        // Responsive
        const ro = new ResizeObserver(() => {
            chart.applyOptions({ width: container.clientWidth });
        });
        ro.observe(container);
    }

    function renderEquityCurveCanvas(canvas, curve) {
        if (!canvas || !canvas.getContext) return;
        const ctx = canvas.getContext('2d');
        const W = canvas.width;
        const H = canvas.height;
        const pad = { top: 20, right: 60, bottom: 30, left: 10 };

        ctx.clearRect(0, 0, W, H);

        const allValues = curve.map(p => p.value).concat(curve.filter(p => p.egx30_value).map(p => p.egx30_value));
        const minV = Math.min(...allValues) * 0.98;
        const maxV = Math.max(...allValues) * 1.02;

        function x(i) { return pad.left + (i / (curve.length - 1)) * (W - pad.left - pad.right); }
        function y(v) { return H - pad.bottom - ((v - minV) / (maxV - minV)) * (H - pad.top - pad.bottom); }

        // Xmore line
        ctx.strokeStyle = '#667eea';
        ctx.lineWidth = 2;
        ctx.beginPath();
        curve.forEach((p, i) => {
            i === 0 ? ctx.moveTo(x(i), y(p.value)) : ctx.lineTo(x(i), y(p.value));
        });
        ctx.stroke();

        // EGX30 line
        const hasEgx = curve.some(p => p.egx30_value !== null);
        if (hasEgx) {
            ctx.strokeStyle = '#9ca3af';
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 3]);
            ctx.beginPath();
            let started = false;
            curve.forEach((p, i) => {
                if (p.egx30_value === null) return;
                if (!started) { ctx.moveTo(x(i), y(p.egx30_value)); started = true; }
                else ctx.lineTo(x(i), y(p.egx30_value));
            });
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Y-axis labels
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#6b7280';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'right';
        for (let i = 0; i <= 4; i++) {
            const val = minV + (i / 4) * (maxV - minV);
            ctx.fillText(formatCompact(val), W - 5, y(val) + 3);
        }
    }

    // ─── Monthly table ───────────────────────────────────────
    function renderMonthlyTable(months, lang) {
        const container = document.getElementById('tmMonthlyTable');
        if (!container || !months || !months.length) return;

        const _t = typeof t === 'function' ? t : (k) => k;
        let html = `<table class="tm-table">
            <thead><tr>
                <th>${_t('tmMonth') || 'Month'}</th>
                <th>Xmore</th>
                <th>EGX30</th>
            </tr></thead><tbody>`;

        for (const m of months) {
            const xCls = m.return_pct >= 0 ? 'tm-pos' : 'tm-neg';
            const eCls = (m.egx30_return_pct !== null && m.egx30_return_pct >= 0) ? 'tm-pos' : 'tm-neg';
            html += `<tr>
                <td>${m.month}</td>
                <td class="${xCls}">${m.return_pct >= 0 ? '+' : ''}${m.return_pct}%</td>
                <td class="${eCls}">${m.egx30_return_pct !== null ? ((m.egx30_return_pct >= 0 ? '+' : '') + m.egx30_return_pct + '%') : '-'}</td>
            </tr>`;
        }

        html += '</tbody></table>';
        container.innerHTML = html;
    }

    // ─── Trade cards ─────────────────────────────────────────
    function renderTradeCards(containerId, trades, lang, isTop) {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!trades || !trades.length) {
            container.innerHTML = '<p class="no-data">-</p>';
            return;
        }

        const esc = typeof escapeHtml === 'function' ? escapeHtml : (s) => s;
        const _t = typeof t === 'function' ? t : (k) => k;

        container.innerHTML = trades.map(tr => {
            const isWin = tr.return_pct >= 0;
            const name = lang === 'ar' ? tr.stock_name_ar : tr.stock_name_en;
            return `
            <div class="tm-trade-card ${isWin ? 'tm-trade-win' : 'tm-trade-loss'}">
                <div class="tm-trade-header">
                    <span class="tm-trade-symbol">${esc(tr.stock_symbol.replace('.CA', ''))}</span>
                    <span class="tm-trade-return ${isWin ? 'tm-pos' : 'tm-neg'}">${isWin ? '+' : ''}${tr.return_pct}%</span>
                </div>
                <div class="tm-trade-name">${esc(name)}</div>
                <div class="tm-trade-details">
                    <span>${_t('tmBought')}: ${tr.buy_price} EGP</span>
                    <span>${_t('tmSold')}: ${tr.sell_price} EGP</span>
                </div>
                <div class="tm-trade-meta">
                    <span>${tr.buy_date} \u2192 ${tr.sell_date}</span>
                    <span>${tr.holding_days} ${_t('tmDays')}</span>
                </div>
                <div class="tm-trade-profit ${isWin ? 'tm-pos' : 'tm-neg'}">
                    ${isWin ? '+' : ''}${formatEGP(tr.profit_egp)} EGP
                </div>
            </div>`;
        }).join('');
    }

    // ─── Timeline ────────────────────────────────────────────
    function renderTimeline(events, lang) {
        const container = document.getElementById('tmTimeline');
        if (!container || !events || !events.length) return;

        const esc = typeof escapeHtml === 'function' ? escapeHtml : (s) => s;

        container.innerHTML = events.slice(0, 50).map(ev => {
            const isBuy = ev.event === 'BUY';
            const reason = lang === 'ar' ? ev.reason_ar : ev.reason_en;
            return `
            <div class="tm-timeline-item ${isBuy ? 'tm-timeline-buy' : 'tm-timeline-sell'}">
                <div class="tm-timeline-dot"></div>
                <div class="tm-timeline-content">
                    <div class="tm-timeline-date">${ev.date}</div>
                    <div class="tm-timeline-event">
                        <span class="tm-timeline-badge ${isBuy ? 'tm-badge-buy' : 'tm-badge-sell'}">${ev.event}</span>
                        <span class="tm-timeline-stock">${esc(ev.stock.replace('.CA', ''))}</span>
                    </div>
                    <div class="tm-timeline-reason">${esc(reason || '')}</div>
                </div>
            </div>`;
        }).join('');
    }

    // ─── Utility ─────────────────────────────────────────────
    function formatEGP(n) {
        if (n === null || n === undefined) return '-';
        return new Intl.NumberFormat('en-EG', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Math.round(n));
    }

    function formatCompact(n) {
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
        return Math.round(n).toString();
    }

    function setMetric(id, value, isPositive) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = value;
        if (isPositive !== undefined) {
            el.classList.toggle('tm-pos', !!isPositive);
            el.classList.toggle('tm-neg', !isPositive);
        }
    }

    function animateCounter(el, from, to) {
        try {
            const CU = (typeof CountUp !== 'undefined') ? CountUp :
                        (typeof countUp !== 'undefined' && countUp.CountUp) ? countUp.CountUp : null;
            if (CU) {
                const cu = new CU(el, to, {
                    startVal: from,
                    duration: 2,
                    separator: ',',
                    decimal: '.',
                    prefix: '',
                    suffix: ''
                });
                cu.start();
                return;
            }
        } catch (e) { /* fallback */ }
        el.textContent = formatEGP(to);
    }

})();
