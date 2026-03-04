import { expect, test, type Page } from "@playwright/test";

const ADMIN_EMAIL = process.env.PLAYWRIGHT_ADMIN_EMAIL || "admin@prism.local";
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_ADMIN_PASSWORD || "Admin@12345";
const DEFAULT_STUDENT_PASSWORD = "Student@12345";

function uniqueEmail(prefix: string): string {
  return `${prefix}.${Date.now()}.${Math.floor(Math.random() * 1_000_000)}@prism.local`;
}

async function login(page: Page, email: string, password: string): Promise<void> {
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign In" }).click();
}

async function register(page: Page, email: string, password: string): Promise<void> {
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm Password").fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();
}

test.describe("auth flows", () => {
  test("redirects unauthenticated users from protected routes with next query", async ({ page }) => {
    await page.goto("/lots?status=occupied", { waitUntil: "networkidle" });

    await expect(page).toHaveURL(/\/login\?next=%2Flots%3Fstatus%3Doccupied$/);
    await expect(page.getByRole("heading", { name: "Login" })).toBeVisible();
  });

  test("shows login validation errors for invalid email and short password", async ({ page }) => {
    await page.goto("/login", { waitUntil: "networkidle" });

    await page.getByLabel("Email").fill("invalid-email");
    await page.getByLabel("Password").fill("123");
    await page.getByRole("button", { name: "Sign In" }).click();

    await expect(page.getByText(/valid format/i)).toBeVisible();
    await expect(page.getByText(/at least 8 characters/i)).toBeVisible();
  });

  test("shows backend auth error for invalid credentials", async ({ page }) => {
    await page.goto("/login", { waitUntil: "networkidle" });

    await login(page, ADMIN_EMAIL, "WrongPass123!");

    await expect(page.getByText(/invalid email or password/i)).toBeVisible();
    await expect(page.getByText(/\/api\/v1\/auth\/login/i)).toHaveCount(0);
  });

  test("sanitizes unsafe next path and lands on dashboard after successful login", async ({ page }) => {
    await page.goto("/login?next=https://malicious.example", { waitUntil: "networkidle" });

    await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);

    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: /control dashboard/i })).toBeVisible();
  });

  test("shows registration validation errors for malformed input", async ({ page }) => {
    await page.goto("/register", { waitUntil: "networkidle" });

    await page.getByLabel("Email").fill("not-an-email");
    await page.getByLabel("Password", { exact: true }).fill("short");
    await page.getByLabel("Confirm Password").fill("different");
    await page.getByRole("button", { name: "Create Account" }).click();

    await expect(page.getByText(/valid format/i)).toBeVisible();
    await expect(page.getByText(/at least 8 characters/i)).toBeVisible();
    await expect(page.getByText(/must match password/i)).toBeVisible();
  });

  test("shows conflict error when registering an existing email", async ({ page }) => {
    await page.goto("/register", { waitUntil: "networkidle" });

    await register(page, ADMIN_EMAIL, ADMIN_PASSWORD);

    await expect(page.getByText(/email already registered/i)).toBeVisible();
  });

  test("registers a student and denies admin route access for non-admin role", async ({ page }) => {
    const email = uniqueEmail("student");
    await page.goto("/register", { waitUntil: "networkidle" });

    await register(page, email, DEFAULT_STUDENT_PASSWORD);

    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: /control dashboard/i })).toBeVisible();

    await page.goto("/admin", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: /access denied/i })).toBeVisible();
  });

  test("forces logout when protected API starts returning unauthorized", async ({ page }) => {
    await page.goto("/login", { waitUntil: "networkidle" });
    await login(page, ADMIN_EMAIL, ADMIN_PASSWORD);
    await expect(page).toHaveURL(/\/$/);

    await page.route("**/api/v1/lots", async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ error: "Authentication required" }),
      });
    });

    await page.reload({ waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/login\?next=%2F$/);
    await expect(page.getByText(/session expired\. please login again\./i)).toBeVisible();
  });
});
