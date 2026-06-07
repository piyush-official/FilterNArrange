import { test, expect } from '@playwright/test';
import path from 'node:path';

const FIXTURE = path.resolve(__dirname, '../../../../tests/fixtures/sample.csv');

test('user can signup, upload, filter, and download', async ({ page }) => {
  const email = `e2e-${Date.now()}@filternarrange.io`;
  await page.goto('/signup');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill('hunter2hunter2');
  await page.getByRole('button', { name: /sign up/i }).click();

  // Lands on workbench
  await expect(page).toHaveURL('/');
  await expect(page.getByRole('heading', { name: /filternarrange/i })).toBeVisible();

  // Upload
  const fileInput = page.getByLabel(/upload csv or json/i);
  await fileInput.setInputFiles(FIXTURE);
  await expect(page.getByText(/Detected: csv/i)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('cell', { name: 'name' })).toBeVisible();

  // Deselect age, keep name + country
  await page.getByLabel('age').uncheck();
  await expect(page.getByRole('table', { name: /filter preview/i })).toBeVisible();

  // Switch format to JSON and download
  await page.getByLabel('JSON').check();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: /^download$/i }).click();
  const download = await downloadPromise;
  const fp = await download.path();
  expect(fp).toBeTruthy();
});
