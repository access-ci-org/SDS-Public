import { test, expect } from "@playwright/test";
import { seed } from "../helpers/seed.js";

test.beforeEach(async ({ request }) => {
    await seed(request);
});

test("modal shows the software description", async ({ page }) => {
    await page.goto("/?software=testpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    await expect(page.locator("#software-data")).toContainText("A test package");
});

test("modal URL state reflects the open software", async ({ page }) => {
    await page.goto("/?software=testpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    expect(page.url()).toContain("software=testpkg");
});

test("closing the modal clears the URL software param", async ({ page }) => {
    await page.goto("/?software=testpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();

    // Click the modal close button (Bootstrap's data-bs-dismiss)
    await page.locator('#softwareDetails-modal [data-bs-dismiss="modal"]').first().click();
    await expect(page.locator("#softwareDetails-modal")).toBeHidden();
    expect(new URL(page.url()).searchParams.has("software")).toBe(false);
});

test("multi-command software shows '+N more' expander", async ({ page, request }) => {
    await seed(request, {
        software: [
            {
                name: "multicmd",
                description: "multi-command pkg",
                resources: [
                    {
                        resource: "test_cluster",
                        version: "2.0.0",
                        command: "module load multicmd/2.0.0, module load deps",
                    },
                ],
            },
        ],
    });
    await page.goto("/?software=multicmd");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    await expect(page.locator("button[data-cmd-target]")).toContainText(/more/);
});
