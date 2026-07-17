import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN, DEFAULT_USER } from "../helpers/seed.js";
import { login, logout } from "../helpers/login.js";

test.beforeEach(async ({ request }) => {
    await seed(request);
});

async function openAdminPanel(page, softwareName) {
    await page.goto(`/?software=${softwareName}`);
    await expect(page.locator("#admin-edit-panel")).toBeVisible({ timeout: 10_000 });
}

// What a logged-out visitor sees in the details modal must match what the
// admin saved — the edit panel and the modal read through different code
// paths, so every save test also asserts the user-facing surface.
async function assertAnonModalShows(page, softwareName, text) {
    await logout(page);
    await page.goto(`/?software=${softwareName}`);
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    await expect(page.locator("#admin-edit-panel")).toHaveCount(0);
    await expect(page.locator("#software-data")).toContainText(text);
}

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
    await openAdminPanel(page, "testpkg");

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

test("saved description reaches the user-facing modal", async ({ page }) => {
    await login(page, DEFAULT_ADMIN);
    await openAdminPanel(page, "testpkg");

    await page.fill(
        '#admin-edit-panel textarea[name="description"]',
        "cross-surface description"
    );
    await page.click('#admin-edit-panel button[type="submit"]');
    await expect(page.locator("#admin-edit-panel .source-admin").first()).toBeVisible({
        timeout: 5000,
    });

    await assertAnonModalShows(page, "testpkg", "cross-surface description");
});

test("saved AI research field reaches the user-facing modal", async ({ page }) => {
    // ai_research_field has no section of its own; it folds into the
    // RESEARCH DISCIPLINE section, so its value must still surface.
    await login(page, DEFAULT_ADMIN);
    await openAdminPanel(page, "testpkg");

    await page.click("#admin-edit-panel #tab-ai-btn");
    // ai_research_field renders as an <input>, not a <textarea>
    await page.fill(
        '#admin-edit-panel [name="ai_research_field"]',
        "Computational Genomics"
    );
    await page.click('#admin-edit-panel button[type="submit"]');
    // The saved override shows up in the AI tab's edit count after the swap.
    await expect(page.locator("#admin-edit-panel #tab-ai-btn .tab-edit-count")).toContainText(
        "1 edited",
        { timeout: 5000 }
    );

    await assertAnonModalShows(page, "testpkg", "Computational Genomics");
});

test("AI field saved for software without AI data reaches the modal", async ({
    page,
    request,
}) => {
    // No AISoftwareInfo row exists for this software; saving an AI field
    // must still reach the user-facing display. The curated description is
    // seeded empty because the DESCRIPTION section prefers it over
    // ai_description when both are present.
    await seed(request, {
        software: [
            {
                name: "noai_pkg",
                description: "",
                resources: [
                    { resource: "test_cluster", version: "1.0.0", command: "" },
                ],
            },
        ],
    });
    await login(page, DEFAULT_ADMIN);
    await openAdminPanel(page, "noai_pkg");

    await page.click("#admin-edit-panel #tab-ai-btn");
    await page.fill(
        '#admin-edit-panel [name="ai_description"]',
        "first AI value"
    );
    await page.click('#admin-edit-panel button[type="submit"]');
    await expect(page.locator("#admin-edit-panel #tab-ai-btn .tab-edit-count")).toContainText(
        "1 edited",
        { timeout: 5000 }
    );

    await assertAnonModalShows(page, "noai_pkg", "first AI value");
});

test("admin revert restores the auto value in panel and modal", async ({
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
    await openAdminPanel(page, "testpkg");

    // Override badge should be present for description
    await expect(
        page.locator('#admin-edit-panel [id="field-description"] .source-admin')
    ).toBeVisible();

    // Click Revert (confirm dialog auto-accepted)
    page.on("dialog", (d) => d.accept());
    await page.click('#admin-edit-panel [id="field-description"] .revert-link');

    // After revert the field shows the auto badge and the auto value again.
    await expect(
        page.locator('#admin-edit-panel [id="field-description"] .source-auto')
    ).toBeVisible({ timeout: 5000 });
    await expect(
        page.locator('#admin-edit-panel textarea[name="description"]')
    ).toHaveValue("A test package");

    await assertAnonModalShows(page, "testpkg", "A test package");
    await expect(page.locator("#software-data")).not.toContainText("overridden via seed");
});
