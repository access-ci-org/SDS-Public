import { test, expect } from "@playwright/test";
import { seed, BASE_PAYLOAD } from "../helpers/seed.js";

async function seedWithBanners(request, banners) {
    await seed(request, { ...BASE_PAYLOAD, banners });
}

test("software-page banner appears on / and not on /containers", async ({ page, request }) => {
    await seedWithBanners(request, [
        { message: "Software only", severity: "info", pages: "software" },
    ]);

    await page.goto("/");
    await expect(page.locator("#banner-area .alert")).toContainText("Software only");

    await page.goto("/containers");
    await expect(page.locator("#banner-area .alert")).toHaveCount(0);
});

test("all-banner appears on each user-facing page", async ({ page, request }) => {
    await seedWithBanners(request, [
        { message: "Everywhere", severity: "warning", pages: "all-user-facing" },
    ]);

    for (const url of ["/", "/containers", "/login"]) {
        await page.goto(url);
        await expect(page.locator("#banner-area .alert")).toContainText("Everywhere");
    }
});

test("dismissed banner reappears on reload (no persistence)", async ({ page, request }) => {
    await seedWithBanners(request, [
        { message: "Dismiss me", severity: "info", pages: "all-user-facing", dismissible: true },
    ]);

    await page.goto("/");
    await expect(page.locator("#banner-area .alert")).toContainText("Dismiss me");
    await page.locator("#banner-area .alert .btn-close").click();
    await expect(page.locator("#banner-area .alert")).toHaveCount(0);

    // No client-side persistence: the next page load re-fetches and shows it again.
    await page.reload();
    await expect(page.locator("#banner-area .alert")).toContainText("Dismiss me");
});

test("non-dismissible banner has no close button", async ({ page, request }) => {
    await seedWithBanners(request, [
        { message: "Sticky", severity: "danger", pages: "software", dismissible: false },
    ]);

    await page.goto("/");
    const alert = page.locator("#banner-area .alert");
    await expect(alert).toContainText("Sticky");
    await expect(alert.locator(".btn-close")).toHaveCount(0);
});

test("markdown link inside banner is rendered as an anchor", async ({ page, request }) => {
    await seedWithBanners(request, [
        { message: "see [docs](https://example.com)", severity: "info", pages: "software" },
    ]);

    await page.goto("/");
    const link = page.locator('#banner-area .alert a[href="https://example.com"]');
    await expect(link).toHaveText("docs");
});

test("inactive banner does not render", async ({ page, request }) => {
    await seedWithBanners(request, [
        { message: "Hidden", severity: "info", pages: "all-user-facing", is_active: false },
    ]);

    await page.goto("/");
    await expect(page.locator("#banner-area .alert")).toHaveCount(0);
});
