/**
 * Plan E §T26 — AI Filter happy path. Opt-in: only runs when the full compose
 * stack is up with Ollama models pre-pulled. CI's nightly e2e job enables it.
 */
import { test, expect } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

test('AI filter mode translates a query and applies the spec', async ({ page }) => {
  await page.goto('/upload/seeded-sample-csv');
  await expect(page.getByTestId('upload-detected')).toBeVisible();

  await page.getByRole('tab', { name: /AI Filter/i }).click();
  await page
    .getByPlaceholder(/ask about your data/i)
    .fill('rows where age > 18');
  await page.getByRole('button', { name: /translate/i }).click();

  await expect(page.getByText(/Confidence:/)).toBeVisible({ timeout: 10_000 });
  await page.getByRole('button', { name: /apply/i }).click();

  await expect(page.getByTestId('filter-preview')).toContainText(/age/);
});
