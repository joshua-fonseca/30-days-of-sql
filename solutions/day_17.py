# Day 17 reference solutions
# Day 17 reference solutions
import sqlite3

from helpers import DATA, datasets_conn, library_full_conn, show


def shop():
    """In-memory copy of data/shop.db (students use sqlite3.connect('data/shop.db'))."""
    src = sqlite3.connect(DATA / "shop.db")
    dst = sqlite3.connect(":memory:")
    src.backup(dst)
    src.close()
    return dst


conn = shop()
lib = library_full_conn()

print("# L1Q1")
show(conn.execute('''
    SELECT product_id, name, price_cents,
           ROW_NUMBER() OVER (ORDER BY price_cents DESC, product_id) AS rn
    FROM products
    ORDER BY rn
'''))

print("# L1Q2")
show(conn.execute('''
    SELECT product_id, name, price_cents,
           ROW_NUMBER() OVER (ORDER BY price_cents DESC, product_id) AS rn,
           RANK()       OVER (ORDER BY price_cents DESC)             AS price_rank,
           DENSE_RANK() OVER (ORDER BY price_cents DESC)             AS price_dense
    FROM products
    ORDER BY rn
'''))

print("# L1Q3")
# They differ only after a tie. RANK leaves a gap (1, 2, 2, 4), DENSE_RANK doesn't (1, 2, 2, 3).
# For a podium with ties you usually want RANK <= 3 (two silvers means nobody gets bronze), but if the
# question is "the top 3 distinct prices" you want DENSE_RANK <= 3.

print("# L1Q4")
show(conn.execute('''
    SELECT product_id, name, price_cents,
           CAST(round(AVG(price_cents) OVER ()) AS INTEGER) AS avg_price,
           CAST(round(price_cents - AVG(price_cents) OVER ()) AS INTEGER) AS diff
    FROM products
    ORDER BY product_id
'''))

print("# L1Q5")
show(conn.execute('''
    SELECT category_id, product_id, name, price_cents,
           CAST(round(AVG(price_cents) OVER (PARTITION BY category_id)) AS INTEGER) AS category_avg
    FROM products
    ORDER BY category_id, product_id
'''))
# The NULL category forms a partition of its own (it is sorted first in SQLite): that single product is compared with itself.

print("# L1Q6")
show(conn.execute('''
    SELECT customer_id, COUNT(*) AS orders,
           DENSE_RANK() OVER (ORDER BY COUNT(*) DESC) AS rank_no
    FROM orders
    GROUP BY customer_id
    ORDER BY orders DESC, customer_id
'''))

print("# L1Q7")
show(conn.execute('''
    SELECT c.first_name || ' ' || c.last_name AS customer,
           SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS spend,
           RANK() OVER (ORDER BY SUM(oi.quantity * oi.unit_price_cents) DESC) AS spend_rank
    FROM customers AS c
    JOIN orders AS o ON o.customer_id = c.customer_id
    JOIN order_items AS oi ON oi.order_id = o.order_id
    WHERE o.status <> 'cancelled'
    GROUP BY c.customer_id
    ORDER BY spend_rank, c.customer_id
    LIMIT 5
'''))

print("# L1Q8")
show(conn.execute('''
    SELECT customer_id, order_id, order_date,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS order_no
    FROM orders
    ORDER BY customer_id, order_no
    LIMIT 8
'''))

print("# L1Q9")
show(conn.execute('''
    WITH product_revenue AS (
        SELECT p.category_id, p.name AS product,
               SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS revenue
        FROM products AS p
        JOIN order_items AS oi ON oi.product_id = p.product_id
        GROUP BY p.product_id
    )
    SELECT c.name AS category, pr.product, pr.revenue,
           round(100.0 * pr.revenue / SUM(pr.revenue) OVER (PARTITION BY pr.category_id), 1) AS share
    FROM product_revenue AS pr
    JOIN categories AS c ON c.category_id = pr.category_id
    ORDER BY category, share DESC, product
'''))

print("# L1Q10")
show(conn.execute('''
    WITH q AS (
        SELECT price_cents,
               NTILE(4) OVER (ORDER BY price_cents, product_id) AS quartile
        FROM products
    )
    SELECT quartile, COUNT(*) AS products, MIN(price_cents) AS cheapest, MAX(price_cents) AS dearest
    FROM q
    GROUP BY quartile
    ORDER BY quartile
'''))

print("# L1Q11")
show(conn.execute('''
    SELECT name, title, salary_cents / 100 AS salary,
           round(PERCENT_RANK() OVER (ORDER BY salary_cents), 2) AS pct_rank
    FROM employees
    ORDER BY salary_cents DESC, employee_id
    LIMIT 5
'''))

print("# L1Q12")
show(conn.execute('''
    SELECT manager_id, name, salary_cents,
           RANK() OVER (PARTITION BY manager_id ORDER BY salary_cents DESC) AS team_rank
    FROM employees
    ORDER BY manager_id, team_rank, employee_id
    LIMIT 8
'''))

print("# L1Q13")
show(lib.execute('''
    SELECT genre, title, pages,
           ROW_NUMBER() OVER (PARTITION BY genre ORDER BY pages DESC, title) AS longest_first
    FROM books
    ORDER BY genre, longest_first
'''))

print("# L1Q14")
show(lib.execute('''
    SELECT m.name, COUNT(l.id) AS loans,
           DENSE_RANK() OVER (ORDER BY COUNT(l.id) DESC) AS loan_rank
    FROM members AS m
    LEFT JOIN loans AS l ON l.member_id = m.id
    GROUP BY m.id
    ORDER BY loans DESC, m.name
'''))

print("# L1Q15")
show(lib.execute('''
    SELECT genre, title, pages,
           MAX(pages) OVER (PARTITION BY genre) AS longest,
           MAX(pages) OVER (PARTITION BY genre) - pages AS shorter_by
    FROM books
    ORDER BY genre, title
    LIMIT 6
'''))

print("# L1Q16")
try:
    conn.execute('SELECT product_id FROM products WHERE ROW_NUMBER() OVER (ORDER BY price_cents DESC) <= 3')
except sqlite3.Error as e:
    print(type(e).__name__ + ':', e)
show(conn.execute('''
    WITH numbered AS (
        SELECT product_id, name, price_cents,
               ROW_NUMBER() OVER (ORDER BY price_cents DESC, product_id) AS rn
        FROM products
    )
    SELECT product_id, name, price_cents FROM numbered WHERE rn <= 3 ORDER BY rn
'''))

print("# L1Q17")
t = sqlite3.connect(':memory:')
t.execute('CREATE TABLE scores (score INTEGER)')
t.executemany('INSERT INTO scores VALUES (?)', [(90,), (85,), (85,), (70,)])
show(t.execute('''
    SELECT score,
           ROW_NUMBER() OVER (ORDER BY score DESC) AS rn,
           RANK() OVER (ORDER BY score DESC) AS rnk,
           DENSE_RANK() OVER (ORDER BY score DESC) AS dense
    FROM scores
    ORDER BY score DESC
'''))

print("# L2Q1")
show(conn.execute('''
    WITH product_revenue AS (
        SELECT p.category_id, p.name AS product,
               SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS revenue
        FROM products AS p
        JOIN order_items AS oi ON oi.product_id = p.product_id
        GROUP BY p.product_id
    ), numbered AS (
        SELECT category_id, product, revenue,
               ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY revenue DESC, product) AS pos
        FROM product_revenue
    )
    SELECT c.name AS category, n.product, n.revenue, n.pos
    FROM numbered AS n
    JOIN categories AS c ON c.category_id = n.category_id
    WHERE n.pos <= 3
    ORDER BY category, n.pos
'''))

print("# L2Q2")
show(conn.execute('''
    WITH numbered AS (
        SELECT customer_id, order_id, order_date, status,
               ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) AS rn
        FROM orders
    )
    SELECT customer_id, order_id, order_date, status
    FROM numbered
    WHERE rn = 1
    ORDER BY customer_id
    LIMIT 6
'''))
print(conn.execute('SELECT COUNT(DISTINCT customer_id) FROM orders').fetchone()[0], 'customers have orders')

print("# L2Q3")
show(conn.execute('''
    WITH spend AS (
        SELECT o.customer_id, SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS spend
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.customer_id
    ), tiles AS (
        SELECT customer_id, spend,
               NTILE(4) OVER (ORDER BY spend DESC, customer_id) AS quartile
        FROM spend
    )
    SELECT quartile, COUNT(*) AS customers, MIN(spend) AS min_spend, MAX(spend) AS max_spend
    FROM tiles
    GROUP BY quartile
    ORDER BY quartile
'''))

print("# L2Q4")
conn.execute('CREATE TEMP TABLE signups AS SELECT * FROM newsletter_signups')
cur = conn.execute('''
    DELETE FROM signups
    WHERE rowid IN (
        SELECT rowid FROM (
            SELECT rowid,
                   ROW_NUMBER() OVER (PARTITION BY lower(trim(email)) ORDER BY signed_up_at, rowid) AS rn
            FROM signups
        )
        WHERE rn > 1
    )
''')
print('deleted:', cur.rowcount)
show(conn.execute('SELECT email, signed_up_at FROM signups ORDER BY lower(trim(email))'))
conn.execute('CREATE UNIQUE INDEX ux_signups_email ON signups (lower(trim(email)))')
try:
    conn.execute("INSERT INTO signups VALUES ('ANA@example.com', '2025-12-24 10:00:00')")
except sqlite3.IntegrityError as e:
    print('IntegrityError:', e)

print("# L2Q5")
show(conn.execute('''
    WITH spend AS (
        SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer, c.country,
               SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS spend
        FROM customers AS c
        JOIN orders AS o ON o.customer_id = c.customer_id
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY c.customer_id
    ), ranked AS (
        SELECT *, RANK() OVER (PARTITION BY country ORDER BY spend DESC) AS rnk
        FROM spend
    )
    SELECT country, customer, spend
    FROM ranked
    WHERE rnk = 1
    ORDER BY country, customer_id
'''))

print("# L2Q6")
show(conn.execute('''
    WITH ranked AS (
        SELECT category_id, name, price_cents,
               DENSE_RANK() OVER (PARTITION BY category_id ORDER BY price_cents DESC) AS dr
        FROM products
        WHERE category_id IS NOT NULL
    )
    SELECT c.name AS category, r.name AS product, r.price_cents
    FROM ranked AS r
    JOIN categories AS c ON c.category_id = r.category_id
    WHERE r.dr = 2
    ORDER BY category, product
'''))

print("# L3Q1")
import csv

fortune = sqlite3.connect(":memory:")
fortune.execute("CREATE TABLE raw (rank TEXT, company TEXT, sector TEXT, revenue TEXT, profit TEXT)")
with open(DATA / "fortune1000_final.csv", newline="", encoding="latin-1") as f:
    fortune.executemany(
        "INSERT INTO raw VALUES (?, ?, ?, ?, ?)",
        [(r["rank"], r["title"], r["Sector"], r["Revenues ($M)"], r["Profits ($M)"]) for r in csv.DictReader(f)],
    )
fortune.execute("""
    CREATE TABLE f1000 AS
    SELECT CAST(rank AS INTEGER) AS rank, company, sector,
           CAST(replace(replace(replace(revenue, '$', ''), ',', ''), ' ', '') AS INTEGER) AS revenue_m,
           CAST(replace(replace(replace(profit, '$', ''), ',', ''), ' ', '') AS REAL) AS profit_m
    FROM raw
""")
print(fortune.execute("SELECT COUNT(*), MAX(revenue_m) FROM f1000").fetchone())
print(fortune.execute("SELECT company, revenue_m FROM f1000 ORDER BY revenue_m DESC LIMIT 1").fetchone())

print("# L3Q2")
show(fortune.execute('''
    WITH numbered AS (
        SELECT sector, company, revenue_m,
               ROW_NUMBER() OVER (PARTITION BY sector ORDER BY revenue_m DESC, rank) AS pos
        FROM f1000
    )
    SELECT sector, company, revenue_m, pos
    FROM numbered
    WHERE pos <= 3
    ORDER BY sector, pos
'''))

print("# L3Q3")
show(fortune.execute('''
    WITH numbered AS (
        SELECT sector, company, revenue_m,
               ROW_NUMBER() OVER (PARTITION BY sector ORDER BY revenue_m DESC, rank) AS pos,
               COUNT(*) OVER (PARTITION BY sector) AS companies,
               SUM(revenue_m) OVER (PARTITION BY sector) AS sector_total
        FROM f1000
    )
    SELECT sector, companies, sector_total, company AS leader,
           round(100.0 * revenue_m / sector_total, 1) AS leader_share
    FROM numbered
    WHERE pos = 1
    ORDER BY leader_share DESC, sector
    LIMIT 6
'''))
