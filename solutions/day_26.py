# Day 26 reference solutions: DuckDB with pandas, Polars and SQLite
import shutil
import sqlite3

import duckdb
import pandas as pd
import polars as pl

from helpers import DATA, WORK, show

people = [
    {"name": "Ana", "age": 31, "city": "Oslo"},
    {"name": "Ben", "age": 25, "city": "Rome"},
    {"name": "Cy", "age": 42, "city": "Oslo"},
    {"name": "Di", "age": 37, "city": "Rome"},
    {"name": "Eli", "age": 29, "city": "Lima"},
]

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
df = pd.DataFrame(people)
show(duckdb.sql("SELECT city, COUNT(*) AS people, round(AVG(age), 1) AS avg_age FROM df GROUP BY city ORDER BY people DESC, city"))

print("# Level 1, Q2")
res = duckdb.sql("SELECT city, COUNT(*) AS people FROM df GROUP BY city ORDER BY city")
as_pandas = res.df()
as_polars = res.pl()
print(isinstance(as_pandas, pd.DataFrame), isinstance(as_polars, pl.DataFrame))
print(as_pandas)
print(as_polars)

print("# Level 1, Q3")
pdf = pl.DataFrame(people)
print(duckdb.sql("SELECT name, age FROM pdf WHERE age >= 30 ORDER BY age DESC").pl())

print("# Level 1, Q4")
print(duckdb.sql("SELECT name FROM df WHERE age > $min ORDER BY name", params={"min": 28}).fetchall())

print("# Level 1, Q5")
con = duckdb.connect()
con.register("people_view", df)
print(con.execute("SELECT COUNT(*), MAX(age) FROM people_view").fetchall())


def oldest(frame: pd.DataFrame):
    local = frame[frame.age > 30]
    return duckdb.sql("SELECT name FROM local ORDER BY age DESC").fetchall()


print("# Level 1, Q6")
print(oldest(df))

print("# Level 1, Q7")
con.execute("CREATE TABLE people AS SELECT * FROM df")
con.execute("INSERT INTO people SELECT * FROM df WHERE city = 'Lima'")
print(con.execute("SELECT COUNT(*) FROM people").fetchall())
show(con.execute("DESCRIBE people"))

print("# Level 1, Q8")
rel = duckdb.sql("SELECT * FROM df")
chained = rel.filter("age > 28").aggregate("city, count(*) AS n").order("city")
show(chained)
same_sql = duckdb.sql("SELECT city, count(*) AS n FROM df WHERE age > 28 GROUP BY city ORDER BY city").fetchall()
print(chained.fetchall() == same_sql)

print("# Level 1, Q9")
table = duckdb.sql("SELECT * FROM df").to_arrow_table()
print(type(table).__module__, table.num_rows, table.column_names)

print("# Level 1, Q10")
back = duckdb.sql("SELECT city, MAX(age) AS oldest FROM pdf GROUP BY city ORDER BY city").df()
print(type(back).__module__, back.shape)

duckdb_attach = duckdb.connect()
print("# Level 1, Q11")
duckdb_attach.execute(f"ATTACH '{DATA / 'shop.db'}' AS shop (TYPE sqlite, READ_ONLY)")
print([r[0] for r in duckdb_attach.execute("SELECT table_name FROM duckdb_tables() WHERE database_name = 'shop' ORDER BY table_name").fetchall()])

print("# Level 1, Q12")
parts = [(t, duckdb_attach.execute(f"SELECT COUNT(*) FROM shop.{t}").fetchone()[0]) for t in
         [r[0] for r in duckdb_attach.execute("SELECT table_name FROM duckdb_tables() WHERE database_name = 'shop' ORDER BY table_name").fetchall()]]
print(parts)

print("# Level 1, Q13")
try:
    duckdb_attach.execute("INSERT INTO shop.categories (name) VALUES ('Nope')")
except duckdb.Error as e:
    print(type(e).__name__, "-", str(e).splitlines()[0])

print("# Level 1, Q14")
duckdb_attach.execute("USE shop")
print(duckdb_attach.execute("SELECT COUNT(*) FROM orders").fetchall())
duckdb_attach.execute("USE memory")

print("# Level 1, Q15")
show(duckdb_attach.execute("""
    SELECT strftime(CAST(order_date AS DATE), '%Y-%m') AS month, COUNT(*) AS orders
    FROM shop.orders WHERE order_date >= '2025-01-01'
    GROUP BY ALL ORDER BY ALL LIMIT 3
"""))

print("# Level 1, Q16")
duckdb_attach.execute("""
    CREATE TABLE local_orders AS
    SELECT order_id, customer_id, CAST(order_date AS DATE) AS order_date, status FROM shop.orders
""")
show(duckdb_attach.execute("SELECT COUNT(*) AS rows, typeof(order_date) AS type FROM local_orders GROUP BY type"))

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
hn = pd.read_csv(DATA / "hacker_news.csv")
hn = hn.reset_index(names="row")
show(duckdb.sql("SELECT row, id, num_points, author FROM hn ORDER BY row LIMIT 5"))
show(duckdb.sql("SELECT row, id, num_points, author FROM hn ORDER BY row DESC LIMIT 5"))
print(hn.tail()[["row", "id", "num_points", "author"]])  # same five rows, in pandas
show(duckdb.sql("SELECT title FROM hn ORDER BY row LIMIT 3"))
print(duckdb.sql("SELECT COUNT(*) AS rows FROM hn").fetchall(), len(duckdb.sql("SELECT * FROM hn").columns))
n_py = duckdb.sql("SELECT COUNT(*) FROM hn WHERE title LIKE '%python%'").fetchall()[0][0]
n_js = duckdb.sql("SELECT COUNT(*) FROM hn WHERE title LIKE '%JavaScript%'").fetchall()[0][0]
p_py = int(hn.title.str.contains("python", na=False).sum())
p_js = int(hn.title.str.contains("JavaScript", na=False).sum())
print(n_py, n_js, (n_py, n_js) == (p_py, p_js))
print(duckdb.sql("SELECT COUNT(*) FROM hn WHERE title ILIKE '%python%'").fetchall())
show(duckdb.sql("SELECT title FROM hn WHERE title LIKE '%JavaScript%' ORDER BY num_points DESC, id LIMIT 3"))

print("# Level 2, Q2")
wh = pd.read_csv(DATA / "weight-height.csv")
by_sql = duckdb.sql("""
    SELECT Gender, COUNT(*) AS n, round(AVG(Height), 2) AS avg_height, round(AVG(Weight), 2) AS avg_weight
    FROM wh GROUP BY Gender ORDER BY Gender
""").df()
by_pandas = (wh.groupby("Gender").agg(n=("Height", "size"), avg_height=("Height", "mean"), avg_weight=("Weight", "mean"))
             .round(2).reset_index())
print(by_sql)
print(by_pandas)
print((by_sql.round(2).values == by_pandas.values).all())

print("# Level 2, Q3")
hnp = pl.read_csv(DATA / "hacker_news.csv")
print(duckdb.sql("""
    SELECT author, COUNT(*) AS posts, CAST(SUM(num_points) AS BIGINT) AS points
    FROM hnp GROUP BY author ORDER BY points DESC, author LIMIT 3
""").pl())

print("# Level 2, Q4")
cities = pl.DataFrame({"city": ["Oslo", "Rome", "Lima"], "country": ["Norway", "Italy", "Peru"]})
show(duckdb.sql("""
    SELECT p.name, p.age, c.country
    FROM df AS p JOIN cities AS c USING (city)
    ORDER BY c.country, p.name
"""))

print("# Level 2, Q5")
copy = WORK / "day26_shop_copy.db"
shutil.copy(DATA / "shop.db", copy)
w = duckdb.connect()
w.execute(f"ATTACH '{copy}' AS lite (TYPE sqlite)")
w.execute("""
    CREATE TABLE lite.top_customers AS
    SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer,
           CAST(SUM(oi.quantity * oi.unit_price_cents) AS BIGINT) AS spend_cents
    FROM lite.customers AS c
    JOIN lite.orders AS o USING (customer_id)
    JOIN lite.order_items AS oi USING (order_id)
    WHERE o.status <> 'cancelled'
    GROUP BY ALL
    ORDER BY spend_cents DESC, customer_id
    LIMIT 5
""")
w.close()
check = sqlite3.connect(copy)
print(check.execute("SELECT * FROM top_customers ORDER BY spend_cents DESC, customer_id").fetchall())
print(check.execute("SELECT sql FROM sqlite_master WHERE name = 'top_customers'").fetchone()[0])
orig = sqlite3.connect(DATA / "shop.db")
print(orig.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'top_customers'").fetchone())

print("# Level 2, Q6")
sql_version = duckdb.sql("SELECT name, age FROM df WHERE city = 'Oslo' ORDER BY age DESC").fetchall()
api_version = duckdb.sql("SELECT * FROM df").filter("city = 'Oslo'").project("name, age").order("age DESC").fetchall()
print(sql_version, sql_version == api_version)

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
rates = pd.DataFrame({"currency": ["USD", "EUR", "GBP"], "per_usd": [1.00, 0.92, 0.79]})
lite_con = duckdb.connect()
lite_con.execute(f"ATTACH '{DATA / 'shop.db'}' AS shop (TYPE sqlite, READ_ONLY)")
show(lite_con.execute("""
    WITH revenue AS (
        SELECT year(CAST(o.order_date AS DATE)) AS year, SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS usd
        FROM shop.orders AS o
        JOIN shop.order_items AS oi USING (order_id)
        WHERE o.status <> 'cancelled'
        GROUP BY ALL
    )
    SELECT r.year, x.currency, round(r.usd * x.per_usd, 2) AS revenue
    FROM revenue AS r CROSS JOIN rates AS x
    ORDER BY r.year, x.per_usd DESC
"""))

print("# Level 3, Q2")
wide = lite_con.execute("""
    PIVOT (
        SELECT c.country, x.currency,
               SUM(oi.quantity * oi.unit_price_cents) / 100.0 * x.per_usd AS revenue
        FROM shop.customers AS c
        JOIN shop.orders AS o USING (customer_id)
        JOIN shop.order_items AS oi USING (order_id)
        CROSS JOIN rates AS x
        WHERE o.status <> 'cancelled'
        GROUP BY c.country, x.currency, x.per_usd
    )
    ON currency IN ('USD', 'EUR', 'GBP')
    USING round(SUM(revenue), 2)
    GROUP BY country
    ORDER BY country
""").df()
print(wide)
copy3 = WORK / "day26_shop_copy3.db"
shutil.copy(DATA / "shop.db", copy3)
lite_con.execute(f"ATTACH '{copy3}' AS out_db (TYPE sqlite)")
lite_con.execute("CREATE TABLE out_db.revenue_by_country AS SELECT * FROM wide")
lite_con.execute("DETACH out_db")
chk = sqlite3.connect(copy3)
print(chk.execute("SELECT * FROM revenue_by_country ORDER BY country").fetchall())
print(chk.execute("SELECT sql FROM sqlite_master WHERE name = 'revenue_by_country'").fetchone()[0])
