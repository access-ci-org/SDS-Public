import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN } from "../helpers/seed.js";
import { login } from "../helpers/login.js";

// Common XSS payload. If unescaped, this fires a dialog (alert).
// All tests register a dialog listener so the dialog itself fails the test.
const XSS = "<img src=x onerror=window.__xssFired=true>";

async function dialogShouldNotFire(page) {
    // Set a flag from the page side too in case onerror runs before our handler binds.
    await page.addInitScript(() => {
        window.__xssFired = false;
    });
}

async function assertNoXss(page) {
    const fired = await page.evaluate(() => window.__xssFired === true);
    expect(fired, "XSS payload executed in the page").toBe(false);
}

// ---- Software fields (admin-editable + server-stored) ----

test(
    "software name is escaped in the details modal title",
    async ({ page, request }) => {
        await seed(request, {
            software: [
                {
                    name: XSS,
                    description: "x",
                    resources: [{ resource: "test_cluster", version: "1", command: "" }],
                },
            ],
        });
        await dialogShouldNotFire(page);
        await page.goto(`/?software=${encodeURIComponent(XSS)}`);
        await page.waitForTimeout(500);
        await assertNoXss(page);
    }
);

test(
    "description text is escaped in the modal body",
    async ({ page, request }) => {
        await seed(request, {
            software: [
                {
                    name: "victim_desc",
                    description: XSS,
                    resources: [{ resource: "test_cluster", version: "1", command: "" }],
                },
            ],
        });
        await dialogShouldNotFire(page);
        await page.goto("/?software=victim_desc");
        await page.waitForTimeout(500);
        await assertNoXss(page);
    }
);

test(
    "AI fields are escaped in the modal body",
    async ({ page, request }) => {
        await seed(request, {
            software: [
                {
                    name: "victim_ai",
                    description: "x",
                    ai: { ai_description: XSS },
                    resources: [{ resource: "test_cluster", version: "1", command: "" }],
                },
            ],
        });
        await dialogShouldNotFire(page);
        await page.goto("/?software=victim_ai");
        await page.waitForTimeout(500);
        await assertNoXss(page);
    }
);

test(
    "command strings are escaped in the modal version list",
    async ({ page, request }) => {
        await seed(request, {
            software: [
                {
                    name: "victim_cmd",
                    description: "x",
                    resources: [
                        { resource: "test_cluster", version: "1.0.0", command: XSS },
                    ],
                },
            ],
        });
        await dialogShouldNotFire(page);
        await page.goto("/?software=victim_cmd");
        await page.waitForTimeout(500);
        await assertNoXss(page);
    }
);

// ---- Container fields ----

test(
    "container name is escaped on the container search page",
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
                    name: XSS,
                    resource: "test_cluster",
                    definition_file: "lcc/x.def",
                    container_file: "",
                    notes: "",
                    software: [{ software: "any", versions: "1", command: "" }],
                },
            ],
        });
        await dialogShouldNotFire(page);
        await page.goto("/containers");
        await page.waitForTimeout(500);
        await assertNoXss(page);
    }
);

test(
    "container notes are escaped in the details modal",
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
                    name: "notes_victim",
                    resource: "test_cluster",
                    definition_file: "lcc/notes.def",
                    container_file: "",
                    notes: XSS,
                    software: [{ software: "any", versions: "1", command: "" }],
                },
            ],
        });
        await dialogShouldNotFire(page);
        await page.goto("/containers");
        await page
            .locator('.view-details[data-container-name="notes_victim"]')
            .click();
        await page.waitForTimeout(500);
        await assertNoXss(page);
    }
);

// ---- Admin-edited content (payload travels via SoftwareEdit) ----

test(
    "admin-edited description is escaped when rendered",
    async ({ page, request }) => {
        await seed(request, {
            software_edits: [{ software_name: "testpkg", description: XSS }],
        });
        await dialogShouldNotFire(page);
        await login(page, DEFAULT_ADMIN);
        await page.goto("/?software=testpkg");
        await page.waitForTimeout(500);
        await assertNoXss(page);
    }
);
