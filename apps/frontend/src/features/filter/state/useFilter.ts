import { useEffect, useState } from 'react';
import { useAuth } from '../../auth';
import * as filterApi from '../api';

export function useFilter(uploadId: string | null, allColumns: string[]) {
  const { token } = useAuth();
  const [selected, setSelected] = useState<string[]>([]);
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { setSelected(allColumns); }, [allColumns.join('|')]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!uploadId || !token || selected.length === 0) { setRows([]); return; }
      setBusy(true); setError(null);
      try {
        const r = await filterApi.preview(uploadId, selected, token);
        if (!cancelled) setRows((r.rows ?? []) as Array<Record<string, unknown>>);
      } catch (e) { if (!cancelled) setError((e as Error).message); }
      finally { if (!cancelled) setBusy(false); }
    }
    run();
    return () => { cancelled = true; };
  }, [uploadId, token, selected.join('|')]);

  return { selected, setSelected, rows, error, busy };
}
