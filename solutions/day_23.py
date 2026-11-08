# Day 23 reference solutions: Meet DuckDB
import csv
import sqlite3
import time
from datetime import datetime

import duckdb

from helpers import DATA, WORK, library_conn, shop_duck, show

# ---------------------------------------------------------------- Level 1
# The running thread: a DuckDB copy of the library, in a file.
lib_path = WORK / "day23_library.duckdb"
lib_path.unlink(missing_ok=True)

print("# Level 1, Q1")
print(duckdb.__version__)
duckdb.sql("SELECT 42 AS answer").show()
print(duckdb.sql("SELECT 42 AS answer").fetchall())
show(duckdb.sql("SELECT 42 AS answer"))

print("# Level 1, Q2")
print("DuckDB:", duckdb.sql("SELECT 7 / 2 AS slash, 7 // 2 AS double_slash, 7 % 2 AS modulo").fetchall())
print("SQLite:", sqlite3.connect(":memory:").execute("SELECT 7 / 2, 7 % 2").fetchall())
# SQLite: / between two integers is integer division (3); DuckDB: / is always a real division (3.5) and // is integer division.

print("# Level 1, Q3")
con = duckdb.connect(str(lib_path))
print(lib_path.exists())  # True: the file is created as soon as you connect

print("# Level 1, Q4")
con.execute("CREATE SEQUENCE book_ids START 1")
con.execute("""
    CREATE TABLE books (
        id      INTEGER PRIMARY KEY DEFAULT nextval('book_ids'),
        title   VARCHAR NOT NULL,
        author  VARCHAR NOT NULL,
        year    INTEGER,
        pages   INTEGER,
        genre   VARCHAR,
        price   DECIMAL(10, 2),
        rating  DECIMAL(2, 1)
    )
""")
show(con.execute("DESCRIBE books"))

print("# Level 1, Q5")
lite = library_conn()  # stands in for the student's 00_practice/library.db
rows = lite.execute(
    "SELECT title, author, year, pages, genre, price_cents / 100.0, rating FROM books ORDER BY id"
).fetchall()
con.executemany(
    "INSERT INTO books (title, author, year, pages, genre, price, rating) VALUES (?, ?, ?, ?, ?, ?, ?)", rows
)

print("# Level 1, Q6")
print(con.execute("SELECT COUNT(*) FROM books").fetchone())
show(con.execute("SELECT id, title, price, rating FROM books ORDER BY id LIMIT 4"))

print("# Level 1, Q7")
show(con.execute("SELECT title, pages FROM books WHERE pages > ? ORDER BY pages DESC, title", [600]))
show(con.execute("SELECT title, genre FROM books WHERE genre = $genre AND year < $year ORDER BY title",
                 {"genre": "Sci-Fi", "year": 2000}))

print("# Level 1, Q8")
try:
    con.execute("INSERT INTO books (title, author, pages) VALUES ('Strict', 'A. Writer', 'many')")
except duckdb.Error as e:
    print(type(e).__name__, "-", str(e).splitlines()[0])

print("# Level 1, Q9")
con.execute("BEGIN")
con.execute("INSERT INTO books (title, author, year, pages) VALUES ('Lenient', 'A. Writer', '2024', 300.7)")
show(con.execute("SELECT title, year, pages, typeof(year), typeof(pages) FROM books WHERE title = 'Lenient'"))
try:
    con.execute("INSERT INTO books (title, author, year) VALUES ('Bad year', 'A. Writer', 'last year')")
except duckdb.Error as e:
    print(type(e).__name__)
con.execute("ROLLBACK")
print(con.execute("SELECT COUNT(*) FROM books").fetchone())  # 12 again

print("# Level 1, Q10")
show(con.execute("SELECT SUM(price) AS total, typeof(SUM(price)) AS type FROM books"))
print(con.execute("SELECT 0.1::DOUBLE + 0.2::DOUBLE AS as_double, 0.1::DECIMAL(10, 2) + 0.2::DECIMAL(10, 2) AS as_decimal").fetchall())

print("# Level 1, Q11")
con.execute("ALTER TABLE books ADD COLUMN added DATE")
con.execute("UPDATE books SET added = DATE '2025-03-14'")
show(con.execute("""
    SELECT title, added, DATE '2025-12-25' - added AS days_to_xmas, added + 30 AS plus_30
    FROM books ORDER BY id LIMIT 2
"""))

print("# Level 1, Q12")
show(con.execute("SELECT [1, 2, 3] AS a_list, {'title': 'Dune', 'year': 1965} AS a_struct, MAP {'a': 1, 'b': 2} AS a_map"))

print("# Level 1, Q13")
plan = con.execute("EXPLAIN SELECT title FROM books WHERE pages > 600").fetchall()[0][1]
print(plan)

print("# Level 1, Q14")
# Row store (SQLite): all values of one row sit together: fast to fetch or change one whole row (OLTP).
# Column store (DuckDB): all values of one column sit together: fast to scan and add up a few columns across millions of rows (OLAP).

print("# Level 1, Q15")
con.close()
con = duckdb.connect(str(lib_path))
print(con.execute("SELECT COUNT(*) FROM books").fetchone())  # (12,): the data survived
con.close()

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
shop_path = WORK / "day23_shop.duckdb"
shop_path.unlink(missing_ok=True)
shop = shop_duck(shop_path)
for t in ["customers", "categories", "products", "orders", "order_items", "employees", "newsletter_signups"]:
    print(t, shop.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
show(shop.execute("SELECT typeof(signup_date) AS signup, typeof(price_cents) AS price FROM customers, products LIMIT 1"))

print("# Level 2, Q2")
show(shop.execute("""
    SELECT c.name AS category, SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS revenue
    FROM order_items AS oi
    JOIN products AS p ON p.product_id = oi.product_id
    JOIN categories AS c ON c.category_id = p.category_id
    GROUP BY c.name
    ORDER BY revenue DESC, category
    LIMIT 3
"""))
show(shop.execute("""
    SELECT COUNT(*) AS customers_without_orders
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE o.order_id IS NULL
"""))
show(shop.execute("""
    WITH spend AS (
        SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer,
               SUM(oi.quantity * oi.unit_price_cents) AS spend_cents
        FROM customers AS c
        JOIN orders AS o ON o.customer_id = c.customer_id
        JOIN order_items AS oi ON oi.order_id = o.order_id
        GROUP BY c.customer_id, customer
    )
    SELECT customer, spend_cents, RANK() OVER (ORDER BY spend_cents DESC) AS rnk
    FROM spend
    ORDER BY rnk, customer
    LIMIT 5
"""))

print("# Level 2, Q3")
show(duckdb.sql("SELECT 5 / 2 AS a, 'a' LIKE 'A' AS b, CAST(2.5 AS INTEGER) AS c, CAST(3.5 AS INTEGER) AS d, 'abc' < 'abd' AS e"))
show(duckdb.sql("SELECT x FROM (VALUES (2), (NULL), (1)) AS t(x) ORDER BY x"))
try:
    duckdb.sql("SELECT '5' + 1").fetchall()
except duckdb.Error as e:
    print(type(e).__name__)

print("# Level 2, Q4")
events_db = WORK / "day23_events.db"
lite = sqlite3.connect(events_db)
lite.execute("CREATE TABLE IF NOT EXISTS events (event_id INTEGER, user_id INTEGER, event_type TEXT, ts TEXT, amount REAL)")
if lite.execute("SELECT COUNT(*) FROM events").fetchone()[0] != 1_000_000:
    lite.execute("DELETE FROM events")
    with (DATA / "big_events.csv").open(newline="") as f:
        reader = csv.reader(f)
        next(reader)
        lite.executemany(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            ((int(a), int(b), c, d, float(e) if e else None) for a, b, c, d, e in reader),
        )
    lite.commit()
duck = duckdb.connect()
duck.execute(f"CREATE TABLE events AS SELECT * FROM '{DATA / 'big_events.csv'}'")
print(lite.execute("SELECT COUNT(*) FROM events").fetchone(), duck.execute("SELECT COUNT(*) FROM events").fetchone())

queries = {
    "events per type": ("SELECT event_type, COUNT(*) AS n FROM events GROUP BY event_type ORDER BY event_type",
                        "SELECT event_type, COUNT(*) AS n FROM events GROUP BY event_type ORDER BY event_type"),
    "busiest users": ("SELECT user_id, COUNT(*) AS n FROM events GROUP BY user_id ORDER BY n DESC, user_id LIMIT 5",
                      "SELECT user_id, COUNT(*) AS n FROM events GROUP BY user_id ORDER BY n DESC, user_id LIMIT 5"),
    "events per month": ("SELECT strftime('%Y-%m', ts) AS month, COUNT(*) AS n FROM events GROUP BY month ORDER BY month",
                         "SELECT strftime(ts, '%Y-%m') AS month, COUNT(*) AS n FROM events GROUP BY month ORDER BY month"),
}
faster = []
for name, (q_lite, q_duck) in queries.items():
    t0 = time.perf_counter()
    a = lite.execute(q_lite).fetchall()
    t_lite = time.perf_counter() - t0
    t0 = time.perf_counter()
    b = duck.execute(q_duck).fetchall()
    t_duck = time.perf_counter() - t0
    assert a == b, name
    faster.append(t_duck < t_lite)
    print(f"{name:18} same answer: {a == b}   DuckDB faster: {t_duck < t_lite}   (SQLite took {t_lite / t_duck:.0f}x longer)")
assert all(faster)
show(duck.execute("SELECT event_type, COUNT(*) AS n FROM events GROUP BY event_type ORDER BY event_type"))
show(duck.execute("SELECT user_id, COUNT(*) AS n FROM events GROUP BY user_id ORDER BY n DESC, user_id LIMIT 5"))
show(duck.execute("SELECT strftime(ts, '%Y-%m') AS month, COUNT(*) AS n FROM events GROUP BY month ORDER BY month LIMIT 3"))
# Why: DuckDB stores each column together and reads only the columns the query needs (event_type, or user_id),
# in big vectorised chunks and on all CPU cores. SQLite reads every row page by page, on one thread.

print("# Level 2, Q5")
show(duckdb.sql("""
    SELECT SUM(x) AS as_double, SUM(x::DECIMAL(10, 2)) AS as_decimal
    FROM (VALUES (0.1::DOUBLE), (0.2::DOUBLE)) AS t(x)
"""))
show(duck.execute("""
    SELECT SUM(CAST(amount AS DECIMAL(10, 2))) AS purchases_total, typeof(SUM(CAST(amount AS DECIMAL(10, 2)))) AS type
    FROM events WHERE event_type = 'purchase'
"""))
show(duck.execute("""
    SELECT SUM(CAST(amount AS DECIMAL(10, 2))) AS net_total FROM events WHERE amount IS NOT NULL
"""))

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
rows = []
with (DATA / "hacker_news.csv").open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        iso = datetime.strptime(r["created_at"], "%m/%d/%Y %H:%M").strftime("%Y-%m-%d %H:%M:%S")
        rows.append((int(r["id"]), r["title"], r["url"] or None, int(r["num_points"]), int(r["num_comments"]), r["author"], iso))
lite = sqlite3.connect(":memory:")
lite.execute("CREATE TABLE hn_iso (id INTEGER, title TEXT, url TEXT, num_points INTEGER, num_comments INTEGER, author TEXT, created_at TEXT)")
lite.executemany("INSERT INTO hn_iso VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
duck = duckdb.connect()
duck.execute("CREATE TABLE hn_iso (id INTEGER, title VARCHAR, url VARCHAR, num_points INTEGER, num_comments INTEGER, author VARCHAR, created_at VARCHAR)")
duck.executemany("INSERT INTO hn_iso VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
print(lite.execute("SELECT COUNT(*) FROM hn_iso").fetchone(), duck.execute("SELECT COUNT(*) FROM hn_iso").fetchone())

SQLITE_QUERY = """
    WITH daily AS (
        SELECT date(created_at) AS day, COUNT(*) AS posts
        FROM hn_iso
        GROUP BY day
    )
    SELECT a.day AS start_day, SUM(b.posts) AS posts_in_window
    FROM daily AS a
    JOIN daily AS b ON b.day >= a.day AND b.day < date(a.day, '+7 days')
    GROUP BY a.day
    ORDER BY posts_in_window DESC, a.day
    LIMIT 3
"""
show(lite.execute(SQLITE_QUERY))
try:
    duck.execute(SQLITE_QUERY)
except duckdb.Error as e:
    print(type(e).__name__, "-", str(e).splitlines()[0])
DUCK_QUERY = SQLITE_QUERY.replace("date(a.day, '+7 days')", "a.day + 7")
show(duck.execute(DUCK_QUERY))
# Only one change: date(day, '+7 days') -> day + 7. date(created_at) works in DuckDB too (it is a cast to DATE).
assert lite.execute(SQLITE_QUERY).fetchall() == [(str(d), int(n)) for d, n in duck.execute(DUCK_QUERY).fetchall()]

print("# Level 3, Q2")
pairs = [
    ("iif(7 > 5, 'big', 'small')", "if(7 > 5, 'big', 'small')"),
    ("julianday('2025-03-14') - julianday('2025-01-01')", "DATE '2025-03-14' - DATE '2025-01-01'"),
    ("date('2025-03-14', '+30 days')", "DATE '2025-03-14' + 30"),
    ("strftime('%Y-%m', '2025-03-14')", "strftime(DATE '2025-03-14', '%Y-%m')"),
    ("CAST(3.7 AS INTEGER)", "CAST(trunc(3.7) AS INTEGER)"),
    ("'Hello' LIKE 'hello'", "'Hello' ILIKE 'hello'"),
]
mem = sqlite3.connect(":memory:")
for sqlite_sql, duck_sql in pairs:
    print(f"{sqlite_sql:52} SQLite -> {mem.execute('SELECT ' + sqlite_sql).fetchone()[0]!s:12} DuckDB -> {duckdb.sql('SELECT ' + duck_sql).fetchall()[0][0]}")
