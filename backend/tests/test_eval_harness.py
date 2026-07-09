"""Tests for the eval harness's own logic — case loading, gold-query
validity, and scoring math. None of this needs GROQ_API_KEY: it's
everything in run_eval.py except the actual model calls inside run_case().
"""

from app.db.query_engine import run_query
from eval.run_eval import load_cases, summarize, write_report


def test_load_cases_returns_15_to_20_cases_with_required_fields():
    cases = load_cases()
    assert 15 <= len(cases) <= 20
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "case ids must be unique"
    for case in cases:
        assert case["question"]
        assert case["gold_sql"]


def test_every_gold_sql_runs_and_returns_a_single_gold_value():
    # Regression guard: if the schema ever changes, this catches a broken
    # gold_sql immediately instead of only surfacing it mid eval run.
    for case in load_cases():
        result = run_query(case["gold_sql"], tuple(case.get("gold_params", [])))
        assert result.row_count == 1, f"{case['id']}: expected exactly one gold row"
        assert "gold_value" in result.rows[0], f"{case['id']}: missing gold_value column"
        assert result.rows[0]["gold_value"] is not None, f"{case['id']}: gold_value is NULL"


def test_summarize_computes_rates_correctly():
    results = [
        {"error": None, "gold_value": "x", "query_correct": True, "answer_correct": True,
         "cited_count": 2, "ungrounded_count": 0},
        {"error": None, "gold_value": "y", "query_correct": True, "answer_correct": False,
         "cited_count": 3, "ungrounded_count": 1},
        {"error": None, "gold_value": "z", "query_correct": False, "answer_correct": False,
         "cited_count": 1, "ungrounded_count": 1},
        {"error": "boom", "gold_value": None, "query_correct": False, "answer_correct": False,
         "cited_count": 0, "ungrounded_count": 0},
    ]
    summary = summarize(results)

    assert summary["cases"] == 4
    assert summary["completed"] == 3
    assert summary["errors"] == 1
    assert summary["query_correctness"] == 2 / 3
    assert summary["numeric_accuracy"] == 1 / 3
    assert summary["total_citations"] == 6
    assert summary["ungrounded_citations"] == 2
    assert summary["hallucination_rate"] == 2 / 6


def test_summarize_handles_no_scored_cases_without_dividing_by_zero():
    summary = summarize([])
    assert summary == {
        "cases": 0, "completed": 0, "errors": 0,
        "query_correctness": 0.0, "numeric_accuracy": 0.0, "hallucination_rate": 0.0,
        "total_citations": 0, "ungrounded_citations": 0,
    }


def test_write_report_produces_markdown_with_summary_and_rows(tmp_path):
    results = [
        {"id": "case_a", "query_correct": True, "answer_correct": True,
         "ungrounded_count": 0, "cited_count": 1, "error": None},
    ]
    summary = summarize([{**results[0], "gold_value": "x", "cited_count": 1, "ungrounded_count": 0}])
    out_path = tmp_path / "report.md"

    write_report(results, summary, path=out_path)

    text = out_path.read_text(encoding="utf-8")
    assert "# Evaluation report" in text
    assert "case_a" in text
    assert "Query correctness" in text
