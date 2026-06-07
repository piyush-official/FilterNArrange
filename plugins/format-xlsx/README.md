# filternarrange-format-xlsx

Excel workbook (.xlsx) plugin via openpyxl. Workbooks may contain multiple
sheets; the gateway calls `plugin.list_sheets()` before parse and the user
picks one. `plugin.parse(source, sheet_name=...)` returns the chosen sheet
as `TabularData` with dict rows keyed by column name.

## Fixture

`tests/fixtures/two_sheets.xlsx` is built from
`scripts/build_xlsx_fixture.py` (run once; not part of CI).
