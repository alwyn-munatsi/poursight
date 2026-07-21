# SKILL: Ask PourSight

A reusable skill definition for PourSight's natural-language-to-grounded-answer capability, so it can be described and invoked consistently outside this specific app (e.g. as a tool definition for another agent, or a skill in a different Claude Code project).

## What it does

Given a plain-English question about a restaurant/bar's sales, inventory, or menu performance, returns a grounded answer, a chart-ready data shape, and (when relevant) a short recommendation drawn from a fixed playbook - never invented numbers. Every number the answer states is traceable back to a value in the query result that actually produced it.

## Invocation

`POST /api/ask` (see `backend/app/api/routes.py`)

### Input

```json
{
  "question": "Which menu items have the lowest profit margin?",
  "conversation_id": "optional-string-for-multi-turn-context"
}
```

### Output

```json
{
  "answer_text": "Fish & Chips has the lowest profit margin at 40.0%, well below Pork Ribs and the other items shown here.",
  "recommendation": "Fish & Chips's margin is 40.0%, below the 45% target - consider a small price increase or a cheaper supplier for its ingredients.",
  "chart": {
    "type": "bar",
    "x_key": "label",
    "y_key": "value",
    "data": [
      { "label": "Fish & Chips", "value": 40.0 },
      { "label": "Pork Ribs", "value": 55.3 }
    ]
  },
  "cited_values": ["Fish & Chips", "40.0%"],
  "intent": "Menu items ranked by lowest profit margin",
  "sql": "SELECT name AS item_name, price_usd, cost_usd, ROUND((price_usd - cost_usd) / price_usd * 100, 1) AS margin_pct FROM menu_items ORDER BY margin_pct ASC LIMIT 5",
  "row_count": 5,
  "truncated": false
}
```

`chart` is `null` for a question with no rows to plot; `chart.type` is one of `bar`, `line`, `pie`, `single_value`, or `table` (table is the fallback when there's no numeric column to plot). `recommendation` is `null` when no playbook rule matched.

## Pipeline (what happens between input and output)

1. **`app/llm/nl_to_sql.py::plan_query()`** - question → `QueryPlan` (intent, sql, params, chart_type, needs_retrieval), via forced tool-calling so the shape is guaranteed.
2. **`app/db/query_engine.py::run_query()`** - validates the SQL (single read-only `SELECT`, whitelisted tables/columns/functions only) and executes it. Untrusted generated SQL never reaches SQLite without passing this.
3. **`app/playbook/rules.py::match_playbook()`** - checks the result shape against 4 fixed rules (low margin, low stock, match-day lift, concentrated best-sellers); no LLM involved.
4. **`app/retrieval/embed_docs.py::retrieve_context()`** - only called if `needs_retrieval` is true; TF-IDF lookup over menu/recipe docs.
5. **`app/llm/answer_gen.py::generate_answer()`** - result rows + playbook candidates + retrieved context → `AnswerPlan` (answer_text, recommendation, cited_values), again via forced tool-calling.
6. **`app/api/chart_builder.py::build_chart()`** - builds the chart deterministically from the real query rows (never from the LLM - see PROMPTS.md's Stage 2 notes for why).

## Constraints

- Read-only, parameterized SQL against a whitelisted schema only - enforced independently at the SQL text level, a SQLite authorizer callback, and a read-only DB connection (three layers; see `query_engine.py`).
- Recommendations come from a fixed rule set (`playbook/rules.py`), never freely generated.
- Every value in `cited_values` is checked against the real query result via `app/llm/grounding.py::is_grounded()` - this is the mechanical hallucination check the eval harness scores against.

## LLM provider

Groq (`llama-3.3-70b-versatile` by default, `GROQ_MODEL` in `.env`), via the OpenAI-compatible `openai` SDK. See `app/llm/client.py` and PROMPTS.md's "LLM provider" section for the porting notes if swapping providers again.
