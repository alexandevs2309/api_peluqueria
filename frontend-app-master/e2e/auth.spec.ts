import { test, expect } from '@playwright/test';

test.describe('Auth — Login & multi-tenant isolation', () => {
  test('Login page loads and shows form', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('Login with invalid credentials shows error', async ({ page }) => {
    await page.goto('/auth/login');
    await page.fill('input[type="email"]', 'nonexistent@test.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    // Expect an error toast or message
    await expect(page.locator('.p-toast, .p-message, .error-message, [role="alert"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('Protected route redirects to login when unauthenticated', async ({ page }) => {
    await page.goto('/client/dashboard');
    await page.waitForURL(/\/auth\/login/, { timeout: 10000 });
    expect(page.url()).toContain('/auth/login');
  });
});
