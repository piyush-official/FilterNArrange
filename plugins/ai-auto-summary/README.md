# ai-auto-summary

Generates a plain-English summary plus key observations.

**Capability name:** `auto_summary`
**Default model:** `llama3.1:8b` (override with `SUMMARY_MODEL`)
**Required tier:** `free`

**Input:** `{ schema, sample_rows[<=50], total_rows, total_size_bytes }`

**Output:** `{ summary, key_observations[] }`
