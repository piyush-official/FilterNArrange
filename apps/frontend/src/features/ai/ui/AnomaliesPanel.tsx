import * as React from 'react';
import { aiApi, AiUnavailableError, type AnomalyFinding } from '../api';
import { AiUnavailable } from './AiUnavailable';

type Props = {
  ref_: string;
  schema: Array<{ name: string; type: string }>;
  sampleRows: Array<Record<string, unknown>>;
  summaryStats: Record<string, unknown>;
};

const SEVERITY_ICON: Record<AnomalyFinding['severity'], string> = {
  low: '·',
  medium: '!',
  high: '!!',
};

export function AnomaliesPanel({
  ref_,
  schema,
  sampleRows,
  summaryStats,
}: Props) {
  const [findings, setFindings] = React.useState<AnomalyFinding[] | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [unavailable, setUnavailable] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const scan = async () => {
    setLoading(true);
    setError(null);
    setUnavailable(null);
    try {
      const r = await aiApi.anomaly({
        ref: ref_,
        schema,
        sample_rows: sampleRows,
        summary_stats: summaryStats,
      });
      setFindings(r.findings);
    } catch (e: unknown) {
      if (e instanceof AiUnavailableError) setUnavailable(e.message);
      else if (e instanceof Error) setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (unavailable) return <AiUnavailable message={unavailable} />;

  return (
    <section data-testid="anomalies-panel">
      <button onClick={scan} disabled={loading}>
        {loading ? 'Scanning…' : 'Scan for anomalies'}
      </button>
      {error && <div role="alert">{error}</div>}
      {findings && (
        <ul>
          {findings.map((f, i) => (
            <li key={i} data-testid="finding" data-severity={f.severity}>
              <span aria-label={`severity ${f.severity}`}>
                {SEVERITY_ICON[f.severity]}
              </span>{' '}
              <strong>{f.kind}</strong>
              {f.column ? ` · ${f.column}` : ''} — {f.description}
              {f.suggested_action ? (
                <em> Suggestion: {f.suggested_action}</em>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
