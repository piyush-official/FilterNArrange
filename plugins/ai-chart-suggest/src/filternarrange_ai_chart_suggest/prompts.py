from .schema import CHART_KINDS

SYSTEM = (
    "You are a data-visualization advisor. Given a dataset schema and the "
    "cardinality (distinct-value count) of each column, recommend exactly ONE "
    f"chart from this set: {CHART_KINDS}. Pick x/y/color columns when "
    "meaningful. Provide a one-line justification. Respond ONLY in JSON."
)


def build_prompt(payload: dict) -> str:
    return (
        f"Schema: {payload['schema']}\n"
        f"Cardinality per column: {payload['cardinality_per_column']}\n\n"
        "Produce JSON: "
        '{"recommended_chart": {"kind": <one of '
        f"{CHART_KINDS}>, "
        '"x"?: <column>, "y"?: <column>, "color"?: <column>, '
        '"justification": <one sentence>}}'
    )
