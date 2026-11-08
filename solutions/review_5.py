# Review 5 reference solutions: DuckDB (Days 23-26)
import shutil
import sqlite3

import duckdb
import pandas as pd
import polars as pl

from helpers import DATA, WORK, shop_duck, show

shop_file = WORK / "review5_shop.duckdb"
shop_duck(shop_file).close()
con = duckdb.connect(str(shop_file))
COUNTRIES = f"'{DATA / 'countries_data.json'}'"
EVENTS = f"'{DATA / 'big_events.csv'}'"

# ---------------------------------------------------------------- Part A
print("# Part A, Q1")
print(con.execute(f"""
    SELECT COUNT(*) FROM {COUNTRIES}
    WHERE population > 50_000_000 AND list_contains(languages, 'English')
""").fetchall())
show(con.execute(f"""
    SELECT name, population FROM {COUNTRIES}
    WHERE population > 50_000_000 AND list_contains(languages, 'English') ORDER BY population DESC, name
"""))

print("# Part A, Q2")
show(con.execute("""
    SELECT EXTRACT(year FROM signup_date) AS year, COUNT(*) AS customers
    FROM customers AS c
    WHERE NOT EXISTS (SELECT 1 FROM orders AS o WHERE o.customer_id = c.customer_id)
    GROUP BY ALL ORDER BY year
"""))

print("# Part A, Q3")
show(con.execute(f"""
    SELECT strftime(ts, '%Y-%m') AS month,
           COUNT(*) AS events,
           round(100.0 * COUNT(*) FILTER (WHERE event_type = 'purchase') / COUNT(*), 2) AS purchase_pct
    FROM {EVENTS}
    GROUP BY ALL ORDER BY month LIMIT 3
"""))

print("# Part A, Q4")
show(con.execute("""
    PIVOT (
        SELECT c.country, o.status FROM orders AS o JOIN customers AS c USING (customer_id)
    )
    ON status USING COUNT(*) GROUP BY country ORDER BY country
"""))

print("# Part A, Q5")
show(con.execute("""
    WITH spend AS (
        SELECT c.country, c.first_name || ' ' || c.last_name AS customer, c.customer_id,
               SUM(oi.quantity * oi.unit_price_cents) AS spend_cents
        FROM customers AS c
        JOIN orders AS o USING (customer_id)
        JOIN order_items AS oi USING (order_id)
        GROUP BY ALL
    )
    SELECT country, customer, spend_cents
    FROM spend
    QUALIFY ROW_NUMBER() OVER (PARTITION BY country ORDER BY spend_cents DESC, customer_id) = 1
    ORDER BY country
"""))

print("# Part A, Q6")
print(con.execute(f"""
    SELECT COUNT(DISTINCT language) FROM (SELECT unnest(languages) AS language FROM {COUNTRIES} WHERE currency = 'Euro')
""").fetchall())

print("# Part A, Q7")
targets = pd.DataFrame({"country": ["USA", "Canada", "France", "UK", "Germany"], "target_dollars": [12000, 11000, 9000, 9000, 6000]})
show(con.execute("""
    WITH rev AS (
        SELECT c.country, SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS revenue
        FROM customers AS c
        JOIN orders AS o USING (customer_id)
        JOIN order_items AS oi USING (order_id)
        WHERE o.status <> 'cancelled'
        GROUP BY ALL
    )
    SELECT country, revenue, target_dollars, revenue >= target_dollars AS hit
    FROM rev JOIN targets USING (country)
    ORDER BY country
"""))

print("# Part A, Q8")
rates = pd.DataFrame({
    "effective": pd.to_datetime(["2024-01-01", "2024-07-01", "2025-01-01", "2025-07-01"]),
    "usd_per_eur": [1.08, 1.07, 1.04, 1.17],
})
show(con.execute("""
    SELECT r.effective AS rate_since, r.usd_per_eur, COUNT(*) AS orders
    FROM orders AS o
    ASOF JOIN rates AS r ON o.order_date >= r.effective
    GROUP BY ALL
    ORDER BY rate_since
"""))

# ---------------------------------------------------------------- Part B
print("# Part B")
print(duckdb.sql("SELECT 7 / 2, 7 // 2, CAST(2.5 AS INTEGER), CAST(-2.5 AS INTEGER)").fetchall())
print(duckdb.sql("SELECT [1, 2, 3][2], [1, 2, 3][-1], len([1, 2, 3, 4][2:3]), list_filter([1, 2, 3, 4], lambda x: x % 2 = 0)").fetchall())
duckdb.sql("CREATE TEMP TABLE sales (month VARCHAR, product VARCHAR, units INTEGER)")
duckdb.sql("INSERT INTO sales VALUES ('jan', 'tea', 3), ('jan', 'cake', 1), ('feb', 'tea', 4), ('jan', 'tea', 2)")
show(duckdb.sql("PIVOT sales ON product USING SUM(units) GROUP BY month ORDER BY month DESC"))
print(duckdb.sql("SELECT x FROM (VALUES (2), (NULL), (1)) AS t(x) ORDER BY x DESC").fetchall())
show(duckdb.sql("""
    SELECT product, units, RANK() OVER (ORDER BY units DESC) AS rnk
    FROM sales QUALIFY rnk <= 2 ORDER BY rnk, product
"""))

# ---------------------------------------------------------------- Part C
print("# Part C, Q1")
show(duckdb.sql(f"SELECT created_at FROM read_csv('{DATA / 'hacker_news.csv'}', dateformat = '%m/%d/%Y %H:%M') LIMIT 2"))
show(duckdb.sql(f"SELECT created_at FROM read_csv('{DATA / 'hacker_news.csv'}', timestampformat = '%m/%d/%Y %H:%M') LIMIT 2"))

print("# Part C, Q2")
df = pd.DataFrame({"name": ["Ana", "Ben", "Cy", "Di"], "city": ["Oslo", "Rome", "Oslo", "Rome"], "age": [31, 25, 42, 37]})
show(duckdb.sql("SELECT name, city, COUNT(*) AS people FROM df GROUP BY ALL ORDER BY name"))
show(duckdb.sql("SELECT city, COUNT(*) AS people FROM df GROUP BY ALL ORDER BY city"))

print("# Part C, Q3")
print(duckdb.sql("""
    SELECT COUNT(*) FROM (VALUES (5), (7)) AS t(price)
    WHERE price > ALL (SELECT x FROM (VALUES (1)) AS s(x) WHERE x > 100)
""").fetchall())
print(duckdb.sql("""
    SELECT COUNT(*) FROM (VALUES (5), (7)) AS t(price)
    WHERE price > (SELECT MAX(x) FROM (VALUES (1)) AS s(x) WHERE x > 100)
""").fetchall())

print("# Part C, Q4")
copy = WORK / "review5_copy.db"
shutil.copy(DATA / "shop.db", copy)
w = duckdb.connect()
w.execute(f"ATTACH '{copy}' AS app (TYPE sqlite)")
w.execute(f"ATTACH '{DATA / 'shop.db'}' AS shop (TYPE sqlite, READ_ONLY)")
w.execute("CREATE TABLE app.t1 AS SELECT customer_id, SUM(quantity * unit_price_cents) AS spend FROM shop.orders JOIN shop.order_items USING (order_id) GROUP BY customer_id")
w.execute("CREATE TABLE app.t2 AS SELECT customer_id, CAST(SUM(quantity * unit_price_cents) AS BIGINT) AS spend FROM shop.orders JOIN shop.order_items USING (order_id) GROUP BY customer_id")
w.close()
lite = sqlite3.connect(copy)
print(lite.execute("SELECT sql FROM sqlite_master WHERE name IN ('t1', 't2') ORDER BY name").fetchall())
print(lite.execute("SELECT typeof(spend) FROM t1 LIMIT 1").fetchall(), lite.execute("SELECT typeof(spend) FROM t2 LIMIT 1").fetchall())

# ---------------------------------------------------------------- Part E
print("# Mini-project")
events_parquet = WORK / "review5_events.parquet"
duckdb.sql(f"COPY (SELECT * FROM {EVENTS}) TO '{events_parquet}' (FORMAT parquet)")
segments = pd.DataFrame({
    "country": ["USA", "Canada", "France", "UK", "Germany"],
    "region": ["Americas", "Americas", "Europe", "Europe", "Europe"],
})
lite_db = duckdb.connect()
lite_db.execute(f"ATTACH '{DATA / 'shop.db'}' AS shop (TYPE sqlite, READ_ONLY)")
report = lite_db.sql(f"""
    WITH customers AS (
        SELECT c.customer_id, s.region FROM shop.customers AS c JOIN segments AS s USING (country)
    ),
    sales AS (
        SELECT cu.region, COUNT(DISTINCT o.order_id) AS orders,
               SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS revenue
        FROM customers AS cu
        JOIN shop.orders AS o USING (customer_id)
        JOIN shop.order_items AS oi USING (order_id)
        WHERE o.status <> 'cancelled'
        GROUP BY cu.region
    ),
    activity AS (
        SELECT cu.region, COUNT(*) AS events, COUNT(*) FILTER (WHERE e.event_type = 'purchase') AS purchases
        FROM customers AS cu
        JOIN '{events_parquet}' AS e ON e.user_id = cu.customer_id
        GROUP BY cu.region
    )
    SELECT cu.region, COUNT(*) AS customers, s.orders, round(s.revenue, 2) AS revenue, a.events, a.purchases
    FROM customers AS cu
    JOIN sales AS s USING (region)
    JOIN activity AS a USING (region)
    GROUP BY ALL
    ORDER BY cu.region
""").pl()
print(report)
out_csv = WORK / "review5_region_report.csv"
report.write_csv(out_csv)
print(out_csv.read_text())
print(duckdb.sql(f"SELECT * FROM '{out_csv}'").fetchall())
