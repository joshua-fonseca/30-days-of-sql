# Day 30 reference solutions: the pattern bank, the sqlglot demo and the final review
import duckdb
import sqlglot

from helpers import DATA, TODAY, WORK, library_full_conn, shop_conn, show
from library_repo import LibraryRepository

conn = shop_conn()
LIVE = "o.status != 'cancelled'"

# ======================================================================== sqlglot
print("# sqlglot")
SQL = "SELECT name, price_cents FROM products WHERE price_cents > 5000 ORDER BY price_cents DESC LIMIT 5"
for dialect in ("tsql", "postgres", "mysql", "duckdb", "oracle"):
    print(f"{dialect:9}", sqlglot.transpile(SQL, read="sqlite", write=dialect)[0])
for sql in ("SELECT iif(stock > 0, 'in stock', 'sold out') FROM products",
            "SELECT group_concat(name, ', ') FROM categories",
            "SELECT date('now', '+7 days')",
            "SELECT strftime('%Y-%m', order_date) FROM orders"):
    print("tsql    ", sqlglot.transpile(sql, read="sqlite", write="tsql")[0])
    print("postgres", sqlglot.transpile(sql, read="sqlite", write="postgres")[0])

# ======================================================================== pattern bank
print("# Pattern bank")


def pattern(n, title, sql, params=()):
    print(f"## P{n} {title}")
    show(conn.execute(sql, params))


pattern(1, "Second-highest value (second most expensive price)", """
    SELECT max(price_cents) AS second_highest_price FROM products
    WHERE price_cents < (SELECT max(price_cents) FROM products)""")

pattern(2, "Nth highest with DENSE_RANK (third highest salary)", """
    SELECT name, salary_cents FROM (
        SELECT name, salary_cents, DENSE_RANK() OVER (ORDER BY salary_cents DESC) AS r FROM employees)
    WHERE r = 3 ORDER BY name""")

pattern(3, "Top-N per group (2 priciest products per category)", """
    SELECT category, product, price_cents FROM (
        SELECT c.name AS category, p.name AS product, p.price_cents,
               ROW_NUMBER() OVER (PARTITION BY c.category_id ORDER BY p.price_cents DESC, p.name) AS rn
        FROM products p JOIN categories c ON c.category_id = p.category_id)
    WHERE rn <= 2 ORDER BY category, rn""")

pattern(4, "Find duplicates (case-insensitive emails)", """
    SELECT lower(trim(email)) AS email, count(*) AS copies FROM newsletter_signups
    GROUP BY lower(trim(email)) HAVING count(*) > 1 ORDER BY copies DESC, email LIMIT 5""")

print("## P5 Remove duplicates (keep the earliest signup)")
copy = shop_conn()
before = copy.execute("SELECT count(*) FROM newsletter_signups").fetchone()[0]
with copy:
    copy.execute("""
        DELETE FROM newsletter_signups WHERE rowid IN (
            SELECT rowid FROM (
                SELECT rowid, ROW_NUMBER() OVER (PARTITION BY lower(trim(email)) ORDER BY signed_up_at, rowid) AS rn
                FROM newsletter_signups) WHERE rn > 1)""")
after = copy.execute("SELECT count(*) FROM newsletter_signups").fetchone()[0]
print(before, after)

pattern(6, "Running total (cumulative revenue, first months of 2025)", """
    WITH monthly AS (
        SELECT strftime('%Y-%m', o.order_date) AS month, sum(i.quantity * i.unit_price_cents) AS cents
        FROM orders o JOIN order_items i ON i.order_id = o.order_id
        WHERE o.status != 'cancelled' AND o.order_date >= '2025-01-01' GROUP BY month)
    SELECT month, cents, sum(cents) OVER (ORDER BY month) AS running_cents FROM monthly ORDER BY month LIMIT 4""")

pattern(7, "Month-over-month change (%)", """
    WITH monthly AS (
        SELECT strftime('%Y-%m', o.order_date) AS month, sum(i.quantity * i.unit_price_cents) AS cents
        FROM orders o JOIN order_items i ON i.order_id = o.order_id
        WHERE o.status != 'cancelled' AND o.order_date >= '2025-01-01' GROUP BY month)
    SELECT month, cents, round(100.0 * (cents - LAG(cents) OVER (ORDER BY month)) / LAG(cents) OVER (ORDER BY month), 1) AS mom_pct
    FROM monthly ORDER BY month LIMIT 4""")

pattern(8, "Pivot with conditional aggregation (status by year)", """
    SELECT substr(order_date, 1, 4) AS year,
           count(*) FILTER (WHERE status = 'delivered') AS delivered,
           count(*) FILTER (WHERE status = 'shipped') AS shipped,
           count(*) FILTER (WHERE status = 'pending') AS pending,
           count(*) FILTER (WHERE status = 'cancelled') AS cancelled
    FROM orders GROUP BY year ORDER BY year""")

pattern(9, "Median (order totals, odd or even count)", """
    WITH totals AS (
        SELECT order_id, sum(quantity * unit_price_cents) AS cents FROM order_items GROUP BY order_id),
    ranked AS (
        SELECT cents, ROW_NUMBER() OVER (ORDER BY cents, order_id) AS rn, count(*) OVER () AS n FROM totals)
    SELECT avg(cents) AS median_cents FROM ranked WHERE rn IN ((n + 1) / 2, (n + 2) / 2)""")

pattern(10, "Gaps and islands (longest run of consecutive order days)", """
    WITH days AS (SELECT DISTINCT customer_id, order_date FROM orders),
    marked AS (
        SELECT customer_id, order_date,
               julianday(order_date) - ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS grp
        FROM days)
    SELECT customer_id, min(order_date) AS first_day, count(*) AS streak_days FROM marked
    GROUP BY customer_id, grp ORDER BY streak_days DESC, customer_id, first_day LIMIT 3""")

pattern(11, "Cohort retention (first-order month vs ordering again the next month)", """
    WITH firsts AS (
        SELECT customer_id, strftime('%Y-%m', min(order_date)) AS cohort FROM orders GROUP BY customer_id),
    next_month AS (
        SELECT f.customer_id, f.cohort,
               EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = f.customer_id
                       AND strftime('%Y-%m', o.order_date) = strftime('%Y-%m', date(f.cohort || '-01', '+1 month'))) AS came_back
        FROM firsts f)
    SELECT cohort, count(*) AS customers, sum(came_back) AS returned_next_month FROM next_month
    GROUP BY cohort ORDER BY cohort LIMIT 5""")

pattern(12, "Sessionization by inactivity gap (a new 'streak of activity' after 60 quiet days)", """
    WITH flagged AS (
        SELECT customer_id, order_date,
               CASE WHEN julianday(order_date) - julianday(LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id)) > 60
                    THEN 1 ELSE 0 END AS new_session
        FROM orders),
    numbered AS (
        SELECT customer_id, order_date, sum(new_session) OVER (PARTITION BY customer_id ORDER BY order_date) AS session_no FROM flagged)
    SELECT customer_id, count(DISTINCT session_no) AS sessions FROM numbered
    GROUP BY customer_id ORDER BY sessions DESC, customer_id LIMIT 3""")

pattern(13, "Bought X but never Y (bought Books, never bought Toys)", """
    SELECT count(DISTINCT o.customer_id) AS customers FROM orders o
    JOIN order_items i ON i.order_id = o.order_id JOIN products p ON p.product_id = i.product_id
    JOIN categories c ON c.category_id = p.category_id
    WHERE c.name = 'Books' AND o.customer_id NOT IN (
        SELECT o2.customer_id FROM orders o2 JOIN order_items i2 ON i2.order_id = o2.order_id
        JOIN products p2 ON p2.product_id = i2.product_id JOIN categories c2 ON c2.category_id = p2.category_id
        WHERE c2.name = 'Toys')""")

pattern(14, "Anti-join (products never ordered)", """
    SELECT p.name FROM products p LEFT JOIN order_items i ON i.product_id = p.product_id
    WHERE i.product_id IS NULL ORDER BY p.name""")

pattern(15, "Ranking with ties (customers by order count, DENSE_RANK, top 3 ranks)", """
    SELECT customer_id, orders, rnk FROM (
        SELECT customer_id, count(*) AS orders, DENSE_RANK() OVER (ORDER BY count(*) DESC) AS rnk
        FROM orders GROUP BY customer_id)
    WHERE rnk <= 3 ORDER BY rnk, customer_id""")

pattern(16, "Relational division (ordered in all four quarters of 2025)", """
    SELECT customer_id FROM orders WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31'
    GROUP BY customer_id
    HAVING count(DISTINCT (CAST(substr(order_date, 6, 2) AS INTEGER) + 2) / 3) = 4
    ORDER BY customer_id LIMIT 5""")

pattern(17, "Recursive CTE (org chart with level)", """
    WITH RECURSIVE chart(employee_id, name, level) AS (
        SELECT employee_id, name, 1 FROM employees WHERE manager_id IS NULL
        UNION ALL
        SELECT e.employee_id, e.name, chart.level + 1 FROM employees e JOIN chart ON e.manager_id = chart.employee_id)
    SELECT level, count(*) AS people FROM chart GROUP BY level ORDER BY level""")

# ======================================================================== final review
print("# Final review")


def one(sql, *params):
    return conn.execute(sql, params).fetchall()


print("Q1", one("SELECT count(*) FROM products WHERE price_cents > 5000"))
print("Q2", one("SELECT count(*) FROM customers WHERE city IS NULL"))
print("Q3", one("SELECT name FROM products ORDER BY price_cents, name LIMIT 3"))
print("Q4", one("SELECT count(*) FROM orders WHERE order_date LIKE '2025-12-%'"))
print("Q5", one("SELECT country, count(*) AS n FROM customers GROUP BY country ORDER BY n DESC, country LIMIT 1"))
print("Q6", one("SELECT 7 / 2, 7 / 2.0, 7 % 2"))
print("Q7", one("SELECT NULL = NULL, NULL IS NULL, 1 + NULL, coalesce(NULL, 5)"))
print("Q8", one("SELECT sum(stock) FROM products"))
print("Q9", one("""SELECT sum(i.quantity * i.unit_price_cents) FROM order_items i
                   JOIN orders o ON o.order_id = i.order_id JOIN products p ON p.product_id = i.product_id
                   JOIN categories c ON c.category_id = p.category_id WHERE c.name = 'Books' AND o.status != 'cancelled'"""))
print("Q10", one("""SELECT count(*) FROM customers c WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id)"""))
print("Q11", one("""SELECT m.name, count(*) AS reports FROM employees e JOIN employees m ON m.employee_id = e.manager_id
                   GROUP BY m.employee_id ORDER BY reports DESC, m.name LIMIT 1"""))
print("Q12", one("""SELECT count(*) FROM products p WHERE price_cents > (SELECT avg(price_cents) FROM products p2 WHERE p2.category_id = p.category_id)"""))
print("Q13", one("""SELECT strftime('%Y-%m', o.order_date) AS month, sum(i.quantity * i.unit_price_cents) AS cents
                   FROM orders o JOIN order_items i ON i.order_id = o.order_id WHERE o.status != 'cancelled'
                   GROUP BY month ORDER BY cents DESC, month LIMIT 1"""))
print("Q14 buggy", one("""SELECT count(*) FROM employees WHERE employee_id NOT IN (SELECT manager_id FROM employees)"""))
print("Q14 fixed", one("""SELECT count(*) FROM employees WHERE employee_id NOT IN (SELECT manager_id FROM employees WHERE manager_id IS NOT NULL)"""))
duck = duckdb.connect()
duck.execute(f"ATTACH '{DATA / 'shop.db'}' AS shop (TYPE sqlite, READ_ONLY)")
print("Q15", duck.execute("SELECT status, count(*) AS orders FROM shop.orders GROUP BY ALL ORDER BY orders DESC, status").fetchall())
print("Q16", one("""WITH d AS (SELECT customer_id, order_date, julianday(order_date) - julianday(LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id)) AS gap FROM orders)
                   SELECT customer_id, CAST(gap AS INTEGER) FROM d ORDER BY gap DESC, customer_id LIMIT 1"""))
repo = LibraryRepository(library_full_conn())
late = repo.overdue(TODAY)
print("Q17", [(x.title, x.days_overdue) for x in late])
print("Q18", duck.execute("""SELECT c.name, p.name, sum(i.quantity) AS units
                              FROM shop.order_items i JOIN shop.products p ON p.product_id = i.product_id
                              JOIN shop.categories c ON c.category_id = p.category_id
                              GROUP BY c.name, p.name QUALIFY row_number() OVER (PARTITION BY c.name ORDER BY units DESC, p.name) = 1
                              ORDER BY c.name LIMIT 3""").fetchall())
print("Q19", sqlglot.transpile("SELECT name FROM products LIMIT 3", read="sqlite", write="tsql")[0])

# ======================================================================== cheat sheet: every line must run
CHEATSHEET = [
    ("Create a table", "CREATE TABLE t_notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL, stars INTEGER DEFAULT 0 CHECK (stars >= 0)) STRICT"),
    ("Change a table", "ALTER TABLE t_notes ADD COLUMN created_on TEXT"),
    ("Insert", "INSERT INTO t_notes (body, stars) VALUES ('first', 3), ('second', 5)"),
    ("Upsert", "INSERT INTO categories (name) VALUES ('Books') ON CONFLICT (name) DO UPDATE SET name = excluded.name"),
    ("Update", "UPDATE t_notes SET stars = stars + 1 WHERE body = 'first'"),
    ("Update from", "UPDATE products SET stock = stock + 1 FROM (SELECT product_id FROM order_items GROUP BY product_id) AS sold WHERE products.product_id = sold.product_id"),
    ("Delete returning", "DELETE FROM t_notes WHERE stars < 5 RETURNING id"),
    ("Select, alias, distinct", "SELECT DISTINCT country AS nation FROM customers"),
    ("Filter and sort", "SELECT name, price_cents FROM products WHERE price_cents BETWEEN 1000 AND 5000 AND name LIKE '%a%' ORDER BY price_cents DESC, name LIMIT 5 OFFSET 2"),
    ("IN, NULL tests", "SELECT first_name FROM customers WHERE country IN ('USA', 'UK') AND city IS NOT NULL"),
    ("CASE, COALESCE", "SELECT name, CASE WHEN price_cents < 1000 THEN 'cheap' ELSE 'normal' END AS band, coalesce(category_id, 0) FROM products"),
    ("Aggregates", "SELECT count(*), count(DISTINCT country), sum(stock), avg(price_cents), min(price_cents), max(price_cents) FROM customers, products LIMIT 1"),
    ("Group and having", "SELECT country, count(*) AS n FROM customers GROUP BY country HAVING count(*) > 5 ORDER BY n DESC, country"),
    ("Conditional aggregate", "SELECT count(*) FILTER (WHERE status = 'delivered') AS delivered, sum(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending FROM orders"),
    ("Inner join", "SELECT o.order_id, c.first_name FROM orders o JOIN customers c ON c.customer_id = o.customer_id"),
    ("Left join (anti-join)", "SELECT c.customer_id FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE o.order_id IS NULL"),
    ("Self join", "SELECT e.name, m.name AS manager FROM employees e LEFT JOIN employees m ON m.employee_id = e.manager_id"),
    ("Cross join", "SELECT c.name, s.n FROM categories c CROSS JOIN (SELECT 1 AS n UNION ALL SELECT 2) s"),
    ("Subquery", "SELECT name FROM products WHERE price_cents > (SELECT avg(price_cents) FROM products)"),
    ("EXISTS", "SELECT first_name FROM customers c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id)"),
    ("CTE", "WITH big AS (SELECT order_id FROM order_items GROUP BY order_id HAVING sum(quantity) > 5) SELECT count(*) FROM big"),
    ("Recursive CTE", "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 10) SELECT sum(i) FROM n"),
    ("Temp table", "CREATE TEMP TABLE spend AS SELECT customer_id, count(*) AS orders FROM orders GROUP BY customer_id"),
    ("Set operations", "SELECT city FROM customers WHERE city IS NOT NULL EXCEPT SELECT 'Paris'"),
    ("Window: ranking", "SELECT name, price_cents, RANK() OVER (ORDER BY price_cents DESC) AS r FROM products"),
    ("Window: running total", "SELECT order_date, sum(count(*)) OVER (ORDER BY order_date) FROM orders GROUP BY order_date"),
    ("Window: previous row", "SELECT order_date, LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) FROM orders"),
    ("Dates", "SELECT date('2025-03-14', '+7 days'), strftime('%Y-%m', '2025-03-14'), julianday('2025-03-14') - julianday('2025-01-01')"),
    ("Strings", "SELECT upper('abc') || '-' || substr('hello', 2, 3), length('abc'), replace('a-b', '-', '+'), instr('hello', 'l'), trim('  x ')"),
    ("JSON", "SELECT json_extract('{\"a\": [1, 2]}', '$.a[1]'), '{\"a\": 5}' ->> '$.a'"),
    ("Index", "CREATE INDEX idx_orders_customer ON orders (customer_id, order_date)"),
    ("Query plan", "EXPLAIN QUERY PLAN SELECT * FROM orders WHERE customer_id = 7"),
    ("View", "CREATE VIEW v_big_orders AS SELECT order_id, sum(quantity * unit_price_cents) AS cents FROM order_items GROUP BY order_id HAVING cents > 50000"),
    ("Trigger", "CREATE TRIGGER trg_note_default AFTER INSERT ON t_notes BEGIN UPDATE t_notes SET created_on = date('now') WHERE id = NEW.id; END"),
    ("Transaction", "BEGIN"),
    ("Pragma", "PRAGMA foreign_keys = ON"),
    ("Drop", "DROP TABLE IF EXISTS t_notes"),
]
print("# Cheat sheet")
cs = shop_conn()
for title, sql in CHEATSHEET:
    if title == "Transaction":
        cs.commit()
    cs.execute(sql).fetchall()
    if title == "Transaction":
        cs.execute("ROLLBACK")
print(len(CHEATSHEET), "statements ran")
