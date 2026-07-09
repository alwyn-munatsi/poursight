"""Mechanical check that an answer's cited values actually appear in the
query result it was supposedly describing. Used both at runtime (to log a
warning if the model drifts) and by the Phase 08 eval harness's query
correctness, numeric accuracy, and hallucination rate metrics.
"""

import math

NUMERIC_REL_TOL = 0.02  # 2% — enough to absorb rounding/formatting, not enough to hide a real miss
NUMERIC_ABS_TOL = 0.01


def _to_float(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text.startswith("$"):
        text = text[1:]
    if text.endswith("%"):
        text = text[:-1]
    return float(text)


def values_match(a, b) -> bool:
    """True if a and b are "the same" for grounding purposes: numerically close
    (absorbing e.g. 40 vs 40.0 vs "40.0%" vs "$40.00") or, failing that, equal as text."""
    try:
        return math.isclose(_to_float(a), _to_float(b), rel_tol=NUMERIC_REL_TOL, abs_tol=NUMERIC_ABS_TOL)
    except (TypeError, ValueError):
        return str(a).strip().lower() == str(b).strip().lower()


def is_grounded(cited_values: list, rows: list[dict]) -> bool:
    row_values = [v for row in rows for v in row.values()]
    return all(any(values_match(cited, v) for v in row_values) for cited in cited_values)


def ungrounded_values(cited_values: list, rows: list[dict]) -> list:
    row_values = [v for row in rows for v in row.values()]
    return [cited for cited in cited_values if not any(values_match(cited, v) for v in row_values)]
