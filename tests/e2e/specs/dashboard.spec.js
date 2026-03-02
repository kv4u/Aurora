import { test, expect } from "@playwright/test";

test.describe("AURORA Dashboard", () => {
  test("should display the login page", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("text=AURORA")).toBeVisible();
    await expect(page.locator("text=Sign In")).toBeVisible();
    await expect(page.locator('input[type="text"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test("should show error on invalid login", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="text"]', "wrong");
    await page.fill('input[type="password"]', "wrong");
    await page.click("text=Sign In");
    await expect(page.locator("text=Invalid credentials")).toBeVisible();
  });

  test("should display dashboard layout after login", async ({ page }) => {
    // TODO: Mock auth when backend is connected
    await page.goto("/");
    await expect(page.locator("text=Dashboard")).toBeVisible();
  });

  test("should navigate between pages", async ({ page }) => {
    await page.goto("/");

    // Click through sidebar navigation
    await page.click("text=Trades");
    await expect(page.locator("h1:text('Trades')")).toBeVisible();

    await page.click("text=Signals");
    await expect(page.locator("h1:text('Signals')")).toBeVisible();

    await page.click("text=Audit");
    await expect(page.locator("h1:text('Audit Trail')")).toBeVisible();

    await page.click("text=Settings");
    await expect(page.locator("h1:text('Settings')")).toBeVisible();

    // Navigate back to dashboard
    await page.click("text=Dashboard");
    await expect(page.locator("h1:text('Dashboard')")).toBeVisible();
  });

  test("should show emergency stop button", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("text=Emergency Stop")).toBeVisible();
  });

  test("should show system status indicators", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("text=System Online")).toBeVisible();
    await expect(page.locator("text=Risk: Normal")).toBeVisible();
  });
});

test.describe("AURORA Settings", () => {
  test("should display risk limits", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.locator("text=Risk Limits")).toBeVisible();
    await expect(page.locator("text=Max Position Size")).toBeVisible();
    await expect(page.locator("text=Max Daily Loss")).toBeVisible();
  });

  test("should display trading mode toggle", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.locator("text=Paper Trading")).toBeVisible();
    await expect(page.locator("text=Live Trading")).toBeVisible();
  });

  test("should display watchlist symbols", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.locator("text=AAPL")).toBeVisible();
    await expect(page.locator("text=MSFT")).toBeVisible();
    await expect(page.locator("text=SPY")).toBeVisible();
  });
});
