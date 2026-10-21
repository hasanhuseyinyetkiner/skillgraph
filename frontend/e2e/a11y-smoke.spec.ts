import { expect, test } from "@playwright/test";

test("a11y smoke: landmarks, nav label, theme control", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("demo-banner")).toBeVisible();
  await expect(page.locator("main#main")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
  const toggle = page.getByTestId("theme-toggle");
  await expect(toggle).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-pressed", /true|false/);
  await toggle.focus();
  await expect(toggle).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(toggle).toHaveAttribute("aria-pressed", /true|false/);

  await page.getByRole("link", { name: "Roles" }).click();
  await expect(page.getByRole("heading", { name: "Role Explorer" })).toBeVisible();
  await expect(page.locator("main#main")).toBeVisible();
});
