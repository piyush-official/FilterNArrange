# filternarrange-filter-expression

SQL-ish row predicate via simpleeval. Translates AND/OR/NOT to lowercase
Python operators and `=` to `==`, then evaluates the resulting Python
expression against a per-row name binding (column-name → value).

`plugin.register_function(name, fn, signature)` is exposed so other layers
can extend the expression vocabulary at runtime.
