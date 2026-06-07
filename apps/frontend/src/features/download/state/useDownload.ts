import { useState } from 'react';
import { useAuth } from '../../auth';
import * as dlApi from '../api';

export function useDownload() {
  const { token } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(uploadId: string, keep: string[], outputFormat: 'csv' | 'json') {
    if (!token) { setError('Not logged in'); return; }
    setBusy(true); setError(null);
    try {
      const conv = await dlApi.convert(uploadId, keep, outputFormat, token);
      window.location.assign(dlApi.downloadUrl(conv.resultId));
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return { busy, error, run };
}
