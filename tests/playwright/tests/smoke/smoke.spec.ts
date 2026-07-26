import { test, expect } from "@playwright/test";

// Smoke test against a running app (local compose or ALB via BASE_URL).
// Verifies the page renders and that the async health/DB checks resolve.
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
});
