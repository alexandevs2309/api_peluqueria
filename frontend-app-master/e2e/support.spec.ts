import { test, expect } from '@playwright/test';

test.describe('Support — Tickets', () => {
  test('Public support page loads', async ({ page }) => {
    await page.goto('/support');
    await expect(page.locator('h1, h2, .support-title').first()).toBeVisible({ timeout: 10000 });
  });
});
