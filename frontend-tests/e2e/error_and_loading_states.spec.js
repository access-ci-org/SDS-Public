import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN } from "../helpers/seed.js";
import { login } from "../helpers/login.js";

test.beforeEach(async ({ request }) => {
    await seed(request);
});

// ---- Loading states ----

test(
    "modal opens immediately with a spinner while data fetches",
    async ({ page }) => {
        // Throttle the modal data endpoint so the spinner stays visible.
        await page.route("**/software_info/**", async (route) => {
            await new Promise((r) => setTimeout(r, 1500));
            await route.continue();
        });
        await page.goto("/");
        await page.waitForSelector("#softwareTable tbody tr");
        await page.click('#softwareTable button.primary-button:has-text("DETAILS")');
        // Spec: modal becomes visible immediately, before the data resolves.
        await expect(page.locator("#softwareDetails-modal")).toBeVisible({
            timeout: 500,
        });
    }
);

// ---- Error visibility ----

test(
    "software_info failure surfaces a visible error (not silent)",
    async ({ page }) => {
        await page.route("**/software_info/**", (route) => route.abort("failed"));
        await page.goto("/");
        await page.waitForSelector("#softwareTable tbody tr");
        await page.click('#softwareTable button.primary-button:has-text("DETAILS")');
        // Spec: showAlert appears with a user-visible error
        await expect(page.locator("#alert-div .alert")).toBeVisible({
            timeout: 5000,
        });
    }
);

test(
    "container detail failure surfaces a visible error",
    async ({ page, request }) => {
        await seed(request, {
            resources: ["test_cluster"],
            software: [
                {
                    name: "any",
                    description: "x",
                    resources: [{ resource: "test_cluster", version: "1", command: "" }],
                },
            ],
            containers: [
                {
                    name: "c1",
                    resource: "test_cluster",
                    definition_file: "lcc/c1.def",
                    container_file: "",
                    notes: "",
                    software: [{ software: "any", versions: "1", command: "" }],
                },
            ],
        });
        await page.route("**/container_details", (route) => route.abort("failed"));
        await page.goto("/containers");
        await page.locator('.view-details[data-container-name="c1"]').click();
        await expect(page.locator("#alert-div .alert")).toBeVisible({
            timeout: 5000,
        });
    }
);

test(
    "admin save failure surfaces a visible error",
    async ({ page }) => {
        await login(page, DEFAULT_ADMIN);
        await page.goto("/?software=testpkg");
        await expect(page.locator("#admin-edit-panel")).toBeVisible({
            timeout: 10_000,
        });
        await page.route("**/admin/edit/software/**", (route) =>
            route.fulfill({ status: 500, body: "boom" })
        );
        await page
            .locator('#admin-edit-panel textarea[name="description"]')
            .fill("anything");
        await page.click('#admin-edit-panel button[type="submit"]');
        await expect(page.locator("#alert-div .alert")).toBeVisible({
            timeout: 5000,
        });
    }
);

// ---- Sanity: tests that should pass today (not xfail) ----

test("modal opens for a known software (happy path)", async ({ page }) => {
    await page.goto("/?software=testpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
});
