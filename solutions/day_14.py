# Day 14 reference solutions: CTEs and temporary tables
import sqlite3

from helpers import WORK, library_full_conn, shop_conn, show

shop = shop_conn()
lib = library_full_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
show(shop.execute("""
    WITH spend AS (
        SELECT o.customer_id, SUM(i.quantity * i.unit_price_cents) AS spend_cents
        FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.customer_id
    )
    SELECT c.first_name || ' ' || c.last_name AS customer, format('%.2f', s.spend_cents / 100.0) AS spend
    FROM spend AS s
    JOIN customers AS c ON c.customer_id = s.customer_id
    WHERE s.spend_cents > (SELECT AVG(spend_cents) FROM spend)
    ORDER BY s.spend_cents DESC, customer
    LIMIT 3
"""))

print("# Level 1, Q2")
print(shop.execute("""
    WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < 10)
    SELECT group_concat(x, ' ') FROM n
""").fetchone()[0])

print("# Level 1, Q3")
show(shop.execute("""
    WITH RECURSIVE d(day) AS (
        SELECT '2025-01-01'
        UNION ALL
        SELECT date(day, '+1 day') FROM d WHERE day < '2025-01-31'
    )
    SELECT COUNT(*) AS days, MIN(day) AS first_day, MAX(day) AS last_day FROM d
"""))

print("# Level 1, Q4")
path = WORK / "day14_library.db"
path.unlink(missing_ok=True)
a = sqlite3.connect(path)
lib.backup(a)  # fill the file with the normalized library
a.execute("""
    CREATE TEMP TABLE unread_books AS
    SELECT b.id, b.title FROM books AS b
    WHERE NOT EXISTS (SELECT 1 FROM loans AS l WHERE l.book_id = b.id)
""")
print(a.execute("SELECT COUNT(*) FROM unread_books").fetchone())
b = sqlite3.connect(path)
try:
    b.execute("SELECT COUNT(*) FROM unread_books")
except sqlite3.OperationalError as e:
    print("second connection:", e)
a.close()
a = sqlite3.connect(path)
try:
    a.execute("SELECT COUNT(*) FROM unread_books")
except sqlite3.OperationalError as e:
    print("after reopening:", e)
a.close(); b.close()

print("# Level 1, Q5")
# CTE: lives for ONE statement, nothing is stored. Temp table: lives until the connection closes, stored (in a temp file or memory),
# can be indexed and updated, and can be used by many statements.

print("# Level 1, Q6")
show(shop.execute("""
    WITH per_category AS (
        SELECT category_id, COUNT(*) AS products, ROUND(AVG(price_cents)) AS avg_cents
        FROM products WHERE category_id IS NOT NULL GROUP BY category_id
    ),
    big AS (SELECT category_id FROM per_category WHERE products >= 6)
    SELECT c.name, pc.products, CAST(pc.avg_cents AS INTEGER) AS avg_cents
    FROM big JOIN per_category AS pc USING (category_id) JOIN categories AS c USING (category_id)
    ORDER BY c.name
"""))

print("# Level 1, Q7")
shop.execute("CREATE TEMP TABLE top_products AS SELECT product_id, name FROM products WHERE price_cents > 5000")
show(shop.execute("SELECT type, name FROM temp.sqlite_master ORDER BY name"))
show(shop.execute("SELECT type, name FROM main.sqlite_master WHERE name LIKE 'top%'"))

print("# Level 1, Q8")
shop.execute("CREATE TEMP TABLE products AS SELECT 1 AS product_id, 'shadow' AS name")
print(shop.execute("SELECT COUNT(*) FROM products").fetchone(), shop.execute("SELECT COUNT(*) FROM main.products").fetchone())
shop.execute("DROP TABLE temp.products")
print(shop.execute("SELECT COUNT(*) FROM products").fetchone())

print("# Level 1, Q9")
shop.execute("""
    CREATE TEMP TABLE lines_2025 AS
    SELECT o.order_id, o.order_date, i.product_id, i.quantity * i.unit_price_cents AS cents
    FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.order_date >= '2025-01-01' AND o.status <> 'cancelled'
""")
shop.execute("CREATE INDEX temp.idx_lines_product ON lines_2025 (product_id)")
show(shop.execute("SELECT name, tbl_name FROM temp.sqlite_master WHERE type = 'index'"))
print(shop.execute("SELECT COUNT(*) FROM lines_2025").fetchone())
for row in shop.execute("EXPLAIN QUERY PLAN SELECT SUM(cents) FROM lines_2025 WHERE product_id = 5"):
    print(row[3])

print("# Level 1, Q10")
show(shop.execute("""
    WITH totals AS (
        SELECT order_id, SUM(quantity * unit_price_cents) AS total_cents FROM order_items GROUP BY order_id
    )
    SELECT order_id, format('%.2f', total_cents / 100.0) AS total
    FROM totals ORDER BY total_cents DESC, order_id LIMIT 3
"""))

print("# Level 1, Q11")
print(shop.execute("""
    WITH RECURSIVE sq(n, square) AS (SELECT 1, 1 UNION ALL SELECT n + 1, (n + 1) * (n + 1) FROM sq WHERE n < 10)
    SELECT group_concat(square, ', ') FROM sq
""").fetchone()[0])

print("# Level 1, Q12")
print(shop.execute("""
    WITH RECURSIVE countdown(n) AS (SELECT 5 UNION ALL SELECT n - 1 FROM countdown WHERE n > 0)
    SELECT group_concat(n, ' ') FROM countdown
""").fetchone()[0])

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
show(shop.execute("""
    WITH RECURSIVE org(employee_id, name, title, level, chain) AS (
        SELECT employee_id, name, title, 1, title
        FROM employees WHERE manager_id IS NULL
        UNION ALL
        SELECT e.employee_id, e.name, e.title, o.level + 1, o.chain || ' > ' || e.title
        FROM employees AS e JOIN org AS o ON e.manager_id = o.employee_id
    )
    SELECT printf('%*s%s', (level - 1) * 2, '', name) AS employee, level, chain
    FROM org
    ORDER BY chain, employee_id
"""))

print("# Level 2, Q2")
show(shop.execute("""
    WITH order_totals AS (
        SELECT o.order_id, o.customer_id, SUM(i.quantity * i.unit_price_cents) AS total_cents
        FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.order_id
    ),
    customer_spend AS (
        SELECT customer_id, COUNT(*) AS orders, SUM(total_cents) AS spend_cents
        FROM order_totals GROUP BY customer_id
    ),
    tiers AS (
        SELECT customer_id, orders, spend_cents,
               CASE WHEN spend_cents >= 100000 THEN 'gold'
                    WHEN spend_cents >= 40000  THEN 'silver'
                    ELSE 'bronze' END AS tier
        FROM customer_spend
    )
    SELECT tier, COUNT(*) AS customers, format('%.2f', AVG(spend_cents) / 100.0) AS avg_spend
    FROM tiers GROUP BY tier ORDER BY MIN(spend_cents) DESC
"""))

print("# Level 2, Q3")
shop.execute("""
    CREATE TEMP TABLE customer_spend AS
    SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer, c.country,
           COUNT(DISTINCT o.order_id) AS orders,
           SUM(i.quantity * i.unit_price_cents) AS spend_cents
    FROM customers AS c
    JOIN orders      AS o ON o.customer_id = c.customer_id
    JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status <> 'cancelled'
    GROUP BY c.customer_id
""")
print(shop.execute("SELECT COUNT(*) FROM customer_spend").fetchone())
print("-- top 3")
show(shop.execute("SELECT customer, format('%.2f', spend_cents / 100.0) AS spend FROM customer_spend ORDER BY spend_cents DESC, customer LIMIT 3"))
print("-- per country")
show(shop.execute("""
    SELECT country, COUNT(*) AS customers, format('%.2f', AVG(spend_cents) / 100.0) AS avg_spend
    FROM customer_spend GROUP BY country ORDER BY AVG(spend_cents) DESC, country"""))
print("-- orders vs spend")
show(shop.execute("""
    SELECT customer, orders, format('%.2f', spend_cents * 1.0 / orders / 100) AS per_order
    FROM customer_spend WHERE orders >= 8 ORDER BY spend_cents * 1.0 / orders DESC, customer LIMIT 3"""))

print("# Level 2, Q4")
print(shop.execute("""
    WITH RECURSIVE pow(n, value) AS (SELECT 0, 1 UNION ALL SELECT n + 1, value * 2 FROM pow WHERE value * 2 <= 1000)
    SELECT group_concat(value, ' ') FROM pow
""").fetchone()[0])

print("# Level 2, Q5")
show(shop.execute("""
    WITH RECURSIVE team(employee_id, name, depth) AS (
        SELECT employee_id, name, 0 FROM employees WHERE name = 'Alan Turing'
        UNION ALL
        SELECT e.employee_id, e.name, t.depth + 1
        FROM employees AS e JOIN team AS t ON e.manager_id = t.employee_id
    )
    SELECT name, depth FROM team ORDER BY depth, name
"""))

print("# Level 2, Q6")
show(shop.execute("""
    WITH RECURSIVE team(top_id, employee_id) AS (
        SELECT employee_id, employee_id FROM employees
        UNION ALL
        SELECT t.top_id, e.employee_id
        FROM employees AS e JOIN team AS t ON e.manager_id = t.employee_id
    )
    SELECT m.name AS manager, COUNT(*) - 1 AS people_below,
           format('%.2f', SUM(e.salary_cents) / 100.0) AS team_payroll
    FROM team AS t
    JOIN employees AS m ON m.employee_id = t.top_id
    JOIN employees AS e ON e.employee_id = t.employee_id
    GROUP BY m.employee_id
    HAVING COUNT(*) > 1
    ORDER BY people_below DESC, manager
"""))

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
daily = """
    WITH RECURSIVE d(day) AS (
        SELECT '2025-01-01'
        UNION ALL
        SELECT date(day, '+1 day') FROM d WHERE day < '2025-12-31'
    ),
    sales AS (
        SELECT o.order_date AS day, SUM(i.quantity * i.unit_price_cents) AS cents
        FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.order_date
    )
    SELECT d.day, COALESCE(s.cents, 0) AS cents
    FROM d LEFT JOIN sales AS s ON s.day = d.day
    ORDER BY d.day
"""
show(shop.execute(f"SELECT day, format('%.2f', cents / 100.0) AS revenue FROM ({daily}) LIMIT 6"))
print(shop.execute(f"SELECT COUNT(*), SUM(cents = 0), format('%.2f', SUM(cents) / 100.0) FROM ({daily})").fetchone())
print(shop.execute("""
    SELECT format('%.2f', SUM(i.quantity * i.unit_price_cents) / 100.0)
    FROM orders o JOIN order_items i ON i.order_id = o.order_id WHERE o.order_date >= '2025-01-01' AND o.status <> 'cancelled'
""").fetchone())

print("# Level 3, Q2")
print(shop.execute("""
    WITH RECURSIVE fib(a, b) AS (SELECT 0, 1 UNION ALL SELECT b, a + b FROM fib WHERE b <= 1000)
    SELECT group_concat(a, ', ') FROM fib WHERE a <= 1000
""").fetchone()[0])

print("# Level 3, Q3")
shop.execute("DROP TABLE IF EXISTS temp.lines_2025")
shop.execute("""
    CREATE TEMP TABLE lines_2025 AS
    SELECT c.name AS category, substr(o.order_date, 1, 7) AS month, i.quantity * i.unit_price_cents AS cents
    FROM order_items AS i
    JOIN orders     AS o ON o.order_id = i.order_id
    JOIN products   AS p ON p.product_id = i.product_id
    JOIN categories AS c ON c.category_id = p.category_id
    WHERE o.order_date >= '2025-01-01' AND o.status <> 'cancelled'
""")
shop.execute("CREATE INDEX temp.idx_lines_cat_month ON lines_2025 (category, month)")
print(shop.execute("SELECT COUNT(*) FROM lines_2025").fetchone())
shop.execute("""
    CREATE TEMP TABLE monthly AS
    SELECT category, month, SUM(cents) AS cents FROM lines_2025 GROUP BY category, month
""")
print("-- best month per category")
show(shop.execute("""
    SELECT m.category, m.month, format('%.2f', m.cents / 100.0) AS revenue
    FROM monthly AS m
    WHERE m.cents = (SELECT MAX(cents) FROM monthly AS x WHERE x.category = m.category)
    ORDER BY m.category
"""))
print("-- best category per month")
show(shop.execute("""
    SELECT m.month, m.category, format('%.2f', m.cents / 100.0) AS revenue
    FROM monthly AS m
    WHERE m.cents = (SELECT MAX(cents) FROM monthly AS x WHERE x.month = m.month)
    ORDER BY m.month
"""))
