# filternarrange-format-tsv

Tab-separated values (TSV) plugin for FilterNArrange. Detects via
`csv.Sniffer` with tab as the dominant delimiter, parses into the
canonical `TabularData` shape, and emits with `csv.QUOTE_MINIMAL`.

## Public API

Standard `FormatPlugin` surface:

- `plugin.manifest` — `FormatManifest`
- `plugin.detect(sample: bytes) -> DetectResult`
- `plugin.parse(source: BinaryIO) -> TabularData`
- `plugin.emit(data: TabularData, sink: BinaryIO) -> None`

## Limits

- First 8 KiB of the file is used for detection.
- Type inference samples the first 200 rows.
- Row payloads are emitted as dicts keyed by column name (Plan B canonical shape).
