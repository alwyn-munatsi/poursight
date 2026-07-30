"""Stage 1: turn a manager's plain-English question into a QueryPlan.

The model is forced (tool_choice) to call emit_query_plan, so the response is
always the constrained JSON shape in schemas.QueryPlan - never free text. The
SQL it returns is untrusted until it passes app.db.query_engine.run_query().
"""

import json

from openai import OpenAI

from app import config
from app.db.connection import get_connection
from app.llm.client import get_client
from app.llm.schemas import QueryPlan

TOOL_NAME = "emit_query_plan"

SCHEMA_DESCRIPTION = """\
- menu_items(item_id, name, category, price_usd, cost_usd, is_active)
    category is one of: Beer, Cider, Spirits, Soft Drink, Starter, Grill, Sadza & Sides, Dessert.
    prices/costs are in USD. margin = (price_usd - cost_usd) / price_usd.
- ingredients(ingredient_id, name, unit, unit_cost_usd, stock_on_hand, reorder_level)
    a current stock snapshot, not a movement ledger.
- recipe_items(item_id, ingredient_id, quantity_per_serving)
    links menu_items to the ingredients used to make them. To list what's in a dish,
    join menu_items.item_id = recipe_items.item_id and
    recipe_items.ingredient_id = ingredients.ingredient_id - always alias recipe_items
    in the JOIN clause (e.g. "JOIN recipe_items ri ON ...") before referencing its
    columns as ri.column_name, or the alias won't exist and the query will fail.
- fx_rates(rate_date, usd_to_zwg)
    illustrative daily USD -> ZWG (Zimbabwe Gold) exchange rate.
- match_days(match_date, opponent, is_home, competition, kickoff_local)
    Arsenal FC fixture calendar (illustrative, not the real schedule).
- orders(order_id, order_datetime, day_of_week, is_weekend, is_match_day, payment_method, currency, table_number)
    payment_method is one of: ecocash, cash_usd, cash_zwg, card.
- order_items(order_item_id, order_id, item_id, quantity, unit_price_usd, line_total_usd)
    one row per menu item within an order - an order usually has several rows.
    For a per-*order* metric (e.g. average order value), first SUM(line_total_usd)
    grouped by order_id, then aggregate across orders - don't aggregate line_total_usd
    directly, that computes a per-*item* metric instead.\
"""

FEW_SHOT_EXAMPLES = """\
Q: "What were my five best-selling items last weekend?"
{
  "intent": "Top 5 items by units sold on the most recent Saturday/Sunday",
  "sql": "SELECT mi.name AS item_name, SUM(oi.quantity) AS units_sold FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN menu_items mi ON mi.item_id = oi.item_id WHERE o.is_weekend = 1 AND date(o.order_datetime) > date(?, '-7 day') GROUP BY mi.item_id ORDER BY units_sold DESC LIMIT 5",
  "params": ["<reference_date>"],
  "chart_type": "bar",
  "needs_retrieval": false
}

Q: "Which menu items have the lowest profit margin?"
{
  "intent": "Menu items ranked by lowest profit margin",
  "sql": "SELECT name AS item_name, price_usd, cost_usd, ROUND((price_usd - cost_usd) / price_usd * 100, 1) AS margin_pct FROM menu_items ORDER BY margin_pct ASC LIMIT 5",
  "params": [],
  "chart_type": "bar",
  "needs_retrieval": false
}

Q: "Did Arsenal match days lift beer sales?"
{
  "intent": "Compare average beer units per order on match days vs non-match days",
  "sql": "SELECT o.is_match_day, ROUND(AVG(beer_qty), 2) AS avg_beer_units_per_order FROM (SELECT o.order_id, o.is_match_day, COALESCE(SUM(CASE WHEN mi.category = 'Beer' THEN oi.quantity END), 0) AS beer_qty FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.order_id LEFT JOIN menu_items mi ON mi.item_id = oi.item_id GROUP BY o.order_id) sub JOIN orders o ON o.order_id = sub.order_id GROUP BY o.is_match_day",
  "params": [],
  "chart_type": "bar",
  "needs_retrieval": false
}

Q: "What is the average order value?"
{
  "intent": "Average total spend per order, across all orders",
  "sql": "SELECT ROUND(AVG(order_total), 2) AS avg_order_value FROM (SELECT order_id, SUM(line_total_usd) AS order_total FROM order_items GROUP BY order_id) per_order",
  "params": [],
  "chart_type": "single_value",
  "needs_retrieval": false
}

Q: "What's in the Peri-Peri Chicken and how much does it cost?"
{
  "intent": "Ingredients and price/cost of the Peri-Peri Chicken",
  "sql": "SELECT mi.name AS item_name, mi.price_usd, mi.cost_usd, i.name AS ingredient_name, ri.quantity_per_serving FROM menu_items mi JOIN recipe_items ri ON ri.item_id = mi.item_id JOIN ingredients i ON i.ingredient_id = ri.ingredient_id WHERE mi.name = ?",
  "params": ["Peri-Peri Chicken"],
  "chart_type": "bar",
  "needs_retrieval": true
}\
"""

TOOL = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "Turn the manager's question into a single read-only SQL query plan against the "
            "PourSight database."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "One sentence paraphrasing what the user wants to know.",
                },
                "sql": {
                    "type": "string",
                    "description": (
                        "A single SQLite SELECT statement (or WITH ... SELECT). Use ? placeholders "
                        "for every literal value and list them in params, in order. Only reference "
                        "the tables and columns listed in the schema."
                    ),
                },
                "params": {
                    "type": "array",
                    "items": {},
                    "description": "Values to bind to the ? placeholders in sql, in the order they appear.",
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "single_value"],
                    "description": (
                        "bar for rankings/comparisons, line for trends over time, pie for "
                        "share-of-total, single_value for one number."
                    ),
                },
                "needs_retrieval": {
                    "type": "boolean",
                    "description": (
                        "True only if answering well also needs qualitative menu/recipe text beyond "
                        "what this SQL query returns."
                    ),
                },
            },
            "required": ["intent", "sql", "params", "chart_type", "needs_retrieval"],
        },
    },
}


def reference_date() -> str:
    """The most recent order date in the dataset, used as "today" for relative dates."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT MAX(order_datetime) AS max_dt FROM orders").fetchone()
        return (row["max_dt"] or "")[:10]
    finally:
        conn.close()


def build_system_prompt(today: str) -> str:
    return (
        "You are the query planner for PourSight, a natural-language analytics assistant "
        "for The Arsenal Bar & Grill, a bar and grill in Bindura, Zimbabwe.\n\n"
        f"Treat {today} as today's date when resolving relative time references such as "
        "\"last weekend\", \"this month\", or \"yesterday\". Compute date ranges with SQLite "
        "date functions (date(), datetime(), strftime()) against that reference date, not the "
        "real calendar.\n\n"
        "Database schema:\n"
        f"{SCHEMA_DESCRIPTION}\n\n"
        "Rules:\n"
        "- Only ever produce a single read-only SELECT (or WITH ... SELECT) statement.\n"
        "- Only reference the tables and columns listed above - nothing else exists.\n"
        "- Never inline a literal value from the question directly into the SQL string; put it in "
        "params and use a ? placeholder instead.\n"
        "- Margins are computed as (price_usd - cost_usd) / price_usd.\n"
        "- If the question needs qualitative context the database can't answer (e.g. what's in a "
        "dish, cooking method) alongside numbers, set needs_retrieval to true.\n\n"
        "Examples:\n"
        f"{FEW_SHOT_EXAMPLES}"
    )


def plan_query(question: str, client: OpenAI | None = None) -> QueryPlan:
    client = client or get_client()
    system = build_system_prompt(reference_date())

    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        tools=[TOOL],
        tool_choice={"type": "function", "function": {"name": TOOL_NAME}},
    )

    message = response.choices[0].message
    tool_calls = message.tool_calls or []
    for call in tool_calls:
        if call.function.name == TOOL_NAME:
            try:
                arguments = json.loads(call.function.arguments)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Model returned invalid JSON for {TOOL_NAME}: {exc}") from exc
            return QueryPlan.model_validate(arguments)

    raise RuntimeError(f"Model did not call {TOOL_NAME}: {message.content!r}")
