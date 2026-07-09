from app.api.chart_builder import build_chart


def test_single_value_returns_first_row_as_is():
    chart = build_chart("single_value", [{"total_orders": 8904}])
    assert chart == {"type": "single_value", "data": {"total_orders": 8904}}


def test_bar_chart_picks_name_as_label_and_qty_as_value():
    rows = [
        {"item_name": "Heineken", "units_sold": 765},
        {"item_name": "Savanna Dry", "units_sold": 776},
    ]
    chart = build_chart("bar", rows)
    assert chart["type"] == "bar"
    assert chart["data"] == [
        {"label": "Heineken", "value": 765},
        {"label": "Savanna Dry", "value": 776},
    ]


def test_bar_chart_prefers_is_match_day_label_over_plain_first_string_search():
    # is_match_day is an int, but its name hints it's the category axis, not a metric.
    rows = [
        {"is_match_day": 0, "avg_beer_units_per_order": 1.18},
        {"is_match_day": 1, "avg_beer_units_per_order": 1.54},
    ]
    chart = build_chart("bar", rows)
    assert chart["data"] == [
        {"label": 0, "value": 1.18},
        {"label": 1, "value": 1.54},
    ]


def test_line_chart_uses_date_column_as_label():
    rows = [{"rate_date": "2026-01-03", "usd_to_zwg": 13.6}, {"rate_date": "2026-01-04", "usd_to_zwg": 13.7}]
    chart = build_chart("line", rows)
    assert chart["data"][0] == {"label": "2026-01-03", "value": 13.6}


def test_falls_back_to_table_when_no_numeric_column():
    rows = [{"name": "Zambezi Lager", "category": "Beer"}]
    chart = build_chart("bar", rows)
    assert chart == {"type": "table", "data": rows}


def test_returns_none_for_empty_rows():
    assert build_chart("bar", []) is None
