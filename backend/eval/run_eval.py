"""The evaluation harness: runs the fixed QA cases in cases.jsonl through the
real pipeline and scores three things per the proposal:

- query correctness: did the model's generated SQL retrieve the right data?
- numeric accuracy: did the final answer actually state the right number/fact?
- hallucination rate: of everything the answer cited, what fraction wasn't
  actually in the model's own query result?

Each case supplies a `gold_sql` we authored ourselves - a single-row,
single-column ("gold_value") query we trust is correct. Query correctness and
numeric accuracy are both scored by checking whether that gold value shows up
(via app.llm.grounding.values_match, so int/float/rounding differences don't
falsely fail a case) in, respectively, the model's raw query result and the
values it actually cited in its answer. This deliberately doesn't compare SQL
text: two different SELECTs can both be "correct" if they return the right data.

Needs GROQ_API_KEY. Run with: python -m eval.run_eval
"""

import json
import sys
from pathlib import Path

from app import config
from app.db.query_engine import run_query
from app.llm.answer_gen import generate_answer
from app.llm.grounding import ungrounded_values, values_match
from app.llm.nl_to_sql import plan_query
from app.playbook.rules import match_playbook
from app.retrieval.build_docs import build_docs
from app.retrieval.embed_docs import reset_index_cache, retrieve_context

CASES_PATH = Path(__file__).parent / "cases.jsonl"
REPORT_PATH = Path(__file__).parent / "report.md"


def load_cases() -> list[dict]:
    lines = CASES_PATH.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _value_in(target, values) -> bool:
    return any(values_match(target, v) for v in values)


def run_case(case: dict) -> dict:
    gold_result = run_query(case["gold_sql"], tuple(case.get("gold_params", [])))
    gold_value = gold_result.rows[0]["gold_value"] if gold_result.rows else None

    result = {"id": case["id"], "question": case["question"], "gold_value": gold_value, "error": None}

    try:
        plan = plan_query(case["question"])
        query_result = run_query(plan.sql, tuple(plan.params))
        row_values = [v for row in query_result.rows for v in row.values()]

        matches = match_playbook(query_result.rows)
        context = retrieve_context(case["question"]) if plan.needs_retrieval else None
        answer = generate_answer(
            intent=plan.intent,
            rows=query_result.rows,
            playbook_matches=matches,
            retrieved_context=context,
        )

        ungrounded = ungrounded_values(answer.cited_values, query_result.rows)

        result.update(
            sql=plan.sql,
            row_count=query_result.row_count,
            answer_text=answer.answer_text,
            cited_values=answer.cited_values,
            query_correct=_value_in(gold_value, row_values) if gold_value is not None else None,
            answer_correct=_value_in(gold_value, answer.cited_values) if gold_value is not None else None,
            cited_count=len(answer.cited_values),
            ungrounded_count=len(ungrounded),
            ungrounded=ungrounded,
        )
    except Exception as exc:  # one bad case must not stop the rest of the harness
        result.update(
            sql=None, row_count=None, answer_text=None, cited_values=[],
            query_correct=False, answer_correct=False,
            cited_count=0, ungrounded_count=0, ungrounded=[],
            error=str(exc),
        )
    return result


def summarize(results: list[dict]) -> dict:
    completed = [r for r in results if r["error"] is None]
    scored = [r for r in completed if r["gold_value"] is not None]
    total_cited = sum(r["cited_count"] for r in completed)
    total_ungrounded = sum(r["ungrounded_count"] for r in completed)

    return {
        "cases": len(results),
        "completed": len(completed),
        "errors": len(results) - len(completed),
        "query_correctness": (sum(1 for r in scored if r["query_correct"]) / len(scored)) if scored else 0.0,
        "numeric_accuracy": (sum(1 for r in scored if r["answer_correct"]) / len(scored)) if scored else 0.0,
        "hallucination_rate": (total_ungrounded / total_cited) if total_cited else 0.0,
        "total_citations": total_cited,
        "ungrounded_citations": total_ungrounded,
    }


def write_report(results: list[dict], summary: dict, path: Path = REPORT_PATH) -> None:
    lines = [
        "# Evaluation report",
        "",
        f"- Cases: {summary['cases']} ({summary['errors']} errored)",
        f"- Query correctness: {summary['query_correctness']:.0%}",
        f"- Numeric accuracy: {summary['numeric_accuracy']:.0%}",
        f"- Hallucination rate: {summary['hallucination_rate']:.0%} "
        f"({summary['ungrounded_citations']}/{summary['total_citations']} citations ungrounded)",
        "",
        "| id | query correct | answer correct | ungrounded citations | error |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['id']} | {r['query_correct']} | {r['answer_correct']} | "
            f"{r['ungrounded_count']}/{r['cited_count']} | {r['error'] or ''} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not config.GROQ_API_KEY:
        print("GROQ_API_KEY is not set - add it to .env before running the eval harness.", file=sys.stderr)
        sys.exit(1)

    build_docs()
    reset_index_cache()

    cases = load_cases()
    results = []
    for case in cases:
        print(f"running: {case['id']}", file=sys.stderr)
        results.append(run_case(case))

    summary = summarize(results)
    write_report(results, summary)
    print(json.dumps(summary, indent=2))
    print(f"Report written to {REPORT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
