# Day 25 reference solutions: DuckDB's friendly SQL and nested types
import duckdb

from helpers import DATA, WORK, shop_duck, show

# Day 23, Level 2 Q1 built this file; here we rebuild it so the solution runs on its own.
shop_file = WORK / "day25_shop.duckdb"
shop_duck(shop_file).close()
con = duckdb.connect(str(shop_file))

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
show(con.execute("SELECT status, COUNT(*) AS orders FROM orders GROUP BY ALL ORDER BY ALL"))
show(con.execute("SELECT country, COUNT(*) AS customers FROM customers GROUP BY ALL ORDER BY customers DESC, country"))
show(con.execute("""
    SELECT c.country, SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS revenue
    FROM order_items AS oi
    JOIN orders AS o USING (order_id)
    JOIN customers AS c USING (customer_id)
    GROUP BY ALL
    ORDER BY revenue DESC
"""))
show(con.execute("""
    SELECT title, COUNT(*) AS people, ROUND(AVG(salary_cents) / 100, 2) AS avg_salary
    FROM employees GROUP BY ALL ORDER BY ALL LIMIT 4
"""))

print("# Level 1, Q2")
show(con.execute("SELECT * EXCLUDE (email, signup_date) FROM customers ORDER BY customer_id LIMIT 3"))

print("# Level 1, Q3")
show(con.execute("""
    SELECT * REPLACE (upper(country) AS country, coalesce(city, 'unknown') AS city)
    FROM customers WHERE customer_id IN (1, 8) ORDER BY customer_id
"""))
show(con.execute("""
    SELECT * EXCLUDE (email, signup_date) REPLACE (lower(country) AS country)
    FROM customers ORDER BY customer_id LIMIT 2
"""))

print("# Level 1, Q4")
show(con.execute("SELECT COLUMNS('.*_name') FROM customers ORDER BY customer_id LIMIT 2"))
show(con.execute("SELECT MIN(COLUMNS('.*_cents')), MAX(COLUMNS('.*_cents')) FROM products"))
show(con.execute("SELECT COUNT(*) - COUNT(COLUMNS(*)) FROM customers"))

print("# Level 1, Q5")
show(con.execute("""
    SELECT c.name AS category, p.name AS product, p.price_cents
    FROM products AS p JOIN categories AS c USING (category_id)
    QUALIFY ROW_NUMBER() OVER (PARTITION BY c.name ORDER BY p.price_cents DESC, p.product_id) <= 3
    ORDER BY category, p.price_cents DESC, product
    LIMIT 6
"""))

print("# Level 1, Q6")
show(con.execute("""
    SELECT customer_id, order_id, order_date
    FROM orders
    QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) = 1
    ORDER BY customer_id
    LIMIT 5
"""))
print(con.execute("""
    SELECT COUNT(*) FROM (
        SELECT customer_id FROM orders
        QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) = 1
    )
""").fetchall())

print("# Level 1, Q7")
show(con.sql("FROM categories ORDER BY name LIMIT 3"))
show(con.sql("FROM products SELECT COUNT(*) AS products, MIN(price_cents) AS cheapest"))

print("# Level 1, Q8")
show(con.execute("""
    SELECT DISTINCT ON (category_id) category_id, name, price_cents
    FROM products
    WHERE category_id IS NOT NULL
    ORDER BY category_id, price_cents, product_id
    LIMIT 3
"""))

print("# Level 1, Q9")
show(con.execute("""
    SELECT c.name AS category, COUNT(*) AS products, list(p.name ORDER BY p.name)[1:2] AS first_two
    FROM products AS p JOIN categories AS c USING (category_id)
    GROUP BY ALL ORDER BY category LIMIT 3
"""))

print("# Level 1, Q10")
print(con.execute("SELECT [x * x FOR x IN range(1, 11) IF x % 2 = 0]").fetchall())
print(con.execute("SELECT list_filter(range(1, 11), lambda x: x % 3 = 0), list_transform(['a', 'b'], lambda x: upper(x))").fetchall())
try:
    con.execute("SELECT list_transform([1, 2, 3], x -> x * 2)")
except duckdb.Error as e:
    print(type(e).__name__, "-", str(e).splitlines()[0])

print("# Level 1, Q11")
show(con.execute("SELECT name, unnest(languages) AS language FROM read_json(?) WHERE name = 'Finland'", [str(DATA / "countries_data.json")]))

print("# Level 1, Q12")
show(con.execute("""
    SELECT item.name AS name, item.dollars AS dollars
    FROM (SELECT {'name': name, 'dollars': price_cents / 100} AS item FROM products ORDER BY product_id LIMIT 3)
"""))

print("# Level 1, Q13")
q = "SELECT order_id FROM orders USING SAMPLE reservoir(5 ROWS) REPEATABLE (7) ORDER BY order_id"
a = con.execute(q).fetchall()
b = con.execute(q).fetchall()
print([r[0] for r in a], a == b)

print("# Level 1, Q14")
print(con.execute("SELECT COUNT(*) FROM generate_series(DATE '2025-01-01', DATE '2025-01-31', INTERVAL 1 DAY)").fetchall())

print("# Level 1, Q15")
con.execute("CREATE OR REPLACE MACRO price_label(cents) AS '$' || (cents // 100) || '.' || lpad((cents % 100)::VARCHAR, 2, '0')")
show(con.execute("SELECT name, price_label(price_cents) AS price FROM products ORDER BY price_cents DESC, name LIMIT 3"))

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
status_year = """
    SELECT status, year(order_date)::VARCHAR AS year FROM orders
"""
show(con.execute(f"PIVOT ({status_year}) ON year USING COUNT(*) GROUP BY status ORDER BY status"))
con.execute(f"CREATE OR REPLACE TABLE status_by_year AS PIVOT ({status_year}) ON year USING COUNT(*) GROUP BY status ORDER BY status")
show(con.execute('UNPIVOT status_by_year ON "2024", "2025" INTO NAME year VALUE orders'))
show(con.execute("""
    SELECT status, year, orders FROM (UNPIVOT status_by_year ON COLUMNS(* EXCLUDE (status)) INTO NAME year VALUE orders)
    ORDER BY status, year LIMIT 4
"""))

print("# Level 2, Q2")
show(con.execute("""
    PIVOT (
        SELECT strftime(o.order_date, '%Y-%m') AS month, c.name AS category, oi.quantity * oi.unit_price_cents AS cents
        FROM order_items AS oi
        JOIN orders AS o USING (order_id)
        JOIN products AS p USING (product_id)
        JOIN categories AS c USING (category_id)
        WHERE year(o.order_date) = 2025
    )
    ON category IN ('Electronics', 'Books', 'Sports')
    USING SUM(cents)
    GROUP BY month
    ORDER BY month
    LIMIT 4
"""))

print("# Level 2, Q3")
con.execute("CREATE TEMP TABLE trades (sym VARCHAR, ts TIMESTAMP, qty INTEGER)")
con.execute("CREATE TEMP TABLE quotes (sym VARCHAR, ts TIMESTAMP, price_cents INTEGER)")
con.execute("""INSERT INTO trades VALUES ('A', '2025-01-01 10:00:05', 10), ('A', '2025-01-01 10:01:30', 5), ('B', '2025-01-01 10:00:50', 7)""")
con.execute("""INSERT INTO quotes VALUES ('A', '2025-01-01 10:00:00', 10000), ('A', '2025-01-01 10:01:00', 10150),
                                       ('B', '2025-01-01 10:00:00', 2000), ('B', '2025-01-01 10:02:00', 2100)""")
show(con.execute("""
    SELECT t.sym, t.ts AS traded_at, t.qty, q.ts AS quoted_at, q.price_cents, t.qty * q.price_cents AS value_cents
    FROM trades AS t ASOF JOIN quotes AS q ON t.sym = q.sym AND t.ts >= q.ts
    ORDER BY t.sym, t.ts
"""))

print("# Level 2, Q4")
show(con.execute("""
    SELECT name, price_cents FROM products
    WHERE price_cents > ALL (SELECT price_cents FROM products WHERE category_id = (SELECT category_id FROM categories WHERE name = 'Books'))
    ORDER BY name
"""))
rewritten = con.execute("""
    SELECT name, price_cents FROM products
    WHERE price_cents > (SELECT MAX(price_cents) FROM products WHERE category_id = (SELECT category_id FROM categories WHERE name = 'Books'))
    ORDER BY name
""").fetchall()
print(len(rewritten))
print(con.execute("""
    SELECT COUNT(*) FROM products
    WHERE price_cents > ALL (SELECT price_cents FROM products WHERE category_id = (SELECT category_id FROM categories WHERE name = 'Garden'))
""").fetchall())  # 40: the Garden category has no products, so "greater than all of nothing" is true for everyone
print(con.execute("""
    SELECT COUNT(*) FROM products
    WHERE price_cents > ANY (SELECT price_cents FROM products WHERE category_id = (SELECT category_id FROM categories WHERE name = 'Garden'))
""").fetchall())  # 0: "greater than at least one of nothing" is false

print("# Level 2, Q5")
show(con.execute("""
    SELECT name, array_to_string([w[1] FOR w IN string_split(name, ' ')], '') AS initials
    FROM employees ORDER BY employee_id LIMIT 4
"""))

print("# Level 2, Q6")
show(con.execute("SELECT COUNT(*) - COUNT(COLUMNS(*)) FROM customers"))
show(con.execute("SELECT COUNT(*) - COUNT(COLUMNS(*)) FROM products"))

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
show(con.execute("""
    SELECT language, COUNT(*) AS countries
    FROM (SELECT unnest(languages) AS language FROM read_json(?))
    GROUP BY ALL
    ORDER BY countries DESC, language
    LIMIT 10
""", [str(DATA / "countries_data.json")]))
# Plain Python: loops and a dictionary. SQL Day 11: three tables and a join. DuckDB: one query on the file.

print("# Level 3, Q2")
show(con.execute("""
    PIVOT (
        SELECT strftime(o.order_date, '%Y-%m') AS month, c.name AS category,
               oi.quantity * oi.unit_price_cents AS cents
        FROM order_items AS oi
        JOIN orders AS o USING (order_id)
        JOIN products AS p USING (product_id)
        JOIN categories AS c USING (category_id)
        WHERE year(o.order_date) = 2025 AND o.status <> 'cancelled'
    )
    ON category IN ('Electronics', 'Books', 'Sports')
    USING COALESCE(SUM(cents), 0) / 100.0
    GROUP BY month
    ORDER BY month
"""))
show(con.execute("""
    SELECT month, category, dollars FROM (
        PIVOT (
            SELECT strftime(o.order_date, '%Y-%m') AS month, c.name AS category,
                   oi.quantity * oi.unit_price_cents AS cents
            FROM order_items AS oi
            JOIN orders AS o USING (order_id)
            JOIN products AS p USING (product_id)
            JOIN categories AS c USING (category_id)
            WHERE year(o.order_date) = 2025 AND o.status <> 'cancelled'
        )
        ON category IN ('Electronics', 'Books', 'Sports')
        USING COALESCE(SUM(cents), 0) / 100.0
        GROUP BY month
    ) UNPIVOT (dollars FOR category IN (Electronics, Books, Sports))
    QUALIFY RANK() OVER (ORDER BY dollars DESC) <= 3
    ORDER BY dollars DESC
"""))
