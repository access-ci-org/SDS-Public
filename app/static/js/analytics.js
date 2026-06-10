import { escapeHtml } from "./utils.js";

document.addEventListener('DOMContentLoaded', async function() {
    // Set default date range (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000));

    document.getElementById('endDate').value = today.toISOString().split('T')[0];
    document.getElementById('startDate').value = thirtyDaysAgo.toISOString().split('T')[0];

    // Event listener for tab changes
    document.addEventListener('shown.bs.tab', function (e) {
        const targetTab = e.target.getAttribute('data-bs-target');
        if (targetTab === '#views') {
            createViewsDetailView();
        } else if (targetTab === '#filters') {
            createFiltersDetailView();
        } else if (targetTab === '#terms') {
            createTermsDetailView();
        }
    });
    window.refreshData = refreshData;
    await loadData();
});
let charts = {}; // Track existing charts

async function loadData() {
    try {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;

        const url = `/analytics/data?start_date=${startDate}&end_date=${endDate}`;
        const response = await fetch(url);
        const data = await response.json();

        displayData(data);
    } catch (error) {
        console.error('Failed to load analytics:', error);
    }
}

function refreshData() {
    // Destroy existing charts
    Object.values(charts).forEach(chart => chart.destroy());
    charts = {};
    loadData();
}

function displayData(data) {
    const searches = data.searches || [];
    const filters = data.filters || [];
    const softwareViews = data.softwareViews || [];

    // Update tab counts
    document.getElementById('searchCount').textContent = searches.length;
    document.getElementById('viewsCount').textContent = softwareViews.length;
    document.getElementById('filtersCount').textContent = filters.length;
    document.getElementById('termsCount').textContent = new Set(searches.map(s => s.searchTerm)).size;

    // Top search terms with "others" grouping
    const searchCounts = {};
    searches.forEach(s => {
        searchCounts[s.searchTerm] = (searchCounts[s.searchTerm] || 0) + 1;
    });
    const topSearchTerms = Object.entries(searchCounts).sort(([,a], [,b]) => b - a);
    const top10Search = topSearchTerms.slice(0, 10);
    const othersSearchCount = topSearchTerms.slice(10).reduce((sum, [,count]) => sum + count, 0);
    if (othersSearchCount > 0) {
        top10Search.push(['Others', othersSearchCount]);
    }

    // Software views with "others" grouping
    const viewCounts = {};
    softwareViews.forEach(v => {
        viewCounts[v.softwareName] = (viewCounts[v.softwareName] || 0) + 1;
    });
    const topSoftware = Object.entries(viewCounts).sort(([,a], [,b]) => b - a);
    const top10Software = topSoftware.slice(0, 10);

    // Time data
    const timeData = {};
    searches.forEach(s => {
        const date = s.timestamp.split('T')[0];
        timeData[date] = (timeData[date] || 0) + 1;
    });
    const dates = Object.keys(timeData).sort();
    const searchCounts2 = dates.map(d => timeData[d]);

    // Filter usage with "others" grouping
    const filterCounts = {};
    filters.forEach(f => {
        if (f.action === 'applied') {
            filterCounts[f.filterType] = (filterCounts[f.filterType] || 0) + 1;
        }
    });
    const filterData = Object.entries(filterCounts);
    const top10Filters = filterData.slice(0, 10);
    const othersFilterCount = filterData.slice(10).reduce((sum, [,count]) => sum + count, 0);
    if (othersFilterCount > 0) {
        top10Filters.push(['Others', othersFilterCount]);
    }

    // Overview charts
    charts.time = new Chart(document.getElementById('timeChart'), {
        type: 'line',
        data: {
            labels: dates.length > 0 ? dates : ['No data'],
            datasets: [{
                label: 'Searches',
                data: dates.length > 0 ? searchCounts2 : [0],
                borderColor: '#007bff',
                tension: 0.4
            }]
        },
        options: {
            maintainAspectRatio: false,
            animation: {
                duration: 50
            }
        }
    });

    charts.search = new Chart(document.getElementById('searchChart'), {
        type: 'doughnut',
        data: {
            labels: top10Search.map(([term]) => term),
            datasets: [{
                data: top10Search.map(([,count]) => count),
                backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6f42c1', '#e83e8c', '#fd7e14', '#20c997', '#6c757d', '#adb5bd']
            }]
        },
        options: {
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, padding: 8 } }
            },
            animation: {
                duration: 50
            }
        }
    });

    charts.software = new Chart(document.getElementById('softwareChart'), {
        type: 'bar',
        data: {
            labels: top10Software.map(([name]) => name),
            datasets: [{
                label: 'Views',
                data: top10Software.map(([,count]) => count),
                backgroundColor: '#28a745'
            }]
        },
        options: {
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true } },
            animation: {duration: 50}
        }
    });

    charts.filter = new Chart(document.getElementById('filterChart'), {
        type: 'pie',
        data: {
            labels: top10Filters.map(([type]) => type),
            datasets: [{
                data: top10Filters.map(([,count]) => count),
                backgroundColor: ['#17a2b8', '#6f42c1', '#e83e8c', '#fd7e14', '#20c997', '#6c757d', '#adb5bd', '#007bff', '#28a745', '#ffc107', '#dc3545']
            }]
        },
        options: {
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, padding: 8 } }
            },
            animation: {duration: 50}
        }
    });

    // Store data for detailed views
    window.analyticsData = { searches, filters, softwareViews, topSearchTerms, topSoftware, filterData };
}


function createViewsDetailView() {
    if (!window.analyticsData) return;


    if (charts.viewsDetail) {
        charts.viewsDetail.destroy();
        charts.viewsDetail = null;
    }

    const canvas = document.getElementById('viewsDetailChart');
    const parent = canvas.parentElement;
    canvas.style.width = '100%';

    charts.viewsDetail = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: window.analyticsData.topSoftware.slice(0, 10).map(([name]) => name),
            datasets: [{
                label: 'Views',
                data: window.analyticsData.topSoftware.slice(0, 10).map(([,count]) => count),
                backgroundColor: '#28a745'
            }]
        },
        options: {
            indexAxis: 'y',
            maintainAspectRatio: true,
            responsive: true,
            animation: {duration: 50}
        }
    });
    // Populate table
    const viewMap = {};
    window.analyticsData.softwareViews.forEach(view => {
        const key = `${view.softwareName}|${view.source}`;
        viewMap[key] = (viewMap[key] || 0) + 1;
    });

    const sortedViews = Object.entries(viewMap)
        .map(([key, count]) => {
            const [softwareName, source] = key.split('|');
            return { softwareName, source, count };
        })
        .sort((a, b) => b.count - a.count);

    const tbody = document.querySelector('#viewsTable tbody');
    tbody.innerHTML = '';
    sortedViews.forEach(view => {
        tbody.innerHTML += `<tr>
            <td>${escapeHtml(view.softwareName)}</td>
            <td>${view.count}</td>
            <td>${escapeHtml(view.source)}</td>
        </tr>`;
    });
}

function createFiltersDetailView() {
    if (!window.analyticsData) return;

    if (charts.filtersDetail) charts.filtersDetail.destroy();

    charts.filtersDetail = new Chart(document.getElementById('filtersDetailChart'), {
        type: 'bar',
        data: {
            labels: window.analyticsData.filterData.map(([type]) => type),
            datasets: [{
                label: 'Usage Count',
                data: window.analyticsData.filterData.map(([,count]) => count),
                backgroundColor: '#17a2b8'
            }]
        },
        options: {
            maintainAspectRatio: true,
            scales: { y: { beginAtZero: true } },
            animation: {
                duration: 100
            }
        }
    });

    // Populate table
    const filterMap = {};
    window.analyticsData.filters.forEach(filter => {
        const values = Array.isArray(filter.filterValues) ? filter.filterValues.join(', ') : filter.filterValues;
        const key = `${filter.filterType}|${values}|${filter.resultCount}`;
        filterMap[key] = (filterMap[key] || 0) + 1;
    });

    const sortedFilters = Object.entries(filterMap)
        .map(([key, count]) => {
            const [type, values, resultCount] = key.split('|');
            return {
                type,
                values,
                resultCount,
                count
            };
        })
        .sort((a, b) => b.count - a.count);

    const tbody = document.querySelector('#filtersTable tbody');
    tbody.innerHTML = '';
    sortedFilters.forEach(item => {
        tbody.innerHTML += `
            <tr>
                <td>${escapeHtml(item.type)}</td>
                <td>${escapeHtml(item.values)}</td>
                <td>${item.count}</td>
                <td>${item.resultCount}</td>
            </tr>
        `;
    });

}

function createTermsDetailView() {
    if (!window.analyticsData) return;

    if (charts.termsDetail) charts.termsDetail.destroy();

    charts.termsDetail = new Chart(document.getElementById('termsDetailChart'), {
        type: 'bar',
        data: {
            labels: window.analyticsData.topSearchTerms.slice(0, 20).map(([term]) => term),
            datasets: [{
                label: 'Search Count',
                data: window.analyticsData.topSearchTerms.slice(0, 20).map(([,count]) => count),
                backgroundColor: '#007bff'
            }]
        },
        options: {
            maintainAspectRatio: true,
            scales: { y: { beginAtZero: true } },
            animation: {
                duration: 50
            }
        }
    });

    // Populate table
    const termMap = {};
    window.analyticsData.searches.forEach(search => {
        const key = `${search.searchTerm}|${search.columnName || 'global'}|${search.resultCount}`;
        termMap[key] = (termMap[key] || 0) + 1;
    });

    const sortedTerms = Object.entries(termMap)
        .map(([key, count]) => {
            const [term, columnName, resultCount] = key.split('|');
            return {
                term,
                columnName,
                resultCount: parseInt(resultCount),
                count
            };
        })
        .sort((a, b) => {
            // Primary sort by resultCount
            if (a.resultCount !== b.resultCount) {
                return a.resultCount - b.resultCount;
            }

            // Secondary sort by count in case of tie in resultCount
            return b.count - a.count;
        });

    const tbody = document.querySelector('#termsTable tbody');
    tbody.innerHTML = '';
    sortedTerms.forEach(item => {
        tbody.innerHTML += `
            <tr>
                <td>${escapeHtml(item.term)}</td>
                <td>${item.count}</td>
                <td>${escapeHtml(item.columnName)}</td>
                <td>${item.resultCount}</td>
            </tr>
        `;
    });

}
