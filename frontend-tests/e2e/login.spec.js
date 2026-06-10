import { test, expect } from "@playwright/test";
import { seed, DEFAULT_ADMIN } from "../helpers/seed.js";

test.beforeEach(async ({ request }) => {
    await seed(request);
});

test("login form is visible at /login", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
});

test("valid credentials redirect away from /login", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[name="username"]', DEFAULT_ADMIN.username);
    await page.fill('input[name="password"]', DEFAULT_ADMIN.password);
    await Promise.all([
        page.waitForURL((url) => !url.pathname.includes("/login")),
        page.click('button[type="submit"], input[type="submit"]'),
    ]);
    expect(page.url()).not.toContain("/login");
});

test("invalid credentials show an error flash", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[name="username"]', "nope");
    await page.fill('input[name="password"]', "wrong");
    await page.click('button[type="submit"], input[type="submit"]');
    await expect(page.locator("body")).toContainText(/invalid/i);
});

test("logout returns to anonymous state", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[name="username"]', DEFAULT_ADMIN.username);
    await page.fill('input[name="password"]', DEFAULT_ADMIN.password);
    await page.click('button[type="submit"], input[type="submit"]');
    await page.waitForURL((url) => !url.pathname.includes("/login"));

    await page.goto("/logout");
    await page.goto("/admin/software");
    // Should bounce to login or be denied
    expect(page.url()).toMatch(/login|^.*\/$/);
});
