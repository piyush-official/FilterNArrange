/**
 * Plan G §T6 — Keycloak login happy path. Opt-in: requires a compose stack
 * with the Keycloak service up and the gateway running with
 * AUTH_PROVIDER=keycloak. CI's nightly e2e profile enables both.
 */
import { test, expect } from '@playwright/test';

test('redirects to Keycloak when AUTH_PROVIDER=keycloak and signs in', async ({ page }) => {
  await page.goto('/login');

  // SPA renders the SSO CTA instead of the email/password form
  await expect(page.getByText(/single sign-on/i)).toBeVisible();
  await page.getByRole('button', { name: /single sign-on/i }).click();

  // Keycloak's hosted login page appears
  await expect(page).toHaveURL(/realms\/filternarrange\/protocol\/openid-connect\/auth/);
  await page.getByLabel(/username|email/i).fill('dev-user');
  await page.getByLabel(/password/i).fill('dev-password');
  await page.getByRole('button', { name: /sign in/i }).click();

  // Back on the SPA, authenticated
  await expect(page).toHaveURL(/\/(?:\?.*)?$/, { timeout: 10_000 });
  await expect(page.getByText(/dev-user/i)).toBeVisible();
});
