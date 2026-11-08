# Day 15 reference solutions: set operations and conditional aggregation
import sqlite3

from helpers import datasets_conn, library_full_conn, shop_conn, show

shop = shop_conn()
lib = library_full_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
show(shop.execute("""
    SELECT first_name || ' ' || last_name AS name FROM customers
    UNION
    SELECT name FROM employees
    ORDER BY name
    LIMIT 5
"""))
print(shop.execute("""
    SELECT COUNT(*) FROM (SELECT first_name || ' ' || last_name FROM customers UNION SELECT name FROM employees)
""").fetchone())

print("# Level 1, Q2")
print(shop.execute("SELECT COUNT(*) FROM (SELECT city FROM customers UNION ALL SELECT city FROM customers)").fetchone(),
      shop.execute("SELECT COUNT(*) FROM (SELECT city FROM customers UNION SELECT city FROM customers)").fetchone(),
      shop.execute("SELECT COUNT(DISTINCT city) FROM customers").fetchone())

print("# Level 1, Q3")
show(shop.execute("""
    SELECT product_id FROM products
    EXCEPT
    SELECT product_id FROM order_items
    ORDER BY product_id
"""))

print("# Level 1, Q4")
print(shop.execute("""
    SELECT COUNT(*) FROM (
        SELECT i.product_id FROM order_items i JOIN orders o ON o.order_id = i.order_id WHERE o.order_date < '2025-01-01'
        INTERSECT
        SELECT i.product_id FROM order_items i JOIN orders o ON o.order_id = i.order_id WHERE o.order_date >= '2025-01-01')
""").fetchone())

print("# Level 1, Q5")
show(shop.execute("""
    SELECT SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered,
           SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled
    FROM orders
"""))

print("# Level 1, Q6")
try:
    shop.execute("SELECT customer_id, first_name FROM customers UNION SELECT employee_id FROM employees")
except sqlite3.OperationalError as e:
    print(e)

print("# Level 1, Q7")
show(shop.execute("""
    SELECT name AS label, 'employee' AS kind FROM employees WHERE employee_id <= 2
    UNION ALL
    SELECT first_name, 'customer' FROM customers WHERE customer_id <= 2
    ORDER BY kind, label
"""))

print("# Level 1, Q8")
show(lib.execute("""
    SELECT name, 'member' AS role FROM members
    UNION
    SELECT name, 'author' FROM authors
    ORDER BY name
    LIMIT 6
"""))

print("# Level 1, Q9")
show(lib.execute("""
    SELECT title FROM books WHERE id IN (SELECT id FROM books EXCEPT SELECT book_id FROM loans) ORDER BY title
"""))

print("# Level 1, Q10")
show(lib.execute("""
    SELECT SUM(pages < 300) AS short,
           SUM(pages BETWEEN 300 AND 500) AS medium,
           SUM(pages > 500) AS long
    FROM books
"""))

print("# Level 1, Q11")
show(shop.execute("""
    SELECT COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
           COUNT(*) FILTER (WHERE status = 'shipped')   AS shipped,
           COUNT(*) FILTER (WHERE status = 'pending')   AS pending,
           COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
           COUNT(*) AS total
    FROM orders
"""))

print("# Level 1, Q12")
# UNION removes duplicate rows (it has to sort or hash to find them), UNION ALL keeps everything and is cheaper.
# Use UNION ALL unless you really need to remove duplicates.

print("# Level 1, Q13")
show(shop.execute("""
    SELECT email AS contact, first_name FROM customers WHERE customer_id = 2
    UNION ALL
    SELECT first_name, email FROM customers WHERE customer_id = 2
"""))
# the columns are matched by position, not by name: the second SELECT's first_name lands in the 'contact' column

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
show(shop.execute("""
    SELECT status,
           COUNT(*) FILTER (WHERE order_date < '2025-01-01') AS y2024,
           COUNT(*) FILTER (WHERE order_date >= '2025-01-01') AS y2025,
           COUNT(*) AS total
    FROM orders
    GROUP BY status
    ORDER BY total DESC
"""))
show(shop.execute("""
    SELECT status,
           SUM(CASE WHEN substr(order_date, 1, 4) = '2024' THEN 1 ELSE 0 END) AS y2024,
           SUM(CASE WHEN substr(order_date, 1, 4) = '2025' THEN 1 ELSE 0 END) AS y2025,
           COUNT(*) AS total
    FROM orders GROUP BY status ORDER BY total DESC
"""))

print("# Level 2, Q2")
python_buyers = """
    SELECT o.customer_id FROM orders o JOIN order_items i ON i.order_id = o.order_id
    JOIN products p ON p.product_id = i.product_id WHERE p.name = '{}'
"""
inter = shop.execute(python_buyers.format("Python Crash Course") + " INTERSECT " + python_buyers.format("SQL for Data Analysis") + " ORDER BY 1").fetchall()
print(inter)
join = shop.execute("""
    SELECT DISTINCT a.customer_id
    FROM (SELECT o.customer_id FROM orders o JOIN order_items i ON i.order_id = o.order_id JOIN products p ON p.product_id = i.product_id WHERE p.name = 'Python Crash Course') AS a
    JOIN (SELECT o.customer_id FROM orders o JOIN order_items i ON i.order_id = o.order_id JOIN products p ON p.product_id = i.product_id WHERE p.name = 'SQL for Data Analysis') AS b
      ON b.customer_id = a.customer_id
    ORDER BY 1
""").fetchall()
print(join == inter, len(join))
having = shop.execute("""
    SELECT o.customer_id FROM orders o JOIN order_items i ON i.order_id = o.order_id JOIN products p ON p.product_id = i.product_id
    WHERE p.name IN ('Python Crash Course', 'SQL for Data Analysis')
    GROUP BY o.customer_id HAVING COUNT(DISTINCT p.name) = 2 ORDER BY 1
""").fetchall()
print(having == inter)

print("# Level 2, Q3")
show(shop.execute("""
    SELECT p.name AS product, c.name AS category
    FROM products AS p LEFT JOIN categories AS c ON c.category_id = p.category_id
    WHERE c.category_id IS NULL
    UNION ALL
    SELECT NULL, c.name
    FROM categories AS c LEFT JOIN products AS p ON p.category_id = c.category_id
    WHERE p.product_id IS NULL
"""))

print("# Level 2, Q4")
show(shop.execute("""
    SELECT c.country,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) FILTER (WHERE cat.name = 'Books') / 100.0) AS books,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) FILTER (WHERE cat.name = 'Toys') / 100.0) AS toys,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) FILTER (WHERE cat.name NOT IN ('Books', 'Toys')) / 100.0) AS other,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) / 100.0) AS total
    FROM customers AS c
    JOIN orders      AS o   ON o.customer_id = c.customer_id
    JOIN order_items AS i   ON i.order_id = o.order_id
    JOIN products    AS p   ON p.product_id = i.product_id
    JOIN categories  AS cat ON cat.category_id = p.category_id
    WHERE o.status <> 'cancelled'
    GROUP BY c.country
    ORDER BY SUM(i.quantity * i.unit_price_cents) DESC
"""))

print("# Level 2, Q5")
show(shop.execute("""
    SELECT 'customers' AS what, COUNT(*) AS n FROM customers
    UNION ALL SELECT 'products', COUNT(*) FROM products
    UNION ALL SELECT 'orders', COUNT(*) FROM orders
    UNION ALL SELECT 'order lines', COUNT(*) FROM order_items
    UNION ALL SELECT 'employees', COUNT(*) FROM employees
"""))

print("# Level 2, Q6")
show(shop.execute("""
    SELECT substr(order_date, 1, 7) AS month,
           COUNT(*) AS orders,
           COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
           round(100.0 * COUNT(*) FILTER (WHERE status = 'cancelled') / COUNT(*), 1) AS cancelled_pct
    FROM orders
    WHERE order_date >= '2025-01-01'
    GROUP BY month
    ORDER BY month
"""))

print("# Level 2, Q7")
# a MySQL-style FULL OUTER JOIN: LEFT JOIN UNION RIGHT JOIN -- here: every customer and every order, side by side
print(shop.execute("""
    SELECT COUNT(*) FROM (
      SELECT c.customer_id, o.order_id FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id
      UNION
      SELECT c.customer_id, o.order_id FROM orders o LEFT JOIN customers c ON c.customer_id = o.customer_id)
""").fetchone(), shop.execute("""
    SELECT COUNT(*) FROM customers c FULL OUTER JOIN orders o ON o.customer_id = c.customer_id""").fetchone())

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
hn = datasets_conn()
show(hn.execute("""
    SELECT COUNT(*) FILTER (WHERE lower(title) LIKE '%python%')     AS python,
           COUNT(*) FILTER (WHERE lower(title) LIKE '%javascript%') AS javascript,
           COUNT(*) FILTER (WHERE lower(title) LIKE '%java%' AND lower(title) NOT LIKE '%javascript%') AS java_only
    FROM hn_posts
"""))
show(hn.execute("""
    SELECT SUM(lower(title) LIKE '%python%') AS python,
           SUM(lower(title) LIKE '%javascript%') AS javascript,
           SUM(lower(title) LIKE '%java%' AND lower(title) NOT LIKE '%javascript%') AS java_only
    FROM hn_posts
"""))

print("# Level 3, Q2")
show(shop.execute("""
    SELECT cat.name AS category,
           COUNT(DISTINCT o.order_id) FILTER (WHERE o.status = 'delivered') AS delivered,
           COUNT(DISTINCT o.order_id) FILTER (WHERE o.status = 'cancelled') AS cancelled,
           COUNT(DISTINCT o.order_id) AS orders,
           format('%.1f', 100.0 * COUNT(DISTINCT o.order_id) FILTER (WHERE o.status = 'cancelled') / COUNT(DISTINCT o.order_id)) AS cancelled_pct
    FROM order_items AS i
    JOIN orders     AS o   ON o.order_id = i.order_id
    JOIN products   AS p   ON p.product_id = i.product_id
    JOIN categories AS cat ON cat.category_id = p.category_id
    GROUP BY cat.category_id
    ORDER BY cancelled_pct DESC, category
"""))

print("# Level 3, Q3")
show(shop.execute("""
    WITH y2024 AS (SELECT DISTINCT customer_id FROM orders WHERE order_date <  '2025-01-01'),
         y2025 AS (SELECT DISTINCT customer_id FROM orders WHERE order_date >= '2025-01-01')
    SELECT 'both years'  AS segment, COUNT(*) AS customers FROM (SELECT * FROM y2024 INTERSECT SELECT * FROM y2025)
    UNION ALL
    SELECT 'lost (2024 only)', COUNT(*) FROM (SELECT * FROM y2024 EXCEPT SELECT * FROM y2025)
    UNION ALL
    SELECT 'new (2025 only)',  COUNT(*) FROM (SELECT * FROM y2025 EXCEPT SELECT * FROM y2024)
    UNION ALL
    SELECT 'ever ordered', COUNT(*) FROM (SELECT * FROM y2024 UNION SELECT * FROM y2025)
"""))
