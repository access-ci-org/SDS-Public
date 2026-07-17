// Shared helpers for client-side code.
//
// These are exported as ES modules so both the browser modules (loaded via
// <script type="module">) and the Vitest test suite can import them.

const HTML_ENTITY_MAP = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
};

/**
 * Escape HTML-significant characters in a string so it is safe to interpolate
 * into HTML via `.html()` / `innerHTML` / template literals.
 *
 * Non-string inputs are coerced via String().
 */
export function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value).replace(/[&<>"']/g, (ch) => HTML_ENTITY_MAP[ch]);
}

/**
 * Split a comma-separated command string (storage format) into an array of
 * trimmed, non-empty commands. Empty / nullish input yields [].
 */
export function splitCommands(raw) {
    if (!raw) return [];
    return String(raw)
        .split(",")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);
}

/**
 * Parse a comma-separated classification string (tags, research disciplines,
 * software types) into trimmed, de-duplicated, non-empty values — one chip per
 * value, keeping first-seen order.
 */
export function parseChipValues(raw) {
    return [...new Set(splitCommands(raw))];
}
