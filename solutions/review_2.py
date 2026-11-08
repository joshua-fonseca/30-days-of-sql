# Review 2 reference solutions (Days 11-16, plus earlier basics)
import sqlite3

from helpers import TODAY, library_full_conn, shop_conn, show

shop = shop_conn()
lib = library_full_conn()

# ------------------------------------------------------------------ Part A: write the query
print("# R2 A1")
show(shop.execute("""
    SELECT p.name AS product, format('%.2f', p.price_cents / 100.0) AS price
    FROM products AS p
    JOIN categories AS c ON c.category_id = p.category_id
    WHERE c.name = 'Books'
    ORDER BY p.price_cents DESC, p.name
"""))

print("# R2 A2")
show(shop.execute("""
    SELECT o.order_id, o.order_date, c.first_name || ' ' || c.last_name AS customer
    FROM orders AS o
    JOIN customers AS c ON c.customer_id = o.customer_id
    WHERE o.order_date >= '2025-03-01' AND o.order_date < '2025-04-01'
    ORDER BY o.order_date, o.order_id
    LIMIT 5
"""))
print(shop.execute("SELECT COUNT(*) FROM orders WHERE order_date >= '2025-03-01' AND order_date < '2025-04-01'").fetchone())

print("# R2 A3")
show(shop.execute("""
    SELECT c.name AS category, COUNT(p.product_id) AS products
    FROM categories AS c
    LEFT JOIN products AS p ON p.category_id = c.category_id
    GROUP BY c.category_id
    ORDER BY products, category
"""))

print("# R2 A4")
show(shop.execute("""
    WITH spend AS (
        SELECT o.customer_id, SUM(i.quantity * i.unit_price_cents) AS cents
        FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.customer_id
    )
    SELECT c.first_name || ' ' || c.last_name AS customer, format('%.2f', s.cents / 100.0) AS spend
    FROM spend AS s JOIN customers AS c ON c.customer_id = s.customer_id
    WHERE s.cents > (SELECT AVG(cents) FROM spend)
    ORDER BY s.cents DESC, customer
    LIMIT 3
"""))
print(shop.execute("""
    WITH spend AS (SELECT o.customer_id, SUM(i.quantity * i.unit_price_cents) AS cents
        FROM orders o JOIN order_items i ON i.order_id = o.order_id WHERE o.status <> 'cancelled' GROUP BY o.customer_id)
    SELECT COUNT(*) FROM spend WHERE cents > (SELECT AVG(cents) FROM spend)
""").fetchone())

print("# R2 A5")
show(shop.execute("""
    WITH RECURSIVE team(employee_id, name, title, depth) AS (
        SELECT employee_id, name, title, 0 FROM employees WHERE name = 'Ada Lovelace'
        UNION ALL
        SELECT e.employee_id, e.name, e.title, t.depth + 1
        FROM employees AS e JOIN team AS t ON e.manager_id = t.employee_id
    )
    SELECT name, title, depth FROM team ORDER BY depth, name
"""))

print("# R2 A6")
show(shop.execute("""
    SELECT c.name AS category,
           format('%.2f', COALESCE(SUM(i.quantity * i.unit_price_cents) FILTER (WHERE o.order_date <  '2025-01-01'), 0) / 100.0) AS y2024,
           format('%.2f', COALESCE(SUM(i.quantity * i.unit_price_cents) FILTER (WHERE o.order_date >= '2025-01-01'), 0) / 100.0) AS y2025
    FROM categories AS c
    LEFT JOIN products    AS p ON p.category_id = c.category_id
    LEFT JOIN order_items AS i ON i.product_id = p.product_id
    LEFT JOIN orders      AS o ON o.order_id = i.order_id AND o.status <> 'cancelled'
    GROUP BY c.category_id
    ORDER BY c.name
"""))

print("# R2 A7")
show(lib.execute("""
    SELECT m.name, COUNT(l.id) AS loans, COUNT(l.id) FILTER (WHERE l.returned_on IS NULL) AS still_out
    FROM members AS m
    LEFT JOIN loans AS l ON l.member_id = m.id
    GROUP BY m.id
    ORDER BY loans DESC, m.name
"""))

print("# R2 A8")
show(shop.execute("""
    SELECT c.first_name || ' ' || c.last_name AS customer
    FROM customers AS c
    WHERE c.customer_id IN (
        SELECT customer_id FROM orders WHERE order_date < '2025-01-01'
        EXCEPT
        SELECT customer_id FROM orders WHERE order_date >= '2025-01-01')
    ORDER BY customer
"""))

print("# R2 A9")
show(shop.execute("""
    SELECT c.first_name || ' ' || c.last_name AS customer,
           MAX(o.order_date) AS last_order,
           CAST(julianday(?) - julianday(MAX(o.order_date)) AS INTEGER) AS days_silent
    FROM customers AS c JOIN orders AS o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id
    ORDER BY days_silent DESC, customer
    LIMIT 5
""", (TODAY,)))

# ------------------------------------------------------------------ Part B: predict
t = sqlite3.connect(":memory:")
t.execute("CREATE TABLE a (x INTEGER)")
t.execute("CREATE TABLE b (y INTEGER)")
t.executemany("INSERT INTO a VALUES (?)", [(1,), (2,), (2,), (None,)])
t.executemany("INSERT INTO b VALUES (?)", [(2,), (3,), (None,)])
print("# R2 B1")
print(t.execute("SELECT COUNT(*) FROM a JOIN b ON a.x = b.y").fetchone())
print("# R2 B2")
print(t.execute("SELECT COUNT(*), COUNT(b.y) FROM a LEFT JOIN b ON a.x = b.y").fetchone())
print("# R2 B3")
print(t.execute("SELECT x FROM a WHERE x NOT IN (SELECT y FROM b)").fetchall())
print("# R2 B4")
print(t.execute("SELECT COUNT(*) FROM (SELECT x FROM a UNION SELECT y FROM b)").fetchone(),
      t.execute("SELECT COUNT(*) FROM (SELECT x FROM a UNION ALL SELECT y FROM b)").fetchone())
print("# R2 B5")
print(t.execute("SELECT date('2025-01-31', '+1 month'), date('2025-03-14', 'start of month', '-1 day'), strftime('%w', '2025-03-14')").fetchone())
print("# R2 B6")
print(t.execute("SELECT x, (SELECT COUNT(*) FROM b WHERE b.y >= a.x) FROM a ORDER BY x").fetchall())

# ------------------------------------------------------------------ Part C: find the bug
print("# R2 C1")
print(shop.execute("""
    SELECT COUNT(*) FROM (
        SELECT c.customer_id, COUNT(o.order_id) AS delivered_2025
        FROM customers AS c LEFT JOIN orders AS o ON o.customer_id = c.customer_id
        WHERE o.status = 'delivered' AND o.order_date >= '2025-01-01'
        GROUP BY c.customer_id)
""").fetchone())
print(shop.execute("""
    SELECT COUNT(*) FROM (
        SELECT c.customer_id, COUNT(o.order_id) AS delivered_2025
        FROM customers AS c
        LEFT JOIN orders AS o ON o.customer_id = c.customer_id AND o.status = 'delivered' AND o.order_date >= '2025-01-01'
        GROUP BY c.customer_id)
""").fetchone())

print("# R2 C2")
print(shop.execute("""
    SELECT SUM(i.quantity * i.unit_price_cents) / COUNT(*) FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
""").fetchone(), shop.execute("""
    SELECT SUM(i.quantity * i.unit_price_cents) / COUNT(DISTINCT o.order_id) FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
""").fetchone())
print(shop.execute("SELECT COUNT(*) FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id").fetchone(), shop.execute("SELECT COUNT(*) FROM orders").fetchone())

print("# R2 C3")
print(shop.execute("""
    SELECT COUNT(*) FROM categories WHERE category_id NOT IN (SELECT category_id FROM products)""").fetchone())
print(shop.execute("""
    SELECT COUNT(*) FROM categories c WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.category_id = c.category_id)""").fetchone())

print("# R2 C4")
t.execute("CREATE TABLE events (at TEXT)")
t.executemany("INSERT INTO events VALUES (?)", [("2025-03-13 23:59:59",), ("2025-03-14 00:00:00",), ("2025-03-14 18:45:00",), ("2025-03-15 08:00:00",)])
print(t.execute("SELECT COUNT(*) FROM events WHERE at BETWEEN '2025-03-14' AND '2025-03-14'").fetchone())
print(t.execute("SELECT COUNT(*) FROM events WHERE at >= '2025-03-14' AND at < '2025-03-15'").fetchone())
print(t.execute("SELECT COUNT(*) FROM events WHERE date(at) = '2025-03-14'").fetchone())

# ------------------------------------------------------------------ Part D: explain
print("# R2 D (sample answers)")
# 1. In a LEFT JOIN, a condition in ON decides which right-hand rows match (left rows are kept either way);
#    a condition in WHERE filters the finished result, so it also removes the NULL filler rows.
# 2. A correlated subquery uses a column of the outer row, so it is evaluated once per outer row; an uncorrelated one runs once.
# 3. CTE: one statement, not stored, readable. Temp table: whole connection, stored, can be indexed and reused.
# 4. UNION removes duplicates (extra work); UNION ALL keeps all rows. Default to UNION ALL.
# 5. ISO-8601 puts the biggest unit first, so text order equals time order.
# 6. A recursive CTE has an anchor SELECT and a recursive SELECT joined by UNION ALL, and must have a stop condition.

# ------------------------------------------------------------------ Part E: mini-project
print("# R2 E1")
mini = """
    WITH order_totals AS (
        SELECT o.order_id, o.customer_id, o.order_date, SUM(i.quantity * i.unit_price_cents) AS cents
        FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.order_id
    ),
    per_customer AS (
        SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer, c.country, c.signup_date,
               MIN(t.order_date) AS first_order, MAX(t.order_date) AS last_order,
               COUNT(t.order_id) AS orders, COALESCE(SUM(t.cents), 0) AS spend_cents
        FROM customers AS c
        LEFT JOIN order_totals AS t ON t.customer_id = c.customer_id
        GROUP BY c.customer_id
    ),
    labelled AS (
        SELECT *,
               CASE WHEN orders = 0 THEN 'never ordered'
                    WHEN julianday(:today) - julianday(last_order) <= 90 THEN 'active'
                    ELSE 'dormant' END AS status
        FROM per_customer
    )
"""
show(shop.execute(mini + """
    SELECT status, COUNT(*) AS customers,
           format('%.2f', COALESCE(SUM(spend_cents), 0) / 100.0) AS total_spend,
           COALESCE(CAST(ROUND(AVG(julianday(first_order) - julianday(signup_date))) AS INTEGER), '-') AS avg_days_to_first_order
    FROM labelled
    GROUP BY status
    ORDER BY customers DESC
""", {"today": TODAY}))
show(shop.execute(mini + """
    SELECT customer, country, orders, format('%.2f', spend_cents / 100.0) AS spend, last_order
    FROM labelled WHERE status = 'dormant'
    ORDER BY spend_cents DESC, customer LIMIT 3
""", {"today": TODAY}))
