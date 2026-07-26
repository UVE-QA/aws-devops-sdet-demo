import { test, expect } from "@playwright/test";

// READ-ONLY. This file lives under tests/smoke/ and is therefore in the
// `smoke` project (see playwright.config.ts) — the only project prod runs.
// Nothing here may create, modify or delete data. Destructive coverage goes
// to tests/regression/, which prod never executes (ADR-0025).
test.describe("aws-devops-sdet-demo smoke", () => {
  test("page loads and health/db statuses resolve", async ({ page }) => {
    await page.goto("/");

    // 1. Title is present and correct.
    const title = page.getByTestId("app-title");
    await expect(title).toBeVisible();
    await expect(title).toContainText("AWS DevOps SDET Demo");

    // 2. API health status element is visible and reports ok.
    const apiHealth = page.getByTestId("api-health-status");
    await expect(apiHealth).toBeVisible();
    await expect(apiHealth).toContainText(/ok/i, { timeout: 15000 });

    // 3. DB check status is visible and eventually reports connected/ok.
    //    The frontend fetches /api/db-check asynchronously, and the DB may
    //    take a moment after startup, so allow a generous timeout.
    const dbCheck = page.getByTestId("db-check-status");
    await expect(dbCheck).toBeVisible();
    await expect(dbCheck).toContainText(/connected|ok/i, { timeout: 30000 });
  });

  test("the items list renders and contains the seeded row", async ({ page }) => {
    await page.goto("/");

    // data-loaded is set by the page once a list response has been rendered,
    // so this waits on a real signal rather than on a timer.
    const table = page.getByTestId("items-table");
    await expect(table).toHaveAttribute("data-loaded", "true", { timeout: 30000 });

    // The seed row is provisioning, not a test fixture (ADR-0017 D2a), and
    // exists in every environment after the seed task. Seeing it in the
    // browser proves the whole path — browser, ALB, app, RDS — read-only.
    await expect(
      page.getByTestId("item-name").filter({ hasText: "seed-item-001" })
    ).toHaveCount(1);
  });
});
