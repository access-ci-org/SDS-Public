import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN, DEFAULT_USER } from "../helpers/seed.js";
import { login, logout } from "../helpers/login.js";

test.beforeEach(async ({ request }) => {
    await seed(request);
});

test("non-admin user does NOT see the admin edit panel", async ({ page }) => {
    await login(page, DEFAULT_USER);
    await page.goto("/?software=testpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    await expect(page.locator("#admin-edit-panel")).toHaveCount(0);
});

test("admin sees the admin edit panel injected via HTMX", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await page.goto("/?software=testpkg");
    await expect(page.locator("#admin-edit-panel")).toBeVisible({ timeout: 10_000 });
});

test("admin save persists across reload", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await page.goto("/?software=testpkg");
    await expect(page.locator("#admin-edit-panel")).toBeVisible({ timeout: 10_000 });

    const desc = page.locator('#admin-edit-panel textarea[name="description"]');
    await desc.fill("edited via e2e");
    await page.click('#admin-edit-panel button[type="submit"]');

    // Wait for the HTMX swap to update the panel
    await expect(page.locator("#admin-edit-panel .source-admin").first()).toBeVisible({
        timeout: 5000,
    });

    // Reload the page and reopen the modal; the override should still be there.
    await page.goto("/?software=testpkg");
    await expect(page.locator("#admin-edit-panel")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('#admin-edit-panel textarea[name="description"]')).toHaveValue(
        "edited via e2e"
    );
});

test("admin revert removes the override (auto-value restore is xfail)", async ({
    page,
    request,
}) => {
    // Seed with an existing override
    await seed(request, {
        software: [
            {
                name: "testpkg",
                description: "A test package",
                resources: [
                    {
                        resource: "test_cluster",
                        version: "1.0.0",
                        command: "module load testpkg/1.0.0",
                    },
                ],
            },
        ],
        software_edits: [
            { software_name: "testpkg", description: "overridden via seed" },
        ],
    });
    await login(page, DEFAULT_ADMIN);
    await page.goto("/?software=testpkg");
    await expect(page.locator("#admin-edit-panel")).toBeVisible({ timeout: 10_000 });

    // Override badge should be present for description
    await expect(
        page.locator('#admin-edit-panel [id="field-description"] .source-admin')
    ).toBeVisible();

    // Click Revert (confirm dialog auto-accepted)
    page.on("dialog", (d) => d.accept());
    await page.click('#admin-edit-panel [id="field-description"] .revert-link');

    // After revert, the description field should no longer show the admin badge.
    await expect(
        page.locator('#admin-edit-panel [id="field-description"] .source-auto')
    ).toBeVisible({ timeout: 5000 });
});
