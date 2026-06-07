FINDING_KINDS = [
    "outlier",
    "missing_values",
    "format_inconsistency",
    "possible_duplicate",
    "type_drift",
]
SEVERITY = ["low", "medium", "high"]

ANOMALY_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["findings"],
    "additionalProperties": False,
    "properties": {
        "findings": {
            "type": "array",
            "maxItems": 40,
            "items": {
                "type": "object",
                "required": ["kind", "severity", "description"],
                "additionalProperties": False,
                "properties": {
                    "kind": {"enum": FINDING_KINDS},
                    "column": {"type": ["string", "null"]},
                    "severity": {"enum": SEVERITY},
                    "description": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 400,
                    },
                    "suggested_action": {
                        "type": ["string", "null"],
                        "maxLength": 300,
                    },
                },
            },
        }
    },
}
