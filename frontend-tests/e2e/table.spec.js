import { test, expect } from "@playwright/test";
import { seed } from "../helpers/seed.js";

test.beforeEach(async ({ request }) => {
    await seed(request);
});

test("software name appears in the main table", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#softwareTable")).toBeVisible();
    await expect(page.locator("#softwareTable tbody")).toContainText("testpkg");
});

test("global search filters the table", async ({ page }) => {
    await seed(page.request, {
        software: [
            {
                name: "alpha",
                description: "alpha desc",
                resources: [{ resource: "test_cluster", version: "1", command: "" }],
            },
            {
                name: "beta",
                description: "beta desc",
                resources: [{ resource: "test_cluster", version: "1", command: "" }],
            },
        ],
    });
    await page.goto("/");
    await page.waitForSelector("#softwareTable tbody tr");

    await page.fill(".dt-search input", "alpha");
    // Wait a beat for DataTables filter
    await page.waitForTimeout(300);

    const bodyText = await page.locator("#softwareTable tbody").innerText();
    expect(bodyText).toContain("alpha");
    expect(bodyText).not.toContain("beta");
});

test("DETAILS button opens the software details modal", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("#softwareTable tbody tr");
    await page.click('#softwareTable button.primary-button:has-text("DETAILS")');
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    await expect(page.locator("#software-modal-title")).toContainText("testpkg");
});

test("?software= deep link opens the modal on first paint", async ({ page }) => {
    await page.goto("/?software=testpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    await expect(page.locator("#software-modal-title")).toContainText("testpkg");
});
