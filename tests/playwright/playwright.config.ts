import { defineConfig, devices } from "@playwright/test";

// BASE_URL points at the running app. Default is the local compose app port.
// In AWS stage this is overridden with the ALB URL.
const baseURL = process.env.BASE_URL || "http://localhost:8000";

export default defineConfig({
  testDir: "./tests",
  // Smoke suite is small; keep it serial and give the DB time to come up.
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL,
    screenshot: "only-on-failure",
    trace: "on-first-retry",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
