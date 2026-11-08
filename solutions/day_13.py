# Day 13 reference solutions: subqueries
from helpers import datasets_conn, languages_conn, library_full_conn, shop_conn, show

shop = shop_conn()
lib = library_full_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
print(shop.execute("SELECT format('%.2f', AVG(price_cents) / 100.0) FROM products").fetchone())
show(shop.execute("""
    SELECT name, format('%.2f', price_cents / 100.0) AS price
    FROM products
    WHERE price_cents > (SELECT AVG(price_cents) FROM products)
    ORDER BY price_cents DESC, name
    LIMIT 5
"""))
print(shop.execute("SELECT COUNT(*) FROM products WHERE price_cents > (SELECT AVG(price_cents) FROM products)").fetchone())

print("# Level 1, Q2")
show(shop.execute("""
    SELECT first_name, last_name
    FROM customers
    WHERE customer_id IN (
        SELECT o.customer_id
        FROM orders AS o
        JOIN order_items AS i ON i.order_id = o.order_id
        WHERE i.product_id = (SELECT product_id FROM products WHERE name = 'Python Crash Course')
    )
    ORDER BY last_name, first_name
    LIMIT 6
"""))
print(shop.execute("""
    SELECT COUNT(*) FROM customers WHERE customer_id IN (
        SELECT o.customer_id FROM orders o JOIN order_items i ON i.order_id = o.order_id
        WHERE i.product_id = (SELECT product_id FROM products WHERE name = 'Python Crash Course'))
""").fetchone())

print("# Level 1, Q3")
a = shop.execute("""
    SELECT c.customer_id FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id
    WHERE o.order_id IS NULL ORDER BY c.customer_id""").fetchall()
b = shop.execute("""
    SELECT customer_id FROM customers WHERE customer_id NOT IN (SELECT customer_id FROM orders) ORDER BY customer_id""").fetchall()
c = shop.execute("""
    SELECT customer_id FROM customers c WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id)
    ORDER BY customer_id""").fetchall()
print(len(a), len(b), len(c), a == b == c)
print([r[0] for r in a])

print("# Level 1, Q4")
show(shop.execute("""
    SELECT name, price_cents FROM products WHERE price_cents = (SELECT MAX(price_cents) FROM products)
"""))

print("# Level 1, Q5")
print(shop.execute("""
    SELECT COUNT(*) FROM orders WHERE customer_id IN (SELECT customer_id FROM customers WHERE country = 'France')
""").fetchone())

print("# Level 1, Q6")
show(shop.execute("""
    SELECT c.first_name, c.last_name
    FROM customers AS c
    WHERE EXISTS (SELECT 1 FROM orders AS o WHERE o.customer_id = c.customer_id AND o.status = 'pending')
    ORDER BY c.last_name, c.first_name
    LIMIT 5
"""))

print("# Level 1, Q7")
show(lib.execute("""
    SELECT title, pages FROM books WHERE pages > (SELECT AVG(pages) FROM books) ORDER BY pages DESC, title
"""))

print("# Level 1, Q8")
show(lib.execute("""
    SELECT name FROM members
    WHERE id IN (SELECT l.member_id FROM loans l JOIN books b ON b.id = l.book_id WHERE b.title = 'Dune')
    ORDER BY name
"""))

print("# Level 1, Q9")
show(lib.execute("""
    SELECT title FROM books b WHERE NOT EXISTS (SELECT 1 FROM loans l WHERE l.book_id = b.id) ORDER BY title
"""))

print("# Level 1, Q10")
# Uncorrelated: the inner query does not mention the outer one; it runs once.
# Correlated: the inner query uses a column of the current outer row, so it conceptually runs once per outer row.

print("# Level 1, Q11")
print(shop.execute("""
    SELECT AVG(n) FROM (SELECT COUNT(*) AS n FROM orders GROUP BY customer_id)
""").fetchone())
print(shop.execute("""
    SELECT ROUND(AVG(n), 2) FROM (SELECT COUNT(*) AS n FROM orders GROUP BY customer_id)
""").fetchone())

print("# Level 1, Q12")
show(shop.execute("""
    SELECT name, price_cents FROM products
    WHERE price_cents > (SELECT MAX(price_cents) FROM products WHERE category_id = (SELECT category_id FROM categories WHERE name = 'Books'))
    ORDER BY price_cents DESC, name
"""))

print("# Level 1, Q13")
# = ANY (...) is IN (...)
show(shop.execute("""
    SELECT name FROM products
    WHERE category_id IN (SELECT category_id FROM categories WHERE name IN ('Toys', 'Garden'))
    ORDER BY name
"""))

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
show(shop.execute("""
    SELECT p.name, c.name AS category, p.price_cents,
           (SELECT CAST(ROUND(AVG(p2.price_cents)) AS INTEGER) FROM products AS p2 WHERE p2.category_id = p.category_id) AS category_avg
    FROM products AS p
    JOIN categories AS c ON c.category_id = p.category_id
    WHERE p.category_id <= 2
    ORDER BY p.product_id
"""))
show(shop.execute("""
    SELECT p.name, p.price_cents, c.name AS category
    FROM products AS p JOIN categories AS c ON c.category_id = p.category_id
    WHERE p.price_cents > (SELECT AVG(p2.price_cents) FROM products AS p2 WHERE p2.category_id = p.category_id)
    ORDER BY p.product_id
    LIMIT 5
"""))

print("# Level 2, Q2")
show(shop.execute("""
    SELECT t.order_id, t.customer_id, t.total_cents, CAST(ROUND(a.avg_cents) AS INTEGER) AS customer_avg
    FROM (SELECT o.order_id, o.customer_id, SUM(i.quantity * i.unit_price_cents) AS total_cents
          FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id GROUP BY o.order_id) AS t
    JOIN (SELECT customer_id, AVG(total_cents) AS avg_cents
          FROM (SELECT o.customer_id, SUM(i.quantity * i.unit_price_cents) AS total_cents
                FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id GROUP BY o.order_id)
          GROUP BY customer_id) AS a ON a.customer_id = t.customer_id
    WHERE t.total_cents > a.avg_cents
    ORDER BY t.total_cents - a.avg_cents DESC, t.order_id
    LIMIT 5
"""))

print("# Level 2, Q3")
print(shop.execute("""
    SELECT COUNT(*) FROM categories WHERE category_id NOT IN (SELECT category_id FROM products)
""").fetchone())
show(shop.execute("""
    SELECT category_id, name FROM categories
    WHERE category_id NOT IN (SELECT category_id FROM products WHERE category_id IS NOT NULL)
"""))
show(shop.execute("""
    SELECT c.category_id, c.name FROM categories c
    WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.category_id = c.category_id)
"""))

print("# Level 2, Q4")
show(shop.execute("""
    SELECT c.first_name || ' ' || c.last_name AS customer,
           format('%.2f', s.spend_cents / 100.0) AS spend
    FROM (SELECT o.customer_id, SUM(i.quantity * i.unit_price_cents) AS spend_cents
          FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
          WHERE o.status <> 'cancelled' GROUP BY o.customer_id) AS s
    JOIN customers AS c ON c.customer_id = s.customer_id
    WHERE s.spend_cents > (SELECT AVG(spend_cents) FROM
        (SELECT SUM(i.quantity * i.unit_price_cents) AS spend_cents
         FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
         WHERE o.status <> 'cancelled' GROUP BY o.customer_id))
    ORDER BY s.spend_cents DESC, customer
    LIMIT 5
"""))

print("# Level 2, Q5")
show(shop.execute("""
    SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer,
           (SELECT MAX(o.order_date) FROM orders AS o WHERE o.customer_id = c.customer_id) AS last_order
    FROM customers AS c
    WHERE c.customer_id BETWEEN 3 AND 8
    ORDER BY c.customer_id
"""))

print("# Level 2, Q6")
show(shop.execute("""
    SELECT c.name
    FROM categories AS c
    WHERE EXISTS (
        SELECT 1 FROM products AS p
        WHERE p.category_id = c.category_id
          AND NOT EXISTS (SELECT 1 FROM order_items AS i WHERE i.product_id = p.product_id))
    ORDER BY c.name
"""))

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
lang = languages_conn()
show(lang.execute("""
    SELECT c.name, c.population
    FROM countries AS c
    WHERE c.id IN (SELECT cl.country_id FROM country_languages cl JOIN languages g ON g.id = cl.language_id WHERE g.name = 'English')
      AND c.population > (SELECT AVG(c2.population)
                          FROM countries AS c2
                          JOIN country_languages AS cl2 ON cl2.country_id = c2.id
                          JOIN languages AS g2 ON g2.id = cl2.language_id
                          WHERE g2.name = 'English')
    ORDER BY c.population DESC, c.name
"""))
print(lang.execute("""
    SELECT CAST(AVG(c2.population) AS INTEGER) FROM countries c2
    JOIN country_languages cl2 ON cl2.country_id = c2.id JOIN languages g2 ON g2.id = cl2.language_id WHERE g2.name = 'English'
""").fetchone())

print("# Level 3, Q2")
hn = datasets_conn()
print(hn.execute("SELECT ROUND(AVG(num_points), 2) FROM hn_posts").fetchone())
show(hn.execute("""
    SELECT author, COUNT(*) AS posts, ROUND(AVG(num_points), 2) AS avg_points
    FROM hn_posts
    GROUP BY author
    HAVING COUNT(*) >= 10 AND AVG(num_points) > (SELECT AVG(num_points) FROM hn_posts)
    ORDER BY avg_points DESC, author
    LIMIT 10
"""))

print("# Level 3, Q3")
show(shop.execute("""
    SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer
    FROM customers AS c
    WHERE NOT EXISTS (
        SELECT 1 FROM products AS p
        WHERE p.category_id = (SELECT category_id FROM categories WHERE name = 'Books')
          AND NOT EXISTS (
              SELECT 1 FROM order_items AS i JOIN orders AS o ON o.order_id = i.order_id
              WHERE o.customer_id = c.customer_id AND i.product_id = p.product_id))
"""))
