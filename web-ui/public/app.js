// API Base URL
const API_URL = '/api';

// EGX Company Name Mapping for search
const COMPANY_NAMES = {
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
    loadStats();
    loadPredictions();
    loadPerformance();
    loadPrices();
});

// Refresh all data
function refreshData() {
    loadStats();
    loadPredictions();
    loadPerformance();
    loadPrices();
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

// Load predictions
async function loadPredictions() {
    try {
        const response = await fetch(`${API_URL}/predictions`);
        const data = await response.json();

        const container = document.getElementById('predictions');

        if (data.length === 0) {
            container.innerHTML = '<p class="loading">No predictions yet. Run python run_agents.py</p>';
            return;
        }

        let html = '<table id="predictionsTable"><thead><tr><th>Stock</th><th>Agent</th><th>Prediction</th><th>Date</th></tr></thead><tbody>';

        data.forEach(pred => {
            const companyName = getCompanyName(pred.symbol);
            const searchText = `${pred.symbol} ${companyName}`.toLowerCase();
            html += `
                <tr data-search="${searchText}">
                    <td><strong>${pred.symbol}</strong><br><small style="color:#666">${companyName}</small></td>
                    <td>${pred.agent_name}</td>
                    <td><span class="prediction-${pred.prediction.toLowerCase()}">${pred.prediction}</span></td>
                    <td>${formatDate(pred.prediction_date)}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading predictions:', error);
        document.getElementById('predictions').innerHTML = '<p class="loading">Error loading predictions</p>';
    }
}

// Filter predictions based on search input (by stock symbol or company name)
function filterPredictions() {
    const searchValue = document.getElementById('predictionsSearch').value.toLowerCase().trim();
    const table = document.getElementById('predictionsTable');

    if (!table) return;

    const rows = table.querySelectorAll('tbody tr');

    rows.forEach(row => {
        const searchText = row.getAttribute('data-search') || '';

        if (searchText.includes(searchValue)) {
            row.classList.remove('hidden-row');
        } else {
            row.classList.add('hidden-row');
        }
    });
}

// Load performance
async function loadPerformance() {
    try {
        const response = await fetch(`${API_URL}/performance`);
        const data = await response.json();

        const container = document.getElementById('performance');

        if (data.length === 0) {
            container.innerHTML = '<p class="loading">No performance data yet. Predictions need to be evaluated.</p>';
            return;
        }

        let html = '<table><thead><tr><th>Agent</th><th>Total Predictions</th><th>Correct</th><th>Accuracy</th></tr></thead><tbody>';

        data.forEach(agent => {
            html += `
                <tr>
                    <td><strong>${agent.agent_name}</strong></td>
                    <td>${agent.total_predictions}</td>
                    <td>${agent.correct_predictions}</td>
                    <td>
                        <div class="accuracy-bar">
                            <div class="accuracy-fill" style="width: ${agent.accuracy}%">
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
        document.getElementById('performance').innerHTML = '<p class="loading">Error loading performance data</p>';
    }
}

// Load latest prices
async function loadPrices() {
    try {
        const response = await fetch(`${API_URL}/prices`);
        const data = await response.json();

        const container = document.getElementById('prices');

        if (data.length === 0) {
            container.innerHTML = '<p class="loading">No price data available</p>';
            return;
        }

        let html = '<table><thead><tr><th>Symbol</th><th>Date</th><th>Close Price</th><th>Volume</th></tr></thead><tbody>';

        data.forEach(stock => {
            html += `
                <tr>
                    <td><strong>${stock.symbol}</strong></td>
                    <td>${formatDate(stock.date)}</td>
                    <td>${parseFloat(stock.close).toFixed(2)}</td>
                    <td>${parseInt(stock.volume).toLocaleString()}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading prices:', error);
        document.getElementById('prices').innerHTML = '<p class="loading">Error loading price data</p>';
    }
}