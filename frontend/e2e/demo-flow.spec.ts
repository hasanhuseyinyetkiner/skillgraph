import { expect, test, type Locator } from "@playwright/test";

async function selectByText(select: Locator, text: string) {
  const value = await select.locator("option").filter({ hasText: text }).first().getAttribute("value");
  if (!value) throw new Error(`No option containing ${text}`);
  await select.selectOption(value);
}

test("demo profile → graph → role fit → learning path", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("demo-banner")).toContainText("Local demo");
  await expect(page.getByRole("heading", { name: /Avery Chen/i })).toBeVisible();

  await page.getByRole("link", { name: "Graph" }).click();
  await expect(page.getByRole("heading", { name: "Graph Explorer" })).toBeVisible();
  await expect(page.getByTestId("cytoscape-canvas")).toBeVisible();
  await expect(page.getByTestId("taxonomy-rail")).toBeVisible();
  await expect(page.getByTestId("adjacency-panel")).toBeVisible();
  await expect(page.getByText(/Graph v\d+/)).toBeVisible({ timeout: 30_000 });

  await page.getByRole("link", { name: "Roles" }).click();
  await expect(page.getByRole("heading", { name: "Role Explorer" })).toBeVisible();
  await selectByText(page.getByTestId("role-select"), "Analytics Engineer");
  await page.getByTestId("compute-fit").click();
  await expect(page.getByTestId("fit-index")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("gap-matrix")).toBeVisible();
  await expect(page.getByTestId("evidence-weights")).toBeVisible();
  await expect(page.getByText(/Exploratory fit index/i).first()).toBeVisible();
  await expect(page.getByText(/not a probability of getting a job/i).first()).toBeVisible();
  await expect(page.getByText(/incomplete|satisfied/i).first()).toBeVisible();

  await page.getByRole("link", { name: "Paths" }).click();
  await expect(page.getByRole("heading", { name: "Path Builder" })).toBeVisible();
  await selectByText(page.getByTestId("path-role-select"), "Analytics Engineer");
  await page.getByTestId("build-path").click();
  await expect(page.getByText(/Cycle-free:\s*yes/i)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Ordered steps" })).toBeVisible();
  await expect(page.getByTestId("path-steps")).toBeVisible();
});
