import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN } from "../helpers/seed.js";
import { login, logout } from "../helpers/login.js";

const NAMED_SOFTWARE = [
    { name: "alpha-one" },
    { name: "alpha-two" },
    { name: "beta-one" },
];

async function gotoOverview(page) {
    await page.goto("/admin/software");
    await expect(page.locator(".sw-table")).toBeVisible();
}

// Software-name links in the list; one per row.
const rowLinks = (page) => page.locator(".sw-table .sw-name a");

test("search filters the software list by name", async ({ page, request }) => {
    await seed(request, { software: NAMED_SOFTWARE });
    await login(page, DEFAULT_ADMIN);
    await gotoOverview(page);
    await expect(rowLinks(page)).toHaveCount(3);

    await page.fill('input[name="search"]', "alpha");
    await page.click('.filter-bar button[type="submit"]');

    await expect(rowLinks(page)).toHaveCount(2);
    await expect(rowLinks(page).filter({ hasText: "beta-one" })).toHaveCount(0);
});

test("overrides filter shows only software with admin edits", async ({ page, request }) => {
    await seed(request, {
        software: NAMED_SOFTWARE,
        software_edits: [{ software_name: "alpha-one", description: "edited desc" }],
    });
    await login(page, DEFAULT_ADMIN);
    await gotoOverview(page);
    await expect(rowLinks(page)).toHaveCount(3);

    // The filter select auto-submits on change.
    await page.selectOption('select[name="filter"]', "overrides");
    await page.waitForURL(/filter=overrides/);

    await expect(rowLinks(page)).toHaveCount(1);
    await expect(rowLinks(page).first()).toHaveText("alpha-one");
    await expect(page.locator(".ov-badge-admin")).toHaveText("1 edited");
});

test("export downloads sds_overrides.json", async ({ page, request }) => {
    await seed(request, {
        software: NAMED_SOFTWARE,
        software_edits: [{ software_name: "alpha-one", description: "edited desc" }],
    });
    await login(page, DEFAULT_ADMIN);
    await gotoOverview(page);

    const downloadPromise = page.waitForEvent("download");
    await page.click('a.btn-primary-ov[href*="export"]');
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toContain("sds_overrides.json");
});

test("imported override reaches the overview and the user-facing modal", async ({ page, request }) => {
    await seed(request);
    await login(page, DEFAULT_ADMIN);
    await gotoOverview(page);

    const payload = {
        software_edits: [{ software_name: "testpkg", description: "imported via e2e" }],
        command_edits: [],
    };
    await page.setInputFiles("#import-file-input", {
        name: "sds_overrides.json",
        mimeType: "application/json",
        buffer: Buffer.from(JSON.stringify(payload)),
    });
    await page.click('#import-form button[type="submit"]');

    // The import redirects back to the overview; the override count reflects it.
    await expect(page.locator(".ov-badge-admin")).toHaveText("1 edited", { timeout: 10_000 });

    // Import writes through to the live tables, so a logged-out visitor
    // sees the imported description in the details modal.
    await logout(page);
    await page.goto("/?software=testpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    await expect(page.locator("#software-data")).toContainText("imported via e2e");
});

test("pagination advances to the next page", async ({ page, request }) => {
    const many = Array.from({ length: 30 }, (_, i) => ({
        name: `pkg-${String(i).padStart(2, "0")}`,
    }));
    await seed(request, { software: many });
    await login(page, DEFAULT_ADMIN);
    await gotoOverview(page);

    await expect(rowLinks(page)).toHaveCount(25);

    await page.click('a.btn-ov-edit:has-text("Next")');

    await expect(rowLinks(page)).toHaveCount(5);
    await expect(page.locator(".pagination-bar")).toContainText("of 30");
});
