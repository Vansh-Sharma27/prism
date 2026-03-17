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

test.describe("lot insights", () => {
  test("supports prediction and recommendation workflows from a lot detail page", async ({ page }) => {
    await login(page);

    await page.goto("/lots/lot-a", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: /lot intelligence/i })).toBeVisible();

    await page.getByLabel("Forecast Day").selectOption("friday");
    await page.getByLabel("Forecast Time").fill("16:30");
    await page.getByRole("button", { name: "Run Prediction" }).click();

    await expect(page.getByRole("heading", { name: /predicted zone load/i })).toBeVisible();
    await expect(page.getByText(/Academic Block A/i)).toBeVisible();
    await expect(page.getByText(/East Wing/i)).toBeVisible();
    await expect(page.getByText(/West Wing/i)).toBeVisible();

    await page.getByLabel("Destination").selectOption("Library");
    await page.getByRole("button", { name: "Recommend Zone" }).click();

    await expect(page.getByRole("heading", { name: /best parking recommendation/i })).toBeVisible();
    await expect(page.getByText(/Library/i)).toBeVisible();
    await expect(page.getByText(/Walk/i)).toBeVisible();
  });
});
