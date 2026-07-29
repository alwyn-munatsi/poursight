"""Live tests for stage 2 (answer generation). Need no key to import the
module, but actually calling the model is skipped unless GROQ_API_KEY
is set - see test_nl_to_sql.py for the same pattern and why.
"""

import os

import pytest

from app.llm.answer_gen import generate_answer
from app.llm.grounding import is_grounded
from app.playbook.rules import match_playbook

pytestmark = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"), reason="requires GROQ_API_KEY"
)


def test_generate_answer_is_grounded_in_the_rows():
    rows = [
        {"item_name": "Fish & Chips", "price_usd": 7.5, "cost_usd": 4.5, "margin_pct": 40.0},
        {"item_name": "Pork Ribs", "price_usd": 8.5, "cost_usd": 3.8, "margin_pct": 55.3},
    ]
    matches = match_playbook(rows)
    plan = generate_answer(
        intent="Menu items ranked by lowest profit margin",
        rows=rows,
        playbook_matches=matches,
    )
    assert plan.answer_text
    # extra_text: the model may legitimately restate the playbook's own threshold
    # (e.g. "below the 45% target"), which isn't in the rows but isn't invented either.
    assert is_grounded(plan.cited_values, rows, [m.recommendation for m in matches])


def test_generate_answer_composes_its_own_recommendation_when_no_candidates():
    # No playbook match here (a single aggregate row) - the model must still produce
    # a non-blank recommendation, grounded in the same rows, not a fabricated fact.
    rows = [{"name": "Zambezi Lager", "units_sold": 331}]
    plan = generate_answer(intent="Best seller", rows=rows, playbook_matches=[])
    assert plan.recommendation.strip()
    assert is_grounded(plan.cited_values, rows)
