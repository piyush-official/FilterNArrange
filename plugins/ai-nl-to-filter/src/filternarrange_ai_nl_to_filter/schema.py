"""NL→Filter output schema.

Wraps the FilterSpec schema established by Plan C's filter plugins. We
import lazily and fall back to a minimal inline schema so unit tests in
environments without ``filternarrange_filter_core`` installed still run.
"""

try:
    from filternarrange_filter_core.schema import FILTER_SPEC_SCHEMA  # type: ignore[import-not-found]
except ImportError:
    FILTER_SPEC_SCHEMA = {
        "type": "object",
        "required": ["kind"],
        "properties": {
            "kind": {"enum": ["column", "row", "expression", "regex"]},
            "columns": {"type": "array", "items": {"type": "string"}},
            "predicate": {"type": "object"},
            "expression": {"type": "string"},
            "pattern": {"type": "string"},
        },
    }


NL2FILTER_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["filter_spec", "confidence"],
    "additionalProperties": False,
    "properties": {
        "filter_spec": FILTER_SPEC_SCHEMA,
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
}
