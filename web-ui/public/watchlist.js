/**
 * Xmore — Frontend Watchlist Module
 * Stock search, add/remove, watchlist display with predictions.
 */

// ============================================
// STATE
// ============================================
let allStocks = [];
let watchlistItems = [];
let watchlistSymbols = new Set();
let searchVisible = false;

// ============================================
// BILINGUAL TEXT
// ============================================
const wlText = {
    en: {
        wl_title: '⭐ My Watchlist',
        wl_stocks_count: '{n} stocks',
        wl_add_stock: '+ Add Stock',
        wl_search_placeholder: 'Search by name, symbol, or sector...',
        wl_follow: '+ Follow',
        wl_following: '✓ Following',
        wl_remove: 'Remove',
        wl_empty: 'No stocks in your watchlist yet. Search above to add some!',
        wl_login_required: 'Login to create your watchlist',
        wl_max_reached: 'Watchlist limit reached',
        wl_no_prediction: 'No prediction yet',
        signal_bullish: 'Bullish',
        signal_bearish: 'Bearish',
        signal_neutral: 'Neutral',
        signal_up: 'UP',
        signal_down: 'DOWN',
        signal_hold: 'HOLD',
        confidence_label: 'confidence',
        wl_consensus: 'Consensus',
        wl_prediction: 'Latest Prediction',
    },
    ar: {
        wl_title: '⭐ قائمة المتابعة',
        wl_stocks_count: '{n} أسهم',
        wl_add_stock: '+ إضافة سهم',
        wl_search_placeholder: 'ابحث بالاسم أو الرمز أو القطاع...',
        wl_follow: '+ متابعة',
        wl_following: '✓ متابَع',
        wl_remove: 'إزالة',
        wl_empty: 'لا توجد أسهم في قائمتك بعد. ابحث أعلاه لإضافة أسهم!',
        wl_login_required: 'سجّل دخولك لإنشاء قائمة متابعة',
        wl_max_reached: 'تم الوصول للحد الأقصى',
        wl_no_prediction: 'لا يوجد تنبؤ بعد',
        signal_bullish: 'صاعد',
        signal_bearish: 'هابط',
        signal_neutral: 'محايد',
        signal_up: 'صاعد',
        signal_down: 'هابط',
        signal_hold: 'محايد',
        confidence_label: 'ثقة',
        wl_consensus: 'الإجماع',
        wl_prediction: 'آخر تنبؤ',
    }
};

function wt(key) {
    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'en';
    return (wlText[lang] && wlText[lang][key]) || wlText.en[key] || key;
}

// escapeHtml() is defined globally in app.js

// ============================================
// LOAD STOCKS (for search)
// ============================================
async function loadAllStocks() {
    try {
        const res = await fetch('/api/stocks');
        const data = await res.json();
        allStocks = data.stocks || [];
    } catch (err) {
        console.error('Failed to load stocks:', err);
        allStocks = [];
    }
}

// ============================================
// SEARCH LOGIC (client-side)
// ============================================
function searchStocks(query) {
    if (!query || query.length < 1) return allStocks;

    const q = query.toLowerCase().trim();

    return allStocks.filter(stock => {
        return (
            stock.symbol.toLowerCase().includes(q) ||
            stock.name_en.toLowerCase().includes(q) ||
            stock.name_ar.includes(q) ||
            (stock.sector_en && stock.sector_en.toLowerCase().includes(q)) ||
            (stock.sector_ar && stock.sector_ar.includes(q))
        );
    }).sort((a, b) => {
        // Exact symbol match first
        const aExact = a.symbol.toLowerCase().startsWith(q) ? 0 : 1;
        const bExact = b.symbol.toLowerCase().startsWith(q) ? 0 : 1;
        return aExact - bExact;
    });
}

function renderSearchResults(stocks) {
    const container = document.getElementById('wlSearchResults');
    if (!container) return;

    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'en';

    if (stocks.length === 0) {
        container.innerHTML = '<div class="wl-search-item"><span style="color:var(--text-muted)">No results</span></div>';
        container.classList.add('active');
        return;
    }

    container.innerHTML = stocks.map(stock => {
        const name = lang === 'ar' ? stock.name_ar : stock.name_en;
        const sector = lang === 'ar' ? (stock.sector_ar || '') : (stock.sector_en || '');
        const isFollowing = watchlistSymbols.has(stock.symbol);
        const btnClass = isFollowing ? 'following' : 'follow';
        const btnText = isFollowing ? wt('wl_following') : wt('wl_follow');

        return `
      <div class="wl-search-item">
        <div class="wl-search-item-info">
          <span class="wl-search-symbol">${escapeHtml(stock.symbol)}</span>
          <span class="wl-search-name">${escapeHtml(name)}</span>
          <span class="wl-search-sector">${escapeHtml(sector)}</span>
        </div>
        <button class="wl-follow-btn ${btnClass}"
                data-stock-id="${stock.id}"
                ${isFollowing ? 'disabled' : ''}
                onclick="addToWatchlist(${stock.id}, this)">
          ${btnText}
        </button>
      </div>
    `;
    }).join('');

    container.classList.add('active');
}

// ============================================
// WATCHLIST API
// ============================================
async function loadWatchlist() {
    if (!currentUser) {
        renderEmptyWatchlist(true);
        return;
    }

    try {
        const res = await fetch('/api/watchlist', { credentials: 'include' });
        if (!res.ok) {
            if (res.status === 401) {
                renderEmptyWatchlist(true);
                return;
            }
            throw new Error('Failed to load watchlist');
        }

        const data = await res.json();
        watchlistItems = data.watchlist || [];
        watchlistSymbols = new Set(watchlistItems.map(w => w.symbol));
        renderWatchlist();
    } catch (err) {
        console.error('Watchlist load error:', err);
        renderEmptyWatchlist(false);
    }
}

async function addToWatchlist(stockId, buttonEl) {
    if (!currentUser) {
        showAuthModal('login');
        return;
    }

    try {
        buttonEl.disabled = true;
        const res = await fetch(`/api/watchlist/${stockId}`, {
            method: 'POST',
            credentials: 'include',
        });

        const data = await res.json();

        if (res.ok) {
            buttonEl.className = 'wl-follow-btn following';
            buttonEl.textContent = wt('wl_following');
            // Invalidate watchlist cache so other tabs re-filter
            if (typeof resetWatchlistCache === 'function') resetWatchlistCache();
            // Reload watchlist to get latest data
            await loadWatchlist();
            // Update search results to reflect new state
            const searchInput = document.getElementById('wlSearchInput');
            if (searchInput && searchInput.value) {
                const results = searchStocks(searchInput.value);
                renderSearchResults(results);
            }
        } else {
            buttonEl.disabled = false;
        }
    } catch (err) {
        console.error('Add to watchlist error:', err);
        buttonEl.disabled = false;
    }
}

async function removeFromWatchlist(stockId) {
    try {
        const res = await fetch(`/api/watchlist/${stockId}`, {
            method: 'DELETE',
            credentials: 'include',
        });

        if (res.ok) {
            // Invalidate watchlist cache so other tabs re-filter
            if (typeof resetWatchlistCache === 'function') resetWatchlistCache();
            await loadWatchlist();
            // Update search results if visible
            const searchInput = document.getElementById('wlSearchInput');
            if (searchInput && searchInput.value) {
                const results = searchStocks(searchInput.value);
                renderSearchResults(results);
            }
        }
    } catch (err) {
        console.error('Remove from watchlist error:', err);
    }
}

// ============================================
// RENDER
// ============================================
function renderEmptyWatchlist(loginRequired) {
    const container = document.getElementById('watchlistCards');
    const titleEl = document.getElementById('wlTitle');
    if (!container) return;

    if (titleEl) titleEl.textContent = wt('wl_title');

    if (loginRequired) {
        container.innerHTML = `<p class="no-data">${wt('wl_login_required')}</p>`;
        return;
    }
    container.innerHTML = `
      <p class="no-data">${wt('wl_empty')}</p>
      <button class="wl-follow-btn follow" onclick="document.getElementById('wlAddBtn')?.click()">${wt('wl_add_stock')}</button>
    `;
}

function renderWatchlist() {
    const container = document.getElementById('watchlistCards');
    const titleEl = document.getElementById('wlTitle');
    if (!container) return;

    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'en';
    const countText = wt('wl_stocks_count').replace('{n}', watchlistItems.length);
    if (titleEl) titleEl.textContent = `${wt('wl_title')} (${countText})`;

    if (watchlistItems.length === 0) {
        container.innerHTML = `<p class="no-data">${wt('wl_empty')}</p>`;
        return;
    }

    container.innerHTML = watchlistItems.map(item => {
        const name = lang === 'ar' ? item.name_ar : item.name_en;
        const sector = lang === 'ar' ? (item.sector_ar || '') : (item.sector_en || '');

        // Signal badge
        let signalHtml = '';
        const signal = item.consensus_signal || item.latest_prediction;
        const confidence = item.latest_confidence;

        if (signal) {
            const signalInfo = getSignalInfo(signal);
            signalHtml = `
        <div class="wl-card-signal">
          <span class="wl-signal-badge" style="background:${signalInfo.bg};color:${signalInfo.color};">
            ${signalInfo.icon} ${signalInfo.label}
          </span>
          ${confidence ? `<span class="wl-confidence">${Math.round(confidence)}% ${wt('confidence_label')}</span>` : ''}
        </div>
      `;
        } else {
            signalHtml = `<p class="wl-no-data">${wt('wl_no_prediction')}</p>`;
        }

        return `
      <div class="wl-card">
        <button class="wl-remove-btn" onclick="removeFromWatchlist(${item.id})" title="${wt('wl_remove')}" aria-label="${escapeHtml(wt('wl_remove'))}">✕</button>
        <div class="wl-card-header">
          <div class="wl-card-stock">
            <strong>${escapeHtml(item.symbol)}</strong>
            <span class="company-name">${escapeHtml(name)}</span>
          </div>
          <span class="wl-card-sector">${escapeHtml(sector)}</span>
        </div>
        ${signalHtml}
      </div>
    `;
    }).join('');
}

function getSignalInfo(signal) {
    const s = (signal || '').toUpperCase();
    if (s === 'UP' || s === 'BULLISH' || s === 'STRONG_BUY' || s === 'BUY') {
        return {
            icon: '▲',
            label: wt('signal_bullish'),
            bg: 'rgba(34, 197, 94, 0.15)',
            color: '#16a34a',
        };
    }
    if (s === 'DOWN' || s === 'BEARISH' || s === 'SELL' || s === 'STRONG_SELL') {
        return {
            icon: '▼',
            label: wt('signal_bearish'),
            bg: 'rgba(239, 68, 68, 0.15)',
            color: '#dc2626',
        };
    }
    return {
        icon: '─',
        label: wt('signal_neutral'),
        bg: 'rgba(107, 114, 128, 0.15)',
        color: '#6b7280',
    };
}

// ============================================
// WATCHLIST LANGUAGE UPDATE
// ============================================
function updateWatchlistLanguage() {
    const addBtn = document.getElementById('wlAddBtn');
    const searchInput = document.getElementById('wlSearchInput');

    if (addBtn) addBtn.textContent = wt('wl_add_stock');
    if (searchInput) searchInput.placeholder = wt('wl_search_placeholder');

    // Re-render if data loaded
    if (watchlistItems.length > 0) {
        renderWatchlist();
    } else if (currentUser) {
        renderEmptyWatchlist(false);
    } else {
        renderEmptyWatchlist(true);
    }
}

// ============================================
// INIT
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    const addBtn = document.getElementById('wlAddBtn');
    const searchBox = document.getElementById('wlSearchBox');
    const searchInput = document.getElementById('wlSearchInput');
    const searchResults = document.getElementById('wlSearchResults');

    // Load all stocks for search
    loadAllStocks();

    // Toggle search box
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            if (!currentUser) {
                showAuthModal('login');
                return;
            }
            searchVisible = !searchVisible;
            if (searchBox) {
                searchBox.style.display = searchVisible ? 'block' : 'none';
                if (searchVisible) {
                    searchInput.focus();
                    // Show all stocks initially
                    renderSearchResults(allStocks);
                } else {
                    searchResults.classList.remove('active');
                }
            }
        });
    }

    // Search input handler
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const query = searchInput.value;
            const results = searchStocks(query);
            renderSearchResults(results);
        });

        // Close search dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (searchBox && !searchBox.contains(e.target) && e.target !== addBtn) {
                searchResults.classList.remove('active');
            }
        });

        // Re-open on focus
        searchInput.addEventListener('focus', () => {
            const query = searchInput.value;
            const results = searchStocks(query);
            renderSearchResults(results);
        });
    }
});
