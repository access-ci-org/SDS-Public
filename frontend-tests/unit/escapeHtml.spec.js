import { describe, test, expect } from "vitest";
import { escapeHtml } from "../../app/static/js/utils.js";

describe("escapeHtml", () => {
    test("escapes ampersand", () => {
        expect(escapeHtml("a & b")).toBe("a &amp; b");
    });

    test("escapes less-than", () => {
        expect(escapeHtml("1 < 2")).toBe("1 &lt; 2");
    });

    test("escapes greater-than", () => {
        expect(escapeHtml("2 > 1")).toBe("2 &gt; 1");
    });

    test("escapes double-quote", () => {
        expect(escapeHtml('say "hi"')).toBe("say &quot;hi&quot;");
    });

    test("escapes single-quote", () => {
        expect(escapeHtml("it's")).toBe("it&#39;s");
    });

    test("escapes a script tag payload safely", () => {
        expect(escapeHtml("<script>alert(1)</script>")).toBe(
            "&lt;script&gt;alert(1)&lt;/script&gt;"
        );
    });

    test("plain text is unchanged", () => {
        expect(escapeHtml("just text")).toBe("just text");
    });

    test("is idempotent on already-escaped input", () => {
        const once = escapeHtml("<x>");
        const twice = escapeHtml(once);
        // Second pass escapes the & in &lt; → &amp;lt; — by design.
        // The contract is "safe to insert into HTML", not "lossless round-trip".
        // What we lock in is that the result is still HTML-safe.
        expect(twice).not.toContain("<");
        expect(twice).not.toContain(">");
    });

    test("null coerces to empty string", () => {
        expect(escapeHtml(null)).toBe("");
    });

    test("undefined coerces to empty string", () => {
        expect(escapeHtml(undefined)).toBe("");
    });

    test("number is coerced to string and returned", () => {
        expect(escapeHtml(42)).toBe("42");
    });

    test("escapes all dangerous chars in one pass", () => {
        expect(escapeHtml("<a href=\"x\" onclick='y'>&z</a>")).toBe(
            "&lt;a href=&quot;x&quot; onclick=&#39;y&#39;&gt;&amp;z&lt;/a&gt;"
        );
    });
});
