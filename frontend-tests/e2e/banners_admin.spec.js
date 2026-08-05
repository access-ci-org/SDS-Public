import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN } from "../helpers/seed.js";
import { login } from "../helpers/login.js";

async function openBannersTab(page) {
    await page.goto("/settings");
    await page.click("#banners-tab");
    await expect(page.locator("#banners-tab-content")).toBeVisible();
}

test("created banner appears on the software page", async ({ page, request }) => {
    await seed(request);
    await login(page, DEFAULT_ADMIN);
    await openBannersTab(page);

    await page.fill("#banner-new-message", "E2E created banner");
    await page.check("#banner-new-page-all");
    await page.click('#banner-new button[type="submit"]');

    // HTMX swaps the tab content; the new banner shows under Existing Banners.
    await expect(
        page.locator(".banner-row", { hasText: "E2E created banner" })
    ).toBeVisible();

    await page.goto("/");
    await expect(page.locator("#banner-area")).toContainText("E2E created banner");
});

test("specific-page checkboxes fire no column-settings requests", async ({ page, request }) => {
    await seed(request);
    await login(page, DEFAULT_ADMIN);
    await openBannersTab(page);

    const strayRequests = [];
    page.on("request", (req) => {
        if (req.url().includes("/update_col_visibility")) strayRequests.push(req.url());
    });

    await page.fill("#banner-new-message", "Specific pages banner");
    await page.check("#banner-new-page-software");
    await page.check("#banner-new-page-container");
    await page.click('#banner-new button[type="submit"]');

    // The success notice arrives after a server round-trip, by which point
    // any change-triggered request would already have been sent.
    await expect(
        page.locator(".alert-success", { hasText: "Banner created." })
    ).toBeVisible();
    expect(strayRequests).toEqual([]);
    await expect(
        page.locator(".alert", { hasText: "Error updating column" })
    ).toHaveCount(0);
});

test("deactivated banner disappears from the software page", async ({ page, request }) => {
    await seed(request, {
        banners: [{ message: "Seeded active banner", pages: "all-user-facing" }],
    });
    await login(page, DEFAULT_ADMIN);

    await page.goto("/");
    await expect(page.locator("#banner-area")).toContainText("Seeded active banner");

    await openBannersTab(page);
    const row = page.locator(".banner-row", { hasText: "Seeded active banner" });
    await row.locator('button:has-text("Deactivate")').click();
    await expect(row.locator(".badge", { hasText: "inactive" })).toBeVisible();

    // No active banners left, so the banner area is not rendered at all.
    await page.goto("/");
    await expect(page.locator("#banner-area")).toHaveCount(0);
});

test("deleted banner row is removed from the banners tab", async ({ page, request }) => {
    await seed(request, {
        banners: [{ message: "Banner to delete", pages: "all-user-facing" }],
    });
    await login(page, DEFAULT_ADMIN);
    await openBannersTab(page);

    // hx-confirm uses window.confirm.
    page.on("dialog", (dialog) => dialog.accept());
    const row = page.locator(".banner-row", { hasText: "Banner to delete" });
    await row.locator('button:has-text("Delete")').click();

    await expect(page.locator(".banner-row")).toHaveCount(0);
    await expect(page.locator("#banners-tab-content")).toContainText("No banners yet");
});
