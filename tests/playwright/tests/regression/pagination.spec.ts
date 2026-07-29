import { test, expect, Page, APIRequestContext } from "@playwright/test";

// DESTRUCTIVE (it creates and deletes rows), so it lives under
// tests/regression/ and prod never runs it (ADR-0025).
//
// The fixture is built through the API and exercised through the BROWSER. That
// split is deliberate: creating 25 rows through the form would spend a minute
// proving something the create test already proves, while what needs proving
// here is what the page does once more rows exist than fit on one.
//
// This suite exists because of ADR-0031 §3. The list is ordered by id ascending
// and paginated, so the newest row is on the LAST page — and a create form that
// reloaded page 1 would silently appear to do nothing as soon as the table
// outgrew a page. That is a defect nobody would see on a fresh stage and
// everybody would see eventually.
const baseURL = process.env.BASE_URL || "http://localhost:8000";
const PAGE_SIZE = 20;
const FIXTURE_ROWS = 25;

const prefix = `pagination-${Date.now()}`;
let api: APIRequestContext;
const createdIds: number[] = [];

test.beforeAll(async ({ playwright }) => {
  api = await playwright.request.newContext({ baseURL });
  for (let i = 0; i < FIXTURE_ROWS; i++) {
    const res = await api.post("/api/items", {
      data: { name: `${prefix}-${String(i).padStart(3, "0")}` },
    });
    expect(res.status(), await res.text()).toBe(201);
    createdIds.push((await res.json()).id);
  }
});

test.afterAll(async () => {
  for (const id of createdIds) {
    await api.delete(`/api/items/${id}`);
  }
  await api.dispose();
});

async function waitForList(page: Page) {
  const table = page.getByTestId("items-table");
  await expect(table).toHaveAttribute("data-loaded", "true", { timeout: 30000 });
  return table;
}

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
  const next = page.getByTestId("next-page");
  for (let i = 0; i < 50 && (await next.isEnabled()); i++) {
    await clickAndWaitForRender(page, "next-page");
  }
}

test.describe("pagination (destructive, stage only)", () => {
  test("one page is shown, and the page says which one it is", async ({ page }) => {
    await page.goto("/");
    const table = await waitForList(page);

    await expect(table).toHaveAttribute("data-count", String(PAGE_SIZE));
    await expect(table).toHaveAttribute("data-offset", "0");
    await expect(table).toHaveAttribute("data-limit", String(PAGE_SIZE));
    await expect(page.getByTestId("item-row")).toHaveCount(PAGE_SIZE);
    await expect(page.getByTestId("page-label")).toHaveText(/page 1 of [2-9]/);

    await expect(page.getByTestId("prev-page")).toBeDisabled();
    await expect(page.getByTestId("next-page")).toBeEnabled();
  });

  test("next and prev move by exactly one page", async ({ page }) => {
    await page.goto("/");
    const table = await waitForList(page);

    const firstPageIds = await page.getByTestId("item-row").evaluateAll((rows) =>
      rows.map((r) => (r as HTMLElement).dataset.itemId)
    );

    await clickAndWaitForRender(page, "next-page");
    await expect(table).toHaveAttribute("data-offset", String(PAGE_SIZE));
    await expect(page.getByTestId("page-label")).toHaveText(/page 2 of /);
    await expect(page.getByTestId("prev-page")).toBeEnabled();

    const secondPageIds = await page.getByTestId("item-row").evaluateAll((rows) =>
      rows.map((r) => (r as HTMLElement).dataset.itemId)
    );
    // No row appears on both pages. An off-by-one in the offset would still
    // render two plausible pages, and only this catches it.
    expect(secondPageIds.filter((id) => firstPageIds.includes(id))).toEqual([]);

    await clickAndWaitForRender(page, "prev-page");
    await expect(table).toHaveAttribute("data-offset", "0");
    await expect(page.getByTestId("prev-page")).toBeDisabled();
  });

  test("the last page ends the walk", async ({ page }) => {
    await page.goto("/");
    const table = await waitForList(page);

    await gotoLastPage(page);

    await expect(page.getByTestId("next-page")).toBeDisabled();
    const offset = Number(await table.getAttribute("data-offset"));
    const count = Number(await table.getAttribute("data-count"));
    const total = Number(await table.getAttribute("data-total"));
    expect(offset + count).toBe(total);
  });

  test("a row created through the form is visible without paging to it", async ({
    page,
  }) => {
    // The whole reason the UI moves instead of the API changing its order.
    // With 25+ rows the new one is on the last page; if the page did not jump
    // there, this assertion fails and the create form looks broken to a user.
    const name = `${prefix}-created-in-the-browser`;

    await page.goto("/");
    await waitForList(page);
    await expect(page.getByTestId("page-label")).toHaveText(/page 1 of /);

    await page.getByTestId("new-item-name").fill(name);
    await page.getByTestId("create-item").click();

    await expect(page.getByTestId("items-message")).toContainText(name);
    await expect(
      page.getByTestId("item-name").filter({ hasText: name })
    ).toHaveCount(1);
    await expect(page.getByTestId("next-page")).toBeDisabled();

    const id = await page
      .locator(`[data-testid="item-row"][data-item-name="${name}"]`)
      .getAttribute("data-item-id");
    if (id) createdIds.push(Number(id));
  });

  test("deleting the only row on the last page steps back a page", async ({
    page,
  }) => {
    // Otherwise the table is empty, the pager says page N of N-1, and the user
    // is looking at a page that no longer exists.
    //
    // The fixture is BUILT to put exactly one row on the last page instead of
    // checking whether this run happens to. The first version of this test
    // skipped itself when the count did not line up, and on its first run it
    // did exactly that - a test that decides from ambient data whether to run
    // is indistinguishable from one that cannot pass, and it reports the same
    // colour either way.
    const before = (await (await api.get("/api/items?limit=1")).json()).total;
    const fillers = (PAGE_SIZE - (before % PAGE_SIZE)) % PAGE_SIZE;
    for (let i = 0; i < fillers; i++) {
      const res = await api.post("/api/items", {
        data: { name: `${prefix}-filler-${String(i).padStart(3, "0")}` },
      });
      expect(res.status(), await res.text()).toBe(201);
      createdIds.push((await res.json()).id);
    }

    // Created LAST, so it holds the highest id and is alone on the last page.
    const name = `${prefix}-zzz-last-row`;
    const created = await api.post("/api/items", { data: { name } });
    expect(created.status(), await created.text()).toBe(201);
    const id = (await created.json()).id;
    createdIds.push(id);

    await page.goto("/");
    await waitForList(page);
    const table = page.getByTestId("items-table");

    await gotoLastPage(page);

    const offsetBefore = Number(await table.getAttribute("data-offset"));
    // Asserted, not assumed: if the arithmetic above is wrong, this fails
    // loudly here rather than turning the real assertion into a coincidence.
    await expect(table).toHaveAttribute("data-count", "1");
    expect(offsetBefore).toBeGreaterThan(0);

    const rendersBefore = await table.getAttribute("data-renders");
    await page
      .locator(`[data-testid="delete-item"][data-item-id="${id}"]`)
      .click();
    await expect(table).not.toHaveAttribute("data-renders", rendersBefore ?? "");
    await waitForList(page);

    await expect(table).toHaveAttribute(
      "data-offset",
      String(offsetBefore - PAGE_SIZE)
    );
    await expect(page.getByTestId("item-row")).toHaveCount(PAGE_SIZE);
  });
});
