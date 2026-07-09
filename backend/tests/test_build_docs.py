from app.db.seed import RECIPES
from app.retrieval.build_docs import DISH_NOTES, DOCS_DIR, build_docs


def test_build_docs_writes_one_file_per_dish():
    paths = build_docs()
    assert len(paths) == len(DISH_NOTES) == 17
    assert all(p.exists() for p in paths)


def test_every_recipe_item_has_a_doc():
    # Catches drift if seed.py's RECIPES gains/loses a dish without DISH_NOTES following.
    assert set(RECIPES.keys()) == set(DISH_NOTES.keys())


def test_doc_ingredients_match_recipe_data():
    build_docs()
    text = (DOCS_DIR / "fish-chips.md").read_text(encoding="utf-8")
    for ingredient_name, qty in RECIPES["Fish & Chips"]:
        assert ingredient_name in text
        assert str(qty) in text


def test_doc_has_expected_sections():
    build_docs()
    text = (DOCS_DIR / "t-bone-steak.md").read_text(encoding="utf-8")
    assert text.startswith("# T-Bone Steak")
    assert "## Ingredients" in text
    assert "## Preparation" in text
    assert "**Price:** $9.50" in text
