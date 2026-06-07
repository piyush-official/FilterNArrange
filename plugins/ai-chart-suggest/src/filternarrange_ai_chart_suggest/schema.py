CHART_KINDS = ["line", "bar", "pie", "histogram", "scatter", "heatmap"]

CHART_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["recommended_chart"],
    "additionalProperties": False,
    "properties": {
        "recommended_chart": {
            "type": "object",
            "required": ["kind", "justification"],
            "additionalProperties": False,
            "properties": {
                "kind": {"enum": CHART_KINDS},
                "x": {"type": ["string", "null"]},
                "y": {"type": ["string", "null"]},
                "color": {"type": ["string", "null"]},
                "justification": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 400,
                },
            },
        }
    },
}
