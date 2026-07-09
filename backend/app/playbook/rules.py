"""The fixed recommendation playbook.

Each rule inspects the *shape* of a query result — which columns are present,
what the values look like — and returns a candidate recommendation, or None
if it doesn't apply. This is deliberately not an LLM call: recommendations
come only from this fixed set, matching the proposal's "small fixed
playbook" scope rather than free-form generation. Stage 2 (answer_gen.py)
picks at most one matched candidate to surface; it never invents its own.
"""

from dataclasses import dataclass

LOW_MARGIN_THRESHOLD_PCT = 45.0
MATCH_DAY_LIFT_THRESHOLD_PCT = 15.0
BEST_SELLER_SHARE_THRESHOLD_PCT = 30.0


@dataclass
class PlaybookMatch:
    rule_id: str
    recommendation: str


def _low_margin_items(rows: list[dict]) -> PlaybookMatch | None:
    candidates = [
        r for r in rows
        if isinstance(r.get("margin_pct"), (int, float)) and r["margin_pct"] < LOW_MARGIN_THRESHOLD_PCT
    ]
    if not candidates:
        return None
    worst = min(candidates, key=lambda r: r["margin_pct"])
    name = worst.get("item_name") or worst.get("name") or "This item"
    return PlaybookMatch(
        rule_id="low_margin_items",
        recommendation=(
            f"{name}'s margin is {worst['margin_pct']}%, below the {LOW_MARGIN_THRESHOLD_PCT:.0f}% "
            "target — consider a small price increase or a cheaper supplier for its ingredients."
        ),
    )


def _low_stock_ingredients(rows: list[dict]) -> PlaybookMatch | None:
    candidates = [
        r for r in rows
        if isinstance(r.get("stock_on_hand"), (int, float))
        and isinstance(r.get("reorder_level"), (int, float))
        and r["stock_on_hand"] <= r["reorder_level"]
    ]
    if not candidates:
        return None
    names = ", ".join(r.get("name", "an ingredient") for r in candidates[:3])
    verb = "is" if len(candidates) == 1 else "are"
    return PlaybookMatch(
        rule_id="low_stock_ingredients",
        recommendation=f"{names} {verb} at or below the reorder level — place a restock order soon.",
    )


def _match_day_lift(rows: list[dict]) -> PlaybookMatch | None:
    by_flag = {r["is_match_day"]: r for r in rows if "is_match_day" in r}
    if 0 not in by_flag or 1 not in by_flag:
        return None
    metric_key = next(
        (k for k, v in by_flag[1].items() if k != "is_match_day" and isinstance(v, (int, float))), None
    )
    if metric_key is None:
        return None
    non_match_value, match_value = by_flag[0].get(metric_key), by_flag[1].get(metric_key)
    if not non_match_value or match_value is None:
        return None
    lift_pct = (match_value - non_match_value) / non_match_value * 100
    if lift_pct < MATCH_DAY_LIFT_THRESHOLD_PCT:
        return None
    return PlaybookMatch(
        rule_id="match_day_lift",
        recommendation=(
            f"Match days lift this by about {lift_pct:.0f}% — make sure beer stock and extra staff "
            "are scheduled ahead of Arsenal fixtures."
        ),
    )


def _concentrated_best_sellers(rows: list[dict]) -> PlaybookMatch | None:
    if len(rows) < 3:
        return None
    qty_key = next(
        (k for k in rows[0] if any(token in k for token in ("qty", "units", "quantity"))), None
    )
    if qty_key is None:
        return None
    values = [r.get(qty_key) for r in rows]
    if not all(isinstance(v, (int, float)) for v in values) or values[0] <= 0:
        return None
    share_pct = values[0] / sum(values) * 100
    if share_pct < BEST_SELLER_SHARE_THRESHOLD_PCT:
        return None
    name_key = next((k for k, v in rows[0].items() if k != qty_key and isinstance(v, str)), None)
    top_name = rows[0].get(name_key, "Your top item") if name_key else "Your top item"
    return PlaybookMatch(
        rule_id="concentrated_best_sellers",
        recommendation=(
            f"{top_name} alone accounts for about {share_pct:.0f}% of the units shown here — make "
            "sure it never runs out of stock, since it's carrying a disproportionate share of sales."
        ),
    )


RULES = (_low_margin_items, _low_stock_ingredients, _match_day_lift, _concentrated_best_sellers)


def match_playbook(rows: list[dict]) -> list[PlaybookMatch]:
    return [match for rule in RULES if (match := rule(rows)) is not None]
