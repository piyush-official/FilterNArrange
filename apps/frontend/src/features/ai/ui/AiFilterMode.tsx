import * as React from 'react';
import { aiApi, AiUnavailableError, type FilterSpec } from '../api';
import { AiUnavailable } from './AiUnavailable';

type Props = {
  ref_: string;
  schema: Array<{ name: string; type: string }>;
  onApply: (spec: FilterSpec) => void;
};

export function AiFilterMode({ ref_, schema, onApply }: Props) {
  const [query, setQuery] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<
    { filter_spec: FilterSpec; confidence: number } | null
  >(null);
  const [unavailable, setUnavailable] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const submit = async () => {
    setLoading(true);
    setError(null);
    setUnavailable(null);
    try {
      const r = await aiApi.nlToFilter({ ref: ref_, query, schema });
      setResult(r);
    } catch (e: unknown) {
      if (e instanceof AiUnavailableError) setUnavailable(e.message);
      else if (e instanceof Error) setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (unavailable) return <AiUnavailable message={unavailable} />;

  return (
    <div data-testid="ai-filter-mode">
      <textarea
        placeholder="Ask about your data..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button onClick={submit} disabled={loading || !query.trim()}>
        {loading ? 'Translating...' : 'Translate'}
      </button>
      {error && <div role="alert">{error}</div>}
      {result && (
        <div>
          <div>Confidence: {(result.confidence * 100).toFixed(0)}%</div>
          <pre>{JSON.stringify(result.filter_spec, null, 2)}</pre>
          <button onClick={() => onApply(result.filter_spec)}>Apply</button>
        </div>
      )}
    </div>
  );
}
