import { test, expect } from "@playwright/test";

// DESTRUCTIVE. This file lives under tests/regression/ and is therefore in the
// `regression` project, which runs against stage and NEVER against prod
// (ADR-0025). stage is seeded and disposable; prod is promoted and public.

// The probe item is created here through the UI and deliberately NOT deleted.
// A separate step then asserts the row exists in the database, which is what
// makes the claim "the UI reached RDS" a measurement rather than an inference:
// the browser wrote it, and a different process, connecting straight to
// PostgreSQL, found it.
const probeName = process.env.UI_PROBE_NAME;

test.beforeAll(() => {
  if (!probeName) {
    throw new Error(
      "UI_PROBE_NAME is not set. The database assertion that follows this " +
        "suite looks up exactly this name; without it the assertion would " +
        "check nothing and pass. Set it in the caller (Makefile or workflow)."
    );
  }
});

async function waitForList(page) {
  const table = page.getByTestId("items-table");
  await expect(table).toHaveAttribute("data-loaded", "true", { timeout: 30000 });
  return table;
}

async function createItem(page, name: string, description?: string) {
  await page.getByTestId("new-item-name").fill(name);
  if (description) {
    await page.getByTestId("new-item-description").fill(description);
  }
  await page.getByTestId("create-item").click();
}

test.describe("items regression (destructive, stage only)", () => {
  test("create through the UI leaves a row for the database assertion", async ({
    page,
  }) => {
    await page.goto("/");
    await waitForList(page);

    await createItem(page, probeName!, "written by the UI regression");

    await expect(page.getByTestId("items-message")).toContainText(probeName!);
    await expect(
      page.getByTestId("item-name").filter({ hasText: probeName! })
    ).toHaveCount(1);

    // Survives a reload: the row came from the server, not from local state.
    await page.reload();
    await waitForList(page);
    await expect(
      page.getByTestId("item-name").filter({ hasText: probeName! })
    ).toHaveCount(1);
  });

  test("create, appears in the list, delete, gone", async ({ page }) => {
    const name = `regression-${Date.now()}`;

    await page.goto("/");
    await waitForList(page);

    await createItem(page, name, "temporary");
    const row = page.getByTestId("item-name").filter({ hasText: name });
    await expect(row).toHaveCount(1);

    await page
      .locator(`[data-testid="delete-item"][data-item-name="${name}"]`)
      .click();

    await expect(page.getByTestId("items-message")).toContainText(/deleted/i);
    await expect(page.getByTestId("item-name").filter({ hasText: name })).toHaveCount(
      0
    );

    // And it is gone from the server, not just from the rendered table.
    await page.reload();
    await waitForList(page);
    await expect(page.getByTestId("item-name").filter({ hasText: name })).toHaveCount(
      0
    );
  });

  test("a duplicate name is refused and surfaced in the UI", async ({ page }) => {
    await page.goto("/");
    await waitForList(page);

    // The seed row is always present, so this needs no setup of its own.
    await createItem(page, "seed-item-001");

    await expect(page.getByTestId("items-message")).toContainText(/already exists/i);
    await expect(
      page.getByTestId("item-name").filter({ hasText: "seed-item-001" })
    ).toHaveCount(1);
  });
});
