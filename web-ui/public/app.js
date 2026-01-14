// API Base URL
const API_URL = '/api';

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
        document.getElementById('latestDate').textContent = data.latestDate || 'N/A';
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
        
        // Group by stock
        const grouped = {};
        data.forEach(pred => {
            if (!grouped[pred.symbol]) grouped[pred.symbol] = [];
            grouped[pred.symbol].push(pred);
        });
        
        let html = '<table><thead><tr><th>Stock</th><th>Agent</th><th>Prediction</th><th>Date</th></tr></thead><tbody>';
        
        Object.keys(grouped).forEach(symbol => {
            grouped[symbol].forEach((pred, idx) => {
                html += `
                    <tr>
                        ${idx === 0 ? `<td rowspan="${grouped[symbol].length}"><strong>${symbol}</strong></td>` : ''}
                        <td>${pred.agent_name}</td>
                        <td><span class="prediction-${pred.prediction.toLowerCase()}">${pred.prediction}</span></td>
                        <td>${pred.prediction_date}</td>
                    </tr>
                `;
            });
        });
        
        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading predictions:', error);
        document.getElementById('predictions').innerHTML = '<p class="loading">Error loading predictions</p>';
    }
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
                    <td>${stock.date}</td>
                    <td>$${parseFloat(stock.close).toFixed(2)}</td>
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