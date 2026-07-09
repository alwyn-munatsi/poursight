"""Tests for the stage-1 NL -> SQL planner.

The schema/reference-date tests need no API key. The live tests actually call
Groq and are skipped unless GROQ_API_KEY is set (e.g. in CI or once a
teammate has added a key to .env) — they exist so we can run them by hand
whenever the prompt changes, not so every `pytest` run costs money.
"""

import os

import pytest

from app.db.query_engine import run_query
from app.llm.nl_to_sql import plan_query, reference_date
from app.llm.schemas import QueryPlan


def test_reference_date_matches_seeded_dataset():
    # seed.py: START_DATE 2026-01-03 + NUM_DAYS 365 -> last day is 2027-01-02.
    assert reference_date() == "2027-01-02"


def test_query_plan_rejects_non_select():
    with pytest.raises(ValueError):
        QueryPlan(intent="x", sql="DELETE FROM orders", params=[], chart_type="bar", needs_retrieval=False)


def test_query_plan_accepts_valid_shape():
    plan = QueryPlan(
        intent="best sellers",
        sql="SELECT name FROM menu_items",
        params=[],
        chart_type="bar",
        needs_retrieval=False,
    )
    assert plan.chart_type == "bar"
    assert plan.needs_retrieval is False


def test_query_plan_rejects_bad_chart_type():
    with pytest.raises(ValueError):
        QueryPlan(intent="x", sql="SELECT 1", params=[], chart_type="scatter3d", needs_retrieval=False)


EXAMPLE_QUESTIONS = [
    "What were my five best-selling items last weekend?",
    "Which menu items have the lowest profit margin?",
    "Did Arsenal match days lift beer sales?",
]


@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="requires GROQ_API_KEY")
@pytest.mark.parametrize("question", EXAMPLE_QUESTIONS)
def test_plan_query_produces_runnable_sql(question):
    plan = plan_query(question)
    result = run_query(plan.sql, tuple(plan.params))
    assert result.row_count > 0
