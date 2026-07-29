import pytest
from pydantic import ValidationError

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
    # 40 (int) vs 40.0 (float) are "the same" cited fact - a naive str() comparison
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


def test_is_grounded_accepts_a_value_only_present_in_extra_text():
    # Real case: the model restates the playbook's own margin threshold ("45%")
    # in its answer - true, not invented, but not in the SQL rows either.
    rows = [{"item_name": "Fish & Chips", "margin_pct": 40.0}]
    extra_text = ["Fish & Chips's margin is 40.0%, below the 45% target - consider a price increase."]
    assert is_grounded(["Fish & Chips", "40.0%", "45%"], rows, extra_text) is True


def test_is_grounded_accepts_a_value_only_present_in_retrieved_context():
    # Real case: a retrieved menu doc mentions the dish's category, which the SQL
    # query never selected.
    rows = [{"name": "Peri-Peri Chicken", "price_usd": 7.0}]
    extra_text = ["# Peri-Peri Chicken\n\n**Category:** Grill  \n**Price:** $7.00"]
    assert is_grounded(["Peri-Peri Chicken", "Grill"], rows, extra_text) is True


def test_is_grounded_still_rejects_values_absent_from_both_sources():
    rows = [{"item_name": "Fish & Chips", "margin_pct": 40.0}]
    extra_text = ["Fish & Chips's margin is 40.0%, below the 45% target."]
    assert ungrounded_values([40.0, "60%"], rows, extra_text) == ["60%"]


def test_answer_plan_cited_values_defaults_to_empty():
    plan = AnswerPlan(
        answer_text="Fish & Chips has the lowest margin at 40%.",
        recommendation="Consider a small price increase on Fish & Chips.",
    )
    assert plan.cited_values == []


def test_answer_plan_requires_a_recommendation():
    # Every answer must carry one - omitting it is a schema violation, not a valid null.
    with pytest.raises(ValidationError):
        AnswerPlan(answer_text="Fish & Chips has the lowest margin at 40%.")


def test_answer_plan_rejects_a_blank_recommendation():
    with pytest.raises(ValidationError):
        AnswerPlan(answer_text="Fish & Chips has the lowest margin at 40%.", recommendation="   ")
