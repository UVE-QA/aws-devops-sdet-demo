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
  // THREE reporters, and the JSON one is not decoration. The HTML report is
  // evidence for a person; the map's suite nodes are filled by a machine, and
  // scripts/fold-results.py reads this file (ADR-0042 D5). It is written INTO
  // playwright-report/ so that publishing the report publishes the data behind
  // it - one directory, one upload, and a reader can check the picture against
  // the same bytes the picture was drawn from.
  reporter: [
    ["html", { open: "never" }],
    ["json", { outputFile: "playwright-report/results.json" }],
    ["list"],
  ],
  // EVIDENCE FOR THE GREEN RUNS TOO, not only for the red ones.
  //
  // `only-on-failure` and `on-first-retry` are the sensible defaults when a
  // report is something an engineer opens after a failure. Since Phase 11.1c the
  // report is PUBLISHED - it is the artifact an outside reader opens to check a
  // claim, and for them every run is a green one. A pass with nothing behind it
  // is exactly the shape this project distrusts everywhere else: a gate seen only
  // green is indistinguishable from a gate that cannot fail, and a green tick
  // with no trace is indistinguishable from a test that asserted nothing.
  //
  // So a trace and a screenshot are recorded for EVERY test. The trace opens in
  // the report's own viewer, with the DOM snapshot, the network log and the
  // timeline of each step. Video stays failure-only: it is large and shows less
  // than the trace already does.
  //
  // Both are published to a public bucket, so what they capture is public: this
  // application has no authentication, no tokens and no personal data, and the
  // ALB name they contain is already in status/<env>.json. That is a property to
  // RE-CHECK if the app ever grows a login, not a fact that stays true by itself.
  use: {
    baseURL,
    screenshot: "on",
    trace: "on",
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
