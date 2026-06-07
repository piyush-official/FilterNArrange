# filternarrange-filter-row

Row-predicate filter. Keeps rows where `predicate.col` satisfies `predicate.op`
against `predicate.value`. Supports the 14-op set defined in
`core.filter_spec.RowOp` (eq/ne/gt/gte/lt/lte, contains/starts_with/ends_with,
regex, in/not_in, is_null/is_not_null).

`validate(spec, schema=...)` returns a list of human-readable strings —
empty list means the spec is valid. Schema-aware: when `schema` is provided,
unknown column names are reported.
