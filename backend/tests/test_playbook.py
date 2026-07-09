from app.playbook.rules import match_playbook


def test_low_margin_rule_fires_below_threshold():
    rows = [
        {"item_name": "Fish & Chips", "price_usd": 7.5, "cost_usd": 4.5, "margin_pct": 40.0},
        {"item_name": "Pork Ribs", "price_usd": 8.5, "cost_usd": 3.8, "margin_pct": 55.3},
    ]
    matches = match_playbook(rows)
    ids = [m.rule_id for m in matches]
    assert "low_margin_items" in ids
    low_margin = next(m for m in matches if m.rule_id == "low_margin_items")
    assert "Fish & Chips" in low_margin.recommendation
    assert "40.0%" in low_margin.recommendation


def test_low_margin_rule_silent_when_all_healthy():
    rows = [{"item_name": "Zambezi Lager", "margin_pct": 56.0}]
    assert match_playbook(rows) == []


def test_low_stock_rule_fires_at_or_below_reorder_level():
    rows = [
        {"name": "Fish Fillet (imported)", "stock_on_hand": 5, "reorder_level": 6},
        {"name": "Potatoes", "stock_on_hand": 60, "reorder_level": 15},
    ]
    matches = match_playbook(rows)
    low_stock = next(m for m in matches if m.rule_id == "low_stock_ingredients")
    assert "Fish Fillet (imported)" in low_stock.recommendation
    assert "Potatoes" not in low_stock.recommendation


def test_match_day_lift_rule_fires_above_threshold():
    rows = [
        {"is_match_day": 0, "avg_beer_units_per_order": 1.00},
        {"is_match_day": 1, "avg_beer_units_per_order": 1.30},
    ]
    matches = match_playbook(rows)
    lift = next(m for m in matches if m.rule_id == "match_day_lift")
    assert "30%" in lift.recommendation


def test_match_day_lift_rule_silent_below_threshold():
    rows = [
        {"is_match_day": 0, "avg_beer_units_per_order": 1.50},
        {"is_match_day": 1, "avg_beer_units_per_order": 1.55},
    ]
    assert match_playbook(rows) == []


def test_concentrated_best_sellers_rule_fires():
    rows = [
        {"item_name": "Heineken", "units_sold": 800},
        {"item_name": "Zambezi Lager", "units_sold": 300},
        {"item_name": "Castle Lager", "units_sold": 280},
    ]
    matches = match_playbook(rows)
    concentrated = next(m for m in matches if m.rule_id == "concentrated_best_sellers")
    assert "Heineken" in concentrated.recommendation


def test_no_rules_fire_on_empty_result():
    assert match_playbook([]) == []


def test_multiple_rules_can_fire_together():
    rows = [
        {"item_name": "Fish & Chips", "margin_pct": 40.0},
        {"is_match_day": 0, "avg_beer_units_per_order": 1.0},
        {"is_match_day": 1, "avg_beer_units_per_order": 1.5},
    ]
    # Not realistic as one query's output, but proves rules are independent of each other.
    matches = match_playbook(rows)
    ids = {m.rule_id for m in matches}
    assert {"low_margin_items", "match_day_lift"} <= ids
