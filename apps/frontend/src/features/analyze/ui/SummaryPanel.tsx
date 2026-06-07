import { useEffect, useState } from 'react';
import { useAuth } from '../../auth';
import { analyze } from '../api';

interface ColumnStats {
  name: string;
  type: string;
  count: number;
  nulls: number;
  distinct: number;
  min?: number;
  max?: number;
  mean?: number;
  median?: number;
  stddev?: number;
  top?: Array<{ value: unknown; count: number }>;
}

interface Props {
  uploadId: string;
  filter?: Record<string, unknown>;
}

export function SummaryPanel({ uploadId, filter }: Props) {
  const { token } = useAuth();
  const [columns, setColumns] = useState<ColumnStats[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setColumns(null); setErr(null);
    analyze(uploadId, 'summary_stats', {}, token, filter)
      .then(r => {
        if (!cancelled) setColumns((r.payload.columns ?? []) as ColumnStats[]);
      })
      .catch(e => { if (!cancelled) setErr((e as Error).message); });
    return () => { cancelled = true; };
  }, [uploadId, token, JSON.stringify(filter)]);

  if (err) return <div role="alert">{err}</div>;
  if (!columns) return <div>Loading summary…</div>;
  return (
    <table className="summary-table">
      <thead>
        <tr>
          <th>Column</th><th>Type</th><th>Count</th><th>Nulls</th><th>Distinct</th>
          <th>Min</th><th>Max</th><th>Mean</th>
        </tr>
      </thead>
      <tbody>
        {columns.map(c => (
          <tr key={c.name}>
            <td>{c.name}</td>
            <td>{c.type}</td>
            <td>{c.count}</td>
            <td>{c.nulls}</td>
            <td>{c.distinct}</td>
            <td>{c.min ?? '—'}</td>
            <td>{c.max ?? '—'}</td>
            <td>{c.mean !== undefined ? c.mean.toFixed(2) : '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
