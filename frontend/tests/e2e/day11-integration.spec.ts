import { expect, test, type Page, type APIRequestContext } from "@playwright/test";

const ADMIN_EMAIL = process.env.PLAYWRIGHT_ADMIN_EMAIL || "admin@prism.local";
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD || "Admin@12345";
const BACKEND_BASE_URL = process.env.PLAYWRIGHT_BACKEND_URL || "http://127.0.0.1:5000";

async function login(page: Page): Promise<void> {
  await page.goto("/login", { waitUntil: "networkidle" });
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByLabel("Password").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page).toHaveURL(/\/$/);
}

async function loginForApi(request: APIRequestContext): Promise<string> {
  const response = await request.post(`${BACKEND_BASE_URL}/api/v1/auth/login`, {
    data: {
      email: ADMIN_EMAIL,
      password: ADMIN_PASSWORD,
    },
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  return body.access_token as string;
}

async function updateSlot(
  request: APIRequestContext,
  token: string,
  body: { is_occupied: boolean; distance_cm: number }
) {
  return request.put(`${BACKEND_BASE_URL}/api/v1/slots/lot-a-slot-1/status`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data: body,
  });
}

test.describe("day 11 integration", () => {
  test("navigates from dashboard to lot detail and reflects a live slot update", async ({ page, request }) => {
    const token = await loginForApi(request);

    const resetResponse = await updateSlot(request, token, {
      is_occupied: false,
      distance_cm: 80.0,
    });
    expect(resetResponse.ok()).toBeTruthy();

    await login(page);

    await expect(page.getByRole("heading", { name: /control dashboard/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /parking lots/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Academic Block A/i })).toBeVisible();

    await page.getByRole("link", { name: /Academic Block A/i }).click();
    await expect(page).toHaveURL(/\/lots\/lot-a$/);
    await expect(page.getByRole("heading", { name: /Academic Block A/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /slot grid/i })).toBeVisible();
    await expect(page.getByLabel("Slot status blocks")).toBeVisible();
    await expect(page.getByText("S01")).toBeVisible();
    await expect(page.getByLabel(/Slot 1: VACANT/i)).toBeVisible({ timeout: 12000 });

    const updateResponse = await updateSlot(request, token, {
      is_occupied: true,
      distance_cm: 8.0,
    });

    expect(updateResponse.ok()).toBeTruthy();
    const updateBody = await updateResponse.json();
    expect(updateBody.changed).toBe(true);

    await expect(page.getByLabel(/Slot 1: OCCUPIED/i)).toBeVisible({ timeout: 12000 });

    await page.goto("/activity", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: /activity log/i })).toBeVisible();
    const activityTable = page.getByRole("table", { name: /activity events/i });
    await expect(activityTable.getByText("S01").first()).toBeVisible({ timeout: 12000 });
    await expect(activityTable.getByText(/^entry$/i).first()).toBeVisible();
  });
});
