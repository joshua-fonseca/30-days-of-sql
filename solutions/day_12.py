# Day 12 reference solutions: outer, self and cross joins
import sqlite3

from helpers import library_full_conn, shop_conn, show

shop = shop_conn()
lib = library_full_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
show(shop.execute("""
    SELECT c.customer_id, c.first_name, c.last_name, c.country
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE o.order_id IS NULL
    ORDER BY c.customer_id
"""))

print("# Level 1, Q2")
show(shop.execute("""
    SELECT p.product_id, p.name
    FROM products AS p
    LEFT JOIN order_items AS i ON i.product_id = p.product_id
    WHERE i.order_id IS NULL
    ORDER BY p.product_id
"""))

print("# Level 1, Q3")
show(shop.execute("""
    SELECT c.category_id, c.name
    FROM categories AS c
    LEFT JOIN products AS p ON p.category_id = c.category_id
    WHERE p.product_id IS NULL
"""))

print("# Level 1, Q4")
show(shop.execute("""
    SELECT e.employee_id, e.name AS employee, e.title, m.name AS manager
    FROM employees AS e
    LEFT JOIN employees AS m ON m.employee_id = e.manager_id
    ORDER BY e.employee_id
"""))

print("# Level 1, Q5")
print(shop.execute("SELECT COUNT(*) FROM customers").fetchone(),
      shop.execute("SELECT COUNT(*) FROM customers c JOIN orders o ON o.customer_id = c.customer_id").fetchone(),
      shop.execute("SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id").fetchone(),
      shop.execute("SELECT COUNT(*), COUNT(o.order_id) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id").fetchone())

print("# Level 1, Q6")
show(shop.execute("""
    SELECT p.product_id, p.name, c.name AS category
    FROM products AS p
    LEFT JOIN categories AS c ON c.category_id = p.category_id
    WHERE c.category_id IS NULL
"""))

print("# Level 1, Q7")
show(shop.execute("""
    SELECT p.name, COALESCE(c.name, 'Uncategorised') AS category
    FROM products AS p
    LEFT JOIN categories AS c ON c.category_id = p.category_id
    ORDER BY p.product_id DESC
    LIMIT 4
"""))

print("# Level 1, Q8")
show(lib.execute("""
    SELECT b.id, b.title
    FROM books AS b
    LEFT JOIN loans AS l ON l.book_id = b.id
    WHERE l.id IS NULL
    ORDER BY b.title
"""))

print("# Level 1, Q9")
show(shop.execute("""
    SELECT e.name, e.title
    FROM employees AS e
    LEFT JOIN employees AS r ON r.manager_id = e.employee_id
    WHERE r.employee_id IS NULL
    ORDER BY e.employee_id
"""))

print("# Level 1, Q10")
print(shop.execute("""
    SELECT COUNT(*) FROM customers c
    LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'cancelled'
""").fetchone(),
shop.execute("""
    SELECT COUNT(*) FROM customers c
    LEFT JOIN orders o ON o.customer_id = c.customer_id
    WHERE o.status = 'cancelled'
""").fetchone())

print("# Level 1, Q11")
show(shop.execute("""
    SELECT c.category_id, c.name, COUNT(p.product_id) AS products
    FROM products AS p
    RIGHT JOIN categories AS c ON c.category_id = p.category_id
    GROUP BY c.category_id
    ORDER BY c.category_id
"""))

print("# Level 1, Q12")
sizes = sqlite3.connect(":memory:")
sizes.execute("CREATE TABLE sizes (size TEXT)")
sizes.execute("CREATE TABLE colours (colour TEXT)")
sizes.executemany("INSERT INTO sizes VALUES (?)", [("S",), ("M",), ("L",)])
sizes.executemany("INSERT INTO colours VALUES (?)", [("red",), ("blue",)])
show(sizes.execute("SELECT size, colour FROM sizes CROSS JOIN colours ORDER BY colour, CASE size WHEN 'S' THEN 1 WHEN 'M' THEN 2 ELSE 3 END"))

print("# Level 1, Q13")
# Bug: the WHERE condition on o.status removes the NULL rows the LEFT JOIN just produced (and customers whose
# orders are all cancelled), so the query behaves like an inner join. Put the condition in ON instead.
print(shop.execute("""
    SELECT COUNT(DISTINCT c.customer_id) FROM customers c
    LEFT JOIN orders o ON o.customer_id = c.customer_id
    WHERE o.status <> 'cancelled'
""").fetchone())
print(shop.execute("""
    SELECT COUNT(DISTINCT c.customer_id) FROM customers c
    LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.status <> 'cancelled'
""").fetchone())

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
show(shop.execute("""
    SELECT c.first_name || ' ' || c.last_name AS customer, COUNT(o.order_id) AS orders
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id
    ORDER BY orders, customer
    LIMIT 8
"""))
print(shop.execute("""
    SELECT COUNT(*) FROM (SELECT c.customer_id FROM customers c
      LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id HAVING COUNT(o.order_id) = 0)
""").fetchone())

print("# Level 2, Q2")
shop.execute("CREATE TABLE months (month TEXT)")
shop.executemany("INSERT INTO months VALUES (?)", [("2025-01",), ("2025-02",), ("2025-03",)])
show(shop.execute("""
    SELECT p.name AS product, m.month
    FROM products AS p
    CROSS JOIN months AS m
    WHERE p.product_id <= 3
    ORDER BY p.product_id, m.month
"""))
print(shop.execute("SELECT COUNT(*) FROM products CROSS JOIN months").fetchone())

print("# Level 2, Q3")
show(lib.execute("""
    SELECT m.id, m.name
    FROM members AS m
    LEFT JOIN loans AS l ON l.member_id = m.id
    WHERE l.id IS NULL
"""))

print("# Level 2, Q4")
show(shop.execute("""
    SELECT p.name AS product, c.name AS category
    FROM products AS p
    FULL OUTER JOIN categories AS c ON c.category_id = p.category_id
    WHERE p.product_id IS NULL OR c.category_id IS NULL
"""))

print("# Level 2, Q5")
show(shop.execute("""
    SELECT a.city, COUNT(*) AS pairs
    FROM customers AS a
    JOIN customers AS b ON b.city = a.city AND b.customer_id > a.customer_id
    GROUP BY a.city
    ORDER BY pairs DESC, a.city
    LIMIT 5
"""))

print("# Level 2, Q6")
show(shop.execute("""
    SELECT m.name AS manager, COUNT(e.employee_id) AS reports
    FROM employees AS m
    JOIN employees AS e ON e.manager_id = m.employee_id
    GROUP BY m.employee_id
    ORDER BY reports DESC, manager
"""))

print("# Level 2, Q7")
show(shop.execute("""
    SELECT p.name AS product, COUNT(o.order_id) AS delivered_lines
    FROM products AS p
    LEFT JOIN order_items AS i ON i.product_id = p.product_id
    LEFT JOIN orders AS o ON o.order_id = i.order_id AND o.status = 'delivered'
    GROUP BY p.product_id
    ORDER BY delivered_lines, product
    LIMIT 5
"""))

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
shop.execute("CREATE TABLE months2025 (month TEXT)")
shop.executemany("INSERT INTO months2025 VALUES (?)", [(f"2025-{m:02d}",) for m in range(1, 13)])
rows = shop.execute("""
    SELECT c.name AS category, m.month,
           format('%.2f', COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL THEN i.quantity * i.unit_price_cents END), 0) / 100.0) AS revenue
    FROM categories AS c
    CROSS JOIN months2025 AS m
    LEFT JOIN products    AS p ON p.category_id = c.category_id
    LEFT JOIN order_items AS i ON i.product_id = p.product_id
    LEFT JOIN orders      AS o ON o.order_id = i.order_id AND o.status <> 'cancelled' AND substr(o.order_date, 1, 7) = m.month
    GROUP BY c.category_id, m.month
    ORDER BY c.name, m.month
""")
show(rows)
print("# Level 3, Q1 counts")
print(shop.execute("""
    SELECT COUNT(*) FROM categories CROSS JOIN months2025
""").fetchone())
print(shop.execute("""
    SELECT COUNT(*) FROM (
    SELECT c.category_id, m.month,
           COALESCE(SUM(CASE WHEN o.order_id IS NOT NULL THEN i.quantity * i.unit_price_cents END), 0) AS cents
    FROM categories AS c
    CROSS JOIN months2025 AS m
    LEFT JOIN products    AS p ON p.category_id = c.category_id
    LEFT JOIN order_items AS i ON i.product_id = p.product_id
    LEFT JOIN orders      AS o ON o.order_id = i.order_id AND o.status <> 'cancelled' AND substr(o.order_date, 1, 7) = m.month
    GROUP BY c.category_id, m.month HAVING cents = 0)
""").fetchone())

print("# Level 3, Q2")
show(shop.execute("""
    SELECT p.product_id, p.name
    FROM products AS p
    LEFT JOIN (
        SELECT i.product_id
        FROM order_items AS i
        JOIN orders    AS o ON o.order_id = i.order_id
        JOIN customers AS c ON c.customer_id = o.customer_id
        WHERE c.country = 'France'
    ) AS fr ON fr.product_id = p.product_id
    WHERE fr.product_id IS NULL
    ORDER BY p.product_id
"""))

print("# Level 3, Q3")
show(shop.execute("""
    SELECT e.name AS employee, m.name AS manager, g.name AS grand_manager
    FROM employees AS e
    LEFT JOIN employees AS m ON m.employee_id = e.manager_id
    LEFT JOIN employees AS g ON g.employee_id = m.manager_id
    ORDER BY e.employee_id
"""))
