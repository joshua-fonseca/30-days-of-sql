# Review 3 reference solutions (Days 11-18)
# Review 3 reference solutions (Days 11-18)
import sqlite3

from helpers import DATA, TODAY, library_full_conn, show


def shop():
    """In-memory copy of data/shop.db (students use sqlite3.connect('data/shop.db'))."""
    src = sqlite3.connect(DATA / "shop.db")
    dst = sqlite3.connect(":memory:")
    src.backup(dst)
    src.close()
    return dst


conn = shop()
lib = library_full_conn()
t = sqlite3.connect(':memory:')
t.executescript('''
    CREATE TABLE a (x INTEGER);
    CREATE TABLE b (x INTEGER);
    INSERT INTO a VALUES (1), (2), (2), (3), (NULL);
    INSERT INTO b VALUES (2), (3), (3), (4);
''')

print("# A1")
show(conn.execute('''
    SELECT p.product_id, p.name, COALESCE(c.name, 'uncategorised') AS category
    FROM products AS p
    LEFT JOIN categories AS c ON c.category_id = p.category_id
    WHERE p.product_id <= 3 OR c.category_id IS NULL
    ORDER BY p.product_id
'''))

print("# A2")
show(conn.execute('''
    SELECT c.customer_id, c.first_name, c.last_name, c.signup_date
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE o.order_id IS NULL
    ORDER BY c.customer_id
'''))

print("# A3")
show(conn.execute('''
    SELECT e.employee_id, e.name, e.title, m.name AS manager
    FROM employees AS e
    LEFT JOIN employees AS m ON m.employee_id = e.manager_id
    ORDER BY e.employee_id
    LIMIT 5
'''))

print("# A4")
show(conn.execute('''
    SELECT strftime('%Y', order_date) AS year,
           COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
           COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
           COUNT(*) FILTER (WHERE status IN ('pending', 'shipped')) AS open,
           COUNT(*) AS total
    FROM orders
    GROUP BY year
    ORDER BY year
'''))

print("# A5")
show(conn.execute('''
    SELECT p.product_id, p.name
    FROM products AS p
    LEFT JOIN order_items AS oi ON oi.product_id = p.product_id
    WHERE oi.order_id IS NULL
    ORDER BY p.product_id
'''))
print(conn.execute('''
    SELECT COUNT(*) FROM products AS p
    WHERE NOT EXISTS (SELECT 1 FROM order_items AS oi WHERE oi.product_id = p.product_id)
''').fetchone())

print("# A6")
show(conn.execute('''
    SELECT strftime('%w', order_date) AS weekday, COUNT(*) AS orders
    FROM orders
    GROUP BY weekday
    ORDER BY weekday
'''))
# Saturday (6) is the busiest.

print("# A7")
show(conn.execute('''
    SELECT p.name, p.price_cents,
           CAST(round((SELECT AVG(p2.price_cents) FROM products AS p2 WHERE p2.category_id = p.category_id)) AS INTEGER) AS category_avg
    FROM products AS p
    WHERE p.price_cents > (SELECT AVG(p2.price_cents) FROM products AS p2 WHERE p2.category_id = p.category_id)
    ORDER BY p.name
'''))

print("# A8")
show(lib.execute('''
    SELECT m.name AS member, b.title, l.due_on,
           CAST(julianday(?) - julianday(l.due_on) AS INTEGER) AS days_overdue
    FROM loans AS l
    JOIN members AS m ON m.id = l.member_id
    JOIN books AS b ON b.id = l.book_id
    WHERE l.returned_on IS NULL AND l.due_on < ?
    ORDER BY l.due_on, l.id
''', (TODAY, TODAY)))

print("# A9")
show(conn.execute('''
    WITH spend AS (
        SELECT o.customer_id, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.customer_id
    ), tiers AS (
        SELECT customer_id, cents,
               CASE WHEN cents >= 100000 THEN 'gold' WHEN cents >= 30000 THEN 'silver' ELSE 'bronze' END AS tier
        FROM spend
    )
    SELECT tier, COUNT(*) AS customers, SUM(cents) AS total_cents
    FROM tiers
    GROUP BY tier
    ORDER BY customers DESC, tier
'''))

print("# A10")
show(conn.execute('''
    WITH units AS (
        SELECT p.category_id, p.name AS product, SUM(oi.quantity) AS units
        FROM products AS p
        JOIN order_items AS oi ON oi.product_id = p.product_id
        WHERE p.category_id IS NOT NULL
        GROUP BY p.product_id
    ), numbered AS (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY units DESC, product) AS pos
        FROM units
    )
    SELECT c.name AS category, n.product, n.units, n.pos
    FROM numbered AS n
    JOIN categories AS c ON c.category_id = n.category_id
    WHERE n.pos <= 2
    ORDER BY category, n.pos
'''))

print("# A11")
show(conn.execute('''
    WITH RECURSIVE org AS (
        SELECT employee_id, name, 1 AS level, name AS chain
        FROM employees
        WHERE manager_id IS NULL
        UNION ALL
        SELECT e.employee_id, e.name, org.level + 1, org.chain || ' > ' || e.name
        FROM employees AS e
        JOIN org ON e.manager_id = org.employee_id
    )
    SELECT level, chain
    FROM org
    ORDER BY chain
'''))

print("# A12")
show(conn.execute('''
    WITH months(month) AS (
        SELECT '2025-01' UNION ALL SELECT '2025-02' UNION ALL SELECT '2025-03'
    ), sales AS (
        SELECT p.category_id, strftime('%Y-%m', o.order_date) AS month,
               SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        JOIN products AS p ON p.product_id = oi.product_id
        WHERE o.status <> 'cancelled'
        GROUP BY p.category_id, month
    )
    SELECT c.name AS category, m.month, COALESCE(s.cents, 0) AS cents
    FROM categories AS c
    CROSS JOIN months AS m
    LEFT JOIN sales AS s ON s.category_id = c.category_id AND s.month = m.month
    ORDER BY category, m.month
'''))

print("# A13")
show(conn.execute('''
    WITH monthly AS (
        SELECT strftime('%Y-%m', o.order_date) AS month, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY month
    ), calc AS (
        SELECT month, cents,
               round(100.0 * (cents - LAG(cents) OVER w) / LAG(cents) OVER w, 1) AS change_pct,
               CAST(round(AVG(cents) OVER (w ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)) AS INTEGER) AS avg_3m
        FROM monthly
        WINDOW w AS (ORDER BY month)
    )
    SELECT month, cents, change_pct, avg_3m
    FROM calc
    WHERE month BETWEEN '2025-01' AND '2025-06'
    ORDER BY month
'''))

print("# A14")
rows = conn.execute('''
    SELECT o.customer_id
    FROM orders AS o JOIN order_items AS oi ON oi.order_id = o.order_id
         JOIN products AS p ON p.product_id = oi.product_id JOIN categories AS c ON c.category_id = p.category_id
    WHERE c.name = 'Books'
    INTERSECT
    SELECT o.customer_id
    FROM orders AS o JOIN order_items AS oi ON oi.order_id = o.order_id
         JOIN products AS p ON p.product_id = oi.product_id JOIN categories AS c ON c.category_id = p.category_id
    WHERE c.name = 'Toys'
    ORDER BY customer_id
''').fetchall()
print(len(rows), [r[0] for r in rows][:8])
print(conn.execute('''
    SELECT COUNT(*) FROM (
        SELECT o.customer_id
        FROM orders AS o JOIN order_items AS oi ON oi.order_id = o.order_id
             JOIN products AS p ON p.product_id = oi.product_id JOIN categories AS c ON c.category_id = p.category_id
        WHERE c.name IN ('Books', 'Toys')
        GROUP BY o.customer_id
        HAVING COUNT(DISTINCT c.name) = 2
    )
''').fetchone())

print("# A15")
show(conn.execute('''
    WITH days AS (
        SELECT DISTINCT customer_id, order_date FROM orders
    ), keyed AS (
        SELECT customer_id, order_date,
               date(order_date, '-' || ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) || ' days') AS grp
        FROM days
    )
    SELECT customer_id, MIN(order_date) AS streak_start, MAX(order_date) AS streak_end, COUNT(*) AS days
    FROM keyed
    GROUP BY customer_id, grp
    HAVING COUNT(*) >= 3
    ORDER BY days DESC, customer_id
'''))

print("# B1")
print("# 1")
show(t.execute('SELECT a.x, b.x FROM a LEFT JOIN b ON a.x = b.x ORDER BY a.x, b.x'))
print("# 2")
print(t.execute('SELECT x FROM b WHERE x NOT IN (SELECT x FROM a)').fetchall(), "   # NULL in the subquery: NOT IN is never true")
print("# 3")
print([t.execute(f'SELECT COUNT(*) FROM (SELECT x FROM a {op} SELECT x FROM b)').fetchone()[0] for op in ('UNION', 'UNION ALL', 'INTERSECT', 'EXCEPT')])
print("# 4")
show(t.execute('SELECT x, SUM(x) OVER (ORDER BY x) AS s, RANK() OVER (ORDER BY x) AS r, LAG(x) OVER (ORDER BY x) AS prev FROM b ORDER BY x'))
print("# 5")
print(t.execute("SELECT date('2025-01-31', '+1 month'), date('2025-03-14', 'start of month', '+1 month', '-1 day'), strftime('%w', '2025-03-14')").fetchone())

print("# C1fix")
print(conn.execute('''
    SELECT COUNT(*)
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id AND o.order_date >= '2025-01-01'
    WHERE o.order_id IS NULL
''').fetchone())

print("# C2fix")
show(conn.execute('''
    SELECT name FROM categories AS c
    WHERE NOT EXISTS (SELECT 1 FROM products AS p WHERE p.category_id = c.category_id)
'''))

print("# C3fix")
print(conn.execute('''
    SELECT COUNT(DISTINCT o.order_id)
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    WHERE o.customer_id = 3
''').fetchone())

print("# C4fix")
show(conn.execute('''
    WITH x AS (
        SELECT order_id, order_date,
               COUNT(*) OVER (ORDER BY order_date, order_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_orders
        FROM orders
    )
    SELECT * FROM x WHERE order_date BETWEEN '2024-04-18' AND '2024-04-20' ORDER BY order_id
'''))

print("# C5fix")
print(conn.execute("SELECT COUNT(*) FROM orders WHERE strftime('%m', order_date) = '03'").fetchone())

print("# C6fix")
print(conn.execute('''
    SELECT COUNT(*) FROM (
        SELECT order_id FROM orders WHERE order_date < '2025-01-01'
        UNION ALL
        SELECT order_id FROM orders WHERE order_date >= '2025-01-01'
    )
''').fetchone())

print("# E1")
conn.execute('''
    CREATE TEMP TABLE customer_report AS
    WITH totals AS (
        SELECT c.customer_id, c.country,
               COUNT(DISTINCT o.order_id) AS orders,
               SUM(oi.quantity * oi.unit_price_cents) AS spend_cents,
               MIN(o.order_date) AS first_order,
               MAX(o.order_date) AS last_order
        FROM customers AS c
        JOIN orders AS o ON o.customer_id = c.customer_id
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY c.customer_id
    ), scored AS (
        SELECT *,
               CAST(julianday('2025-12-31') - julianday(last_order) AS INTEGER) AS days_idle,
               RANK() OVER (PARTITION BY country ORDER BY spend_cents DESC) AS country_rank,
               CASE WHEN spend_cents >= 100000 THEN 'gold' WHEN spend_cents >= 30000 THEN 'silver' ELSE 'bronze' END AS tier
        FROM totals
    ), days AS (
        SELECT DISTINCT customer_id, order_date FROM orders
    ), keyed AS (
        SELECT customer_id, order_date,
               date(order_date, '-' || ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) || ' days') AS grp
        FROM days
    ), streaks AS (
        SELECT customer_id, COUNT(*) AS days FROM keyed GROUP BY customer_id, grp
    ), best AS (
        SELECT customer_id, MAX(days) AS best_streak FROM streaks GROUP BY customer_id
    )
    SELECT s.customer_id, s.country, s.orders, s.spend_cents, s.first_order, s.last_order,
           s.days_idle, s.country_rank, s.tier, b.best_streak
    FROM scored AS s
    JOIN best AS b ON b.customer_id = s.customer_id
''')
show(conn.execute('SELECT * FROM customer_report ORDER BY spend_cents DESC, customer_id LIMIT 6'))
print(conn.execute('SELECT COUNT(*) FROM customer_report').fetchone()[0], 'rows')

print("# E2")
print("# (a) top customer of each country")
show(conn.execute('SELECT country, customer_id, spend_cents FROM customer_report WHERE country_rank = 1 ORDER BY country, customer_id'))
print("# (b) tiers")
show(conn.execute('SELECT tier, COUNT(*) AS customers, SUM(spend_cents) AS spend_cents FROM customer_report GROUP BY tier ORDER BY spend_cents DESC'))
print("# (c) gold or silver with a streak of 3+ days")
show(conn.execute("SELECT customer_id, tier, best_streak FROM customer_report WHERE tier IN ('gold', 'silver') AND best_streak >= 3 ORDER BY best_streak DESC, customer_id"))
