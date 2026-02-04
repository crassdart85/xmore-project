// API Base URL
const API_URL = '/api';

// Agent Name Mapping for display with descriptions
const AGENT_INFO = {
    'MA_Crossover_Agent': {
        name: 'Moving Average Trend',
        description: 'Analyzes short and long-term moving average crossovers to identify trend changes'
    },
    'ML_RandomForest': {
        name: 'AI Price Predictor',
        description: 'Machine learning model using historical patterns to predict price movements'
    },
    'RSI_Agent': {
        name: 'Momentum Indicator',
        description: 'Uses Relative Strength Index to detect overbought/oversold conditions'
    },
    'Volume_Spike_Agent': {
        name: 'Volume Analysis',
        description: 'Monitors unusual volume activity to predict potential price movements'
    },
};

// Get display name for an agent
function getAgentDisplayName(agentName) {
    return AGENT_INFO[agentName]?.name || agentName;
}

// Get agent description for tooltips
function getAgentDescription(agentName) {
    return AGENT_INFO[agentName]?.description || '';
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
    loadStats();
    loadPredictions();
    loadPerformance();
    loadPrices();
});

// Refresh all data with loading state
async function refreshData() {
    const btn = document.getElementById('refreshBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Refreshing...';
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
            btn.textContent = 'Refresh Data';
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
            container.innerHTML = '<p class="no-data">No predictions yet. Run python run_agents.py to generate predictions.</p>';
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

        let html = '<table id="predictionsTable"><thead><tr><th>Stock</th><th>Agent</th><th>Prediction</th><th>Date</th></tr></thead><tbody>';

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

                html += `
                    <td><span class="agent-name" title="${agentDescription}">${agentDisplayName}</span></td>
                    <td><span class="prediction-${pred.prediction.toLowerCase()}">${pred.prediction}</span></td>
                    <td>${formatDate(pred.prediction_date)}</td>
                </tr>`;
            });
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading predictions:', error);
        document.getElementById('predictions').innerHTML = '<p class="error-message">Could not load predictions. Check if the server is running.</p>';
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
            container.innerHTML = '<p class="no-data">No performance data yet. Run evaluate.py after predictions are made to see agent accuracy.</p>';
            return;
        }

        let html = '<table><thead><tr><th>Agent</th><th>Total Predictions</th><th>Correct</th><th>Accuracy</th></tr></thead><tbody>';

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
        container.innerHTML = '<p class="error-message">Could not load performance data. Check if the server is running.</p>';
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
            container.innerHTML = '<p class="no-data">No price data available yet.</p>';
            return;
        }

        let html = '<table><thead><tr><th>Stock</th><th>Date</th><th>Close Price</th><th>Volume</th></tr></thead><tbody>';

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
        container.innerHTML = '<p class="error-message">Could not load price data. Check if the server is running.</p>';
    }
}