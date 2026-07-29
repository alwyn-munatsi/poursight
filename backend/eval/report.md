# Evaluation report

- Cases: 20 (1 errored)
- Query correctness: 95%
- Numeric accuracy: 95%
- Hallucination rate: 0% (0/44 citations ungrounded)
- Recommendation coverage: 100% (every completed case is expected to have one - see PROMPTS.md v3)

| id | query correct | answer correct | has recommendation | ungrounded citations | error |
|---|---|---|---|---|---|
| best_selling_item_overall | True | True | True | 0/2 |  |
| best_sellers_last_weekend | True | True | True | 0/10 |  |
| lowest_margin_item | True | True | True | 0/4 |  |
| highest_margin_item | True | True | True | 0/4 |  |
| match_day_beer_lift | True | True | True | 0/4 |  |
| total_orders | True | True | True | 0/1 |  |
| total_revenue | True | True | True | 0/1 |  |
| average_order_value | True | True | True | 0/1 |  |
| best_selling_category | True | True | True | 0/2 |  |
| ecocash_share | False | False | True | 0/1 |  |
| low_stock_ingredient | True | True | True | 0/3 |  |
| most_expensive_item | True | True | True | 0/2 |  |
| cheapest_item | True | True | True | 0/2 |  |
| beer_item_count | True | True | True | 0/1 |  |
| weekend_revenue | True | True | True | 0/1 |  |
| avg_fx_rate | True | True | True | 0/1 |  |
| retrieval_dish_price | False | False | False | 0/0 | no such column: ri.quantity_per_serving |
| relative_date_yesterday | True | True | True | 0/1 |  |
| match_days_count | True | True | True | 0/1 |  |
| best_selling_starter | True | True | True | 0/2 |  |
