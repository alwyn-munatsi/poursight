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


def test_low_margin_rule_tolerates_a_differently_aliased_column():
    # The model might call this "profit_margin_pct" instead of "margin_pct" for a
    # different phrasing of the same question - the rule must still catch it.
    rows = [{"item_name": "Fish & Chips", "profit_margin_pct": 40.0}]
    matches = match_playbook(rows)
    assert any(m.rule_id == "low_margin_items" for m in matches)


def test_low_margin_rule_normalizes_a_raw_fraction_to_percent():
    # (price_usd - cost_usd) / price_usd returned as-is, not multiplied by 100.
    rows = [{"item_name": "Fish & Chips", "margin_ratio": 0.40}]
    matches = match_playbook(rows)
    low_margin = next(m for m in matches if m.rule_id == "low_margin_items")
    assert "40.0%" in low_margin.recommendation


def test_low_stock_rule_tolerates_differently_aliased_columns():
    rows = [{"name": "Fish Fillet (imported)", "current_stock": 4, "reorder_point": 6}]
    matches = match_playbook(rows)
    assert any(m.rule_id == "low_stock_ingredients" for m in matches)


def test_match_day_lift_rule_tolerates_differently_aliased_flag_column():
    rows = [
        {"was_match_day": 0, "avg_beer_units_per_order": 1.00},
        {"was_match_day": 1, "avg_beer_units_per_order": 1.30},
    ]
    matches = match_playbook(rows)
    assert any(m.rule_id == "match_day_lift" for m in matches)


def test_rules_are_independent_of_each_other():
    # Each call sees a realistic, uniform-shape result (as any single SQL query would
    # actually return) and only its own rule should fire.
    margin_rows = [{"item_name": "Fish & Chips", "margin_pct": 40.0}]
    match_day_rows = [
        {"is_match_day": 0, "avg_beer_units_per_order": 1.0},
        {"is_match_day": 1, "avg_beer_units_per_order": 1.5},
    ]
    assert {m.rule_id for m in match_playbook(margin_rows)} == {"low_margin_items"}
    assert {m.rule_id for m in match_playbook(match_day_rows)} == {"match_day_lift"}
