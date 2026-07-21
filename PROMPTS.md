# Prompts

Log of the prompts used in PourSight's two LLM stages, and how they evolved. Update this as prompts change during Phase 03 and Phase 04 - keep failed iterations, not just the final version, so the evaluation harness results can be read against prompt history.

## LLM provider

**Groq** (`api.groq.com`), model `llama-3.3-70b-versatile` by default (`GROQ_MODEL` in `.env`). Originally built against Anthropic's Claude API; switched after hitting a billing wall mid-Phase-08. Groq's API is OpenAI-compatible, so both stages use the `openai` Python SDK pointed at Groq's base URL (`app/llm/client.py::get_client()`) rather than a Groq-specific SDK. The only real porting cost was the tool-calling envelope shape:

| | Anthropic | OpenAI-compatible (Groq) |
|---|---|---|
| System prompt | top-level `system` param | a `{"role": "system", ...}` message |
| Tool schema | `{"name", "description", "input_schema"}` | `{"type": "function", "function": {"name", "description", "parameters"}}` |
| Force a specific tool | `tool_choice={"type": "tool", "name": ...}` | `tool_choice={"type": "function", "function": {"name": ...}}` |
| Reading the result | `response.content` blocks, `block.type == "tool_use"`, `block.input` (already a dict) | `response.choices[0].message.tool_calls`, `call.function.arguments` (a JSON **string** - needs `json.loads`) |

The actual JSON Schemas describing `QueryPlan`/`AnswerPlan` didn't change at all, just their wrapper. `plan_query()`/`generate_answer()` still return the same Pydantic models either way, so nothing downstream of Stage 1/2 knew the provider changed.

## Stage 1 - NL to structured query

Implemented in `backend/app/llm/nl_to_sql.py`. The model is called with `tool_choice` forcing a call to `emit_query_plan`, so the response is always the `QueryPlan` shape (`intent`, `sql`, `params`, `chart_type`, `needs_retrieval`) - never free text.

**Reference date.** The dataset is a fixed historical window (2026-01-03 to 2027-01-02), not a live stream, so "today" for resolving phrases like "last weekend" can't be the real calendar date. `reference_date()` uses `MAX(orders.order_datetime)` as "today" and the system prompt tells the model to compute relative ranges against that value with SQLite's `date()`/`strftime()` functions instead of `date('now')`.

**Schema description** given to the model (kept intentionally compact - full column comments live in `schema.sql`, not here, to keep the prompt small):

```
- menu_items(item_id, name, category, price_usd, cost_usd, is_active)
- ingredients(ingredient_id, name, unit, unit_cost_usd, stock_on_hand, reorder_level)
- recipe_items(item_id, ingredient_id, quantity_per_serving)
- fx_rates(rate_date, usd_to_zwg)
- match_days(match_date, opponent, is_home, competition, kickoff_local)
- orders(order_id, order_datetime, day_of_week, is_weekend, is_match_day, payment_method, currency, table_number)
- order_items(order_item_id, order_id, item_id, quantity, unit_price_usd, line_total_usd)
```

**Rules given to the model:**
- Single read-only `SELECT` (or `WITH ... SELECT`) only.
- Only the tables/columns above exist - this is enforced again, independently, by `query_engine.py`'s whitelist, so a rule violation here is caught rather than silently trusted.
- No inlined literals - every value goes in `params`, bound via `?` placeholders. (SQL injection defense: the model never writes user-controlled text directly into the query string.)
- Margin is always `(price_usd - cost_usd) / price_usd`.
- `needs_retrieval: true` only when the question needs qualitative menu/recipe text a SQL query can't produce (wired up in Phase 05).

**Few-shot examples** - the three example questions from the proposal, each with a full worked `QueryPlan`:
1. *"What were my five best-selling items last weekend?"* - `is_weekend = 1 AND date(order_datetime) > date(?, '-7 day')`, `chart_type: bar`.
2. *"Which menu items have the lowest profit margin?"* - `ORDER BY margin_pct ASC LIMIT 5`, `chart_type: bar`.
3. *"Did Arsenal match days lift beer sales?"* - average beer units per order grouped by `is_match_day`, `chart_type: bar`.

See `nl_to_sql.py` for the exact strings; this file summarizes rather than duplicates them so the two can't drift silently.

## Stage 2 - Grounded answer generation

Implemented in `backend/app/llm/answer_gen.py`. Forces `tool_choice` on `emit_answer`, returning `AnswerPlan` (`answer_text`, `recommendation`, `cited_values`).

**Deviation from the original plan doc:** the initial architecture sketch had stage 2 return `chart_spec` and `grounded_fields`. In practice:
- `chart_spec` moved out of the LLM call entirely. The chart is built deterministically by backend code (Phase 06) directly from the real query rows plus stage 1's `chart_type` - the model never re-transcribes numbers into a chart, so a chart-data hallucination simply can't happen.
- `grounded_fields` became `cited_values`: instead of asking the model to point at which fields it used, it lists the literal values it's asserting as fact. `app/llm/grounding.py::is_grounded()` then mechanically checks each cited value against the real result rows (numeric-tolerant comparison - `40` matches `40.0` matches `40.0000001` within 2%/0.01 - falling back to case-insensitive string equality for non-numeric values). This is a cheap, objective hallucination check - no second LLM call needed - and it's what Phase 08's eval harness uses for the hallucination-rate metric.

**Recommendation flow:** `app/playbook/rules.py::match_playbook(rows)` runs four fixed, column-pattern-triggered rules over the query result - no LLM involved - and returns zero or more candidate strings:
- `low_margin_items` - any row with `margin_pct < 45%`.
- `low_stock_ingredients` - any row where `stock_on_hand <= reorder_level`.
- `match_day_lift` - a row pair keyed by `is_match_day` (0/1) where the match-day value is ≥15% higher.
- `concentrated_best_sellers` - a ranked list (≥3 rows) where the top row is ≥30% of the total.

The candidates (if any) are passed into the stage-2 prompt as plain text; the model is instructed to pick at most one, may lightly reword it, but must not invent a new one or alter its meaning. `recommendation: null` when no rule fires.

**Rules given to the model:**
- Every number in `answer_text` must come from the provided rows; list it in `cited_values` exactly as given.
- Keep `answer_text` to 2-4 sentences.
- Recommendation must be chosen from the candidates or `null` - never freely generated.

## Retrieval (feeds into Stage 2)

`backend/app/retrieval/build_docs.py` generates 17 menu/recipe markdown docs (one per dish that has a recipe in `seed.py`) - ingredients and price are pulled from the same data that seeds the database, so the corpus can't drift out of sync with it; the description/prep text is hand-authored, since that's the actual qualitative content structured columns can't hold.

`backend/app/retrieval/embed_docs.py::search()` is plain TF-IDF + cosine similarity, not a neural embedding model - deliberately, since the corpus is ~17 short documents and static. No API key, network call, or extra ML dependency needed for something this size; `search()`/`retrieve_context()` are the only surface callers touch, so this is a drop-in place to swap in a real embedding model later if the corpus grows.

When Stage 1 sets `needs_retrieval: true`, the caller runs `retrieve_context(question)` and passes the result as Stage 2's `retrieved_context` argument, appended to the prompt as "Relevant menu/recipe context." The wiring itself (deciding *when* to call retrieval) lives in the API route, built in Phase 06 - for now it's exercised directly in `tests/test_pipeline_e2e.py`.

## Evaluation harness

`backend/eval/cases.jsonl` (20 cases) + `backend/eval/run_eval.py`. Each case is `{id, question, gold_sql}` - `gold_sql` is a query **we** authored and trust, always shaped to return exactly one row with one column named `gold_value`. No case stores an expected SQL string or a hardcoded expected number: the gold value is computed fresh from the live database every run, so the harness stays correct even after the dataset is regenerated.

Scoring deliberately doesn't compare SQL text - two different `SELECT`s can both be correct if they return the same data. Instead, for each case:
- **Query correctness** - does `gold_value` appear anywhere in the model's own generated-SQL result rows? (Tests Stage 1.)
- **Numeric accuracy** - does `gold_value` appear in the model's final `cited_values`? (Tests Stage 2 - did it actually surface the right fact, not just retrieve it.)
- **Hallucination rate** - aggregated over every case, what fraction of all `cited_values` are *not* grounded in that case's own query result (via `grounding.ungrounded_values()`)? This is citation-level, not case-level, so one case with three invented numbers weighs more than three cases each inventing one.

The 20 cases include the proposal's three example questions verbatim, plus variants exercising: aggregates (totals, averages, counts), rankings (best/worst by margin, price, category), the `is_match_day` comparison shape, the `needs_retrieval` path (`retrieval_dish_price`), and - specifically - `relative_date_yesterday`, which stress-tests the Stage 1 reference-date design (the gold SQL mirrors the exact `MAX(order_datetime) - 1 day` convention taught to the model, so the two can only disagree on a real model error, not a "yesterday" definition mismatch).

**Found while building this phase, not before:** `low_stock_ingredients` (a Phase 04 playbook rule) could never fire against the real seeded data - every ingredient's `stock_on_hand` was comfortably above its `reorder_level`. Fixed in `seed.py` by deliberately seeding Fish Fillet (imported) below its reorder level, so both the playbook rule and the `low_stock_ingredient` eval case have a real example to detect. Also found and fixed a `query_engine.py` authorizer bug the same way: `COUNT(*)` triggers SQLite's internal rowid-only read with an *empty* column name (not a real column, not `"ROWID"` as documented elsewhere), which the whitelist authorizer was denying - every `COUNT(*)`-based gold query failed until this was special-cased.

## Iteration notes

**v1 (first full run, Groq/llama-3.3-70b-versatile):** 20/20 cases completed, 95% query correctness, 75% numeric accuracy, 0% hallucination rate.

One real bug, not just a scoring artifact: `average_order_value` failed both query correctness *and* numeric accuracy. The model generated `SELECT AVG(line_total_usd) FROM order_items` - the average *line item* value ($5.01) - for a question asking for the average *order* value ($11.69). Since `order_items` has several rows per order, averaging `line_total_usd` directly silently computes the wrong granularity. This is a natural mistake without an example showing the group-by-order_id-first pattern.

**v2:** added a schema note on `order_items` explicitly warning about this ("an order usually has several rows... don't aggregate line_total_usd directly, that computes a per-item metric instead") and a fourth few-shot example for "What is the average order value?" showing the correct `GROUP BY order_id` subquery pattern. Re-verified: the same question now produces `SELECT ROUND(AVG(order_total), 2) FROM (SELECT order_id, SUM(line_total_usd) AS order_total FROM order_items GROUP BY order_id) per_order` → `11.69`, matching gold exactly.

Most of the remaining v1 numeric-accuracy misses (`best_selling_item_overall`, `best_sellers_last_weekend`, `lowest_margin_item`, `cheapest_item`) were all cases with a **string** gold value (an item name) where `query_correct` was `True` - the SQL retrieved the right row, but the model didn't always echo that exact name into `cited_values`, likely because the stage-2 prompt's wording ("every *number* you state... list it in cited_values") reads as number-specific. The model treats it more loosely in practice - several other string-valued cases (`best_selling_category`, `most_expensive_item`, `low_stock_ingredient`) passed - so this reads as prompt-wording looseness rather than a hard rule.

**v2 also reworded the Stage 2 prompt** (`answer_gen.py::build_system_prompt()`) from "every *number*... list it in cited_values" to "every number or *name*... this includes item/category names, not just numbers" - tightening exactly the ambiguity above. Re-running the full 20-case harness after both v2 changes: see the current numbers in README/eval/report.md rather than trusting this note to stay in sync - re-run `python -m eval.run_eval` any time this file's v2 date is older than the last prompt change.
