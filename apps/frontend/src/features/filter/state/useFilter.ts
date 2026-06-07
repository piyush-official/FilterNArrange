import { useEffect, useState } from 'react';
import { useAuth } from '../../auth';
import * as filterApi from '../api';

/**
 * Plan C: useFilter now drives previews from a fully-formed filter spec (any
 * kind). Plan B's column-only signature is gone — callers build the spec dict
 * in WorkbenchPage based on the active FilterMode.
 */
export function useFilter(uploadId: string | null, filter: Record<string, unknown> | null) {
  const { token } = useAuth();
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [schema, setSchema] = useState<Array<{ name: string; type: string; nullable: boolean }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const filterKey = filter ? JSON.stringify(filter) : '';

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!uploadId || !token || !filter) {
        setRows([]); setSchema([]); return;
      }
      setBusy(true); setError(null);
      try {
        const r = await filterApi.previewAny(uploadId, filter, token);
        if (!cancelled) {
          setRows(r.rows ?? []);
          setSchema(r.schema ?? []);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setBusy(false);
      }
    }
    run();
    return () => { cancelled = true; };
  }, [uploadId, token, filterKey]);

  return { rows, schema, error, busy };
}
