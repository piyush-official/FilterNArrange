# filternarrange-format-xml

XML plugin via lxml with **safe** parsing (entities disabled, no network).
Returns `TreeData` where:

- element children become child nodes
- attributes are `@name`-keyed children
- mixed-content text content uses a `#text` child
