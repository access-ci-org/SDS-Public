import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN, DEFAULT_USER } from "../helpers/seed.js";
import { login } from "../helpers/login.js";

test.beforeEach(async ({ request }) => {
    await seed(request);
});

async function openApiPage(page) {
    await page.goto("/admin/api");
    await expect(page.locator("#keys-table")).toBeVisible();
}

// Creates a key through the UI and returns the raw key value, which is
// shown exactly once in the new-key alert.
async function createKey(page, label) {
    await page.fill("#key-label", label);
    await page.click("#create-key-btn");
    await expect(page.locator("#new-key-alert")).toBeVisible();
    return (await page.locator("#new-key-value").textContent()).trim();
}

test("created key authenticates /api/v1 requests", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await openApiPage(page);

    const raw = await createKey(page, "e2e round-trip");
    expect(raw).toMatch(/^sds_/);
    await expect(
        page.locator("#keys-table tbody tr", { hasText: "e2e round-trip" })
    ).toBeVisible();

    const authed = await page.request.get("/api/v1/resources", {
        headers: { "X-API-Key": raw },
    });
    expect(authed.status()).toBe(200);

    // The session cookie alone is not enough — the API wants the key header.
    const noKey = await page.request.get("/api/v1/resources");
    expect(noKey.status()).toBe(401);
});

test("revoked key stops authenticating", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await openApiPage(page);

    const raw = await createKey(page, "e2e revoke");
    const before = await page.request.get("/api/v1/resources", {
        headers: { "X-API-Key": raw },
    });
    expect(before.status()).toBe(200);

    // Revoke uses window.confirm.
    page.on("dialog", (dialog) => dialog.accept());
    const row = page.locator("#keys-table tbody tr", { hasText: "e2e revoke" });
    await row.locator(".revoke-btn").click();
    // The revoke button turns into a delete button once the server confirms.
    await expect(row.locator(".delete-btn")).toBeVisible();

    // A key that is present but revoked is refused with 403 (401 is
    // reserved for a missing header).
    const after = await page.request.get("/api/v1/resources", {
        headers: { "X-API-Key": raw },
    });
    expect(after.status()).toBe(403);
});

test("navbar API link opens the page for admins", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await page.goto("/settings");
    await page.click('nav a[href="/admin/api"]');
    await expect(page.locator("#keys-table")).toBeVisible();
});

test("activity tab lists authenticated requests", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await openApiPage(page);

    const raw = await createKey(page, "e2e activity");
    // The row built after create links the prefix to the filtered view.
    const newRow = page.locator("#keys-table tbody tr", { hasText: "e2e activity" });
    await expect(newRow.locator('a[href^="/admin/api?key="]')).toBeVisible();

    const authed = await page.request.get("/api/v1/resources", {
        headers: { "X-API-Key": raw },
    });
    expect(authed.status()).toBe(200);

    // The activity table is server-rendered, so reload to pick up the
    // request that was just logged, then follow the prefix link — it opens
    // the Activity tab filtered to this key.
    await page.goto("/admin/api");
    await page.locator("#keys-table tbody tr", { hasText: "e2e activity" })
        .locator('a[href^="/admin/api?key="]').click();
    await expect(page.locator("#activity-tab-pane")).toBeVisible();
    const table = page.locator("#activity-table");
    await expect(table).toContainText("/api/v1/resources");
    await expect(table).toContainText("e2e activity");

    // "show all" drops the filter but stays on the Activity tab.
    await page.click('a[href="/admin/api?tab=activity"]');
    await expect(page.locator("#activity-tab-pane")).toBeVisible();
    await expect(page.locator("#activity-table")).toContainText("/api/v1/resources");
});

test("docs and MCP tabs render the contract", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await openApiPage(page);

    // toContainText reads textContent even on hidden panes, so the
    // visibility checks are what actually verify the tab switch happened.
    await page.click("#docs-tab");
    await expect(page.locator("#docs-tab-pane")).toBeVisible();
    await expect(page.locator("#keys-tab-pane")).toBeHidden();
    await expect(page.locator("#docs-tab-pane")).toContainText("/software/search");
    await expect(page.locator("#docs-tab-pane")).toContainText("SDS REST API");

    await page.click("#mcp-tab");
    await expect(page.locator("#mcp-tab-pane")).toBeVisible();
    await expect(page.locator("#mcp-url")).toContainText("/mcp");
    await expect(page.locator("#mcp-tab-pane")).toContainText("Authorization: Bearer");
    await expect(page.locator("#mcp-tab-pane")).toContainText("Claude Desktop");
});

test("non-admin cannot reach the API admin page", async ({ page }) => {
    await login(page, DEFAULT_USER);

    const resp = await page.goto("/admin/api");
    expect(resp.status()).toBe(403);

    // Non-admins get no navbar API link, and the settings page has no
    // key-management UI.
    await page.goto("/settings");
    await expect(page.locator('nav a[href="/admin/api"]')).toHaveCount(0);
    await expect(page.locator("#apikeys-tab")).toHaveCount(0);
    await expect(page.locator("#banners-tab")).toHaveCount(0);
});
