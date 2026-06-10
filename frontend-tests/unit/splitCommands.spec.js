import { describe, test, expect } from "vitest";
import { splitCommands } from "../../app/static/js/utils.js";

describe("splitCommands", () => {
    test("empty string returns empty array", () => {
        expect(splitCommands("")).toEqual([]);
    });

    test("null returns empty array", () => {
        expect(splitCommands(null)).toEqual([]);
    });

    test("undefined returns empty array", () => {
        expect(splitCommands(undefined)).toEqual([]);
    });

    test("single command without comma", () => {
        expect(splitCommands("module load pytorch")).toEqual(["module load pytorch"]);
    });

    test("two comma-separated commands", () => {
        expect(splitCommands("module load pytorch, module load deps")).toEqual([
            "module load pytorch",
            "module load deps",
        ]);
    });

    test("trims whitespace around each command", () => {
        expect(splitCommands("  a  ,   b  ")).toEqual(["a", "b"]);
    });

    test("drops empty entries from doubled commas", () => {
        expect(splitCommands("a,,b")).toEqual(["a", "b"]);
    });

    test("drops whitespace-only entries", () => {
        expect(splitCommands("a,   ,b")).toEqual(["a", "b"]);
    });

    test("trailing comma does not produce empty entry", () => {
        expect(splitCommands("a, b,")).toEqual(["a", "b"]);
    });

    test("coerces non-string input via String()", () => {
        expect(splitCommands(42)).toEqual(["42"]);
    });
});
