# Day 11 reference solutions: INNER JOIN
from helpers import languages_conn, library_full_conn, shop_conn, show

shop = shop_conn()
lib = library_full_conn()
ds = languages_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
show(shop.execute("""
    SELECT o.order_id, c.first_name || ' ' || c.last_name AS customer, o.order_date
    FROM orders AS o
    INNER JOIN customers AS c ON c.customer_id = o.customer_id
    ORDER BY o.order_id
    LIMIT 5
"""))

print("# Level 1, Q2")
show(shop.execute("""
    SELECT i.order_id, p.name AS product, i.quantity
    FROM order_items AS i
    JOIN products AS p ON p.product_id = i.product_id
    ORDER BY i.order_id, p.name
    LIMIT 5
"""))

print("# Level 1, Q3")
show(shop.execute("""
    SELECT p.name AS product, c.name AS category
    FROM products AS p
    JOIN categories AS c ON c.category_id = p.category_id
    ORDER BY p.product_id
    LIMIT 8
"""))

print("# Level 1, Q4")
print(shop.execute("SELECT COUNT(*) FROM products").fetchone(),
      shop.execute("SELECT COUNT(*) FROM products AS p JOIN categories AS c ON c.category_id = p.category_id").fetchone())
# Gift Card Holder (id 39) has a NULL category_id, and NULL never equals anything, so it has no match
show(shop.execute("SELECT product_id, name FROM products WHERE category_id IS NULL"))

print("# Level 1, Q5")
show(shop.execute("""
    SELECT p.name AS product, c.name AS category
    FROM products AS p JOIN categories AS c USING (category_id)
    ORDER BY p.product_id
    LIMIT 3
"""))

print("# Level 1, Q6")
show(shop.execute("""
    SELECT p.name AS product, i.quantity, format('%.2f', i.unit_price_cents / 100.0) AS unit_price
    FROM order_items AS i JOIN products AS p ON p.product_id = i.product_id
    WHERE i.order_id = 3
    ORDER BY p.name
"""))

print("# Level 1, Q7")
show(shop.execute("""
    SELECT DISTINCT c.first_name, c.last_name
    FROM customers AS c JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE c.country = 'Canada'
    ORDER BY c.last_name, c.first_name
"""))

print("# Level 1, Q8")
show(lib.execute("""
    SELECT b.title, a.name AS author
    FROM books AS b JOIN authors AS a ON a.id = b.author_id
    ORDER BY b.title
    LIMIT 5
"""))

print("# Level 1, Q9")
show(lib.execute("""
    SELECT l.id, m.name AS member, l.loaned_on
    FROM loans AS l JOIN members AS m ON m.id = l.member_id
    ORDER BY l.id
    LIMIT 5
"""))

print("# Level 1, Q10")
show(lib.execute("""
    SELECT l.id, b.title, l.loaned_on
    FROM loans AS l JOIN books AS b ON b.id = l.book_id
    WHERE l.returned_on IS NULL
    ORDER BY l.id
"""))

print("# Level 1, Q11")
show(lib.execute("""
    SELECT b.title, a.name
    FROM books AS b JOIN authors AS a ON a.id = b.author_id
    WHERE a.name = 'Andy Weir'
    ORDER BY b.title
"""))

print("# Level 1, Q12")
# An INNER JOIN keeps only the rows that have a match on BOTH sides; rows with no partner disappear.

print("# Level 1, Q13")
try:
    shop.execute("SELECT order_id, quantity FROM orders JOIN order_items ON orders.order_id = order_items.order_id")
except Exception as e:
    print(type(e).__name__, e)
show(shop.execute("SELECT orders.order_id, quantity FROM orders JOIN order_items ON orders.order_id = order_items.order_id ORDER BY 1, 2 LIMIT 3"))

print("# Level 1, Q14")
show(shop.execute("""
    SELECT p.name, c.name AS category
    FROM products AS p JOIN categories AS c ON p.category_id = c.category_id
    WHERE c.name = 'Toys'
    ORDER BY p.name
    LIMIT 3
"""))

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
show(shop.execute("""
    SELECT c.name AS category,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) / 100.0) AS revenue
    FROM order_items AS i
    JOIN products   AS p ON p.product_id = i.product_id
    JOIN categories AS c ON c.category_id = p.category_id
    JOIN orders     AS o ON o.order_id = i.order_id
    WHERE o.status <> 'cancelled'
    GROUP BY c.category_id
    ORDER BY SUM(i.quantity * i.unit_price_cents) DESC, category
"""))

print("# Level 2, Q2")
show(shop.execute("""
    SELECT c.first_name || ' ' || c.last_name AS customer,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) / 100.0) AS spend
    FROM customers AS c
    JOIN orders      AS o ON o.customer_id = c.customer_id
    JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status <> 'cancelled'
    GROUP BY c.customer_id
    ORDER BY SUM(i.quantity * i.unit_price_cents) DESC, customer
    LIMIT 5
"""))

print("# Level 2, Q3")
show(lib.execute("""
    SELECT m.name AS member, b.title, a.name AS author, l.loaned_on
    FROM loans AS l
    JOIN members AS m ON m.id = l.member_id
    JOIN books   AS b ON b.id = l.book_id
    JOIN authors AS a ON a.id = b.author_id
    ORDER BY l.loaned_on, l.id
"""))

print("# Level 2, Q4")
show(shop.execute("""
    SELECT c.country,
           COUNT(*)                   AS joined_rows,
           COUNT(DISTINCT o.order_id) AS orders
    FROM customers AS c
    JOIN orders      AS o ON o.customer_id = c.customer_id
    JOIN order_items AS i ON i.order_id = o.order_id
    GROUP BY c.country
    ORDER BY orders DESC, c.country
"""))

print("# Level 2, Q5")
show(shop.execute("""
    SELECT DISTINCT p.name
    FROM customers AS c
    JOIN orders      AS o ON o.customer_id = c.customer_id
    JOIN order_items AS i ON i.order_id = o.order_id
    JOIN products    AS p ON p.product_id = i.product_id
    WHERE c.country = 'France'
    ORDER BY p.name
    LIMIT 8
"""))
print(shop.execute("""
    SELECT COUNT(DISTINCT p.product_id)
    FROM customers c JOIN orders o ON o.customer_id = c.customer_id
    JOIN order_items i ON i.order_id = o.order_id JOIN products p ON p.product_id = i.product_id
    WHERE c.country = 'France'
""").fetchone())

print("# Level 2, Q6")
show(shop.execute("""
    SELECT substr(o.order_date, 1, 7) AS month,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) / 100.0) AS revenue
    FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status <> 'cancelled' AND o.order_date >= '2025-01-01'
    GROUP BY month
    ORDER BY month
"""))

print("# Level 2, Q7")
# step by step: row counts after each join (a model answer for the 'build it up' habit)
steps = [
    "SELECT COUNT(*) FROM order_items",
    "SELECT COUNT(*) FROM order_items i JOIN orders o ON o.order_id = i.order_id",
    "SELECT COUNT(*) FROM order_items i JOIN orders o ON o.order_id = i.order_id JOIN products p ON p.product_id = i.product_id",
    "SELECT COUNT(*) FROM order_items i JOIN orders o ON o.order_id = i.order_id JOIN products p ON p.product_id = i.product_id JOIN categories c ON c.category_id = p.category_id",
]
print([shop.execute(s).fetchone()[0] for s in steps])

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
show(ds.execute("""
    SELECT l.name AS language, COUNT(*) AS countries
    FROM languages AS l
    JOIN country_languages AS cl ON cl.language_id = l.id
    GROUP BY l.id
    ORDER BY countries DESC, language
    LIMIT 10
"""))

print("# Level 3, Q2")
show(ds.execute("""
    SELECT c.name
    FROM countries AS c
    JOIN country_languages AS a ON a.country_id = c.id JOIN languages AS la ON la.id = a.language_id AND la.name = 'English'
    JOIN country_languages AS b ON b.country_id = c.id JOIN languages AS lb ON lb.id = b.language_id AND lb.name = 'French'
    ORDER BY c.name
"""))

print("# Level 3, Q3")
show(shop.execute("""
    SELECT c.country,
           COUNT(DISTINCT c.customer_id) AS buyers,
           COUNT(DISTINCT o.order_id)    AS orders,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) / 100.0) AS revenue
    FROM customers AS c
    JOIN orders      AS o ON o.customer_id = c.customer_id
    JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status <> 'cancelled'
    GROUP BY c.country
    ORDER BY SUM(i.quantity * i.unit_price_cents) DESC, c.country
"""))

print("# Level 3, Q4")
show(shop.execute("""
    SELECT p.name AS product, cat.name AS category,
           SUM(i.quantity)               AS units,
           COUNT(DISTINCT o.customer_id) AS buyers
    FROM order_items AS i
    JOIN orders     AS o   ON o.order_id = i.order_id
    JOIN products   AS p   ON p.product_id = i.product_id
    JOIN categories AS cat ON cat.category_id = p.category_id
    WHERE o.status <> 'cancelled'
    GROUP BY p.product_id
    ORDER BY units DESC, product
    LIMIT 5
"""))
