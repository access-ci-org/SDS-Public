import { describe, test, expect } from "vitest";
import { DataTablesAnalytics } from "../../app/static/js/tableAnalytics.js";

function summarize(data) {
    return new DataTablesAnalytics().processAnalyticsSummary(data);
}

describe("processAnalyticsSummary", () => {
    test("null input returns null", () => {
        expect(summarize(null)).toBeNull();
    });

    test("empty data yields all zeros and empty arrays", () => {
        const out = summarize({ searches: [], filters: [], softwareViews: [] });
        expect(out.totalSearches).toBe(0);
        expect(out.totalFilters).toBe(0);
        expect(out.totalSoftwareViews).toBe(0);
        expect(out.uniqueSearchTerms).toBe(0);
        expect(out.uniqueSoftwareViewed).toBe(0);
        expect(out.topSearchTerms).toEqual([]);
        expect(out.topViewedSoftware).toEqual([]);
        expect(out.filterUsage).toEqual([]);
        expect(out.timeBasedData).toEqual({});
    });

    test("missing keys are treated as empty", () => {
        const out = summarize({});
        expect(out.totalSearches).toBe(0);
        expect(out.totalFilters).toBe(0);
        expect(out.totalSoftwareViews).toBe(0);
    });

    test("top search terms are counted per term (not aggregated under undefined)", () => {
        // The original typo aggregated every search under the same `undefined` key.
        // Two distinct terms must produce two entries.
        const out = summarize({
            searches: [
                { searchTerm: "pytorch", timestamp: "2026-01-01T00:00:00Z" },
                { searchTerm: "pytorch", timestamp: "2026-01-01T00:00:00Z" },
                { searchTerm: "numpy", timestamp: "2026-01-01T00:00:00Z" },
            ],
            filters: [],
            softwareViews: [],
        });
        expect(out.topSearchTerms).toHaveLength(2);
        const byTerm = Object.fromEntries(
            out.topSearchTerms.map((e) => [e.term, e.count])
        );
        expect(byTerm.pytorch).toBe(2);
        expect(byTerm.numpy).toBe(1);
    });

    test("top search terms truncated to 10", () => {
        const searches = [];
        for (let i = 0; i < 15; i++) {
            searches.push({
                searchTerm: `term_${i}`,
                timestamp: "2026-01-01T00:00:00Z",
            });
        }
        const out = summarize({ searches, filters: [], softwareViews: [] });
        expect(out.topSearchTerms).toHaveLength(10);
    });

    test("top viewed software ranked by count, truncated to 10", () => {
        const views = [];
        for (let i = 0; i < 12; i++) {
            const repeats = i; // software_i viewed i times
            for (let j = 0; j < repeats; j++) {
                views.push({
                    softwareName: `sw_${i}`,
                    timestamp: "2026-01-01T00:00:00Z",
                });
            }
        }
        const out = summarize({
            searches: [],
            filters: [],
            softwareViews: views,
        });
        expect(out.topViewedSoftware).toHaveLength(10);
        // First entry has the highest count
        const counts = out.topViewedSoftware.map((e) => e.count);
        const sorted = [...counts].sort((a, b) => b - a);
        expect(counts).toEqual(sorted);
    });

    test("filter usage counts only 'applied' actions", () => {
        const out = summarize({
            searches: [],
            filters: [
                { filterType: "Tags", action: "applied" },
                { filterType: "Tags", action: "applied" },
                { filterType: "Tags", action: "cleared" },
                { filterType: "Resource", action: "applied" },
            ],
            softwareViews: [],
        });
        const byType = Object.fromEntries(
            out.filterUsage.map((e) => [e.filterType, e.count])
        );
        expect(byType.Tags).toBe(2);
        expect(byType.Resource).toBe(1);
    });

    test("time-based data groups by date (YYYY-MM-DD)", () => {
        const out = summarize({
            searches: [
                { searchTerm: "x", timestamp: "2026-06-01T10:00:00Z" },
                { searchTerm: "y", timestamp: "2026-06-01T11:00:00Z" },
                { searchTerm: "z", timestamp: "2026-06-02T09:00:00Z" },
            ],
            filters: [],
            softwareViews: [
                { softwareName: "a", timestamp: "2026-06-01T12:00:00Z" },
            ],
        });
        expect(out.timeBasedData["2026-06-01"].searches).toBe(2);
        expect(out.timeBasedData["2026-06-01"].views).toBe(1);
        expect(out.timeBasedData["2026-06-02"].searches).toBe(1);
        expect(out.timeBasedData["2026-06-02"].views).toBe(0);
    });

    test("unique counts use Set semantics", () => {
        const out = summarize({
            searches: [
                { searchTerm: "pytorch", timestamp: "2026-01-01T00:00:00Z" },
                { searchTerm: "pytorch", timestamp: "2026-01-02T00:00:00Z" },
                { searchTerm: "numpy", timestamp: "2026-01-03T00:00:00Z" },
            ],
            filters: [],
            softwareViews: [
                { softwareName: "x", timestamp: "2026-01-01T00:00:00Z" },
                { softwareName: "x", timestamp: "2026-01-02T00:00:00Z" },
            ],
        });
        expect(out.uniqueSearchTerms).toBe(2);
        expect(out.uniqueSoftwareViewed).toBe(1);
    });
});
