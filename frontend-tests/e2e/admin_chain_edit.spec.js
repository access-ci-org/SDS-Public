import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN } from "../helpers/seed.js";
import { login } from "../helpers/login.js";

// Two collected load routes for one version; the admin panel's Resource
// Commands tab exposes per-chain controls over them.
const CHAIN_SOFTWARE = {
    name: "chainpkg",
    description: "chain-edit pkg",
    resources: [
        {
            resource: "test_cluster",
            version: "1.0",
            command: "module load chainpkg/1.0",
            load_commands: [
                "module load chainpkg/1.0",
                "module load gcc/12.3.0 chainpkg/1.0",
            ],
        },
    ],
};

async function seedAndOpenCommandsTab(page, request, extra = {}) {
    await seed(request, { software: [CHAIN_SOFTWARE], ...extra });
    await login(page, DEFAULT_ADMIN);
    await page.goto("/?software=chainpkg");
    await expect(page.locator("#admin-edit-panel")).toBeVisible({ timeout: 10_000 });
    await page.locator("#tab-cmd-btn").click();
}

async function saveAndWait(page) {
    // wait on the PUT itself: navigating away too early would abort the
    // in-flight HTMX request and lose the save
    const done = page.waitForResponse(
        (resp) =>
            resp.url().includes("/admin/edit/software/") &&
            resp.request().method() === "PUT"
    );
    await page.locator(".btn-save").click();
    await done;
}

test("hiding a chain removes it from the details modal", async ({ page, request }) => {
    await seedAndOpenCommandsTab(page, request);
    await page.locator('input[name="block__0__chain__1__hide"]').check();
    await saveAndWait(page);

    await page.goto("/?software=chainpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    await expect(
        page.locator("#softwareDetails-modal")
    ).toContainText("module load chainpkg/1.0");
    // only one command left: no expander
    await expect(page.locator("button[data-cmd-target]")).toHaveCount(0);
});

test("adding a command shows it in the details modal", async ({ page, request }) => {
    await seedAndOpenCommandsTab(page, request);
    await page.locator('input[name="block__0__new"]').fill("run-chainpkg.sh");
    await saveAndWait(page);

    await page.goto("/?software=chainpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    const expander = page.locator("button[data-cmd-target]");
    await expect(expander).toContainText("+ 2 more");
    await expander.click();
    await expect(page.locator("#softwareDetails-modal")).toContainText("run-chainpkg.sh");
});

test("picking a primary chain reorders the modal list", async ({ page, request }) => {
    await seedAndOpenCommandsTab(page, request);
    await page.locator('input[name="block__0__primary"][value="chain__1"]').check();
    await saveAndWait(page);

    await page.goto("/?software=chainpkg");
    await expect(page.locator("#softwareDetails-modal")).toBeVisible();
    // the chained route now shows first; the direct load sits behind
    // the expander
    await expect(
        page.locator('[aria-label="Command for software"]')
    ).toContainText("module load gcc/12.3.0 chainpkg/1.0");
});

test("stale override is listed and deletable", async ({ page, request }) => {
    await seedAndOpenCommandsTab(page, request, {
        command_edits: [
            {
                software_name: "chainpkg",
                resource_name: "test_cluster",
                software_version: "1.0",
                target_command: "module load gone/9.9 chainpkg/1.0",
                suppressed: true,
            },
        ],
    });

    const stale = page.locator("#stale-overrides");
    await expect(stale).toBeVisible();
    await expect(stale).toContainText("module load gone/9.9 chainpkg/1.0");

    page.on("dialog", (dialog) => dialog.accept());
    const done = page.waitForResponse(
        (resp) =>
            resp.url().includes("/command_edit/") &&
            resp.request().method() === "DELETE"
    );
    await stale.locator(".revert-link").click();
    await done;
    await expect(page.locator("#stale-overrides")).toHaveCount(0);
});
