"""Mechanical check that an answer's cited values actually appear in
content the model was legitimately given. Used both at runtime (to log a
warning if the model drifts) and by the Phase 08 eval harness's query
correctness, numeric accuracy, and hallucination rate metrics.

"Legitimately given" is two things, not just the query rows:
  1. The query result rows (structured, checked with numeric tolerance).
  2. Trusted prose the model was also shown - playbook candidate text and
     retrieved menu/recipe doc text (checked as a substring match, since
     these are natural-language sources, not structured values). Without
     this, a value the model correctly restates from a playbook threshold
     (e.g. "below the 45% target") or a retrieved doc's metadata (e.g. a
     dish's category) gets wrongly flagged as hallucinated.
"""

import math

NUMERIC_REL_TOL = 0.02  # 2% - enough to absorb rounding/formatting, not enough to hide a real miss
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


def _appears_in_text(value, text: str) -> bool:
    if not text:
        return False
    haystack = text.lower()
    candidate = str(value).strip().lower()
    if candidate and candidate in haystack:
        return True
    stripped = candidate.strip("%$")
    return bool(stripped) and stripped in haystack


def ungrounded_values(cited_values: list, rows: list[dict], extra_text: list[str] | None = None) -> list:
    row_values = [v for row in rows for v in row.values()]
    blob = " ".join(extra_text or [])
    return [
        cited for cited in cited_values
        if not any(values_match(cited, v) for v in row_values)
        and not _appears_in_text(cited, blob)
    ]


def is_grounded(cited_values: list, rows: list[dict], extra_text: list[str] | None = None) -> bool:
    return not ungrounded_values(cited_values, rows, extra_text)
