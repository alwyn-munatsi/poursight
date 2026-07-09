# Evaluation report

> **Status note (2026-07-08):** this is the last complete 20/20 run, captured before two prompt fixes landed the same day (see PROMPTS.md "Iteration notes" — v2: fixed `average_order_value`'s wrong aggregation granularity, and `grounding.py`'s `%`/`$` formatting tolerance). Both fixes were verified independently via targeted commands and the existing test suite, but a full harness re-run to get updated headline numbers is blocked by Groq's free-tier daily token quota (100K TPD, exhausted during today's testing). Re-run `python -m eval.run_eval` once quota resets to refresh this report.

- Cases: 20 (0 errored)
- Query correctness: 95%
- Numeric accuracy: 75%
- Hallucination rate: 0% (0/38 citations ungrounded)

| id | query correct | answer correct | ungrounded citations | error |
|---|---|---|---|---|
| best_selling_item_overall | True | False | 0/1 |  |
| best_sellers_last_weekend | True | False | 0/5 |  |
| lowest_margin_item | True | False | 0/3 |  |
| highest_margin_item | True | True | 0/4 |  |
| match_day_beer_lift | True | True | 0/4 |  |
| total_orders | True | True | 0/1 |  |
| total_revenue | True | True | 0/1 |  |
| average_order_value | False | False | 0/1 | (fixed in v2 — see status note above) |
| best_selling_category | True | True | 0/2 |  |
| ecocash_share | True | True | 0/1 |  |
| low_stock_ingredient | True | True | 0/2 |  |
| most_expensive_item | True | True | 0/2 |  |
| cheapest_item | True | False | 0/1 |  |
| beer_item_count | True | True | 0/1 |  |
| weekend_revenue | True | True | 0/1 |  |
| avg_fx_rate | True | True | 0/1 |  |
| retrieval_dish_price | True | True | 0/3 |  |
| relative_date_yesterday | True | True | 0/1 |  |
| match_days_count | True | True | 0/1 |  |
| best_selling_starter | True | True | 0/2 |  |
