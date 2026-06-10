import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN } from "../helpers/seed.js";
import { login } from "../helpers/login.js";

test.beforeEach(async ({ request }) => {
    await seed(request);
});

test("logged-in user can view settings", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await page.goto("/settings");
    await expect(page.locator("body")).toContainText(/settings/i);
});

test("download CSV button triggers a file download", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await page.goto("/settings");
    // The download button lives inside the "Download Data" tab; switch to it first.
    await page.click("#download-tab");
    const [download] = await Promise.all([
        page.waitForEvent("download"),
        page.click("#download-software-csv"),
    ]);
    expect(download.suggestedFilename()).toContain(".csv");
});

test.fixme(
    "column rename persists across reload",
    async ({ page }) => {
        // xfail until AppSettings table ships
    }
);
