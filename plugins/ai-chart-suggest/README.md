# ai-chart-suggest

Suggests the single most useful chart for a dataset.

**Capability name:** `chart_suggest`
**Default model:** `llama3.1:8b` (override with `CHART_MODEL`)
**Required tier:** `free`

**Input:** `{ schema, cardinality_per_column }`

**Output:** `{ recommended_chart: { kind, x?, y?, color?, justification } }`
where `kind ∈ {line, bar, pie, histogram, scatter, heatmap}`.
