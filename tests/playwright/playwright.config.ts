import { defineConfig, devices } from "@playwright/test";

// BASE_URL points at the running app. Default is the local compose app port.
// In AWS this is overridden with the ALB URL (stage) or the public HTTPS name
// (prod).
const baseURL = process.env.BASE_URL || "http://localhost:8000";

// Two projects, split by DIRECTORY, not by a naming convention and not by a
// comment in a workflow:
//
//   smoke        read-only. The ONLY project prod runs.
//   regression   destructive. stage and local compose only.
//
// Before this split, promote-prod.yml ran `npx playwright test` — the whole
// testDir — and its "read-only on purpose" comment was true only because no
// destructive spec existed yet. The first one would have silently made it
// false. The split makes the property structural: a spec is read-only or not
// according to where it lives, and prod selects `--project=smoke`.
//
// A spec file matching NEITHER project would be run by nothing and reported by
// nothing, which is the same silent-pass shape as an empty discovery in
// `make tf-validate`. scripts/assert-spec-coverage.sh fails on it.
export default defineConfig({
  testDir: "./tests",
  // The suites are small and share one database; keep them serial.
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
      name: "smoke",
      testMatch: /[\\/]smoke[\\/].*\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "regression",
      testMatch: /[\\/]regression[\\/].*\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
