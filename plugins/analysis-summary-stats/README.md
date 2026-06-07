# filternarrange-analysis-summary-stats

Per-column summary statistics:

- numeric columns → `min / max / mean / median / stddev` + count + nulls + distinct
- non-numeric → top-N value frequencies (default N = 10, override via `options.top_n`)
