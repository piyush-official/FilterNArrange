/**
 * Plan F §T38 — oversize (413) and feature-gate (403) e2e. Opt-in: assumes
 * compose stack is up with the FREE-tier default 5 MB upload cap, and the
 * test session is authenticated as a free user.
 */
import { test, expect } from '@playwright/test';

test('FREE tier: oversize upload returns 413 PAYLOAD_TOO_LARGE', async ({
  request,
}) => {
  const big = Buffer.alloc(6 * 1024 * 1024); // 6 MB > 5 MB cap
  const r = await request.post('/api/v1/uploads', {
    multipart: {
      file: { name: 'big.bin', mimeType: 'application/octet-stream', buffer: big },
    },
  });
  expect(r.status()).toBe(413);
  const body = await r.json();
  expect(body.code).toBe('PAYLOAD_TOO_LARGE');
});

test('FREE tier: paid endpoint returns 403 FEATURE_REQUIRES_PAID_TIER', async ({
  request,
}) => {
  const r = await request.post('/api/v1/ai/nl-to-filter', {
    data: { ref: 'uploads/x.csv', query: 'rows where age > 18' },
  });
  expect(r.status()).toBe(403);
  const body = await r.json();
  expect(body.code).toBe('FEATURE_REQUIRES_PAID_TIER');
  expect(body.upgrade_hint).toBeTruthy();
});
