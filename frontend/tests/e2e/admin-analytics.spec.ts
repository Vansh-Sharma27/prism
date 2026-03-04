import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.PLAYWRIGHT_ADMIN_EMAIL || "admin@prism.local";
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD || "Admin@12345";

async function login(page: Page): Promise<void> {
  await page.goto("/login", { waitUntil: "networkidle" });
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByLabel("Password").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page).toHaveURL(/\/$/);
}

test.describe("admin analytics", () => {
  test("supports analytics window selection and csv export", async ({ page }) => {
    await login(page);

    await page.goto("/admin", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: "Admin Control" })).toBeVisible();
    await expect(
      page.locator('section[aria-label="Sensor health table"]').getByText(/Uptime 24h/i).first()
    ).toBeVisible();

    const windowSelect = page.getByLabel("Analytics Window");
    await windowSelect.selectOption("14");
    await expect(windowSelect).toHaveValue("14");

    const exportButton = page.getByRole("button", { name: "Export CSV" });
    await expect(exportButton).toBeEnabled();

    const downloadPromise = page.waitForEvent("download");
    await exportButton.click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toContain("prism-admin-analytics-14d.csv");
  });
});
