import { authHeaders } from '../../shared/api/client';

export type FilterSpec = {
  kind: 'column' | 'row' | 'expression' | 'regex';
  columns?: string[];
  predicate?: Record<string, unknown>;
  expression?: string;
  pattern?: string;
};

export type NlToFilterResponse = {
  filter_spec: FilterSpec;
  confidence: number;
};

export type SummaryResponse = {
  summary: string;
  key_observations: string[];
};

export type ChartKind =
  | 'line'
  | 'bar'
  | 'pie'
  | 'histogram'
  | 'scatter'
  | 'heatmap';

export type ChartSuggestion = {
  recommended_chart: {
    kind: ChartKind;
    x?: string | null;
    y?: string | null;
    color?: string | null;
    justification: string;
  };
};

export type AnomalyFinding = {
  kind:
    | 'outlier'
    | 'missing_values'
    | 'format_inconsistency'
    | 'possible_duplicate'
    | 'type_drift';
  column?: string | null;
  severity: 'low' | 'medium' | 'high';
  description: string;
  suggested_action?: string | null;
};

export type AnomalyResponse = { findings: AnomalyFinding[] };

export class AiUnavailableError extends Error {
  override name = 'AiUnavailableError';
  constructor(public code: string, message: string) {
    super(message);
  }
}

export class AiError extends Error {
  override name = 'AiError';
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function call<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) {
    if (data.code === 'AI_CAPABILITY_DISABLED') {
      throw new AiUnavailableError(
        data.code,
        data.message ?? 'AI capability is disabled',
      );
    }
    throw new AiError(
      data.code ?? 'AI_ERROR',
      data.message ?? 'AI error',
      r.status,
    );
  }
  return data as T;
}

export const aiApi = {
  nlToFilter: (req: {
    ref: string;
    query: string;
    schema?: Array<{ name: string; type: string }>;
  }) => call<NlToFilterResponse>('/api/v1/ai/nl-to-filter', req),
  summary: (req: {
    ref: string;
    schema: Array<{ name: string; type: string }>;
    sample_rows: Array<Record<string, unknown>>;
    total_rows: number;
    total_size_bytes: number;
  }) => call<SummaryResponse>('/api/v1/ai/summary', req),
  chartSuggest: (req: {
    ref: string;
    schema: Array<{ name: string; type: string }>;
    cardinality_per_column: Record<string, number>;
  }) => call<ChartSuggestion>('/api/v1/ai/chart-suggest', req),
  anomaly: (req: {
    ref: string;
    schema?: Array<{ name: string; type: string }>;
    sample_rows?: Array<Record<string, unknown>>;
    summary_stats?: Record<string, unknown>;
  }) => call<AnomalyResponse>('/api/v1/ai/anomaly', req),
};
