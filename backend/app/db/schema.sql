-- PourSight schema: The Arsenal Bar & Grill, Bindura, Zimbabwe (synthetic pilot dataset)

CREATE TABLE IF NOT EXISTS menu_items (
    item_id     INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL CHECK (category IN (
                    'Beer', 'Cider', 'Spirits', 'Soft Drink',
                    'Starter', 'Grill', 'Sadza & Sides', 'Dessert'
                )),
    price_usd   REAL NOT NULL,
    cost_usd    REAL NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id   INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    unit            TEXT NOT NULL,
    unit_cost_usd   REAL NOT NULL,
    stock_on_hand   REAL NOT NULL,
    reorder_level   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_items (
    item_id                 INTEGER NOT NULL REFERENCES menu_items(item_id),
    ingredient_id           INTEGER NOT NULL REFERENCES ingredients(ingredient_id),
    quantity_per_serving    REAL NOT NULL,
    PRIMARY KEY (item_id, ingredient_id)
);

-- Illustrative USD -> ZWG (Zimbabwe Gold) daily rate; not sourced from official RBZ data.
CREATE TABLE IF NOT EXISTS fx_rates (
    rate_date       TEXT PRIMARY KEY,
    usd_to_zwg      REAL NOT NULL
);

-- Arsenal FC (English Premier League) fixture calendar, used for match-day sales correlation.
CREATE TABLE IF NOT EXISTS match_days (
    match_date      TEXT PRIMARY KEY,
    opponent        TEXT NOT NULL,
    is_home         INTEGER NOT NULL,
    competition     TEXT NOT NULL,
    kickoff_local   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        INTEGER PRIMARY KEY,
    order_datetime  TEXT NOT NULL,
    day_of_week     TEXT NOT NULL,
    is_weekend      INTEGER NOT NULL,
    is_match_day    INTEGER NOT NULL,
    payment_method  TEXT NOT NULL CHECK (payment_method IN ('cash_usd', 'cash_zwg', 'ecocash', 'card')),
    currency        TEXT NOT NULL CHECK (currency IN ('USD', 'ZWG')),
    table_number    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id   INTEGER PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES orders(order_id),
    item_id         INTEGER NOT NULL REFERENCES menu_items(item_id),
    quantity        INTEGER NOT NULL,
    unit_price_usd  REAL NOT NULL,
    line_total_usd  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_item ON order_items(item_id);
CREATE INDEX IF NOT EXISTS idx_orders_datetime ON orders(order_datetime);
