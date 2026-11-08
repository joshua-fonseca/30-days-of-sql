"""Assert that data/shop.db still has every deliberate quirk the lessons rely on (see data/README.md)."""

import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parent.parent / "data" / "shop.db"
c = sqlite3.connect(db)


def scalar(sql):
    return c.execute(sql).fetchone()[0]


checks = {
    "customers": (scalar("SELECT COUNT(*) FROM customers"), 60),
    "customers with no orders": (scalar("SELECT COUNT(*) FROM customers WHERE customer_id NOT IN (SELECT customer_id FROM orders)"), 6),
    "products never ordered": (scalar("SELECT COUNT(*) FROM products WHERE product_id NOT IN (SELECT product_id FROM order_items)"), 4),
    "products with NULL category": (scalar("SELECT COUNT(*) FROM products WHERE category_id IS NULL"), 1),
    "categories with no products": (scalar("SELECT COUNT(*) FROM categories WHERE category_id NOT IN (SELECT category_id FROM products WHERE category_id IS NOT NULL)"), 1),
    "customers with NULL email": (scalar("SELECT COUNT(*) FROM customers WHERE email IS NULL"), 3),
    "customers with NULL city": (scalar("SELECT COUNT(*) FROM customers WHERE city IS NULL"), 7),
    "employees without a manager": (scalar("SELECT COUNT(*) FROM employees WHERE manager_id IS NULL"), 1),
    "orders placed before signup": (scalar("SELECT COUNT(*) FROM orders o JOIN customers c USING (customer_id) WHERE o.order_date < c.signup_date"), 0),
    "newsletter rows": (scalar("SELECT COUNT(*) FROM newsletter_signups"), 20),
    "newsletter distinct after lower(trim())": (scalar("SELECT COUNT(DISTINCT lower(trim(email))) FROM newsletter_signups"), 12),
    "foreign key violations": (len(c.execute("PRAGMA foreign_key_check").fetchall()), 0),
}
bad = False
for label, (got, want) in checks.items():
    ok = got == want
    bad |= not ok
    print(f"{'ok  ' if ok else 'FAIL'} {label}: {got}" + ("" if ok else f" (want {want})"))

# Softer checks: ranges rather than exact numbers.
orders = scalar("SELECT COUNT(*) FROM orders")
items = scalar("SELECT COUNT(*) FROM order_items")
repriced = scalar("SELECT COUNT(*) FROM order_items oi JOIN products p USING (product_id) WHERE oi.unit_price_cents <> p.price_cents")
nov_dec = scalar("SELECT COUNT(*) FROM orders WHERE strftime('%m', order_date) IN ('11', '12')")
ranges = {
    "orders in 380..420": 380 <= orders <= 420,
    "order_items in 900..1100": 900 <= items <= 1100,
    "some unit prices differ from current price": repriced > 50,
    "Nov+Dec hold >25% of orders (seasonality)": nov_dec / orders > 0.25,
    "customer 3 has 5 consecutive order days (streak)": scalar(
        "SELECT COUNT(DISTINCT order_date) FROM orders WHERE customer_id = 3 AND order_date BETWEEN '2024-03-11' AND '2024-03-15'") == 5,
}
for label, ok in ranges.items():
    bad |= not ok
    print(f"{'ok  ' if ok else 'FAIL'} {label}")

raise SystemExit(1 if bad else 0)
