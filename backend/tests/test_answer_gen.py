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
    plan = generate_answer(
        intent="Menu items ranked by lowest profit margin",
        rows=rows,
        playbook_matches=match_playbook(rows),
    )
    assert plan.answer_text
    assert is_grounded(plan.cited_values, rows)


def test_generate_answer_returns_null_recommendation_when_no_candidates():
    rows = [{"name": "Zambezi Lager", "units_sold": 331}]
    plan = generate_answer(intent="Best seller", rows=rows, playbook_matches=[])
    # Not a hard guarantee of model behavior, but candidates=[] should make a fabricated
    # recommendation obviously wrong per the system prompt's rules.
    assert plan.recommendation is None
