import * as React from 'react';
import { isPaid, UPGRADE_HINT_HREF, type Tier } from '../tier';

/**
 * Plan F §T31 — gates ``children`` behind paid tier.
 *
 * Pure presentational: callers pass the current tier (typically from the
 * ``useBilling`` hook). Free users see an upgrade CTA instead of the
 * gated content.
 */
export function PaidGate({
  tier,
  feature,
  children,
}: {
  tier: Tier | undefined;
  feature: string;
  children: React.ReactNode;
}) {
  if (isPaid(tier)) return <>{children}</>;
  return (
    <div className="paid-gate" data-testid="paid-gate" data-feature={feature}>
      <p>
        <strong>{feature}</strong> is a paid-tier feature.
      </p>
      <a href={UPGRADE_HINT_HREF} className="paid-gate__upgrade">
        Upgrade to unlock
      </a>
    </div>
  );
}
