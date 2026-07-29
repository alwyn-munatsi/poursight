"""End-to-end smoke test for the full question -> answer pipeline
(Phases 02-05 wired together). A small preview of what the Phase 08 eval
harness will do at scale; skipped without GROQ_API_KEY like the other
live tests. The actual API route handler doesn't exist until Phase 06 - this
test inlines the same orchestration ad hoc, just to prove the pieces compose.
"""

import os

import pytest

from app.db.query_engine import run_query
from app.llm.answer_gen import generate_answer
from app.llm.grounding import is_grounded
from app.llm.nl_to_sql import plan_query
from app.playbook.rules import match_playbook
from app.retrieval.build_docs import build_docs
from app.retrieval.embed_docs import reset_index_cache, retrieve_context

pytestmark = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"), reason="requires GROQ_API_KEY"
)

EXAMPLE_QUESTIONS = [
    "What were my five best-selling items last weekend?",
    "Which menu items have the lowest profit margin?",
    "Did Arsenal match days lift beer sales?",
    "What's in the Peri-Peri Chicken and how much does it cost?",
]


@pytest.fixture(scope="module", autouse=True)
def menu_docs_ready():
    build_docs()
    reset_index_cache()


@pytest.mark.parametrize("question", EXAMPLE_QUESTIONS)
def test_question_to_grounded_answer(question):
    query_plan = plan_query(question)
    result = run_query(query_plan.sql, tuple(query_plan.params))
    assert result.row_count > 0

    context = retrieve_context(question) if query_plan.needs_retrieval else None
    matches = match_playbook(result.rows)
    answer = generate_answer(
        intent=query_plan.intent,
        rows=result.rows,
        playbook_matches=matches,
        retrieved_context=context,
    )

    extra_text = [m.recommendation for m in matches]
    if context:
        extra_text.append(context)

    assert answer.answer_text
    assert answer.recommendation.strip(), f"Missing recommendation for {question!r}"
    assert is_grounded(answer.cited_values, result.rows, extra_text), (
        f"Ungrounded citation for {question!r}: {answer.cited_values} vs {result.rows[:5]}"
    )
