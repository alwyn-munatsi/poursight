"""Generate a synthetic sales/inventory dataset for The Arsenal Bar & Grill.

Distributions (order volume, item mix) are modeled loosely on public restaurant
POS datasets; menu, ingredients, currency, and match-day fields are authored
for this pilot and are not real business records. Match fixtures are
illustrative, not the real Arsenal FC calendar.

Run with: python -m app.db.seed
"""

import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "poursight.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

RANDOM_SEED = 42
START_DATE = date(2026, 1, 3)
NUM_DAYS = 365  # a full year, so the dataset supports real seasonality and volume

# (name, price_usd, cost_usd)
MENU_ITEMS = {
    "Beer": [
        # Local (Zimbabwe-brewed, via Delta Corporation)
        ("Zambezi Lager", 2.50, 1.10),
        ("Lion Lager", 2.50, 1.05),
        ("Bohlingers Lager", 2.30, 1.00),
        ("Castle Lager", 2.60, 1.15),
        ("Castle Lite", 2.70, 1.15),
        ("Eagle Lager", 2.20, 0.95),
        ("Golden Pilsner", 2.40, 1.05),
        ("Carling Black Label", 2.60, 1.15),
        # Imported (priced higher to reflect import duties)
        ("Heineken", 3.50, 1.60),
        ("Windhoek Lager", 3.20, 1.45),
        ("Hansa Pilsener", 3.00, 1.35),
        ("Guinness Foreign Extra Stout", 3.60, 1.65),
        ("Corona Extra", 3.80, 1.75),
        ("Amstel Lager", 3.30, 1.50),
        ("Carlsberg", 3.40, 1.55),
        ("Stella Artois", 3.70, 1.70),
    ],
    "Cider": [
        ("Savanna Dry", 2.80, 1.20),
        ("Hunters Dry", 2.80, 1.20),
        ("Hunters Gold", 2.90, 1.25),
    ],
    "Spirits": [
        ("Amarula (single)", 3.50, 1.10),
        ("Chateau Brandy (single)", 3.00, 0.95),
        ("Gordon's Gin (single)", 3.20, 1.00),
        ("Smirnoff Vodka (single)", 3.20, 1.00),
        ("Jameson Whisky (single)", 4.50, 1.60),
        ("Zed Rum (single)", 2.80, 0.85),
    ],
    "Soft Drink": [
        ("Mazoe Orange Crush", 1.20, 0.35),
        ("Coca-Cola", 1.50, 0.45),
        ("Sprite", 1.50, 0.45),
        ("Bottled Water", 1.00, 0.25),
    ],
    "Starter": [
        ("Peri-Peri Wings", 4.50, 1.80),
        ("Beef Samosas", 3.50, 1.20),
        ("Chicken Livers", 4.00, 1.50),
    ],
    "Grill": [
        ("T-Bone Steak", 9.50, 4.20),
        ("Grilled Chicken Quarter", 6.50, 2.60),
        ("Boerewors & Chips", 6.00, 2.30),
        ("Peri-Peri Chicken", 7.00, 2.80),
        ("Pork Ribs", 8.50, 3.80),
        ("Beef Kebabs", 6.50, 2.60),
        ("Fish & Chips", 7.50, 4.50),  # imported fish -> deliberately the thinnest margin
    ],
    "Sadza & Sides": [
        ("Sadza & Beef Stew", 5.50, 2.10),
        ("Sadza neMuriwo", 4.00, 1.30),
        ("Chips & Fries", 2.50, 0.70),
        ("Coleslaw", 2.00, 0.55),
        ("Rice & Gravy", 3.50, 1.10),
    ],
    "Dessert": [
        ("Malva Pudding", 3.50, 1.10),
        ("Ice Cream Sundae", 3.00, 0.90),
    ],
}

# Baseline category sampling weights; tuned so Beer/Grill dominate, matching a bar & grill.
# Beer carries a larger share of the weight since the catalog now spans 16 local + imported labels.
CATEGORY_WEIGHTS = {
    "Beer": 38, "Cider": 8, "Spirits": 10, "Soft Drink": 12,
    "Starter": 8, "Grill": 18, "Sadza & Sides": 9, "Dessert": 2,
}

# (name, unit, unit_cost_usd, stock_on_hand, reorder_level)
INGREDIENTS = [
    ("Beef Steak Cuts", "kg", 6.50, 40, 10),
    ("Chicken Quarters", "kg", 3.20, 55, 15),
    ("Pork Ribs (raw)", "kg", 5.80, 30, 8),
    ("Boerewors Sausage", "kg", 4.50, 25, 8),
    ("Fish Fillet (imported)", "kg", 8.00, 4, 6),  # deliberately below reorder_level: imports are slow to restock
    ("Maize Meal", "kg", 1.10, 80, 20),
    ("Covo/Rape (Muriwo)", "kg", 1.40, 25, 8),
    ("Potatoes", "kg", 0.90, 60, 15),
    ("Cabbage", "kg", 0.70, 20, 6),
    ("Carrots", "kg", 1.00, 15, 5),
    ("Rice", "kg", 1.60, 35, 10),
    ("Cooking Oil", "litre", 2.20, 30, 8),
    ("Peri-Peri Sauce", "litre", 4.00, 12, 4),
    ("Beef Kebab Cubes", "kg", 6.80, 20, 6),
    ("Chicken Livers (raw)", "kg", 3.00, 15, 5),
    ("Samosa Pastry & Filling", "kg", 3.50, 12, 4),
    ("Milk", "litre", 1.20, 25, 8),
    ("Sugar", "kg", 1.30, 20, 6),
    ("Custard/Ice Cream Mix", "kg", 3.80, 10, 3),
    ("Gravy Powder", "kg", 2.50, 8, 3),
]

# menu item name -> [(ingredient name, quantity_per_serving)]
RECIPES = {
    "T-Bone Steak": [("Beef Steak Cuts", 0.35), ("Cooking Oil", 0.02)],
    "Grilled Chicken Quarter": [("Chicken Quarters", 0.40), ("Peri-Peri Sauce", 0.03)],
    "Boerewors & Chips": [("Boerewors Sausage", 0.30), ("Potatoes", 0.30), ("Cooking Oil", 0.03)],
    "Peri-Peri Chicken": [("Chicken Quarters", 0.40), ("Peri-Peri Sauce", 0.05)],
    "Pork Ribs": [("Pork Ribs (raw)", 0.45), ("Peri-Peri Sauce", 0.03)],
    "Beef Kebabs": [("Beef Kebab Cubes", 0.30), ("Cooking Oil", 0.02)],
    "Fish & Chips": [("Fish Fillet (imported)", 0.30), ("Potatoes", 0.30), ("Cooking Oil", 0.04)],
    "Sadza & Beef Stew": [("Maize Meal", 0.25), ("Beef Steak Cuts", 0.20), ("Cooking Oil", 0.02)],
    "Sadza neMuriwo": [("Maize Meal", 0.25), ("Covo/Rape (Muriwo)", 0.20), ("Cooking Oil", 0.02)],
    "Chips & Fries": [("Potatoes", 0.35), ("Cooking Oil", 0.04)],
    "Coleslaw": [("Cabbage", 0.15), ("Carrots", 0.05)],
    "Rice & Gravy": [("Rice", 0.20), ("Gravy Powder", 0.03)],
    "Peri-Peri Wings": [("Chicken Quarters", 0.30), ("Peri-Peri Sauce", 0.04)],
    "Beef Samosas": [("Samosa Pastry & Filling", 0.20), ("Cooking Oil", 0.03)],
    "Chicken Livers": [("Chicken Livers (raw)", 0.30), ("Cooking Oil", 0.02)],
    "Malva Pudding": [("Sugar", 0.10), ("Milk", 0.10)],
    "Ice Cream Sundae": [("Custard/Ice Cream Mix", 0.15), ("Sugar", 0.03)],
}

# Illustrative Premier League opponents, not a real season fixture list.
OPPONENTS = [
    "Chelsea", "Newcastle United", "Liverpool", "Manchester City", "Tottenham Hotspur",
    "Aston Villa", "Brighton & Hove Albion", "West Ham United", "Everton", "Manchester United",
    "Nottingham Forest", "Wolverhampton Wanderers", "Crystal Palace", "Fulham", "Brentford",
    "AFC Bournemouth", "Burnley", "Leeds United", "Sunderland",
]
KICKOFF_SLOTS = ["15:00 CAT", "17:00 CAT", "19:30 CAT", "21:45 CAT", "22:00 CAT"]


def generate_match_fixtures(rng: random.Random) -> list[tuple[int, str, int, str, str]]:
    """A home-and-away fixture against each opponent, spread evenly across the year."""
    matchups = [(opp, is_home) for opp in OPPONENTS for is_home in (1, 0)]
    rng.shuffle(matchups)

    interval = NUM_DAYS / len(matchups)
    used_offsets = set()
    fixtures = []
    for i, (opponent, is_home) in enumerate(matchups):
        offset = max(0, min(NUM_DAYS - 1, round(i * interval + rng.uniform(-1.5, 1.5))))
        while offset in used_offsets and offset < NUM_DAYS - 1:
            offset += 1
        used_offsets.add(offset)
        kickoff = rng.choice(KICKOFF_SLOTS)
        fixtures.append((offset, opponent, is_home, "Premier League", kickoff))
    return sorted(fixtures, key=lambda f: f[0])

PAYMENT_METHODS = ["ecocash", "cash_usd", "card", "cash_zwg"]
PAYMENT_WEIGHTS = [0.42, 0.28, 0.15, 0.15]


def build_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())


def seed_menu_items(conn: sqlite3.Connection) -> dict:
    """Insert menu items, return {name: item_id}."""
    name_to_id = {}
    item_id = 1
    for category, items in MENU_ITEMS.items():
        for name, price, cost in items:
            conn.execute(
                "INSERT INTO menu_items (item_id, name, category, price_usd, cost_usd) VALUES (?, ?, ?, ?, ?)",
                (item_id, name, category, price, cost),
            )
            name_to_id[name] = item_id
            item_id += 1
    return name_to_id


def seed_ingredients(conn: sqlite3.Connection) -> dict:
    name_to_id = {}
    for ingredient_id, (name, unit, unit_cost, stock, reorder) in enumerate(INGREDIENTS, start=1):
        conn.execute(
            "INSERT INTO ingredients (ingredient_id, name, unit, unit_cost_usd, stock_on_hand, reorder_level) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ingredient_id, name, unit, unit_cost, stock, reorder),
        )
        name_to_id[name] = ingredient_id
    return name_to_id


def seed_recipes(conn: sqlite3.Connection, item_ids: dict, ingredient_ids: dict) -> None:
    for item_name, ingredients in RECIPES.items():
        for ingredient_name, qty in ingredients:
            conn.execute(
                "INSERT INTO recipe_items (item_id, ingredient_id, quantity_per_serving) VALUES (?, ?, ?)",
                (item_ids[item_name], ingredient_ids[ingredient_name], qty),
            )


def seed_fx_rates(conn: sqlite3.Connection, rng: random.Random) -> None:
    rate = 13.5
    for offset in range(NUM_DAYS):
        day = START_DATE + timedelta(days=offset)
        rate += rng.uniform(-0.15, 0.25)  # slow depreciation drift
        rate = max(12.0, min(rate, 22.0))
        conn.execute(
            "INSERT INTO fx_rates (rate_date, usd_to_zwg) VALUES (?, ?)",
            (day.isoformat(), round(rate, 2)),
        )


def seed_match_days(conn: sqlite3.Connection, fixtures: list[tuple[int, str, int, str, str]]) -> set:
    match_dates = set()
    for offset, opponent, is_home, competition, kickoff in fixtures:
        day = START_DATE + timedelta(days=offset)
        conn.execute(
            "INSERT INTO match_days (match_date, opponent, is_home, competition, kickoff_local) "
            "VALUES (?, ?, ?, ?, ?)",
            (day.isoformat(), opponent, is_home, competition, kickoff),
        )
        match_dates.add(day)
    return match_dates


def weighted_category(rng: random.Random, is_match_day: bool, is_weekend: bool) -> str:
    weights = dict(CATEGORY_WEIGHTS)
    if is_match_day:
        weights["Beer"] *= 1.8
        weights["Grill"] *= 1.3
    elif is_weekend:
        weights["Beer"] *= 1.3
        weights["Cider"] *= 1.2
        weights["Grill"] *= 1.15
    categories, cat_weights = zip(*weights.items())
    return rng.choices(categories, weights=cat_weights, k=1)[0]


def order_datetime_for(day: date, rng: random.Random, is_match_day: bool) -> datetime:
    # Lunch (11-14) or evening (17-23); match days skew heavily to evening kickoff crowds.
    if is_match_day or rng.random() < 0.65:
        hour = rng.randint(17, 23)
    else:
        hour = rng.randint(11, 14)
    minute = rng.randint(0, 59)
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


def seed_orders(conn: sqlite3.Connection, item_ids: dict, match_dates: set, rng: random.Random) -> None:
    order_id = 1
    order_item_id = 1
    all_items = [(name, cat) for cat, items in MENU_ITEMS.items() for name, _, _ in items]
    items_by_category: dict[str, list[str]] = {}
    for cat, items in MENU_ITEMS.items():
        items_by_category[cat] = [name for name, _, _ in items]
    price_by_name = {name: price for items in MENU_ITEMS.values() for name, price, _ in items}

    for offset in range(NUM_DAYS):
        day = START_DATE + timedelta(days=offset)
        day_of_week = day.strftime("%A")
        is_weekend = day_of_week in ("Saturday", "Sunday")
        is_match_day = day in match_dates

        base_orders = 20
        multiplier = 1.0
        if is_weekend:
            multiplier *= 1.6
        if is_match_day:
            multiplier *= 1.4
        num_orders = max(4, round(base_orders * multiplier * rng.uniform(0.85, 1.15)))

        for _ in range(num_orders):
            order_dt = order_datetime_for(day, rng, is_match_day)
            payment_method = rng.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1)[0]
            currency = "ZWG" if payment_method in ("ecocash", "cash_zwg") and rng.random() < 0.7 else "USD"
            table_number = rng.randint(1, 20)

            conn.execute(
                "INSERT INTO orders (order_id, order_datetime, day_of_week, is_weekend, is_match_day, "
                "payment_method, currency, table_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (order_id, order_dt.isoformat(sep=" "), day_of_week, int(is_weekend), int(is_match_day),
                 payment_method, currency, table_number),
            )

            num_line_items = rng.choices([1, 2, 3, 4, 5], weights=[30, 30, 22, 12, 6], k=1)[0]
            for _ in range(num_line_items):
                category = weighted_category(rng, is_match_day, is_weekend)
                item_name = rng.choice(items_by_category[category])
                quantity = rng.choices([1, 2, 3], weights=[70, 24, 6], k=1)[0]
                unit_price = price_by_name[item_name]
                conn.execute(
                    "INSERT INTO order_items (order_item_id, order_id, item_id, quantity, unit_price_usd, "
                    "line_total_usd) VALUES (?, ?, ?, ?, ?, ?)",
                    (order_item_id, order_id, item_ids[item_name], quantity, unit_price,
                     round(unit_price * quantity, 2)),
                )
                order_item_id += 1

            order_id += 1


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        build_schema(conn)
        item_ids = seed_menu_items(conn)
        ingredient_ids = seed_ingredients(conn)
        seed_recipes(conn, item_ids, ingredient_ids)
        seed_fx_rates(conn, rng)
        fixtures = generate_match_fixtures(rng)
        match_dates = seed_match_days(conn, fixtures)
        seed_orders(conn, item_ids, match_dates, rng)
        conn.commit()

        counts = {}
        for table in ("menu_items", "ingredients", "recipe_items", "fx_rates",
                       "match_days", "orders", "order_items"):
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"Seeded {DB_PATH}")
        for table, count in counts.items():
            print(f"  {table}: {count} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
