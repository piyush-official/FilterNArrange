import { useEffect, useState } from 'react';
import { fetchBillingMe, type BillingMe } from './api';

export function useBilling(): { data: BillingMe | undefined; error: Error | null; refresh: () => Promise<void> } {
  const [data, setData] = useState<BillingMe | undefined>(undefined);
  const [error, setError] = useState<Error | null>(null);

  const refresh = async () => {
    try {
      setData(await fetchBillingMe());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e : new Error(String(e)));
    }
  };

  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  return { data, error, refresh };
}
