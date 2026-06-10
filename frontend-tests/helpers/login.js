export async function login(page, { username, password }) {
    await page.goto("/login");
    await page.fill('input[name="username"]', username);
    await page.fill('input[name="password"]', password);
    await Promise.all([
        page.waitForURL((url) => !url.pathname.includes("/login")),
        page.click('button[type="submit"], input[type="submit"]'),
    ]);
}

export async function logout(page) {
    await page.goto("/logout");
}
