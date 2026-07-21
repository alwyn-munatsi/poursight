# Evaluation report

> **Status note (2026-07-09):** run after both v2 prompt fixes (see PROMPTS.md Iteration notes). 14/20 cases completed before hitting Groq's free-tier daily token quota again (100K TPD covers roughly 14 of our 20 two-call cases) — the 6 unscored rows below are quota errors, not model failures. Of the 14 that did complete: 13/14 correct on both query correctness and numeric accuracy, 0 hallucinated citations. The one genuine miss, `ecocash_share`, is not yet root-caused (diagnostic attempt itself hit the same quota wall). Re-run the remaining 6 cases and diagnose `ecocash_share` once quota resets.

- Cases: 20 (6 errored)
- Query correctness: 93%
- Numeric accuracy: 93%
- Hallucination rate: 0% (0/38 citations ungrounded)

| id | query correct | answer correct | ungrounded citations | error |
|---|---|---|---|---|
| best_selling_item_overall | True | True | 0/2 |  |
| best_sellers_last_weekend | True | True | 0/10 |  |
| lowest_margin_item | True | True | 0/4 |  |
| highest_margin_item | True | True | 0/4 |  |
| match_day_beer_lift | True | True | 0/4 |  |
| total_orders | True | True | 0/1 |  |
| total_revenue | True | True | 0/1 |  |
| average_order_value | True | True | 0/1 |  |
| best_selling_category | True | True | 0/2 |  |
| ecocash_share | False | False | 0/1 |  |
| low_stock_ingredient | True | True | 0/3 |  |
| most_expensive_item | True | True | 0/2 |  |
| cheapest_item | True | True | 0/2 |  |
| beer_item_count | True | True | 0/1 |  |
| weekend_revenue | False | False | 0/0 | Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kkwq49cdfk7s89c3s5m3n4hb` service tier `on_demand` on tokens per day (TPD): Limit 100000, Used 99477, Requested 725. Please try again in 2m54.528s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}} |
| avg_fx_rate | False | False | 0/0 | Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kkwq49cdfk7s89c3s5m3n4hb` service tier `on_demand` on tokens per day (TPD): Limit 100000, Used 99475, Requested 1633. Please try again in 15m57.312s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}} |
| retrieval_dish_price | False | False | 0/0 | Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kkwq49cdfk7s89c3s5m3n4hb` service tier `on_demand` on tokens per day (TPD): Limit 100000, Used 99473, Requested 1645. Please try again in 16m5.952s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}} |
| relative_date_yesterday | False | False | 0/0 | Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kkwq49cdfk7s89c3s5m3n4hb` service tier `on_demand` on tokens per day (TPD): Limit 100000, Used 99471, Requested 1665. Please try again in 16m21.504s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}} |
| match_days_count | False | False | 0/0 | Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kkwq49cdfk7s89c3s5m3n4hb` service tier `on_demand` on tokens per day (TPD): Limit 100000, Used 99469, Requested 1630. Please try again in 15m49.536s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}} |
| best_selling_starter | False | False | 0/0 | Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_01kkwq49cdfk7s89c3s5m3n4hb` service tier `on_demand` on tokens per day (TPD): Limit 100000, Used 99467, Requested 1663. Please try again in 16m16.319999999s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}} |
