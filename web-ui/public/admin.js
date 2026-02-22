const API_BASE = '/api/admin';
const SECRET_KEY = 'admin_secret';
const LANG_KEY = 'lang';
const THEME_KEY = 'theme';
const SECRET_COOKIE_NAME = 'xmore_admin_secret';

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const reportRows = document.getElementById('reportRows');
const adminSecretInput = document.getElementById('adminSecretInput');
const saveSecretBtn = document.getElementById('saveSecretBtn');
const secretStatus = document.getElementById('secretStatus');
const auditHealth = document.getElementById('auditHealth');
const agentHealth = document.getElementById('agentHealth');

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getSecret() {
    return localStorage.getItem(SECRET_KEY) || '';
}

function setSecret(secret) {
    const normalized = String(secret || '').trim();
    localStorage.setItem(SECRET_KEY, normalized);
    adminSecretInput.value = normalized;
    document.cookie = `${SECRET_COOKIE_NAME}=${encodeURIComponent(normalized)}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Lax`;
}

function apiHeaders(extra = {}) {
    const headers = { ...extra };
    const secret = getSecret();
    if (secret) headers['x-admin-secret'] = secret;
    return headers;
}

function applyThemeAndLanguage() {
    const theme = localStorage.getItem(THEME_KEY) ||
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);

    const lang = localStorage.getItem(LANG_KEY) || 'en';
    const isArabic = lang === 'ar';
    document.documentElement.lang = isArabic ? 'ar' : 'en';
    document.documentElement.dir = isArabic ? 'rtl' : 'ltr';
    document.body.classList.toggle('rtl', isArabic);
}

function formatDate(isoDate) {
    if (!isoDate) return '-';
    const d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return escapeHtml(isoDate);
    return d.toLocaleString();
}

function setUploadMessage(message, isError = false) {
    uploadStatus.className = isError ? 'admin-upload-status error-message' : 'admin-upload-status no-data';
    uploadStatus.textContent = message;
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
        credentials: 'include',
        ...options,
        headers: apiHeaders(options.headers || {})
    });

    if (!response.ok) {
        let details = '';
        try {
            const data = await response.json();
            details = data.error || data.details || '';
        } catch (_err) {
            details = '';
        }
        throw new Error(details || `Request failed (${response.status})`);
    }

    return response.json();
}

function renderSystemHealth(data) {
    const audit = data.audit_log;
    const agent = data.agent_performance_daily;

    auditHealth.innerHTML = audit ? `
        <p><strong>Table:</strong> ${escapeHtml(audit.table_name || '-')}</p>
        <p><strong>Field:</strong> ${escapeHtml(audit.field_changed || '-')}</p>
        <p><strong>At:</strong> ${escapeHtml(formatDate(audit.changed_at))}</p>
    ` : '<p class="no-data">No audit data available.</p>';

    agentHealth.innerHTML = agent ? `
        <p><strong>Date:</strong> ${escapeHtml(agent.snapshot_date || '-')}</p>
        <p><strong>Agent:</strong> ${escapeHtml(agent.agent_name || '-')}</p>
        <p><strong>30D:</strong> ${escapeHtml(String(agent.win_rate_30d ?? '-'))}% (${escapeHtml(String(agent.predictions_30d ?? 0))} preds)</p>
        <p><strong>90D:</strong> ${escapeHtml(String(agent.win_rate_90d ?? '-'))}% (${escapeHtml(String(agent.predictions_90d ?? 0))} preds)</p>
    ` : '<p class="no-data">No agent daily data available.</p>';
}

async function loadSystemHealth() {
    try {
        const data = await fetchJson(`${API_BASE}/system-health`);
        renderSystemHealth(data);
    } catch (err) {
        auditHealth.innerHTML = `<p class="error-message">${escapeHtml(err.message)}</p>`;
        agentHealth.innerHTML = `<p class="error-message">${escapeHtml(err.message)}</p>`;
    }
}

function renderReports(reports) {
    if (!reports || reports.length === 0) {
        reportRows.innerHTML = '<tr><td colspan="5" class="no-data">No reports yet.</td></tr>';
        return;
    }

    reportRows.innerHTML = reports.map(report => {
        const status = report.status || 'Pending';
        const statusClass = status === 'Processed' ? 'admin-status-processed' : 'admin-status-pending';
        return `
            <tr>
                <td>${escapeHtml(report.filename || '-')}</td>
                <td>${escapeHtml(formatDate(report.upload_date))}</td>
                <td>${escapeHtml(report.language || '-')}</td>
                <td><span class="admin-status-badge ${statusClass}">${escapeHtml(status)}</span></td>
                <td>${escapeHtml(report.summary || '-')}</td>
            </tr>
        `;
    }).join('');
}

async function loadReports() {
    try {
        const data = await fetchJson(`${API_BASE}/reports`);
        renderReports(data.reports || []);
    } catch (err) {
        reportRows.innerHTML = `<tr><td colspan="5" class="error-message">${escapeHtml(err.message)}</td></tr>`;
    }
}

const ALLOWED_UPLOAD_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif'];

async function uploadReport(file) {
    if (!file) return;
    const fileName = file.name || '';
    const ext = fileName.toLowerCase().slice(fileName.lastIndexOf('.'));
    if (!ALLOWED_UPLOAD_EXTENSIONS.includes(ext)) {
        setUploadMessage('Only PDF and image files (PNG, JPG, WEBP, BMP, TIFF) are allowed.', true);
        return;
    }

    setUploadMessage(`Uploading ${fileName}...`);
    const body = new FormData();
    body.append('report', file);

    try {
        const result = await fetchJson(`${API_BASE}/reports/upload`, {
            method: 'POST',
            body
        });
        setUploadMessage(`Processed: ${result.filename} (${result.language})`);
        await Promise.all([loadSystemHealth(), loadReports()]);
    } catch (err) {
        setUploadMessage(err.message, true);
    }
}

function bindDropZone() {
    const openPicker = () => fileInput.click();

    dropZone.addEventListener('click', openPicker);
    dropZone.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            openPicker();
        }
    });

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files && event.target.files[0];
        uploadReport(file);
        fileInput.value = '';
    });

    ['dragenter', 'dragover'].forEach(type => {
        dropZone.addEventListener(type, (event) => {
            event.preventDefault();
            event.stopPropagation();
            dropZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(type => {
        dropZone.addEventListener(type, (event) => {
            event.preventDefault();
            event.stopPropagation();
            dropZone.classList.remove('drag-over');
        });
    });

    dropZone.addEventListener('drop', (event) => {
        const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
        uploadReport(file);
    });
}

function bindSecretInput() {
    const save = () => {
        setSecret(adminSecretInput.value);
        secretStatus.textContent = getSecret() ? 'Secret saved in browser storage.' : 'Secret cleared.';
        loadSystemHealth();
        loadReports();
        loadSources();
    };

    adminSecretInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') save();
    });
    saveSecretBtn.addEventListener('click', save);
}

// ============================================================
// CUSTOM NEWS SOURCES
// ============================================================

const sourceRows = document.getElementById('sourceRows');
const sourceStatus = document.getElementById('sourceStatus');
const addSourceBtn = document.getElementById('addSourceBtn');
const addSourcePanel = document.getElementById('addSourcePanel');
const saveSrcBtn = document.getElementById('saveSrcBtn');
const cancelSrcBtn = document.getElementById('cancelSrcBtn');
const srcType = document.getElementById('srcType');
const srcName = document.getElementById('srcName');
const srcUrl = document.getElementById('srcUrl');
const srcBotToken = document.getElementById('srcBotToken');
const srcChatId = document.getElementById('srcChatId');
const srcBotRow = document.getElementById('srcBotRow');
const srcChatRow = document.getElementById('srcChatRow');
const srcUrlRow = document.getElementById('srcUrlRow');
const srcLang = document.getElementById('srcLang');
const srcInterval = document.getElementById('srcInterval');

const TYPE_LABELS = {
    url: 'URL',
    rss: 'RSS',
    telegram_public: 'Telegram Public',
    telegram_bot: 'Telegram Bot',
    manual: 'Manual',
};

function setSourceStatus(msg, isError = false) {
    sourceStatus.className = isError ? 'admin-upload-status error-message' : 'admin-upload-status no-data';
    sourceStatus.textContent = msg;
}

function renderSources(sources) {
    if (!sources || sources.length === 0) {
        sourceRows.innerHTML = '<tr><td colspan="8" class="no-data">No custom sources yet. Click "Add Source" to get started.</td></tr>';
        return;
    }
    sourceRows.innerHTML = sources.map(s => {
        const activeBadge = s.is_active
            ? '<span class="admin-status-badge admin-status-processed">Active</span>'
            : '<span class="admin-status-badge admin-status-pending">Paused</span>';
        const lastFetched = s.last_fetched_at ? formatDate(s.last_fetched_at) : 'Never';
        const urlDisplay = s.source_url ? `<span title="${escapeHtml(s.source_url)}">${escapeHtml(s.source_url.slice(0, 40))}${s.source_url.length > 40 ? '…' : ''}</span>` : '—';
        const toggleLabel = s.is_active ? 'Pause' : 'Resume';
        return `<tr>
            <td>${escapeHtml(s.name)}</td>
            <td>${escapeHtml(TYPE_LABELS[s.source_type] || s.source_type)}</td>
            <td>${urlDisplay}</td>
            <td>${escapeHtml(s.language || 'auto')}</td>
            <td>${activeBadge}</td>
            <td>${escapeHtml(lastFetched)}</td>
            <td>${escapeHtml(String(s.article_count || 0))}</td>
            <td style="white-space:nowrap;">
                <button class="admin-btn" onclick="fetchSourceNow(${s.id}, this)" ${s.source_type === 'manual' ? 'disabled' : ''}>Fetch Now</button>
                <button class="admin-btn" onclick="toggleSource(${s.id}, ${!s.is_active})">${escapeHtml(toggleLabel)}</button>
                <button class="admin-btn admin-btn-danger" onclick="deleteSource(${s.id})">Delete</button>
            </td>
        </tr>`;
    }).join('');
}

async function loadSources() {
    try {
        const data = await fetchJson(`${API_BASE}/sources`);
        renderSources(data.sources || []);
    } catch (err) {
        sourceRows.innerHTML = `<tr><td colspan="8" class="error-message">${escapeHtml(err.message)}</td></tr>`;
    }
}

async function saveSource() {
    const name = (srcName.value || '').trim();
    const type = srcType.value;
    const url = (srcUrl.value || '').trim();
    const botToken = (srcBotToken.value || '').trim();
    const chatId = (srcChatId.value || '').trim();
    const lang = srcLang.value;
    const interval = srcInterval.value;

    if (!name) return setSourceStatus('Source name is required.', true);
    if (['url', 'rss', 'telegram_public'].includes(type) && !url) {
        return setSourceStatus('URL / channel is required for this source type.', true);
    }
    if (type === 'telegram_bot' && (!botToken || !chatId)) {
        return setSourceStatus('Bot token and Chat ID are required for Telegram Bot sources.', true);
    }

    setSourceStatus('Saving…');
    try {
        await fetchJson(`${API_BASE}/sources`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name, source_type: type, source_url: url || null,
                bot_token: botToken || null, chat_id: chatId || null,
                language: lang, fetch_interval_hours: interval,
            }),
        });
        setSourceStatus(`Source "${name}" added.`);
        addSourcePanel.style.display = 'none';
        srcName.value = '';
        srcUrl.value = '';
        srcBotToken.value = '';
        srcChatId.value = '';
        await loadSources();
    } catch (err) {
        setSourceStatus(err.message, true);
    }
}

async function toggleSource(id, active) {
    try {
        await fetchJson(`${API_BASE}/sources/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: active }),
        });
        await loadSources();
    } catch (err) {
        setSourceStatus(err.message, true);
    }
}

async function deleteSource(id) {
    if (!confirm('Delete this source? All associated articles will also be removed.')) return;
    try {
        await fetchJson(`${API_BASE}/sources/${id}`, { method: 'DELETE' });
        await loadSources();
    } catch (err) {
        setSourceStatus(err.message, true);
    }
}

async function fetchSourceNow(id, btn) {
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Fetching…';
    }
    setSourceStatus('Fetching…');
    try {
        const result = await fetchJson(`${API_BASE}/sources/${id}/fetch`, { method: 'POST' });
        const msg = result.ok
            ? `Fetched ${result.articles_fetched} items, ${result.articles_new} new for "${result.source_name}"`
            : `Error: ${result.error || 'Unknown error'}`;
        setSourceStatus(msg, !result.ok);
        await loadSources();
    } catch (err) {
        setSourceStatus(err.message, true);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Fetch Now'; }
    }
}

function updateSourceFormFields() {
    const type = srcType.value;
    const needsUrl = ['url', 'rss', 'telegram_public'].includes(type);
    const needsBot = type === 'telegram_bot';
    srcUrlRow.style.display = (needsUrl || needsBot) ? '' : 'none';
    srcBotRow.style.display = needsBot ? '' : 'none';
    srcChatRow.style.display = needsBot ? '' : 'none';
    srcUrl.placeholder = type === 'telegram_public' ? 't.me/channelname' : 'https://…';
}

function bindSourceForm() {
    addSourceBtn.addEventListener('click', () => {
        const isVisible = addSourcePanel.style.display !== 'none';
        addSourcePanel.style.display = isVisible ? 'none' : '';
    });
    cancelSrcBtn.addEventListener('click', () => { addSourcePanel.style.display = 'none'; });
    saveSrcBtn.addEventListener('click', saveSource);
    srcType.addEventListener('change', updateSourceFormFields);
    updateSourceFormFields();
}

// ============================================================
// WHATSAPP / MANUAL FEED
// ============================================================

const waDropZone = document.getElementById('waDropZone');
const waFileInput = document.getElementById('waFileInput');
const waText = document.getElementById('waText');
const waSourceName = document.getElementById('waSourceName');
const waSubmitBtn = document.getElementById('waSubmitBtn');
const waStatus = document.getElementById('waStatus');
const waFileName = document.getElementById('waFileName');

let waSelectedFile = null;

function setWaStatus(msg, isError = false) {
    waStatus.className = isError ? 'admin-upload-status error-message' : 'admin-upload-status no-data';
    waStatus.textContent = msg;
}

async function submitWhatsApp() {
    const text = (waText.value || '').trim();
    const sourceName = (waSourceName.value || 'Telegram').trim();

    if (!text && !waSelectedFile) {
        return setWaStatus('Please paste text or select a file.', true);
    }

    setWaStatus('Submitting to pipeline…');
    waSubmitBtn.disabled = true;

    const body = new FormData();
    body.append('text', text);
    body.append('source_name', sourceName);
    if (waSelectedFile) body.append('file', waSelectedFile);

    try {
        const result = await fetchJson(`${API_BASE}/sources/manual`, { method: 'POST', body });
        if (result.ok) {
            const sym = (result.symbols_matched || []).join(', ') || 'general market';
            setWaStatus(`Stored and matched to: ${sym} (${result.language || 'auto'}, ${result.sentiment || '—'})`);
            waText.value = '';
            waSelectedFile = null;
            waFileName.textContent = '';
            await loadSources();
        } else {
            setWaStatus(result.error || 'Failed to process content.', true);
        }
    } catch (err) {
        setWaStatus(err.message, true);
    } finally {
        waSubmitBtn.disabled = false;
    }
}

function bindWaDropZone() {
    const openPicker = () => waFileInput.click();

    waDropZone.addEventListener('click', openPicker);
    waDropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPicker(); }
    });

    waFileInput.addEventListener('change', (e) => {
        waSelectedFile = e.target.files && e.target.files[0];
        waFileName.textContent = waSelectedFile ? waSelectedFile.name : '';
        waFileInput.value = '';
    });

    ['dragenter', 'dragover'].forEach(t => {
        waDropZone.addEventListener(t, (e) => { e.preventDefault(); e.stopPropagation(); waDropZone.classList.add('drag-over'); });
    });
    ['dragleave', 'drop'].forEach(t => {
        waDropZone.addEventListener(t, (e) => { e.preventDefault(); e.stopPropagation(); waDropZone.classList.remove('drag-over'); });
    });
    waDropZone.addEventListener('drop', (e) => {
        waSelectedFile = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
        waFileName.textContent = waSelectedFile ? waSelectedFile.name : '';
    });

    waSubmitBtn.addEventListener('click', submitWhatsApp);
}

// ============================================================
// INFO BANNERS (dismissible hints for new admins)
// ============================================================

const DISMISSED_HINTS_KEY = 'admin_dismissed_hints';

function loadDismissedHints() {
    try { return new Set(JSON.parse(localStorage.getItem(DISMISSED_HINTS_KEY) || '[]')); }
    catch (_) { return new Set(); }
}

function initInfoBanners() {
    const dismissed = loadDismissedHints();
    document.querySelectorAll('.admin-info-banner').forEach(banner => {
        const key = banner.dataset.hint;
        if (key && dismissed.has(key)) banner.classList.add('dismissed');
    });

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.admin-info-dismiss');
        if (!btn) return;
        const key = btn.dataset.dismiss;
        const banner = btn.closest('.admin-info-banner');
        if (banner) banner.classList.add('dismissed');
        if (key) {
            const set = loadDismissedHints();
            set.add(key);
            localStorage.setItem(DISMISSED_HINTS_KEY, JSON.stringify([...set]));
        }
    });
}

// ============================================================
// TAB SHOW / HIDE
// ============================================================

const TAB_DEFS = [
    { id: 'tab-health',   label: 'System Health' },
    { id: 'tab-kb',       label: 'Knowledge Base' },
    { id: 'tab-reports',  label: 'Reports' },
    { id: 'tab-sources',  label: 'News Sources' },
    { id: 'tab-telegram', label: 'Telegram Feed' },
];

const HIDDEN_TABS_KEY = 'admin_hidden_tabs';
const ACTIVE_TAB_KEY  = 'admin_active_tab';

function loadHiddenTabs() {
    try { return new Set(JSON.parse(localStorage.getItem(HIDDEN_TABS_KEY) || '[]')); }
    catch (_) { return new Set(); }
}

function saveHiddenTabs(hiddenSet) {
    localStorage.setItem(HIDDEN_TABS_KEY, JSON.stringify([...hiddenSet]));
}

function applyTabVisibility(hiddenSet) {
    TAB_DEFS.forEach(({ id }) => {
        const btn = document.querySelector(`[data-tab="${id}"]`);
        if (btn) btn.dataset.hidden = hiddenSet.has(id) ? 'true' : 'false';
    });
}

function switchTab(tabId) {
    document.querySelectorAll('.admin-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
        btn.setAttribute('aria-selected', btn.dataset.tab === tabId ? 'true' : 'false');
    });
    document.querySelectorAll('.admin-tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === tabId);
    });
    localStorage.setItem(ACTIVE_TAB_KEY, tabId);
}

function firstVisibleTab(hiddenSet) {
    for (const { id } of TAB_DEFS) {
        if (!hiddenSet.has(id)) return id;
    }
    return TAB_DEFS[0].id;
}

function buildTabCheckboxes(hiddenSet) {
    const container = document.getElementById('tabCheckboxes');
    if (!container) return;
    container.innerHTML = TAB_DEFS.map(({ id, label }) => {
        const checked = !hiddenSet.has(id) ? 'checked' : '';
        return `<label>
            <input type="checkbox" data-tab-toggle="${escapeHtml(id)}" ${checked}>
            ${escapeHtml(label)}
        </label>`;
    }).join('');

    container.querySelectorAll('input[data-tab-toggle]').forEach(cb => {
        cb.addEventListener('change', () => {
            const hidden = loadHiddenTabs();
            if (cb.checked) { hidden.delete(cb.dataset.tabToggle); }
            else            { hidden.add(cb.dataset.tabToggle); }

            // Keep at least one tab visible
            const allHidden = TAB_DEFS.every(({ id }) => hidden.has(id));
            if (allHidden) { hidden.delete(cb.dataset.tabToggle); cb.checked = true; }

            saveHiddenTabs(hidden);
            applyTabVisibility(hidden);

            // If the active tab just got hidden, switch to first visible
            const activeId = localStorage.getItem(ACTIVE_TAB_KEY) || TAB_DEFS[0].id;
            if (hidden.has(activeId)) switchTab(firstVisibleTab(hidden));
        });
    });
}

function bindTabBar() {
    document.getElementById('adminTabList').addEventListener('click', (e) => {
        const btn = e.target.closest('.admin-tab-btn');
        if (btn && btn.dataset.tab) switchTab(btn.dataset.tab);
    });

    const configBtn   = document.getElementById('tabConfigBtn');
    const configPanel = document.getElementById('tabConfigPanel');

    configBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = !configPanel.hidden;
        configPanel.hidden = isOpen;
        configBtn.setAttribute('aria-expanded', String(!isOpen));
    });

    document.addEventListener('click', (e) => {
        if (!configPanel.hidden && !configPanel.contains(e.target) && e.target !== configBtn) {
            configPanel.hidden = true;
            configBtn.setAttribute('aria-expanded', 'false');
        }
    });
}

function initTabs() {
    const hidden = loadHiddenTabs();
    applyTabVisibility(hidden);
    buildTabCheckboxes(hidden);
    bindTabBar();
    const saved  = localStorage.getItem(ACTIVE_TAB_KEY);
    const target = (saved && !hidden.has(saved)) ? saved : firstVisibleTab(hidden);
    switchTab(target);
}

// ============================================================
// BOOTSTRAP
// ============================================================

async function bootstrap() {
    applyThemeAndLanguage();
    adminSecretInput.value = getSecret();
    initInfoBanners();
    initTabs();
    bindDropZone();
    bindSecretInput();
    bindSourceForm();
    bindWaDropZone();
    if (getSecret()) {
        await Promise.all([loadSystemHealth(), loadReports(), loadSources()]);
    } else {
        auditHealth.innerHTML = '<p class="no-data">Enter admin secret above to load data.</p>';
        agentHealth.innerHTML = '<p class="no-data">Enter admin secret above to load data.</p>';
        reportRows.innerHTML = '<tr><td colspan="5" class="no-data">Enter admin secret above to load data.</td></tr>';
        sourceRows.innerHTML = '<tr><td colspan="8" class="no-data">Enter admin secret above to load data.</td></tr>';
    }
}

bootstrap();
