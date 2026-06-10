import { test, expect } from "@playwright/test";
import { seed } from "../helpers/seed.js";

test.beforeEach(async ({ request }) => {
    await seed(request, {
        resources: ["test_cluster"],
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
                name: "c1",
                resource: "test_cluster",
                definition_file: "lcc/c1.def",
                container_file: "",
                notes: "",
                software: [{ software: "testpkg", versions: "1.0.0", command: "" }],
            },
            {
                name: "c2",
                resource: "test_cluster",
                definition_file: "lcc/c2.def",
                container_file: "",
                notes: "",
                software: [{ software: "testpkg", versions: "1.0.0", command: "" }],
            },
        ],
    });
});

test("multi-container modal renders an accordion item per container", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector("#softwareTable tbody tr");
    await page.click("#softwareTable a.viewContainer");
    await expect(page.locator("#container-modal")).toBeVisible();
    const items = page.locator("#container-accordion .accordion-item");
    await expect(items).toHaveCount(2);
});
