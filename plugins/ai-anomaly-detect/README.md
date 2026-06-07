# ai-anomaly-detect

Flags outliers, missing values, format inconsistencies, possible duplicates,
and type drift.

**Capability name:** `anomaly_detect`
**Default model:** `llama3.1:8b` (override with `ANOMALY_MODEL`)
**Required tier:** `free`

**Input:** `{ schema, sample_rows, summary_stats }`

**Output:** `{ findings: [{ kind, column?, severity, description, suggested_action? }] }`
where `kind ∈ {outlier, missing_values, format_inconsistency, possible_duplicate, type_drift}`
and `severity ∈ {low, medium, high}`.

For full-dataset scans (not bounded by sample size), submit
`POST /api/v1/jobs` with `kind: "ai-anomaly-full"`.
