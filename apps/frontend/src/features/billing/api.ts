import { authHeaders } from '../../shared/api/client';
import type { Tier } from '../../shared/tier';

export interface BillingMe {
  tier: Tier;
  ops_today: number;
  ops_limit: number;
  ops_unlimited: boolean;
  max_upload_mb: number;
  upload_unlimited: boolean;
  upgrade_hint: string | null;
}

export async function fetchBillingMe(): Promise<BillingMe> {
  const r = await fetch('/api/v1/billing/me', { headers: authHeaders() });
  if (!r.ok) throw new Error(`billing/me failed: ${r.status}`);
  return r.json();
}
