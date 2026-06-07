# filternarrange-analysis-group-by

Group-by aggregation. `options = {"by": ["col_a"], "agg": {"col_b": ["sum","count","avg"]}}`.
Supported aggregators: `sum`, `count`, `avg`, `min`, `max`, `median`.
Output column names follow `{column}_{aggregator}` (e.g. `amount_sum`,
`amount_count`).
