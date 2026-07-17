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

test("every AI field's content is visible in the modal", async ({ page, request }) => {
    // Fields without a dedicated section fold into another one (research
    // field/area into RESEARCH DISCIPLINE, software class into SOFTWARE
    // TYPE); every value must surface somewhere in the modal. The curated
    // description is seeded empty because the DESCRIPTION section prefers
    // it over ai_description when both are present.
    await seed(request, {
        software: [
            {
                name: "aifull",
                description: "",
                ai: {
                    ai_description: "AI-DESC-MARKER",
                    ai_software_type: "TYPE-MARKER",
                    ai_software_class: "CLASS-MARKER",
                    ai_research_field: "FIELD-MARKER",
                    ai_research_area: "AREA-MARKER",
                    ai_research_discipline: "DISCIPLINE-MARKER",
                    ai_core_features: "FEATURES-MARKER",
                    ai_general_tags: "tagone, tagtwo",
                    ai_example_use: "EXAMPLE-USE-MARKER",
                },
                resources: [
                    { resource: "test_cluster", version: "1.0.0", command: "m" },
                ],
            },
        ],
    });
    await page.goto("/?software=aifull");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();

    const modal = page.locator("#softwareDetails-modal");
    for (const marker of [
        "AI-DESC-MARKER",
        "TYPE-MARKER",
        "CLASS-MARKER",
        "FIELD-MARKER",
        "AREA-MARKER",
        "DISCIPLINE-MARKER",
        "FEATURES-MARKER",
        "tagone",
    ]) {
        await expect(modal).toContainText(marker);
    }
});

test("multi-command software shows '+N more' expander", async ({ page, request }) => {
    // command holds only the canonical one; the extra route arrives via
    // load_commands, so the expander proves the modal reads the list
    await seed(request, {
        software: [
            {
                name: "multicmd",
                description: "multi-command pkg",
                resources: [
                    {
                        resource: "test_cluster",
                        version: "2.0.0",
                        command: "module load multicmd/2.0.0",
                        load_commands: [
                            "module load multicmd/2.0.0",
                            "module load gcc/12.3.0 multicmd/2.0.0",
                        ],
                    },
                ],
            },
        ],
    });
    await page.goto("/?software=multicmd");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    const expander = page.locator("button[data-cmd-target]");
    await expect(expander).toContainText("+ 1 more");
    await expander.click();
    await expect(
        page.locator("#softwareDetails-modal")
    ).toContainText("module load gcc/12.3.0 multicmd/2.0.0");
});
