'use strict';

// ============================================
// TIME MACHINE — Frontend Module
// Past: ephemeral portfolio backtest (Yahoo Finance via Python)
// Future: Monte Carlo / GBM probabilistic forecast (numpy via Python)
// ============================================

(function () {
    let tmChart = null;       // LW Charts instance (Past equity curve)
    let fcBandChart = null;   // LW Charts instance (Future band chart)
    let fcStocksLoaded = false;

    // ─── Public entry point (called by switchToTab) ───────────
    window.loadTimeMachine = function () {
        initSubTabs();
        initTimeMachineForm();
        initFutureForm();
    };

    // ─── Sub-tab switching (Past / Future) ───────────────────
    function initSubTabs() {
        const pastBtn   = document.getElementById('tmSubPast');
        const futureBtn = document.getElementById('tmSubFuture');
        const pastPane  = document.getElementById('tmTabPast');
        const futurePane = document.getElementById('tmTabFuture');
        if (!pastBtn || !futureBtn) return;

        function activatePast() {
            pastPane.style.display = '';
            futurePane.style.display = 'none';
            pastBtn.classList.add('tm-subtab-active');
            futureBtn.classList.remove('tm-subtab-active');
            pastBtn.setAttribute('aria-selected', 'true');
            futureBtn.setAttribute('aria-selected', 'false');
        }

        function activateFuture() {
            pastPane.style.display = 'none';
            futurePane.style.display = '';
            futureBtn.classList.add('tm-subtab-active');
            pastBtn.classList.remove('tm-subtab-active');
            futureBtn.setAttribute('aria-selected', 'true');
            pastBtn.setAttribute('aria-selected', 'false');
            if (!fcStocksLoaded) loadForecastSymbols();
        }

        if (!pastBtn._tmSubBound) {
            pastBtn._tmSubBound = true;
            pastBtn.addEventListener('click', activatePast);
            futureBtn.addEventListener('click', activateFuture);
        }
    }

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

    // ================================================================
    // FUTURE TAB — Monte Carlo Forecast
    // ================================================================

    // ─── Load stock list into selector ───────────────────────
    async function loadForecastSymbols() {
        const select = document.getElementById('fcSymbol');
        const search = document.getElementById('fcSymbolSearch');
        if (!select) return;

        try {
            const res = await fetch('/api/stocks', { credentials: 'include' });
            if (!res.ok) throw new Error('Failed to load stocks');
            const data = await res.json();
            const stocks = data.stocks || data || [];

            const lang = (typeof currentLang !== 'undefined') ? currentLang : 'en';
            select.innerHTML = '<option value="">— Select stock —</option>' +
                stocks.map(s => {
                    const name = lang === 'ar' ? (s.name_ar || s.name_en) : (s.name_en || s.name_ar);
                    const sym  = s.symbol.replace('.CA', '');
                    return `<option value="${s.symbol}" data-name="${escHtml(name)}" data-sym="${escHtml(sym)}">${escHtml(sym)} — ${escHtml(name)}</option>`;
                }).join('');

            fcStocksLoaded = true;

            // Live search filter
            if (search) {
                search.addEventListener('input', () => {
                    const q = search.value.toLowerCase();
                    Array.from(select.options).forEach(opt => {
                        if (!opt.value) return; // keep placeholder
                        const text = (opt.dataset.sym + ' ' + (opt.dataset.name || '')).toLowerCase();
                        opt.style.display = text.includes(q) ? '' : 'none';
                    });
                });
            }
        } catch (err) {
            if (select) select.innerHTML = '<option value="">Could not load stocks</option>';
        }
    }

    // ─── Escape helper (local fallback) ──────────────────────
    function escHtml(v) {
        return typeof escapeHtml === 'function' ? escapeHtml(v) : String(v ?? '');
    }

    // ─── Initialise Future form bindings ─────────────────────
    function initFutureForm() {
        const runBtn       = document.getElementById('fcRunBtn');
        const amountInput  = document.getElementById('fcAmount');
        const slider       = document.getElementById('fcAmountSlider');
        const display      = document.getElementById('fcAmountDisplay');
        if (!runBtn) return;

        // Amount ↔ slider sync
        function syncFcDisplay() {
            const val = parseInt(amountInput.value) || 50000;
            if (display) display.textContent = formatEGP(val) + ' EGP';
        }
        if (slider) {
            slider.addEventListener('input', () => { amountInput.value = slider.value; syncFcDisplay(); });
        }
        if (amountInput) {
            amountInput.addEventListener('input', () => {
                if (slider) slider.value = Math.min(Math.max(amountInput.value, 1000), 500000);
                syncFcDisplay();
            });
        }
        syncFcDisplay();

        // Horizon preset buttons
        document.querySelectorAll('.fc-horizon-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.fc-horizon-btn').forEach(b => b.classList.remove('fc-horizon-active'));
                btn.classList.add('fc-horizon-active');
                const hid = document.getElementById('fcHorizon');
                if (hid) hid.value = btn.getAttribute('data-days');
            });
        });

        // Scenario radio buttons — highlight active
        document.querySelectorAll('input[name="fcScenario"]').forEach(radio => {
            radio.addEventListener('change', () => {
                document.querySelectorAll('.fc-scenario-opt').forEach(lbl => lbl.classList.remove('fc-scenario-active'));
                if (radio.checked) radio.closest('.fc-scenario-opt').classList.add('fc-scenario-active');
            });
        });

        if (!runBtn._fcBound) {
            runBtn._fcBound = true;
            runBtn.addEventListener('click', runForecast);
        }
    }

    // ─── Run Monte Carlo forecast ─────────────────────────────
    async function runForecast() {
        const symbol    = (document.getElementById('fcSymbol')?.value || '').trim();
        const amount    = parseFloat(document.getElementById('fcAmount')?.value) || 0;
        const horizon   = parseInt(document.getElementById('fcHorizon')?.value, 10) || 63;
        const scenario  = document.querySelector('input[name="fcScenario"]:checked')?.value || 'base';
        const resultsDiv = document.getElementById('fcResults');
        const loadingDiv = document.getElementById('fcLoading');
        const runBtn    = document.getElementById('fcRunBtn');
        const _t = typeof t === 'function' ? t : (k) => k;

        if (!symbol) {
            if (typeof showToast === 'function') showToast('error', _t('fcSelectSymbol') || 'Please select a stock.');
            return;
        }
        if (!amount || amount < 1000) {
            if (typeof showToast === 'function') showToast('error', _t('tmInvalidAmount') || 'Enter a valid amount (min 1,000 EGP).');
            return;
        }

        if (resultsDiv) resultsDiv.style.display = 'none';
        if (loadingDiv) loadingDiv.style.display = 'flex';
        if (runBtn) runBtn.disabled = true;

        try {
            const res = await fetch('/api/timemachine/forecast', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol, investment_amount: amount, horizon, scenario }),
            });
            const data = await res.json();

            if (!res.ok || !data.ok) {
                throw new Error(data.error || _t('tmErrorGeneric') || 'Forecast failed.');
            }

            renderForecastResults(data);
        } catch (err) {
            if (resultsDiv) {
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = `<div class="tm-empty-state">
                    <div class="tm-empty-icon">📊</div>
                    <h3>${escHtml(err.message)}</h3>
                    <p class="tm-empty-hint">Try a different stock or check that price data is available.</p>
                </div>`;
            }
        } finally {
            if (loadingDiv) loadingDiv.style.display = 'none';
            if (runBtn) runBtn.disabled = false;
        }
    }

    // ─── Render forecast results ──────────────────────────────
    function renderForecastResults(d) {
        const resultsDiv = document.getElementById('fcResults');
        if (!resultsDiv) return;

        const fmtEGP = (v) => v !== null && v !== undefined ? formatEGP(v) + ' EGP' : '—';
        const fmtPct = (v) => v !== null && v !== undefined
            ? (v >= 0 ? '+' : '') + v.toFixed(2) + '%' : '—';

        // Expected value
        const evEl = document.getElementById('fcExpectedValue');
        if (evEl) {
            evEl.textContent = fmtEGP(d.expected_value);
            evEl.className = 'fc-hero-value ' + (d.expected_return_pct >= 0 ? 'tm-pos' : 'tm-neg');
        }
        const erEl = document.getElementById('fcExpectedReturn');
        if (erEl) {
            erEl.textContent = fmtPct(d.expected_return_pct);
            erEl.className = 'fc-hero-return ' + (d.expected_return_pct >= 0 ? 'tm-pos' : 'tm-neg');
        }

        // Probability bar
        const prob = d.probability_positive;
        const probBar = document.getElementById('fcProbBar');
        const probVal = document.getElementById('fcProbValue');
        if (probBar) {
            probBar.style.width = Math.min(100, Math.max(0, prob)) + '%';
            probBar.style.background = prob >= 50 ? 'var(--accent)' : '#ef4444';
        }
        if (probVal) {
            probVal.textContent = prob + '%';
            probVal.className = 'fc-hero-value fc-prob-value ' + (prob >= 50 ? 'tm-pos' : 'tm-neg');
        }

        // Volatility / drift
        const volEl = document.getElementById('fcVolatility');
        if (volEl) volEl.textContent = d.volatility_annual_pct + '% / yr';
        const driftEl = document.getElementById('fcDriftUsed');
        if (driftEl) driftEl.textContent = 'Drift used: ' + fmtPct(d.drift_used_pct) + '/yr';

        // Range row
        setFcVal('fcWorstCase', fmtEGP(d.worst_case_value), false);
        setFcVal('fcMedian', fmtEGP(d.median_value), null);
        setFcVal('fcBestCase', fmtEGP(d.best_case_value), true);

        // Model params
        setFcText('fcDrift', fmtPct(d.drift_annual_pct) + '/yr');
        const scenAdj = d.drift_used_pct - d.drift_annual_pct;
        setFcText('fcScenarioUsed', (scenAdj >= 0 ? '+' : '') + (scenAdj * 100).toFixed(0) + 'bp (' + d.scenario + ')');
        setFcText('fcDataPoints', d.data_points + ' days');
        setFcText('fcSimCount', d.simulations_count.toLocaleString());

        // Band chart
        renderBandChart(d.band_data, d.investment_amount);

        // Histogram
        const canvas = document.getElementById('fcHistogram');
        if (canvas) renderHistogram(canvas, d.histogram, d.investment_amount);

        resultsDiv.style.display = 'block';
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function setFcVal(id, text, isPos) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = text;
        if (isPos === true) el.className = 'fc-range-value tm-pos';
        else if (isPos === false) el.className = 'fc-range-value tm-neg';
        else el.className = 'fc-range-value';
    }

    function setFcText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    // ─── Band chart (LW Charts) ───────────────────────────────
    function renderBandChart(bandData, initialAmount) {
        const container = document.getElementById('fcBandChart');
        if (!container || !bandData || bandData.length < 2) return;

        if (fcBandChart) { try { fcBandChart.remove(); } catch (e) {} fcBandChart = null; }
        container.innerHTML = '';

        if (typeof LightweightCharts === 'undefined') {
            renderBandChartCanvas(container, bandData, initialAmount);
            return;
        }

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const bgColor = isDark ? '#1e1e2e' : '#ffffff';
        const textColor = isDark ? '#e4e4e7' : '#333333';
        const gridColor = isDark ? '#3f3f46' : '#e5e7eb';

        // Simulate dates from today
        const today = new Date();
        function addWorkdays(base, days) {
            const d = new Date(base);
            let added = 0;
            while (added < days) {
                d.setDate(d.getDate() + 1);
                if (d.getDay() !== 0 && d.getDay() !== 6) added++;
            }
            return d;
        }
        function toTimestamp(d) {
            return Math.floor(d.getTime() / 1000);
        }

        const chart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 280,
            layout: { background: { color: bgColor }, textColor },
            grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
            rightPriceScale: { borderColor: gridColor },
            timeScale: { borderColor: gridColor, timeVisible: true },
        });

        const chartData = bandData.map(pt => {
            const ts = pt.day === 0 ? toTimestamp(today)
                : toTimestamp(addWorkdays(today, pt.day));
            return { day: pt.day, time: ts, worst: pt.worst, median: pt.median, best: pt.best };
        });

        // Best (green dashed)
        const bestSeries = chart.addLineSeries({ color: '#22c55e', lineWidth: 1, lineStyle: 1 });
        bestSeries.setData(chartData.map(p => ({ time: p.time, value: p.best })));

        // Median (blue solid)
        const medSeries = chart.addAreaSeries({
            topColor: 'rgba(102,126,234,0.2)', bottomColor: 'rgba(102,126,234,0.02)',
            lineColor: '#667eea', lineWidth: 2,
        });
        medSeries.setData(chartData.map(p => ({ time: p.time, value: p.median })));

        // Worst (red dashed)
        const worstSeries = chart.addLineSeries({ color: '#ef4444', lineWidth: 1, lineStyle: 1 });
        worstSeries.setData(chartData.map(p => ({ time: p.time, value: p.worst })));

        // Initial investment baseline
        const baseSeries = chart.addLineSeries({ color: '#9ca3af', lineWidth: 1, lineStyle: 2 });
        baseSeries.setData([
            { time: toTimestamp(today), value: initialAmount },
            { time: chartData[chartData.length - 1].time, value: initialAmount },
        ]);

        chart.timeScale().fitContent();
        fcBandChart = chart;

        const ro = new ResizeObserver(() => chart.applyOptions({ width: container.clientWidth }));
        ro.observe(container);
    }

    // Canvas fallback for band chart
    function renderBandChartCanvas(container, bandData, initialAmount) {
        const canvas = document.createElement('canvas');
        canvas.height = 280;
        canvas.width = container.clientWidth || 600;
        container.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        const W = canvas.width, H = canvas.height;
        const pad = { top: 15, right: 80, bottom: 25, left: 10 };

        const allVals = bandData.flatMap(p => [p.worst, p.median, p.best, initialAmount]);
        const minV = Math.min(...allVals) * 0.97;
        const maxV = Math.max(...allVals) * 1.03;
        const n = bandData.length;

        const xp = (i) => pad.left + (i / (n - 1)) * (W - pad.left - pad.right);
        const yp = (v) => H - pad.bottom - ((v - minV) / (maxV - minV)) * (H - pad.top - pad.bottom);

        // Filled band (best to worst)
        ctx.beginPath();
        bandData.forEach((p, i) => i === 0 ? ctx.moveTo(xp(i), yp(p.best)) : ctx.lineTo(xp(i), yp(p.best)));
        bandData.slice().reverse().forEach((p, i) => ctx.lineTo(xp(n - 1 - i), yp(p.worst)));
        ctx.closePath();
        ctx.fillStyle = 'rgba(102,126,234,0.08)';
        ctx.fill();

        [['#22c55e', bandData.map(p => p.best)], ['#667eea', bandData.map(p => p.median)], ['#ef4444', bandData.map(p => p.worst)]].forEach(([color, vals]) => {
            ctx.strokeStyle = color;
            ctx.lineWidth = color === '#667eea' ? 2 : 1;
            ctx.setLineDash(color === '#667eea' ? [] : [4, 3]);
            ctx.beginPath();
            vals.forEach((v, i) => i === 0 ? ctx.moveTo(xp(i), yp(v)) : ctx.lineTo(xp(i), yp(v)));
            ctx.stroke();
            ctx.setLineDash([]);
        });

        // Baseline
        ctx.strokeStyle = '#9ca3af'; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(xp(0), yp(initialAmount)); ctx.lineTo(xp(n - 1), yp(initialAmount));
        ctx.stroke(); ctx.setLineDash([]);

        // Y-axis labels
        ctx.fillStyle = '#9ca3af'; ctx.font = '10px sans-serif'; ctx.textAlign = 'right';
        for (let i = 0; i <= 4; i++) {
            const v = minV + (i / 4) * (maxV - minV);
            ctx.fillText(formatCompact(v), W - 5, yp(v) + 3);
        }
    }

    // ─── Outcome distribution histogram ──────────────────────
    function renderHistogram(canvas, hist, initialAmount) {
        if (!canvas || !hist || !hist.counts || !hist.edges) return;
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;
        const cssW = canvas.parentElement?.clientWidth || 600;
        const cssH = 200;
        canvas.width = cssW * dpr;
        canvas.height = cssH * dpr;
        canvas.style.width = cssW + 'px';
        canvas.style.height = cssH + 'px';
        ctx.scale(dpr, dpr);

        const W = cssW, H = cssH;
        const pad = { top: 12, right: 12, bottom: 28, left: 12 };
        const counts = hist.counts;
        const edges  = hist.edges;
        const n = counts.length;
        const maxCount = Math.max(...counts);
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

        ctx.clearRect(0, 0, W, H);

        const barW = (W - pad.left - pad.right) / n;
        const plotH = H - pad.top - pad.bottom;

        // Draw bars
        for (let i = 0; i < n; i++) {
            const leftEdge  = edges[i];
            const rightEdge = edges[i + 1];
            const midVal    = (leftEdge + rightEdge) / 2;
            const barH = (counts[i] / maxCount) * plotH;
            const x = pad.left + i * barW;
            const y = H - pad.bottom - barH;

            ctx.fillStyle = midVal >= initialAmount ? 'rgba(34,197,94,0.75)' : 'rgba(239,68,68,0.75)';
            ctx.fillRect(x + 1, y, barW - 2, barH);
        }

        // Vertical line at initial investment
        const invPct = (initialAmount - edges[0]) / (edges[edges.length - 1] - edges[0]);
        const invX = pad.left + invPct * (W - pad.left - pad.right);
        ctx.strokeStyle = '#9ca3af';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 3]);
        ctx.beginPath(); ctx.moveTo(invX, pad.top); ctx.lineTo(invX, H - pad.bottom); ctx.stroke();
        ctx.setLineDash([]);

        // "Invested" label
        ctx.fillStyle = '#9ca3af'; ctx.font = '10px sans-serif'; ctx.textAlign = 'center';
        ctx.fillText('Invested', invX, pad.top + 8);

        // X-axis labels (min / mid / max)
        ctx.textAlign = 'left';
        ctx.fillText(formatCompact(edges[0]), pad.left, H - 6);
        ctx.textAlign = 'center';
        ctx.fillText(formatCompact(edges[Math.floor(n / 2)]), pad.left + (W - pad.left - pad.right) / 2, H - 6);
        ctx.textAlign = 'right';
        ctx.fillText(formatCompact(edges[n]), W - pad.right, H - 6);
    }

})();
