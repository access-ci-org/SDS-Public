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
