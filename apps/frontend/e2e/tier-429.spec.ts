/**
 * Plan F §T37 — quota 429 path. Opt-in: only runs against a compose stack
 * configured with FREE_TIER_DAILY_OPS=1 so we can trip the limit in one
 * extra call. CI's nightly e2e profile sets that env var.
 */
import { test, expect } from '@playwright/test';

test('FREE tier hits 429 after exceeding daily ops quota', async ({
  page,
  request,
}) => {
  // First call consumes the lone allowance; the second should be 429.
  await request.post('/api/v1/detect', {
    data: { ref: 'uploads/seeded-sample-csv' },
  });
  const second = await request.post('/api/v1/detect', {
    data: { ref: 'uploads/seeded-sample-csv' },
  });
  expect(second.status()).toBe(429);
  const body = await second.json();
  expect(body.code).toBe('TIER_QUOTA_EXCEEDED');
  expect(body.upgrade_hint).toBeTruthy();

  // UI surfaces it on /jobs as a toast / banner.
  await page.goto('/jobs');
  await expect(
    page.getByText(/quota/i).first(),
  ).toBeVisible({ timeout: 5_000 });
});
