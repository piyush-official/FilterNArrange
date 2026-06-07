SUMMARY_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["summary", "key_observations"],
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 1000},
        "key_observations": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 300},
            "maxItems": 10,
        },
    },
}
