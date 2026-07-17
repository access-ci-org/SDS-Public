import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN, DEFAULT_USER } from "../helpers/seed.js";
import { login } from "../helpers/login.js";

test.beforeEach(async ({ request }) => {
    await seed(request);
});

async function openApiKeysTab(page) {
    await page.goto("/settings");
    await page.click("#apikeys-tab");
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
    await openApiKeysTab(page);

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
    await openApiKeysTab(page);

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

test("non-admin user does not see the API keys or banners tabs", async ({ page }) => {
    await login(page, DEFAULT_USER);
    await page.goto("/settings");

    await expect(page.locator("#user-tab")).toBeVisible();
    await expect(page.locator("#apikeys-tab")).toHaveCount(0);
    await expect(page.locator("#banners-tab")).toHaveCount(0);
});
