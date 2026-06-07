SYSTEM = (
    "You convert natural-language data questions into a structured FilterSpec. "
    "A FilterSpec has one of four kinds: 'column' (project columns), 'row' "
    "(predicate over rows), 'expression' (free-form SQL-like), 'regex' (match "
    "pattern). Use 'row' for value comparisons, 'column' for column projection, "
    "'expression' only when row predicates don't suffice, 'regex' for pattern "
    "search. Respond ONLY in JSON. Include a confidence in [0,1]."
)


def build_prompt(payload: dict) -> str:
    return (
        f"Detected schema: {payload['schema']}\n"
        f"User query: {payload['query']!r}\n\n"
        'Return JSON: {"filter_spec": <FilterSpec>, "confidence": <0-1>}'
    )
