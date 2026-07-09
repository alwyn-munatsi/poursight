"""Builds chart_spec directly from real query result rows — never from the
LLM. Stage 2 only writes the answer text; the model never re-transcribes a
number into a chart, so a chart-data hallucination can't happen (see
PROMPTS.md's Stage 2 "deviation from the original plan" note).
"""

# Column-name hints used to pick the "label" column over a plain first-string
# guess — e.g. picks a date column for a trend line, or is_match_day (an int)
# over an unrelated string column that happens to come first.
LABEL_HINTS = ("name", "date", "category", "day", "item", "payment_method", "currency", "opponent")


def _pick_label_key(row: dict) -> str:
    keys = list(row.keys())
    for key in keys:
        if any(hint in key.lower() for hint in LABEL_HINTS):
            return key
    for key in keys:
        if isinstance(row[key], str):
            return key
    return keys[0]


def _pick_value_key(row: dict, label_key: str) -> str | None:
    for key, value in row.items():
        if key != label_key and isinstance(value, (int, float)) and not isinstance(value, bool):
            return key
    return None


def build_chart(chart_type: str, rows: list[dict]) -> dict | None:
    if not rows:
        return None

    if chart_type == "single_value":
        return {"type": "single_value", "data": rows[0]}

    label_key = _pick_label_key(rows[0])
    value_key = _pick_value_key(rows[0], label_key)
    if value_key is None:
        # No numeric column to plot — fall back to a plain table the frontend can render.
        return {"type": "table", "data": rows}

    return {
        "type": chart_type,
        "x_key": "label",
        "y_key": "value",
        "data": [{"label": row.get(label_key), "value": row.get(value_key)} for row in rows],
    }
