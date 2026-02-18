'use strict';

// ============================================
// TIME MACHINE — Frontend Module
// Ephemeral architecture: fetches live from Yahoo Finance via Python
// ============================================

(function () {
    let tmChart = null;       // Lightweight Charts instance

    // ─── Public entry point (called by switchToTab) ───────────
    window.loadTimeMachine = function () {
        initTimeMachineForm();
    };

    window.updateTimeMachineLanguage = function () {
        document.querySelectorAll('#tab-timemachine [data-translate]').forEach(el => {
            const key = el.getAttribute('data-translate');
            if (typeof t === 'function') el.textContent = t(key);
        });
        const brief = document.getElementById('timemachineBrief');
        if (brief && typeof t === 'function') brief.textContent = t('timemachineBrief');
    };

    // ─── Form initialisation ─────────────────────────────────
    function initTimeMachineForm() {
        const dateInput = document.getElementById('tmStartDate');
        const amountInput = document.getElementById('tmAmount');
        const slider = document.getElementById('tmAmountSlider');
        const display = document.getElementById('tmAmountDisplay');
        const simulateBtn = document.getElementById('tmSimulateBtn');

        if (!dateInput || !amountInput) return;

        // Set date constraints: max = yesterday, min = 2 years ago
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        const twoYearsAgo = new Date(today);
        twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);

        dateInput.max = yesterday.toISOString().split('T')[0];
        dateInput.min = twoYearsAgo.toISOString().split('T')[0];

        // Default to 6 months ago
        if (!dateInput.value) {
            const sixMonths = new Date(today);
            sixMonths.setMonth(sixMonths.getMonth() - 6);
            dateInput.value = sixMonths.toISOString().split('T')[0];
        }

        // Amount ↔ slider sync
        function syncDisplay() {
            const val = parseInt(amountInput.value) || 50000;
            if (display) display.textContent = formatEGP(val) + ' EGP';
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
                const d = new Date();
                if (months === 0) {
                    // Max range = 2 years ago
                    d.setFullYear(d.getFullYear() - 2);
                    d.setDate(d.getDate() + 1); // just inside 2-year limit
                } else {
                    d.setMonth(d.getMonth() - months);
                }
                const str = d.toISOString().split('T')[0];
                // Clamp to min
                dateInput.value = str < dateInput.min ? dateInput.min : str;

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
        const lang = (typeof currentLang !== 'undefined') ? currentLang : 'en';
        const _t = typeof t === 'function' ? t : (k) => k;

        // Validate
        if (!amount || amount < 5000 || amount > 10000000) {
            if (typeof showToast === 'function') showToast('error', _t('tmInvalidAmount'));
            return;
        }
        if (!startDate) {
            if (typeof showToast === 'function') showToast('error', _t('tmSelectDate') || 'Please select a start date');
            return;
        }

        // Show loading, hide previous results
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
                // Use bilingual message from Python/server
                const msg = lang === 'ar'
                    ? (data.message_ar || data.message_en || _t('tmErrorGeneric'))
                    : (data.message_en || data.message_ar || _t('tmErrorGeneric'));
                throw new Error(msg);
            }

            renderResults(data.simulation);
        } catch (err) {
            console.error('Simulation error:', err);
            const esc = typeof escapeHtml === 'function' ? escapeHtml : (s) => s;
            const _t2 = typeof t === 'function' ? t : (k) => k;
            if (resultsDiv) {
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = `
                    <div class="tm-empty-state">
                        <div class="tm-empty-icon">⏳</div>
                        <h3>${esc(err.message)}</h3>
                        <p class="tm-empty-hint">${esc(_t2('tmTryDifferent') || 'Try a different date range or amount.')}</p>
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

        if (invested) invested.textContent = formatEGP(sim.input_amount) + ' EGP';
        if (final) {
            if (typeof CountUp !== 'undefined' || (typeof countUp !== 'undefined')) {
                animateCounter(final, sim.input_amount, sim.final_value);
            } else {
                final.textContent = formatEGP(sim.final_value) + ' EGP';
            }
            final.className = 'tm-final ' + (isProfit ? 'tm-profit' : 'tm-loss');
        }
        if (badge) {
            const sign = isProfit ? '+' : '';
            badge.textContent = `${sign}${sim.total_return_pct}% (${sign}${formatEGP(sim.total_return_egp)} EGP)`;
            badge.className = 'tm-hero-return ' + (isProfit ? 'tm-badge-profit' : 'tm-badge-loss');
        }

        // Arrow direction for RTL
        const arrow = document.querySelector('.tm-hero-arrow');
        if (arrow) arrow.textContent = document.documentElement.dir === 'rtl' ? '\u2190' : '\u2192';

        // Duration
        const durationEl = document.getElementById('tmDuration');
        if (durationEl) {
            durationEl.textContent = lang === 'ar'
                ? (sim.duration_display_ar || sim.duration_display_en || `${sim.duration_days} days`)
                : (sim.duration_display_en || `${sim.duration_days} days`);
        }

        // Key metrics
        setMetric('tmAlpha',
            sim.benchmark.alpha_pct !== null
                ? `${sim.benchmark.alpha_pct >= 0 ? '+' : ''}${sim.benchmark.alpha_pct}%`
                : 'N/A',
            sim.benchmark.alpha_pct !== null ? sim.benchmark.alpha_pct >= 0 : undefined
        );
        setMetric('tmAnnualized',
            `${sim.annualized_return_pct >= 0 ? '+' : ''}${sim.annualized_return_pct}%`,
            sim.annualized_return_pct >= 0
        );
        setMetric('tmTotalTrades', sim.risk_metrics.total_trades);
        setMetric('tmWinRate', `${sim.risk_metrics.win_rate_pct}%`);
        setMetric('tmMaxDrawdown', `${sim.risk_metrics.max_drawdown_pct}%`);
        setMetric('tmSharpe', sim.risk_metrics.sharpe_ratio);

        // Equity curve
        renderEquityCurve(sim.equity_curve);

        // Monthly breakdown
        renderMonthlyTable(sim.monthly_breakdown, lang);

        // Top trades
        renderTradeCards('tmTopTrades', sim.top_trades, lang);
        renderTradeCards('tmWorstTrades', sim.worst_trades || [], lang);

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

        if (typeof LightweightCharts !== 'undefined') {
            renderEquityCurveLW(container, curve);
        } else {
            renderEquityCurveCanvas(container, curve);
        }
    }

    function renderEquityCurveLW(container, curve) {
        container.innerHTML = '';
        if (tmChart) { try { tmChart.remove(); } catch (e) {} tmChart = null; }

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

        // Xmore portfolio (green area)
        const xmoreSeries = chart.addAreaSeries({
            topColor: 'rgba(102, 126, 234, 0.4)',
            bottomColor: 'rgba(102, 126, 234, 0.05)',
            lineColor: '#667eea',
            lineWidth: 2
        });
        xmoreSeries.setData(curve.map(p => ({ time: p.date, value: p.value })));

        // EGX30 benchmark (gray dashed)
        const hasEgx = curve.some(p => p.egx30_value !== null);
        if (hasEgx) {
            const egxSeries = chart.addLineSeries({
                color: '#9ca3af',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed
            });
            egxSeries.setData(
                curve.filter(p => p.egx30_value !== null)
                     .map(p => ({ time: p.date, value: p.egx30_value }))
            );
        }

        chart.timeScale().fitContent();
        tmChart = chart;

        const ro = new ResizeObserver(() => {
            chart.applyOptions({ width: container.clientWidth });
        });
        ro.observe(container);
    }

    function renderEquityCurveCanvas(container, curve) {
        // Fallback canvas renderer
        let canvas = container.querySelector('canvas');
        if (!canvas) {
            canvas = document.createElement('canvas');
            canvas.width = container.clientWidth || 600;
            canvas.height = 300;
            container.innerHTML = '';
            container.appendChild(canvas);
        }
        const ctx = canvas.getContext('2d');
        const W = canvas.width;
        const H = canvas.height;
        const pad = { top: 20, right: 70, bottom: 30, left: 10 };

        ctx.clearRect(0, 0, W, H);

        const allValues = curve.map(p => p.value)
            .concat(curve.filter(p => p.egx30_value != null).map(p => p.egx30_value));
        const minV = Math.min(...allValues) * 0.98;
        const maxV = Math.max(...allValues) * 1.02;

        function x(i) { return pad.left + (i / (curve.length - 1)) * (W - pad.left - pad.right); }
        function y(v) { return H - pad.bottom - ((v - minV) / (maxV - minV)) * (H - pad.top - pad.bottom); }

        ctx.strokeStyle = '#667eea';
        ctx.lineWidth = 2;
        ctx.beginPath();
        curve.forEach((p, i) => {
            i === 0 ? ctx.moveTo(x(i), y(p.value)) : ctx.lineTo(x(i), y(p.value));
        });
        ctx.stroke();

        const hasEgx = curve.some(p => p.egx30_value != null);
        if (hasEgx) {
            ctx.strokeStyle = '#9ca3af';
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 3]);
            ctx.beginPath();
            let started = false;
            curve.forEach((p, i) => {
                if (p.egx30_value == null) return;
                if (!started) { ctx.moveTo(x(i), y(p.egx30_value)); started = true; }
                else ctx.lineTo(x(i), y(p.egx30_value));
            });
            ctx.stroke();
            ctx.setLineDash([]);
        }

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
            const eCls = m.egx30_return_pct !== null && m.egx30_return_pct >= 0 ? 'tm-pos' : 'tm-neg';
            html += `<tr>
                <td>${m.month}</td>
                <td class="${xCls}">${m.return_pct >= 0 ? '+' : ''}${m.return_pct}%</td>
                <td class="${eCls}">${m.egx30_return_pct !== null
                    ? (m.egx30_return_pct >= 0 ? '+' : '') + m.egx30_return_pct + '%'
                    : '-'}</td>
            </tr>`;
        }

        html += '</tbody></table>';
        container.innerHTML = html;
    }

    // ─── Trade cards ─────────────────────────────────────────
    function renderTradeCards(containerId, trades, lang) {
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
            const name = lang === 'ar' ? (tr.stock_name_ar || tr.stock_symbol) : (tr.stock_name_en || tr.stock_symbol);
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
                    <span>${tr.buy_date} &rarr; ${tr.sell_date}</span>
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

    // ─── Utilities ───────────────────────────────────────────
    function formatEGP(n) {
        if (n === null || n === undefined) return '-';
        return new Intl.NumberFormat('en-EG', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(Math.round(n));
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
            const CU = (typeof CountUp !== 'undefined') ? CountUp
                : (typeof countUp !== 'undefined' && countUp.CountUp) ? countUp.CountUp
                : null;
            if (CU) {
                const cu = new CU(el, to, {
                    startVal: from,
                    duration: 2,
                    separator: ',',
                    decimal: '.',
                });
                cu.start();
                return;
            }
        } catch (e) { /* fallback */ }
        el.textContent = formatEGP(to) + ' EGP';
    }

})();
