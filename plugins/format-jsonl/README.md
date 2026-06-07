# filternarrange-format-jsonl

JSON Lines (`.jsonl` / `.ndjson`) plugin. One JSON object per line. Detection
rejects whole-document JSON (arrays / single objects) so the json plugin can
claim those.

## Public API

- `plugin.detect(sample) -> DetectResult`
- `plugin.parse(source) -> TabularData`
- `plugin.emit(data, sink) -> None`

## Notes

- Type inference samples the first 200 lines.
- Union schema: every key seen across the sample becomes a column.
