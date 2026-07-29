import { test, expect, Page } from "@playwright/test";

// DESTRUCTIVE. This file lives under tests/regression/ and is therefore in the
// `regression` project, which runs against stage and NEVER against prod
// (ADR-0025). stage is seeded and disposable; prod is promoted and public.

// Two probe items are created here through the UI and deliberately NOT deleted.
// A separate step then asserts them in the database, which is what makes the
// claim "the UI reached RDS" a measurement rather than an inference: the
// browser wrote them, and a different process, connecting straight to
// PostgreSQL, found them.
//
//   UI_PROBE_NAME        created through the create form
//   UI_EDIT_PROBE_NAME   created under another name and RENAMED to this one
//                        through the edit form. The database assertion checks
//                        updated_at > created_at, which a plain create cannot
//                        produce — so the row proves an UPDATE happened, not
//                        just an INSERT with the right name (Phase 16a).
const probeName = process.env.UI_PROBE_NAME;
const editProbeName = process.env.UI_EDIT_PROBE_NAME;

test.beforeAll(() => {
  const missing = [
    !probeName && "UI_PROBE_NAME",
    !editProbeName && "UI_EDIT_PROBE_NAME",
  ].filter(Boolean);
  if (missing.length) {
    throw new Error(
      `${missing.join(" and ")} not set. The database assertion that follows ` +
        "this suite looks up exactly these names; without them the assertion " +
        "would check nothing and pass. Set them in the caller (Makefile or " +
        "workflow)."
    );
  }
});

async function waitForList(page: Page) {
  const table = page.getByTestId("items-table");
  await expect(table).toHaveAttribute("data-loaded", "true", { timeout: 30000 });
  return table;
}

// The list is paginated and ordered by id ASCENDING, so a freshly created row
// is on the LAST page (ADR-0031). The UI jumps there after a create, but a
// RELOAD starts at page 1 again — so anything asserting "it is still there
// after a reload" has to walk to the end, or it is asserting about a page the
// row was never on. On a small database the two are the same page, which is
// exactly why this would have gone unnoticed until stage grew.
// Clicking a pager button and then waiting for `data-loaded` waits for
// NOTHING: the attribute was already "true" from the render before the click.
// This waits for the render COUNTER to move, which only a new render can do.
// Without it the next `isEnabled()` reads the previous page's button state,
// and the click that follows hangs until the test times out.
async function clickAndWaitForRender(page: Page, testId: string) {
  const table = page.getByTestId("items-table");
  const before = await table.getAttribute("data-renders");
  await page.getByTestId(testId).click();
  await expect(table).not.toHaveAttribute("data-renders", before ?? "");
  await expect(table).toHaveAttribute("data-loaded", "true", { timeout: 30000 });
}

async function gotoLastPage(page: Page) {
  await waitForList(page);
  const next = page.getByTestId("next-page");
  // Bounded: the loop advances one page per iteration and the button disables
  // at the end. A cap turns a UI bug into a failed test instead of a hang.
  for (let i = 0; i < 50 && (await next.isEnabled()); i++) {
    await clickAndWaitForRender(page, "next-page");
  }
}

async function createItem(page: Page, name: string, description?: string) {
  await page.getByTestId("new-item-name").fill(name);
  if (description) {
    await page.getByTestId("new-item-description").fill(description);
  }
  await page.getByTestId("create-item").click();
}

async function editItem(
  page: Page,
  currentName: string,
  next: { name?: string; description?: string }
) {
  await page
    .locator(`[data-testid="edit-item"][data-item-name="${currentName}"]`)
    .click();
  if (next.name !== undefined) {
    await page.getByTestId("edit-item-name").fill(next.name);
  }
  if (next.description !== undefined) {
    await page.getByTestId("edit-item-description").fill(next.description);
  }
  await page.getByTestId("save-item").click();
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
    await gotoLastPage(page);
    await expect(
      page.getByTestId("item-name").filter({ hasText: probeName! })
    ).toHaveCount(1);
  });

  test("edit through the UI rewrites the row the database assertion checks", async ({
    page,
  }) => {
    const startingName = `${editProbeName}-before-rename`;

    await page.goto("/");
    await waitForList(page);

    await createItem(page, startingName, "created to be renamed");
    await expect(
      page.getByTestId("item-name").filter({ hasText: startingName })
    ).toHaveCount(1);

    await editItem(page, startingName, {
      name: editProbeName!,
      description: "renamed through the UI",
    });

    await expect(page.getByTestId("items-message")).toContainText(/updated/i);
    await expect(
      page.getByTestId("item-name").filter({ hasText: editProbeName! })
    ).toHaveCount(1);
    await expect(
      page.getByTestId("item-name").filter({ hasText: startingName })
    ).toHaveCount(0);

    await page.reload();
    await gotoLastPage(page);
    await expect(
      page.getByTestId("item-name").filter({ hasText: editProbeName! })
    ).toHaveCount(1);
  });

  test("editing only the description leaves the name alone", async ({ page }) => {
    const name = `regression-desc-${Date.now()}`;

    await page.goto("/");
    await waitForList(page);
    await createItem(page, name, "first");

    await editItem(page, name, { description: "second" });

    const row = page.locator(`[data-testid="item-row"][data-item-name="${name}"]`);
    await expect(row).toHaveCount(1);
    await expect(row.getByTestId("item-description")).toHaveText("second");

    await page
      .locator(`[data-testid="delete-item"][data-item-name="${name}"]`)
      .click();
    await expect(page.getByTestId("items-message")).toContainText(/deleted/i);
  });

  test("an edit onto a name that already exists is refused and surfaced", async ({
    page,
  }) => {
    const name = `regression-conflict-${Date.now()}`;

    await page.goto("/");
    await waitForList(page);
    await createItem(page, name, "will try to take a taken name");

    // The seed row is always present, so this needs no second fixture.
    await editItem(page, name, { name: "seed-item-001" });

    await expect(page.getByTestId("items-message")).toContainText(/already exists/i);
    // Refused, and the row is unchanged rather than half-applied.
    await page.reload();
    await gotoLastPage(page);
    await expect(
      page.locator(`[data-testid="item-row"][data-item-name="${name}"]`)
    ).toHaveCount(1);

    await page
      .locator(`[data-testid="delete-item"][data-item-name="${name}"]`)
      .click();
    await expect(page.getByTestId("items-message")).toContainText(/deleted/i);
  });

  test("cancelling an edit changes nothing", async ({ page }) => {
    const name = `regression-cancel-${Date.now()}`;

    await page.goto("/");
    await waitForList(page);
    await createItem(page, name, "unchanged");

    await page
      .locator(`[data-testid="edit-item"][data-item-name="${name}"]`)
      .click();
    await page.getByTestId("edit-item-name").fill(`${name}-typed-but-abandoned`);
    await page.getByTestId("cancel-edit").click();

    await page.reload();
    await gotoLastPage(page);
    await expect(
      page.locator(`[data-testid="item-row"][data-item-name="${name}"]`)
    ).toHaveCount(1);
    await expect(
      page.getByTestId("item-name").filter({ hasText: `${name}-typed-but-abandoned` })
    ).toHaveCount(0);

    await page
      .locator(`[data-testid="delete-item"][data-item-name="${name}"]`)
      .click();
    await expect(page.getByTestId("items-message")).toContainText(/deleted/i);
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

    // And it is gone from the server, not just from the rendered table. Walked
    // to the last page first: asserting "absent" on page 1 would also pass for
    // a row that is merely on page 2, which is a vacuous green.
    await page.reload();
    await gotoLastPage(page);
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
