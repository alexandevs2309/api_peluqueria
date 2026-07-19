import { Page } from '@playwright/test';
import { randomUUID } from 'crypto';

/**
 * Fill login form and submit.
 * Adjust selectors to match the actual login component template.
 */
export async function login(page: Page, email: string, password: string) {
  await page.goto('/auth/login');
  await page.waitForSelector('input[type="email"]', { timeout: 10000 });
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  // Wait for redirect to dashboard
  await page.waitForURL(/\/client\/dashboard/, { timeout: 15000 });
}

export function uniqueEmail(): string {
  const id = randomUUID().slice(0, 8);
  return `e2e-${id}@test.auron-suite.com`;
}

export function uniqueName(prefix = 'e2e'): string {
  return `${prefix}-${randomUUID().slice(0, 8)}`;
}
