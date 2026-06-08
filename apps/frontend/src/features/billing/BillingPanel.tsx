import * as React from 'react';
import { useBilling } from './useBilling';

/**
 * Plan F §T32 — current tier, today's op usage, upload cap, upgrade CTA when free.
 */
export function BillingPanel() {
  const { data, error } = useBilling();
  if (error) return <div role="alert">Failed to load billing: {error.message}</div>;
  if (!data) return <div data-testid="billing-loading">Loading billing…</div>;

  return (
    <section data-testid="billing-panel" className="billing-panel">
      <h2>Plan</h2>
      <p>
        Tier: <strong data-testid="billing-tier">{data.tier}</strong>
      </p>
      <p>
        Today: <strong>{data.ops_today}</strong>{' '}
        {data.ops_unlimited ? '(unlimited)' : `/ ${data.ops_limit}`}
      </p>
      <p>
        Max upload:{' '}
        <strong>
          {data.upload_unlimited ? 'unlimited' : `${data.max_upload_mb} MB`}
        </strong>
      </p>
      {data.upgrade_hint && (
        <p>
          <a href={data.upgrade_hint} className="billing-panel__upgrade">
            Upgrade to paid
          </a>
        </p>
      )}
    </section>
  );
}
