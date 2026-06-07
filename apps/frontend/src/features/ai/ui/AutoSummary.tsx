import * as React from 'react';
import { aiApi, AiUnavailableError, type SummaryResponse } from '../api';
import { AiUnavailable } from './AiUnavailable';

type Props = {
  ref_: string;
  schema: Array<{ name: string; type: string }>;
  sampleRows: Array<Record<string, unknown>>;
  totalRows: number;
  totalSizeBytes: number;
  skip: boolean;
};

export function AutoSummary({
  ref_,
  schema,
  sampleRows,
  totalRows,
  totalSizeBytes,
  skip,
}: Props) {
  const [data, setData] = React.useState<SummaryResponse | null>(null);
  const [unavailable, setUnavailable] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (skip) return;
    let cancelled = false;
    setLoading(true);
    aiApi
      .summary({
        ref: ref_,
        schema,
        sample_rows: sampleRows,
        total_rows: totalRows,
        total_size_bytes: totalSizeBytes,
      })
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof AiUnavailableError) setUnavailable(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ref_, skip, schema, sampleRows, totalRows, totalSizeBytes]);

  if (unavailable) return <AiUnavailable message={unavailable} />;
  if (loading) {
    return <div data-testid="ai-summary-loading">Generating summary…</div>;
  }
  if (!data) return null;

  return (
    <section data-testid="auto-summary">
      <h3>Summary</h3>
      <p>{data.summary}</p>
      {data.key_observations.length > 0 && (
        <ul>
          {data.key_observations.map((o, i) => (
            <li key={i}>{o}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
