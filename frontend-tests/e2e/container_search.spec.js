import { test, expect } from "@playwright/test";
import { seed } from "../helpers/seed.js";

test.beforeEach(async ({ request }) => {
    await seed(request, {
        resources: ["test_cluster", "gpu_cluster"],
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
        containers: [
            {
                name: "alpha_container",
                resource: "test_cluster",
                definition_file: "lcc/alpha.def",
                container_file: "lcc/alpha.sif",
                notes: "alpha notes",
                software: [{ software: "testpkg", versions: "1.0.0", command: "" }],
            },
            {
                name: "beta_container",
                resource: "gpu_cluster",
                definition_file: "lcc/beta.def",
                container_file: "lcc/beta.sif",
                notes: "",
                software: [{ software: "testpkg", versions: "1.0.0", command: "" }],
            },
        ],
    });
});

test("container grid renders both containers", async ({ page }) => {
    await page.goto("/containers");
    await expect(page.locator("#containerGrid")).toContainText("alpha_container");
    await expect(page.locator("#containerGrid")).toContainText("beta_container");
});

test("resource select filters containers", async ({ page }) => {
    await page.goto("/containers");
    await page.selectOption("#resourceSelect", "gpu_cluster");
    await expect(page.locator("#containerGrid")).toContainText("beta_container");
    await expect(page.locator("#containerGrid")).not.toContainText("alpha_container");
});

test("search input adds a tag and filters", async ({ page }) => {
    await page.goto("/containers");
    await page.fill("#searchInput", "alpha");
    await page.keyboard.press("Enter");
    await expect(page.locator("#containerGrid")).toContainText("alpha_container");
    await expect(page.locator("#containerGrid")).not.toContainText("beta_container");
});

test("View Details opens the single-container modal", async ({ page }) => {
    await page.goto("/containers");
    await page
        .locator('.view-details[data-container-name="alpha_container"]')
        .click();
    await expect(page.locator("#containerDetailsModal")).toBeVisible();
    await expect(page.locator("#containerDetailsModal")).toContainText("alpha_container");
});
