import * as React from 'react';
import { aiApi, AiUnavailableError, type ChartSuggestion as ChartSug } from '../api';
import { AiUnavailable } from './AiUnavailable';

type Props = {
  ref_: string;
  schema: Array<{ name: string; type: string }>;
  cardinality: Record<string, number>;
  skip: boolean;
};

export function ChartSuggestion({ ref_, schema, cardinality, skip }: Props) {
  const [data, setData] = React.useState<ChartSug | null>(null);
  const [unavailable, setUnavailable] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (skip) return;
    let cancelled = false;
    setLoading(true);
    aiApi
      .chartSuggest({
        ref: ref_,
        schema,
        cardinality_per_column: cardinality,
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
  }, [ref_, skip, schema, cardinality]);

  if (unavailable) return <AiUnavailable message={unavailable} />;
  if (loading) {
    return <div data-testid="chart-suggest-loading">Suggesting chart…</div>;
  }
  if (!data) return null;

  const c = data.recommended_chart;
  return (
    <section data-testid="chart-suggestion">
      <h3>Suggested chart</h3>
      <p>
        <strong>{c.kind}</strong> — x={c.x ?? '—'} y={c.y ?? '—'} color=
        {c.color ?? '—'}
      </p>
      <p>{c.justification}</p>
    </section>
  );
}
