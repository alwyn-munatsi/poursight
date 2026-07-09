from app.llm.grounding import is_grounded, ungrounded_values
from app.llm.schemas import AnswerPlan


def test_is_grounded_true_when_all_values_present():
    rows = [{"name": "Fish & Chips", "margin_pct": 40.0}, {"name": "Pork Ribs", "margin_pct": 55.3}]
    assert is_grounded(["Fish & Chips", 40.0], rows) is True


def test_is_grounded_false_on_invented_number():
    rows = [{"name": "Fish & Chips", "margin_pct": 40.0}]
    assert is_grounded([40.0, 12.5], rows) is False


def test_ungrounded_values_lists_only_the_missing_ones():
    rows = [{"name": "Fish & Chips", "margin_pct": 40.0}]
    assert ungrounded_values([40.0, 12.5, "Fish & Chips"], rows) == [12.5]


def test_is_grounded_tolerates_int_vs_float_formatting():
    # 40 (int) vs 40.0 (float) are "the same" cited fact — a naive str() comparison
    # would wrongly call this ungrounded.
    rows = [{"margin_pct": 40.0}]
    assert is_grounded([40], rows) is True


def test_is_grounded_tolerates_small_rounding_difference():
    rows = [{"avg_beer_units_per_order": 1.5427}]
    assert is_grounded([1.54], rows) is True


def test_is_grounded_rejects_a_real_miss_despite_tolerance():
    rows = [{"avg_beer_units_per_order": 1.18}]
    assert is_grounded([1.54], rows) is False


def test_is_grounded_tolerates_percent_and_dollar_formatting():
    # Real case seen from the model: it cites "40.0%" in prose while the row holds 40.0.
    rows = [{"margin_pct": 40.0}, {"price_usd": 7.5}]
    assert is_grounded(["40.0%", "$7.50"], rows) is True


def test_answer_plan_defaults():
    plan = AnswerPlan(answer_text="Fish & Chips has the lowest margin at 40%.")
    assert plan.recommendation is None
    assert plan.cited_values == []
