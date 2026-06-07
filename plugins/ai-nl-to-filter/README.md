# ai-nl-to-filter

Translates a natural-language query into a structured `FilterSpec`.

**Capability name (entry-point):** `nl_to_filter`
**Default model:** `qwen2.5:7b` (override with `NL2FILTER_MODEL`)
**Required tier:** `free`

**Input:**

```json
{
  "ref": "uploads/.../file.csv",
  "query": "rows where age > 18",
  "schema": [{ "name": "age", "type": "integer" }]
}
```

**Output:**

```json
{
  "filter_spec": { "kind": "row", "predicate": { } },
  "confidence": 0.0
}
```
