// analytics that sends user search data to server endpoints

export class DataTablesAnalytics {
    constructor() {
        this.apiBase = '/analytics'
    }

    async trackSearch(searchTerm, resultCount) {
        if (!searchTerm.trim()) return;

        await this.sendEvent('search', {
            searchTerm: searchTerm.toLowerCase(),
            resultCount,
            searchType: 'global'
        });
    }

    async trackColumnSearch(columnName, searchTerm, resultCount) {
        if (!searchTerm.trim()) return;

        await this.sendEvent('search', {
            searchTerm: searchTerm.toLowerCase(),
            columnName,
            resultCount,
            searchType: 'column'
        });
    }

    async trackFilter(filterType, filterValues, resultCount) {
        await this.sendEvent('filter', {
            filterType,
            filterValues,
            resultCount,
            action: filterValues.length > 0 ? 'applied': 'cleared'
        });
    }

    async trackSoftwareView(softwareName, source = 'table') {
        await this.sendEvent('software_view', {
            softwareName,
            source
        })
    }

    async sendEvent(eventType, data){
        try {
            await fetch(`${this.apiBase}/track`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    eventType,
                    data,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (error) {
            console.error('Analytics tracking failed:', error);
        }
    }

    async getAnalyticsData(days = 30) {
        try {
            const response = await fetch (`${this.apiBase}/data?days=${days}`)
            if (!response.ok) throw new Error('Failed to fetch analytics');
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch analytics:', error);
            return null
        }
    }

    processAnalyticsSummary(analyticsData) {
        if (!analyticsData) return null;

        const searches = analyticsData.searches || [];
        const filters = analyticsData.filters || [];
        const softwareViews = analyticsData.softwareViews || [];

        // top search terms
        const searchCounts = {};
        searches.forEach(search => {
            searchCounts[searchCounts.searchTerm] = (searchCounts[search.searchTerm] || 0) + 1
        });
        const topSearchTerms = Object.entries(searchCounts)
            .sort(([,a], [,b]) => b -a)
            .slice(0,10)
            .map(([term, count]) => ({term, count}));

        // top viewed software
        const viewCounts = {};
        softwareViews.forEach(view => {
            viewCounts[view.softwareName] = (viewCounts[view.softwareName] || 0) + 1;
        });
        const topViewedSoftware = Object.entries(viewCounts)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10)
            .map(([software, count]) => ({ software, count }));

        // filter usage
        const filterCounts = {};
        filters.forEach(filter => {
            if (filter.action === 'applied') {
                filterCounts[filter.filterType] = (filterCounts[filter.filterType] || 0) + 1;
            }
        });
        const filterUsage = Object.entries(filterCounts)
            .sort(([,a], [,b]) => b - a)
            .map(([filterType, count]) => ({ filterType, count }));

        // time-based analytics
        const timeData = {};
        searches.forEach(search => {
            const date = search.timestamp.split('T')[0];
            if (!timeData[date]) timeData[date] = { searches: 0, views: 0 };
            timeData[date].searches++;
        });
        softwareViews.forEach(view => {
            const date = view.timestamp.split('T')[0];
            if (!timeData[date]) timeData[date] = { searches: 0, views: 0 };
            timeData[date].views++;
        });

        return {
            totalSearches: searches.length,
            uniqueSearchTerms: [...new Set(searches.map(s => s.searchTerm))].length,
            totalFilters: filters.length,
            totalSoftwareViews: softwareViews.length,
            uniqueSoftwareViewed: [...new Set(softwareViews.map(v => v.softwareName))].length,
            topSearchTerms,
            topViewedSoftware,
            filterUsage,
            timeBasedData: timeData
        }
    }
}

