"""Generate menu/recipe markdown documents from the same recipe data used to
seed the database, so the retrieval corpus can never drift out of sync with
what's actually in menu_items/recipe_items. Hand-authored description/prep
text is layered on top — that's the actual qualitative content retrieval
exists to serve, since it isn't in the structured tables.

Run with: python -m app.retrieval.build_docs
"""

import re
from pathlib import Path

from app.db.seed import INGREDIENTS, MENU_ITEMS, RECIPES

DOCS_DIR = Path(__file__).parent / "menu_docs"

INGREDIENT_UNITS = {name: unit for name, unit, *_ in INGREDIENTS}

DISH_NOTES = {
    "T-Bone Steak": {
        "description": "A thick-cut T-bone of Zimbabwean farm beef, grilled over open coals to order.",
        "prep": "Grilled rare, medium, or well done on request, rested briefly, then plated with a side of your choice.",
    },
    "Grilled Chicken Quarter": {
        "description": "A flame-grilled chicken quarter, marinated overnight in a peri-peri style basting.",
        "prep": "Basted twice while grilling over open coals; served bone-in.",
    },
    "Boerewors & Chips": {
        "description": "Traditional farm-style boerewors sausage, coiled and grilled, served with a portion of chips.",
        "prep": "Grilled whole in a coil, sliced at the table, served with hand-cut chips.",
    },
    "Peri-Peri Chicken": {
        "description": "Chicken basted repeatedly in housemade peri-peri sauce while grilling — spicier than the Grilled Chicken Quarter.",
        "prep": "Basted three times during grilling for a sticky, spicy finish. Ask for mild if the standard sauce is too hot.",
    },
    "Pork Ribs": {
        "description": "A full rack of pork ribs, slow-basted in a sticky peri-peri glaze and finished on the grill.",
        "prep": "Slow-cooked then finished over open coals with a final glaze of peri-peri sauce.",
    },
    "Beef Kebabs": {
        "description": "Skewered cubes of marinated beef, grilled with onion and pepper between the cubes.",
        "prep": "Marinated overnight, threaded onto skewers with vegetables, grilled to order.",
    },
    "Fish & Chips": {
        "description": "Imported hake fillet, battered and fried, served with a portion of chips. The fish is imported frozen since Bindura is landlocked, which is why it carries the thinnest margin on the menu.",
        "prep": "Battered fresh to order and deep fried, served with hand-cut chips and a lemon wedge.",
    },
    "Sadza & Beef Stew": {
        "description": "A mound of stiff maize-meal sadza served with a rich beef stew — the most traditional Zimbabwean combination on the menu.",
        "prep": "Sadza is stirred fresh to order; the beef stew is simmered slowly with onion and tomato.",
    },
    "Sadza neMuriwo": {
        "description": "Sadza served with sauteed covo/rape (a leafy green also called muriwo) — a lighter vegetarian option.",
        "prep": "The greens are sauteed with onion and a little cooking oil, served alongside freshly stirred sadza.",
    },
    "Chips & Fries": {
        "description": "Hand-cut potato chips, double-fried for a crisp finish.",
        "prep": "Cut fresh in-house, blanched, then double-fried to order.",
    },
    "Coleslaw": {
        "description": "A simple cabbage and carrot slaw, served cold as a side.",
        "prep": "Shredded fresh and tossed to order; no advance prep held overnight.",
    },
    "Rice & Gravy": {
        "description": "Steamed rice with a side of gravy — a lighter alternative to sadza.",
        "prep": "Rice is steamed in batches through service; gravy is made fresh from pan drippings.",
    },
    "Peri-Peri Wings": {
        "description": "Chicken wings tossed in peri-peri sauce and grilled — a popular starter to share.",
        "prep": "Grilled first, then tossed in sauce just before serving so they stay crisp.",
    },
    "Beef Samosas": {
        "description": "Pastry parcels filled with spiced minced beef, deep fried and served as a starter.",
        "prep": "Filled and folded in-house, fried to order in small batches.",
    },
    "Chicken Livers": {
        "description": "Pan-fried chicken livers in a peri-peri sauce — a popular starter with regulars.",
        "prep": "Pan-fried hot and fast to keep the livers tender, finished with peri-peri sauce.",
    },
    "Malva Pudding": {
        "description": "A South African-style sweet, spongy baked pudding, served warm with custard.",
        "prep": "Baked in batches, warmed and plated to order with a ladle of custard.",
    },
    "Ice Cream Sundae": {
        "description": "Vanilla ice cream with toppings — the lighter dessert option on the menu.",
        "prep": "Scooped to order and finished with toppings at the pass.",
    },
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def build_docs() -> list[Path]:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    category_by_name = {}
    price_by_name = {}
    for category, items in MENU_ITEMS.items():
        for name, price, _cost in items:
            category_by_name[name] = category
            price_by_name[name] = price

    written = []
    for item_name, notes in DISH_NOTES.items():
        lines = [
            f"# {item_name}",
            "",
            f"**Category:** {category_by_name[item_name]}  ",
            f"**Price:** ${price_by_name[item_name]:.2f}",
            "",
            notes["description"],
            "",
            "## Ingredients",
        ]
        for ingredient_name, qty in RECIPES.get(item_name, []):
            unit = INGREDIENT_UNITS[ingredient_name]
            lines.append(f"- {ingredient_name} ({qty} {unit} per serving)")
        lines += ["", "## Preparation", "", notes["prep"]]

        path = DOCS_DIR / f"{_slug(item_name)}.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    paths = build_docs()
    print(f"Wrote {len(paths)} menu docs to {DOCS_DIR}")
