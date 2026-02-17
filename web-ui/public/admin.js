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
    };

    adminSecretInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') save();
    });
    saveSecretBtn.addEventListener('click', save);
}

async function bootstrap() {
    applyThemeAndLanguage();
    adminSecretInput.value = getSecret();
    bindDropZone();
    bindSecretInput();
    await Promise.all([loadSystemHealth(), loadReports()]);
}

bootstrap();
