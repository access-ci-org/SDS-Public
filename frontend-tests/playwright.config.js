import { defineConfig, devices } from "@playwright/test";

const PORT = process.env.SDS_E2E_PORT || "5001";
const BASE_URL = `http://localhost:${PORT}`;

export default defineConfig({
    testDir: "./e2e",
    fullyParallel: false,
    workers: 1,
    timeout: 30 * 1000,
    expect: { timeout: 5 * 1000 },
    reporter: [["list"]],
    use: {
        baseURL: BASE_URL,
        screenshot: "only-on-failure",
        trace: "retain-on-failure",
        video: "off",
    },
    projects: [
        { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    ],
    webServer: {
        command: `flask --app app run --port ${PORT}`,
        cwd: "..",
        url: `${BASE_URL}/__test__/ping`,
        reuseExistingServer: !process.env.CI,
        timeout: 60 * 1000,
        env: {
            TESTING: "1",
            SDS_DATA_DIR: "/tmp/sds_e2e_db",
            FLASK_DEBUG: "0",
            // The AI display surface is under test; force the flags on
            // regardless of the local config.yaml.
            SDS_USE_API: "1",
            SDS_USE_AI_INFO: "1",
        },
    },
});
