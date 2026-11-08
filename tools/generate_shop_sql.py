"""One-off generator for data/shop.sql.

Run once, commit the output, then treat shop.sql as frozen: lessons and solutions
depend on the exact data. Seeded and standard-library only, so a rerun reproduces it.

    uv run python tools/generate_shop_sql.py
"""

import random
from datetime import date, timedelta
from pathlib import Path

random.seed(30)

OUT = Path(__file__).resolve().parent.parent / "data" / "shop.sql"
START, END = date(2024, 1, 1), date(2025, 12, 31)

FIRST = ["Ava", "Liam", "Noah", "Emma", "Olivia", "Mia", "Ethan", "Lucas", "Sofia", "Mason",
         "Isla", "Leo", "Zoe", "Ryan", "Nora", "Omar", "Priya", "Chen", "Yuki", "Diego",
         "Amara", "Hugo", "Freya", "Kofi", "Lena", "Mateo", "Ines", "Jonas", "Tara", "Sam"]
LAST = ["Smith", "Johnson", "Brown", "Lee", "Garcia", "Martin", "Nguyen", "Patel", "Khan", "Silva",
        "Kim", "Lopez", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris",
        "Clark", "Lewis", "Walker", "Young", "Allen", "King", "Wright", "Scott", "Green", "Baker"]
CITIES = [("Toronto", "Canada"), ("Vancouver", "Canada"), ("Montreal", "Canada"), ("Chicago", "USA"),
          ("Austin", "USA"), ("Seattle", "USA"), ("London", "UK"), ("Manchester", "UK"),
          ("Berlin", "Germany"), ("Lyon", "France")]

CATEGORIES = ["Electronics", "Books", "Home & Kitchen", "Toys", "Sports", "Clothing", "Grocery", "Garden"]
# 'Garden' deliberately has no products. (name, category, price_cents)
PRODUCTS = [
    ("Wireless Mouse", "Electronics", 2499), ("USB-C Cable", "Electronics", 999),
    ("Bluetooth Speaker", "Electronics", 5999), ("Noise-Cancelling Headphones", "Electronics", 14999),
    ("Webcam", "Electronics", 4999), ("Phone Stand", "Electronics", 1499),
    ("Python Crash Course", "Books", 3999), ("SQL for Data Analysis", "Books", 4499),
    ("The Pragmatic Programmer", "Books", 4999), ("Sci-Fi Anthology", "Books", 1799),
    ("Cookbook Basics", "Books", 2499), ("Mystery Novel", "Books", 1499),
    ("Chef's Knife", "Home & Kitchen", 6999), ("Cast Iron Pan", "Home & Kitchen", 3499),
    ("French Press", "Home & Kitchen", 2999), ("Bamboo Cutting Board", "Home & Kitchen", 1999),
    ("Desk Lamp", "Home & Kitchen", 2799), ("Throw Blanket", "Home & Kitchen", 2399),
    ("Building Blocks Set", "Toys", 3499), ("Jigsaw Puzzle 1000pc", "Toys", 1999),
    ("Remote Control Car", "Toys", 4499), ("Board Game Night", "Toys", 3999),
    ("Yoga Mat", "Sports", 2999), ("Water Bottle", "Sports", 1799),
    ("Running Shoes", "Sports", 8999), ("Resistance Bands", "Sports", 1599),
    ("Jump Rope", "Sports", 1299), ("Camping Hammock", "Sports", 3999),
    ("Cotton T-Shirt", "Clothing", 1899), ("Denim Jacket", "Clothing", 7999),
    ("Wool Socks", "Clothing", 1299), ("Rain Coat", "Clothing", 5999),
    ("Beanie", "Clothing", 1599), ("Espresso Beans 1kg", "Grocery", 2299),
    ("Green Tea Box", "Grocery", 1199), ("Dark Chocolate Bar", "Grocery", 399),
    ("Olive Oil 500ml", "Grocery", 1499), ("Mixed Nuts 500g", "Grocery", 1099),
    ("Gift Card Holder", None, 599),  # NULL category on purpose
    ("Mystery Box", "Toys", 2999),
]
# 4 products never ordered:
NEVER_ORDERED = {"Camping Hammock", "Jump Rope", "Beanie", "Mystery Box"}

EMPLOYEES = [  # (id, name, title, manager_id, hire_date, salary_cents)
    (1, "Grace Hopper", "CEO", None, "2019-01-07", 18500000),
    (2, "Alan Turing", "VP Engineering", 1, "2019-03-18", 14000000),
    (3, "Ada Lovelace", "VP Sales", 1, "2019-05-06", 13500000),
    (4, "Edsger Dijkstra", "VP Operations", 1, "2020-02-10", 13000000),
    (5, "Barbara Liskov", "Engineering Manager", 2, "2020-06-01", 11000000),
    (6, "Donald Knuth", "Engineering Manager", 2, "2020-09-14", 10800000),
    (7, "Margaret Hamilton", "Sales Manager", 3, "2021-01-11", 9800000),
    (8, "Linus Torvalds", "Warehouse Manager", 4, "2021-04-05", 8800000),
    (9, "Tim Berners-Lee", "Software Engineer", 5, "2021-08-23", 8200000),
    (10, "Radia Perlman", "Software Engineer", 5, "2022-02-07", 8400000),
    (11, "Ken Thompson", "Software Engineer", 6, "2022-05-16", 8600000),
    (12, "Hedy Lamarr", "Sales Associate", 7, "2022-09-12", 5600000),
    (13, "Katherine Johnson", "Sales Associate", 7, "2023-03-06", 5400000),
    (14, "Dennis Ritchie", "Warehouse Associate", 8, "2023-06-19", 4800000),
    (15, "Annie Easley", "Warehouse Associate", 8, "2024-01-15", 4600000),
]

# month -> relative order weight (more in Nov/Dec)
SEASON = {1: 0.8, 2: 0.7, 3: 0.9, 4: 0.9, 5: 1.0, 6: 1.0, 7: 0.9, 8: 0.9, 9: 1.0, 10: 1.1, 11: 1.9, 12: 2.2}


def q(v):
    """SQL literal."""
    if v is None:
        return "NULL"
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def rand_date(lo, hi):
    """Random date in [lo, hi], weighted by month seasonality (rejection sampling)."""
    span = (hi - lo).days
    while True:
        d = lo + timedelta(days=random.randint(0, span))
        if random.random() < SEASON[d.month] / 2.2:
            return d


# ---------------------------------------------------------------- customers
NUM_CUSTOMERS = 60
customers = []
used_emails = set()
for cid in range(1, NUM_CUSTOMERS + 1):
    first, last = random.choice(FIRST), random.choice(LAST)
    city, country = random.choice(CITIES)
    email = f"{first}.{last}{cid}@example.com".lower()
    signup = date(2023, 6, 1) + timedelta(days=random.randint(0, 600))
    customers.append({"id": cid, "first": first, "last": last, "email": email,
                      "city": city, "country": country, "signup": signup})
# Quirks: 3 NULL emails, a handful of NULL cities. Country stays filled in.
for c in random.sample(customers, 3):
    c["email"] = None
for c in random.sample(customers, 7):
    c["city"] = None
# Guarantee some duplicate first names (the pool of 30 makes this near-certain, but be explicit).
customers[10]["first"], customers[11]["first"] = "Sam", "Sam"
customers[20]["first"] = "Emma"
customers[21]["first"] = "Emma"

# 6 customers never order. Keep ids spread out.
NO_ORDER = {5, 17, 23, 36, 44, 58}
STREAKERS = {3: date(2024, 3, 11), 12: date(2025, 2, 3), 29: date(2025, 11, 20)}  # id -> streak start
for cid in STREAKERS:  # streak customers sign up before their streak
    customers[cid - 1]["signup"] = date(2024, 1, 5)
orderers = [c for c in customers if c["id"] not in NO_ORDER]
weights = [random.choice([1, 1, 2, 3, 6]) for _ in orderers]  # a few heavy buyers

# ----------------------------------------------------------------- orders
orders = []  # (order_id, customer_id, order_date, status)


def add_order(cid, d):
    orders.append([0, cid, d])


for c in orderers:  # every active customer gets at least one order, so exactly NO_ORDER have none
    add_order(c["id"], rand_date(max(c["signup"], START), END))
for _ in range(331):
    c = random.choices(orderers, weights)[0]
    lo = max(c["signup"], START)
    add_order(c["id"], rand_date(lo, END))

# Consecutive-day streaks (gaps-and-islands material): lengths 5, 4, 3, plus a broken streak for customer 3.
for cid, start in STREAKERS.items():
    length = {3: 5, 12: 4, 29: 3}[cid]
    for i in range(length):
        add_order(cid, start + timedelta(days=i))
# Customer 3 also has a second, shorter run after a gap, which makes the "islands" idea concrete.
for i in range(2):
    add_order(3, date(2024, 3, 20) + timedelta(days=i))

orders.sort(key=lambda o: (o[2], o[1]))
for i, o in enumerate(orders, start=1):
    o[0] = i

CUTOFF_RECENT = END - timedelta(days=21)
for o in orders:
    d = o[2]
    r = random.random()
    if d > CUTOFF_RECENT:
        o.append("pending" if r < 0.5 else "shipped")
    elif r < 0.08:
        o.append("cancelled")
    elif d > END - timedelta(days=60) and r < 0.2:
        o.append("shipped")
    else:
        o.append("delivered")

# ------------------------------------------------------------ order items
products = []
for pid, (name, cat, price) in enumerate(PRODUCTS, start=1):
    cat_id = CATEGORIES.index(cat) + 1 if cat else None
    products.append({"id": pid, "name": name, "cat": cat_id, "price": price,
                     "stock": random.randint(0, 120)})
orderable = [p for p in products if p["name"] not in NEVER_ORDERED]
popularity = [random.choice([1, 1, 2, 4, 7]) for _ in orderable]

items = []  # (order_id, product_id, qty, unit_price_cents)
for oid, _cid, _d, _status in orders:
    n = random.choices([1, 2, 3, 4, 5], [28, 30, 22, 13, 7])[0]
    chosen = set()
    while len(chosen) < n:
        chosen.add(random.choices(orderable, popularity)[0]["id"])
    for pid in sorted(chosen):
        p = products[pid - 1]
        price = p["price"]
        if random.random() < 0.15:  # price changed since the order
            price = round(price * random.choice([0.85, 0.9, 0.95, 1.05, 1.1]))
        items.append((oid, pid, random.choices([1, 2, 3, 4], [60, 25, 10, 5])[0], price))

# ----------------------------------------------------- newsletter signups
# Exact duplicates and case/whitespace-only differences, for the duplicates lesson (Day 17).
base = ["ana@example.com", "ben@example.com", "carla@example.com", "dev@example.com", "elif@example.com",
        "farid@example.com", "gina@example.com", "hiro@example.com", "iris@example.com", "jules@example.com",
        "kira@example.com", "luca@example.com"]
newsletter = []
t0 = date(2025, 1, 1)
for e in base:
    newsletter.append((e, f"{t0 + timedelta(days=random.randint(0, 200))} {random.randint(8, 20):02d}:{random.randint(0, 59):02d}:00"))
# 3 exact duplicates, 3 case-only duplicates, 2 whitespace+case duplicates (later signups)
for e in ["ana@example.com", "dev@example.com", "hiro@example.com"]:
    newsletter.append((e, f"{t0 + timedelta(days=random.randint(201, 300))} 10:00:00"))
for e in ["Ben@Example.com", "CARLA@example.com", "Gina@example.COM"]:
    newsletter.append((e, f"{t0 + timedelta(days=random.randint(201, 300))} 11:30:00"))
for e in [" iris@example.com", "Jules@example.com "]:
    newsletter.append((e, f"{t0 + timedelta(days=random.randint(201, 300))} 12:45:00"))
newsletter.sort(key=lambda r: r[1])

# ------------------------------------------------------------------ write
lines = [
    "-- shop.sql: the teaching database for 30 Days of SQL. Generated by tools/generate_shop_sql.py (seed 30).",
    "-- FROZEN: do not regenerate casually, lessons and solutions depend on this exact data.",
    "PRAGMA foreign_keys = ON;",
    "",
    "CREATE TABLE customers (",
    "    customer_id  INTEGER PRIMARY KEY,",
    "    first_name   TEXT NOT NULL,",
    "    last_name    TEXT NOT NULL,",
    "    email        TEXT UNIQUE,",
    "    city         TEXT,",
    "    country      TEXT NOT NULL,",
    "    signup_date  TEXT NOT NULL",
    ") STRICT;",
    "",
    "CREATE TABLE categories (",
    "    category_id  INTEGER PRIMARY KEY,",
    "    name         TEXT NOT NULL UNIQUE",
    ") STRICT;",
    "",
    "CREATE TABLE products (",
    "    product_id   INTEGER PRIMARY KEY,",
    "    name         TEXT NOT NULL,",
    "    category_id  INTEGER REFERENCES categories (category_id),",
    "    price_cents  INTEGER NOT NULL CHECK (price_cents > 0),",
    "    stock        INTEGER NOT NULL CHECK (stock >= 0)",
    ") STRICT;",
    "",
    "CREATE TABLE orders (",
    "    order_id     INTEGER PRIMARY KEY,",
    "    customer_id  INTEGER NOT NULL REFERENCES customers (customer_id),",
    "    order_date   TEXT NOT NULL,",
    "    status       TEXT NOT NULL CHECK (status IN ('pending', 'shipped', 'delivered', 'cancelled'))",
    ") STRICT;",
    "",
    "CREATE TABLE order_items (",
    "    order_id          INTEGER NOT NULL REFERENCES orders (order_id),",
    "    product_id        INTEGER NOT NULL REFERENCES products (product_id),",
    "    quantity          INTEGER NOT NULL CHECK (quantity > 0),",
    "    unit_price_cents  INTEGER NOT NULL,",
    "    PRIMARY KEY (order_id, product_id)",
    ") STRICT;",
    "",
    "CREATE TABLE employees (",
    "    employee_id   INTEGER PRIMARY KEY,",
    "    name          TEXT NOT NULL,",
    "    title         TEXT NOT NULL,",
    "    manager_id    INTEGER REFERENCES employees (employee_id),",
    "    hire_date     TEXT NOT NULL,",
    "    salary_cents  INTEGER NOT NULL",
    ") STRICT;",
    "",
    "-- No constraints on purpose: this table has duplicates for the Day 17 lesson.",
    "CREATE TABLE newsletter_signups (",
    "    email         TEXT NOT NULL,",
    "    signed_up_at  TEXT NOT NULL",
    ") STRICT;",
    "",
]


def block(table, cols, rows):
    out = [f"INSERT INTO {table} ({', '.join(cols)}) VALUES"]
    out.append(",\n".join("    (" + ", ".join(q(v) for v in r) + ")" for r in rows) + ";")
    out.append("")
    return out


lines += block("customers", ["customer_id", "first_name", "last_name", "email", "city", "country", "signup_date"],
               [(c["id"], c["first"], c["last"], c["email"], c["city"], c["country"], str(c["signup"])) for c in customers])
lines += block("categories", ["category_id", "name"], [(i, n) for i, n in enumerate(CATEGORIES, start=1)])
lines += block("products", ["product_id", "name", "category_id", "price_cents", "stock"],
               [(p["id"], p["name"], p["cat"], p["price"], p["stock"]) for p in products])
lines += block("employees", ["employee_id", "name", "title", "manager_id", "hire_date", "salary_cents"], EMPLOYEES)
lines += block("orders", ["order_id", "customer_id", "order_date", "status"],
               [(o[0], o[1], str(o[2]), o[3]) for o in orders])
lines += block("order_items", ["order_id", "product_id", "quantity", "unit_price_cents"], items)
lines += block("newsletter_signups", ["email", "signed_up_at"], newsletter)

OUT.write_text("\n".join(lines))
print(f"wrote {OUT}: {len(customers)} customers, {len(products)} products, {len(orders)} orders, {len(items)} items")
