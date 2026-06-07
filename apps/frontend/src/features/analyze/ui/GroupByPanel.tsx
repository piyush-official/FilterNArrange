import { useState } from 'react';
import { useAuth } from '../../auth';
import { analyze } from '../api';

interface Props {
  uploadId: string;
  filter?: Record<string, unknown>;
}

const AGGS = ['sum', 'count', 'avg', 'min', 'max', 'median'] as const;
type Agg = (typeof AGGS)[number];

export function GroupByPanel({ uploadId, filter }: Props) {
  const { token } = useAuth();
  const [by, setBy] = useState('');
  const [aggCol, setAggCol] = useState('');
  const [fn, setFn] = useState<Agg>('sum');
  const [groups, setGroups] = useState<Array<Record<string, unknown>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    if (!by || !aggCol || !token) return;
    try {
      setGroups(null); setErr(null);
      const r = await analyze(
        uploadId, 'group_by',
        { by: [by], agg: { [aggCol]: [fn] } },
        token, filter,
      );
      setGroups((r.payload.groups ?? []) as Array<Record<string, unknown>>);
    } catch (e) { setErr((e as Error).message); }
  }

  const headers = groups && groups[0] ? Object.keys(groups[0]) : [];

  return (
    <div>
      <input
        aria-label="group-by-col"
        placeholder="group by column"
        value={by}
        onChange={e => setBy(e.target.value)}
      />
      <input
        aria-label="agg-col"
        placeholder="aggregate column"
        value={aggCol}
        onChange={e => setAggCol(e.target.value)}
      />
      <select
        aria-label="agg-fn"
        value={fn}
        onChange={e => setFn(e.target.value as Agg)}
      >
        {AGGS.map(f => <option key={f} value={f}>{f}</option>)}
      </select>
      <button onClick={run}>Run</button>
      {err && <p role="alert">{err}</p>}
      {groups && (
        <table>
          <thead><tr>{headers.map(h => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>
            {groups.map((g, i) => (
              <tr key={i}>
                {headers.map(h => <td key={h}>{String(g[h] ?? '')}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
