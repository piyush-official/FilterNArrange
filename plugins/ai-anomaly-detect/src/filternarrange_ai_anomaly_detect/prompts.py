from .schema import FINDING_KINDS, SEVERITY

SYSTEM = (
    "You are a data-quality reviewer. Given a schema, sample rows, and "
    "per-column summary statistics, identify problems. Each finding's "
    f"kind must be one of {FINDING_KINDS} and severity one of {SEVERITY}. "
    "Only emit findings you have evidence for. Respond ONLY in JSON."
)


def build_prompt(payload: dict) -> str:
    return (
        f"Schema: {payload['schema']}\n"
        f"Sample rows: {payload['sample_rows']}\n"
        f"Summary stats: {payload['summary_stats']}\n\n"
        'Produce JSON: {"findings": ['
        '{"kind": <one of '
        f"{FINDING_KINDS}>, "
        '"column"?: <column or null>, '
        '"severity": <low|medium|high>, '
        '"description": <one sentence>, '
        '"suggested_action"?: <one sentence>}]}'
    )
