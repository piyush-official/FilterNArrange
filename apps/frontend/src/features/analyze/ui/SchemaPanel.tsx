import { useEffect, useState } from 'react';
import { useAuth } from '../../auth';
import { analyze } from '../api';

interface PathStats {
  path: string;
  types: string[];
  depth_min: number;
  depth_max: number;
  frequency: number;
}

interface SchemaPayload {
  paths: PathStats[];
  leaf_count: number;
  depth: number;
}

interface Props {
  uploadId: string;
  filter?: Record<string, unknown>;
}

export function SchemaPanel({ uploadId, filter }: Props) {
  const { token } = useAuth();
  const [data, setData] = useState<SchemaPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setData(null); setErr(null);
    analyze(uploadId, 'schema_infer', {}, token, filter)
      .then(r => { if (!cancelled) setData(r.payload as unknown as SchemaPayload); })
      .catch(e => { if (!cancelled) setErr((e as Error).message); });
    return () => { cancelled = true; };
  }, [uploadId, token, JSON.stringify(filter)]);

  if (err) return <div role="alert">{err}</div>;
  if (!data) return <div>Loading schema…</div>;
  return (
    <div>
      <p>Leaf count: {data.leaf_count}, depth: {data.depth}</p>
      <table>
        <thead>
          <tr><th>Path</th><th>Types</th><th>Depth (min..max)</th><th>Frequency</th></tr>
        </thead>
        <tbody>
          {data.paths.map(p => (
            <tr key={p.path}>
              <td><code>{p.path}</code></td>
              <td>{p.types.join(', ')}</td>
              <td>{p.depth_min}..{p.depth_max}</td>
              <td>{p.frequency}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
