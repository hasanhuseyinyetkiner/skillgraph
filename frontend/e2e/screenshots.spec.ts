import { expect, test, type Locator, type Page } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const shotDir = path.resolve(frontendRoot, "../../docs/screenshots");

async function selectByText(select: Locator, text: string) {
  const value = await select.locator("option").filter({ hasText: text }).first().getAttribute("value");
  if (!value) throw new Error(`No option containing ${text}`);
  await select.selectOption(value);
}

async function setTheme(page: Page, theme: "light" | "dark") {
  await page.addInitScript((themeName) => {
    localStorage.setItem("skillgraph-theme", themeName);
    document.documentElement.classList.toggle("dark", themeName === "dark");
  }, theme);
}

async function shot(page: Page, name: string) {
  await page.screenshot({
    path: path.join(shotDir, `${name}.png`),
    fullPage: false,
  });
}

for (const theme of ["light", "dark"] as const) {
  test(`capture ${theme} portfolio screens`, async ({ page }) => {
    await setTheme(page, theme);

    await page.goto("/graph");
    await expect(page.getByRole("heading", { name: "Graph Explorer" })).toBeVisible();
    await expect(page.getByTestId("cytoscape-canvas")).toBeVisible();
    await expect(page.getByTestId("taxonomy-rail")).toBeVisible();
    await expect(page.getByText(/Graph v\d+/)).toBeVisible({ timeout: 30_000 });
    await page.waitForTimeout(1500);
    await shot(page, `graph-explorer-${theme}`);

    await page.goto("/roles");
    await expect(page.getByRole("heading", { name: "Role Explorer" })).toBeVisible();
    await selectByText(page.getByTestId("role-select"), "Analytics Engineer");
    await page.getByTestId("compute-fit").click();
    await expect(page.getByTestId("fit-index")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("gap-matrix")).toBeVisible();
    await expect(page.getByTestId("evidence-weights")).toBeVisible();
    await expect(page.getByTestId("gap-chart")).toBeVisible();
    await page.waitForTimeout(800);
    await shot(page, `role-explorer-${theme}`);

    await page.goto("/path");
    await expect(page.getByRole("heading", { name: "Path Builder" })).toBeVisible();
    await selectByText(page.getByTestId("path-role-select"), "Analytics Engineer");
    await page.getByTestId("build-path").click();
    await expect(page.getByText(/Cycle-free:\s*yes/i)).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("path-steps")).toBeVisible();
    await page.waitForTimeout(500);
    await shot(page, `path-builder-${theme}`);
  });
}
