SYSTEM = (
    "You are a data-analysis assistant. Given a dataset's schema, a small "
    "sample of rows, and row/byte counts, write a short plain-English summary "
    "describing what the data is about and what stands out. "
    "Respond ONLY in the JSON shape requested. Do not invent statistics."
)


def build_prompt(payload: dict) -> str:
    return (
        f"Schema: {payload['schema']}\n"
        f"Sample rows (truncated to 50): {payload['sample_rows'][:50]}\n"
        f"Total rows: {payload['total_rows']}\n"
        f"Total size (bytes): {payload['total_size_bytes']}\n\n"
        'Produce JSON: {"summary": <string, 1-3 sentences>, '
        '"key_observations": [<short bullet, 0-10>]}'
    )
