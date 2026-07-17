import { describe, test, expect } from "vitest";
import { parseChipValues } from "../../app/static/js/utils.js";

describe("parseChipValues", () => {
    test("splits a comma-separated string into trimmed values", () => {
        expect(parseChipValues("a, b, c")).toEqual(["a", "b", "c"]);
    });

    test("collapses tokens that differ only by surrounding whitespace", () => {
        // A ", "-joined value split on a bare "," yields " what?", which must
        // de-dup against "what?" so only one chip renders.
        expect(parseChipValues("Physics, what?, what?")).toEqual(["Physics", "what?"]);
    });

    test("de-dups exact duplicates, keeping first-seen order", () => {
        expect(parseChipValues("b, a, b")).toEqual(["b", "a"]);
    });

    test("handles a separator with no space", () => {
        expect(parseChipValues("a,b")).toEqual(["a", "b"]);
    });

    test("drops empty tokens", () => {
        expect(parseChipValues("a,, ,b")).toEqual(["a", "b"]);
    });

    test("returns [] for empty or nullish input", () => {
        expect(parseChipValues("")).toEqual([]);
        expect(parseChipValues(null)).toEqual([]);
        expect(parseChipValues(undefined)).toEqual([]);
    });

    test("returns a single value unchanged", () => {
        expect(parseChipValues("what?")).toEqual(["what?"]);
    });
});
