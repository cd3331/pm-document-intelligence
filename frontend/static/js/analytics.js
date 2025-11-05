/**
 * Analytics Dashboard JavaScript
 * Handles chart rendering, data fetching, and dashboard interactivity
 */

// Global variables
let charts = {};
let currentDateRange = {
    start: moment().subtract(29, 'days'),
    end: moment()
};
let refreshInterval = null;

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeDateRangePicker();
    loadDashboard();
    startAutoRefresh();
});

/**
 * Initialize date range picker
 */
function initializeDateRangePicker() {
    $('#daterange').daterangepicker({
        startDate: currentDateRange.start,
        endDate: currentDateRange.end,
        ranges: {
            'Today': [moment(), moment()],
            'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
            'Last 7 Days': [moment().subtract(6, 'days'), moment()],
            'Last 30 Days': [moment().subtract(29, 'days'), moment()],
            'This Month': [moment().startOf('month'), moment().endOf('month')],
            'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        }
    }, function(start, end) {
        currentDateRange.start = start;
        currentDateRange.end = end;
        loadDashboard();
    });
}

/**
 * Load complete dashboard
 */
async function loadDashboard() {
    showLoading(true);

    try {
        // Load all data in parallel
        await Promise.all([
            loadDocumentStats(),
            loadUserActivity(),
            loadCostBreakdown(),
            loadPerformanceMetrics(),
            loadInsights()
        ]);
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('Failed to load analytics data');
    } finally {
        showLoading(false);
    }
}

/**
 * Load document statistics
 */
async function loadDocumentStats() {
    try {
        const params = new URLSearchParams({
            start_date: currentDateRange.start.toISOString(),
            end_date: currentDateRange.end.toISOString()
        });

        const response = await fetch(`/api/analytics/documents/stats?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to fetch document stats');

        const data = await response.json();

        // Update stat cards
        document.getElementById('totalDocs').textContent = data.total_documents.toLocaleString();
        document.getElementById('successRate').textContent = `${data.success_rate}%`;

        // Update document processing trend chart
        updateDocumentsTrendChart(data.time_series);

        // Update status chart
        updateStatusChart(data.documents_by_status);

    } catch (error) {
        console.error('Error loading document stats:', error);
    }
}

/**
 * Load user activity data
 */
async function loadUserActivity() {
    try {
        const params = new URLSearchParams({
            start_date: currentDateRange.start.toISOString(),
            end_date: currentDateRange.end.toISOString()
        });

        const response = await fetch(`/api/analytics/users/activity?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });

        if (response.status === 403) {
            // Not an admin, hide admin section
            return;
        }

        if (!response.ok) throw new Error('Failed to fetch user activity');

        const data = await response.json();

        // Update stat card
        document.getElementById('activeUsers').textContent = data.active_users.toLocaleString();

        // Show admin section
        document.getElementById('adminSection').classList.remove('hidden');

        // Update top users table
        updateTopUsersTable(data.top_users);

        // Load behavior data for peak times chart
        await loadPeakUsageTimes();

    } catch (error) {
        console.error('Error loading user activity:', error);
    }
}

/**
 * Load peak usage times
 */
async function loadPeakUsageTimes() {
    try {
        const params = new URLSearchParams({
            start_date: currentDateRange.start.toISOString(),
            end_date: currentDateRange.end.toISOString()
        });

        const response = await fetch(`/api/analytics/users/behavior?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });

        if (!response.ok) return;

        const data = await response.json();
        updateUsageChart(data.peak_usage_times);

    } catch (error) {
        console.error('Error loading peak usage times:', error);
    }
}

/**
 * Load cost breakdown
 */
async function loadCostBreakdown() {
    try {
        const params = new URLSearchParams({
            start_date: currentDateRange.start.toISOString(),
            end_date: currentDateRange.end.toISOString(),
            group_by: 'service'
        });

        const response = await fetch(`/api/analytics/costs/breakdown?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });

        if (response.status === 403) {
            // Not an admin
            document.getElementById('totalCost').textContent = 'N/A';
            return;
        }

        if (!response.ok) throw new Error('Failed to fetch cost breakdown');

        const data = await response.json();

        // Update stat card
        document.getElementById('totalCost').textContent = `$${data.total_cost.toFixed(2)}`;

        // Update cost chart
        updateCostChart(data.breakdown);

    } catch (error) {
        console.error('Error loading cost breakdown:', error);
    }
}

/**
 * Load performance metrics
 */
async function loadPerformanceMetrics() {
    try {
        const params = new URLSearchParams({
            start_date: currentDateRange.start.toISOString(),
            end_date: currentDateRange.end.toISOString()
        });

        const response = await fetch(`/api/analytics/performance/processing?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to fetch performance metrics');

        const data = await response.json();

        // Update performance chart
        if (data.by_document_type) {
            updatePerformanceChart(data.by_document_type);
        }

    } catch (error) {
        console.error('Error loading performance metrics:', error);
    }
}

/**
 * Load AI-generated insights
 */
async function loadInsights() {
    try {
        const params = new URLSearchParams({
            start_date: currentDateRange.start.toISOString(),
            end_date: currentDateRange.end.toISOString()
        });

        const response = await fetch(`/api/analytics/documents/insights?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to fetch insights');

        const data = await response.json();
        updateInsightsSection(data);

    } catch (error) {
        console.error('Error loading insights:', error);
    }
}

/**
 * Update charts
 */
function updateDocumentsTrendChart(timeSeriesData) {
    const ctx = document.getElementById('documentsChart');

    // Destroy existing chart if it exists
    if (charts.documentsChart) {
        charts.documentsChart.destroy();
    }

    const dates = timeSeriesData.map(d => d.date);
    const counts = timeSeriesData.map(d => d.total);

    charts.documentsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Documents Processed',
                data: counts,
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updateStatusChart(statusData) {
    const ctx = document.getElementById('statusChart');

    if (charts.statusChart) {
        charts.statusChart.destroy();
    }

    const labels = Object.keys(statusData);
    const data = Object.values(statusData);

    const colors = {
        'completed': 'rgb(16, 185, 129)',
        'processing': 'rgb(59, 130, 246)',
        'failed': 'rgb(239, 68, 68)',
        'pending': 'rgb(251, 191, 36)'
    };

    const backgroundColors = labels.map(label => colors[label] || 'rgb(156, 163, 175)');

    charts.statusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
            datasets: [{
                data: data,
                backgroundColor: backgroundColors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

function updateCostChart(costData) {
    const ctx = document.getElementById('costChart');

    if (charts.costChart) {
        charts.costChart.destroy();
    }

    const labels = Object.keys(costData);
    const data = Object.values(costData);

    charts.costChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels.map(formatServiceName),
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgb(255, 99, 132)',
                    'rgb(54, 162, 235)',
                    'rgb(255, 205, 86)',
                    'rgb(75, 192, 192)',
                    'rgb(153, 102, 255)',
                    'rgb(255, 159, 64)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': $' + context.parsed.toFixed(2);
                        }
                    }
                }
            }
        }
    });
}

function updatePerformanceChart(performanceData) {
    const ctx = document.getElementById('performanceChart');

    if (charts.performanceChart) {
        charts.performanceChart.destroy();
    }

    const labels = performanceData.map(d => d.document_type);
    const data = performanceData.map(d => d.avg_processing_time_seconds);

    charts.performanceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.map(l => l.toUpperCase()),
            datasets: [{
                label: 'Avg. Processing Time (seconds)',
                data: data,
                backgroundColor: 'rgba(139, 92, 246, 0.8)',
                borderColor: 'rgb(139, 92, 246)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function updateUsageChart(peakTimes) {
    const ctx = document.getElementById('usageChart');

    if (charts.usageChart) {
        charts.usageChart.destroy();
    }

    const hours = peakTimes.map(d => `${d.hour}:00`);
    const counts = peakTimes.map(d => d.count);

    charts.usageChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours,
            datasets: [{
                label: 'Activity Count',
                data: counts,
                backgroundColor: 'rgba(59, 130, 246, 0.6)',
                borderColor: 'rgb(59, 130, 246)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Update UI elements
 */
function updateTopUsersTable(topUsers) {
    const tbody = document.getElementById('topUsersTable');
    tbody.innerHTML = '';

    topUsers.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${user.username}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.document_count}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${moment().fromNow()}</td>
        `;
        tbody.appendChild(row);
    });
}

function updateInsightsSection(insights) {
    const container = document.getElementById('insightsContainer');
    container.innerHTML = '';

    // Common themes
    if (insights.common_themes && insights.common_themes.length > 0) {
        const themesDiv = createInsightCard(
            'fas fa-tags',
            'Common Themes',
            `Top themes: ${insights.common_themes.slice(0, 3).map(t => t.theme).join(', ')}`,
            'blue'
        );
        container.appendChild(themesDiv);
    }

    // Sentiment trend
    if (insights.sentiment_trends && insights.sentiment_trends.overall_sentiment) {
        const sentimentText = `Overall sentiment is ${insights.sentiment_trends.overall_sentiment} (${insights.sentiment_trends.positive_percentage}% positive)`;
        const sentimentDiv = createInsightCard(
            'fas fa-smile',
            'Sentiment Analysis',
            sentimentText,
            insights.sentiment_trends.overall_sentiment === 'positive' ? 'green' : 'yellow'
        );
        container.appendChild(sentimentDiv);
    }

    // Risk indicators
    if (insights.risk_indicators && insights.risk_indicators.total_risks > 0) {
        const riskText = `${insights.risk_indicators.total_risks} potential risks identified`;
        const riskDiv = createInsightCard(
            'fas fa-exclamation-triangle',
            'Risk Indicators',
            riskText,
            'red'
        );
        container.appendChild(riskDiv);
    }

    // Action item completion
    if (insights.action_item_completion_rate) {
        const completionText = `${insights.action_item_completion_rate}% of action items completed`;
        const completionDiv = createInsightCard(
            'fas fa-tasks',
            'Action Items',
            completionText,
            'purple'
        );
        container.appendChild(completionDiv);
    }
}

function createInsightCard(icon, title, text, color) {
    const colorClasses = {
        'blue': 'bg-blue-50 text-blue-600',
        'green': 'bg-green-50 text-green-600',
        'yellow': 'bg-yellow-50 text-yellow-600',
        'red': 'bg-red-50 text-red-600',
        'purple': 'bg-purple-50 text-purple-600'
    };

    const div = document.createElement('div');
    div.className = `flex items-start p-4 rounded-lg ${colorClasses[color] || 'bg-gray-50'}`;
    div.innerHTML = `
        <i class="${icon} ${colorClasses[color]?.split(' ')[1] || 'text-gray-600'} mt-1 mr-3"></i>
        <div>
            <p class="font-medium text-gray-900">${title}</p>
            <p class="text-sm text-gray-600 mt-1">${text}</p>
        </div>
    `;
    return div;
}

/**
 * Export functions
 */
async function exportToPDF() {
    showLoading(true);

    try {
        const params = new URLSearchParams({
            report_type: 'custom',
            start_date: currentDateRange.start.toISOString(),
            end_date: currentDateRange.end.toISOString(),
            format: 'pdf'
        });

        const response = await fetch(`/api/analytics/reports/generate?${params}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to generate PDF report');

        showSuccess('PDF report generation started. You will receive it via email.');
        toggleExportMenu();

    } catch (error) {
        console.error('Error generating PDF:', error);
        showError('Failed to generate PDF report');
    } finally {
        showLoading(false);
    }
}

async function exportToExcel() {
    showLoading(true);

    try {
        const params = new URLSearchParams({
            report_type: 'custom',
            start_date: currentDateRange.start.toISOString(),
            end_date: currentDateRange.end.toISOString(),
            format: 'excel'
        });

        const response = await fetch(`/api/analytics/reports/generate?${params}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to generate Excel report');

        showSuccess('Excel report generation started. You will receive it via email.');
        toggleExportMenu();

    } catch (error) {
        console.error('Error generating Excel:', error);
        showError('Failed to generate Excel report');
    } finally {
        showLoading(false);
    }
}

async function exportToCSV() {
    try {
        const params = new URLSearchParams({
            data_type: 'documents',
            start_date: currentDateRange.start.toISOString(),
            end_date: currentDateRange.end.toISOString()
        });

        const response = await fetch(`/api/analytics/export/csv?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAccessToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to export CSV');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analytics_export_${moment().format('YYYY-MM-DD')}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        toggleExportMenu();

    } catch (error) {
        console.error('Error exporting CSV:', error);
        showError('Failed to export CSV');
    }
}

/**
 * Utility functions
 */
function refreshDashboard() {
    loadDashboard();
}

function startAutoRefresh() {
    // Refresh every 5 minutes
    refreshInterval = setInterval(() => {
        loadDashboard();
    }, 5 * 60 * 1000);
}

function toggleExportMenu() {
    const menu = document.getElementById('exportMenu');
    menu.classList.toggle('hidden');
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (show) {
        overlay.classList.remove('hidden');
    } else {
        overlay.classList.add('hidden');
    }
}

function showError(message) {
    alert(message); // Replace with better notification system
}

function showSuccess(message) {
    alert(message); // Replace with better notification system
}

function getAccessToken() {
    // Get token from localStorage or cookie
    return localStorage.getItem('access_token') || '';
}

function formatServiceName(service) {
    return service.split('_').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

// Close export menu when clicking outside
document.addEventListener('click', function(event) {
    const menu = document.getElementById('exportMenu');
    const button = event.target.closest('button');

    if (!menu.contains(event.target) && button?.textContent?.includes('Export') === false) {
        menu.classList.add('hidden');
    }
});
