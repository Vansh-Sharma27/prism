import { expect, test } from "@playwright/test";

const HYDRATION_PATTERNS = [
  /hydration failed/i,
  /didn't match/i,
  /server rendered html/i,
  /tree hydrated/i,
  /hydration error/i,
];

const ROUTES_TO_CHECK = ["/login", "/register"];

function isHydrationMessage(text: string): boolean {
  return HYDRATION_PATTERNS.some((pattern) => pattern.test(text));
}

test.describe("hydration console guard", () => {
  for (const route of ROUTES_TO_CHECK) {
    test(`has no hydration mismatch warnings on ${route}`, async ({ page }) => {
      const hydrationConsoleMessages: string[] = [];
      const pageErrors: string[] = [];

      page.on("console", (msg) => {
        const text = msg.text();
        if ((msg.type() === "warning" || msg.type() === "error") && isHydrationMessage(text)) {
          hydrationConsoleMessages.push(`[console:${msg.type()}] ${text}`);
        }
      });

      page.on("pageerror", (error) => {
        const text = String(error?.message ?? error);
        if (isHydrationMessage(text)) {
          pageErrors.push(`[pageerror] ${text}`);
        }
      });

      await page.goto(route, { waitUntil: "networkidle" });
      await expect(page.locator("body")).toBeVisible();

      // Give React hydration a moment to flush any client-side warnings.
      await page.waitForTimeout(1200);

      const issues = [...hydrationConsoleMessages, ...pageErrors];
      expect(issues, `Hydration issues found on route ${route}:\n${issues.join("\n")}`).toEqual([]);
    });
  }
});
