# filternarrange-format-yaml

YAML 1.2 plugin built on PyYAML's **safe** loader. Always returns `TreeData`.
Detection prefers `---` doc markers; JSON-syntax inputs are intentionally
de-prioritised so the JSON plugin can claim them.
