import { defineConfig } from "vitest/config";

export default defineConfig({
    test: {
        environment: "node",
        include: ["unit/**/*.spec.js"],
        // E2E (Playwright) lives in e2e/ and is run by Playwright, not Vitest.
    },
});
