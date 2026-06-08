/** Plan F §T30 — tier helper shared across features. */
export type Tier = 'free' | 'paid';

export function isPaid(tier: Tier | undefined): boolean {
  return tier === 'paid';
}

export const UPGRADE_HINT_HREF = '/account/billing';
