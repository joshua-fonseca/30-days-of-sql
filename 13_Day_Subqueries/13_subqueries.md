<div align="center">
  <h1> 30 Days Of SQL: Day 13 - Subqueries</h1>
</div>

[<< Day 12](../12_Day_Outer_self_cross_joins/12_outer_self_cross_joins.md) | [Day 14 >>](../14_Day_CTEs_and_temp_tables/14_ctes_and_temp_tables.md)

- [Day 13](#day-13)
  - [What Is a Subquery?](#what-is-a-subquery)
  - [Scalar Subqueries](#scalar-subqueries)
  - [Subqueries with IN and NOT IN](#subqueries-with-in-and-not-in)
    - [IN](#in)
    - [The NOT IN Trap](#the-not-in-trap)
  - [EXISTS and NOT EXISTS](#exists-and-not-exists)
  - [Correlated Subqueries](#correlated-subqueries)
    - [Slow Motion: What "For Each Row" Means](#slow-motion-what-for-each-row-means)
    - [A Subquery in the SELECT List](#a-subquery-in-the-select-list)
  - [Subqueries in FROM (Derived Tables)](#subqueries-in-from-derived-tables)
  - [Subquery or Join?](#subquery-or-join)
  - [ANY and ALL](#any-and-all)
  - [ Exercises: Day 13](#exercises-day-13)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 13

## What Is a Subquery?

A **subquery** is a `SELECT` written inside another statement, in parentheses. The inner query runs first and hands its result to the outer query, like a calculation in brackets in school maths. You can ask: "which products cost more than the
average product?" That is really two questions in one: *what is the average?* and then *which are above it?* A subquery lets you ask both in a single statement.

Subqueries come in four shapes, depending on what they return and where they are used:

| Shape | Returns | Used |
|---|---|---|
| scalar subquery | one value | anywhere a value fits: `WHERE price > (...)`, or in `SELECT` |
| list subquery | one column, many rows | after `IN` / `NOT IN` |
| `EXISTS` subquery | yes or no | after `EXISTS` / `NOT EXISTS` |
| derived table | a whole table | in `FROM` |

All the examples use `shop.db` from Day 11.

```py
import sqlite3
from helpers import show

conn = sqlite3.connect('data/shop.db')
```

## Scalar Subqueries

A subquery that returns exactly **one row with one column** can be used as a plain value. Step one, the inner question on its own:

```py
print(conn.execute('SELECT AVG(price_cents) FROM products').fetchone())
# (3364.0,)
```

The average is about 3364 cents. Step two would be to paste that number into a `WHERE`. But the number could change tomorrow, and pasting numbers into code is how bugs happen. Put the query itself in the brackets:

```sql
-- syntax
SELECT columns
FROM table_name
WHERE column > (SELECT AVG(column) FROM table_name);
```

```py
show(conn.execute('''
    SELECT name, format('%.2f', price_cents / 100.0) AS price
    FROM products
    WHERE price_cents > (SELECT AVG(price_cents) FROM products)
    ORDER BY price_cents DESC, name
    LIMIT 5
'''))
```

```sh
name                         price
---------------------------  ------
Noise-Cancelling Headphones  149.99
Running Shoes                89.99
Denim Jacket                 79.99
Chef's Knife                 69.99
Bluetooth Speaker            59.99
(5 rows)
```

A scalar subquery can also be used in the `SELECT` list, to show a value next to every row:

```py
show(conn.execute('''
    SELECT name, price_cents,
           (SELECT MAX(price_cents) FROM products) - price_cents AS cheaper_than_max_by
    FROM products
    ORDER BY product_id
    LIMIT 3
'''))
```

```sh
name               price_cents  cheaper_than_max_by
-----------------  -----------  -------------------
Wireless Mouse     2499         12500
USB-C Cable        999          14000
Bluetooth Speaker  5999         9000
(3 rows)
```

Two things to remember. If a scalar subquery returns **no rows**, its value is `NULL`. If it returns **several rows**, SQLite quietly takes the first one (other databases raise an error), which hides bugs, so make sure the inner query really can only return one row.

## Subqueries with IN and NOT IN

### IN

You met `IN (1, 2, 3)` with a hand-written list on Day 5. The list can also come from a subquery: "customers whose id appears in the orders table".

```sql
-- syntax
SELECT columns
FROM table_a
WHERE column IN (SELECT column FROM table_b WHERE ...);
```

Which customers have ordered a Webcam? First find the product, then the orders, then the customers, one subquery inside the next:

```py
show(conn.execute('''
    SELECT first_name, last_name
    FROM customers
    WHERE customer_id IN (
        SELECT o.customer_id
        FROM orders AS o
        JOIN order_items AS i ON i.order_id = o.order_id
        WHERE i.product_id = (SELECT product_id FROM products WHERE name = 'Webcam')
    )
    ORDER BY last_name, first_name
    LIMIT 5
'''))
```

```sh
first_name  last_name
----------  ---------
Emma        Anderson
Sam         Anderson
Mia         Baker
Lena        Green
Sam         Khan
(5 rows)
```

Read it from the inside out: the innermost query finds the Webcam's id; the middle one lists the customers who ordered it; the outer one prints their names. Notice that each customer appears at most once, even if they
bought the Webcam three times. That is one difference from a join (more below).

### The NOT IN Trap

`NOT IN` finds rows that are **not** in the list, for example the categories that have no products:

```py
show(conn.execute('''
    SELECT name FROM categories
    WHERE category_id NOT IN (SELECT category_id FROM products)
'''))
```

```sh
name
----
(0 rows)
```

Zero rows? But the Garden category has no products (Day 12 found it). What went wrong? One product has `category_id = NULL`. So the list is `(1, 2, ..., 7, NULL)`. For Garden, `8 NOT IN (1, ..., 7, NULL)` means
`8 <> 1 AND ... AND 8 <> 7 AND 8 <> NULL`. The last test is `NULL` (Day 5's three-valued logic), so the whole `AND` chain is never `TRUE`, and the row is rejected.

**Common mistake:** `NOT IN` returns nothing at all whenever the subquery's list contains a `NULL`. Two fixes. Either keep the `NULL`s out of the list:

```py
show(conn.execute('''
    SELECT name FROM categories
    WHERE category_id NOT IN (SELECT category_id FROM products WHERE category_id IS NOT NULL)
'''))
```

```sh
name
------
Garden
(1 row)
```

or use `NOT EXISTS`, which is not fooled by `NULL`. That is next.

## EXISTS and NOT EXISTS

`EXISTS (subquery)` is true if the subquery returns **at least one row**. It does not care what the columns are, only whether there is a row, so the convention is to write `SELECT 1`.

```sql
-- syntax
SELECT columns
FROM table_a
WHERE EXISTS (SELECT 1 FROM table_b WHERE table_b.key = table_a.key);

SELECT columns
FROM table_a
WHERE NOT EXISTS (SELECT 1 FROM table_b WHERE table_b.key = table_a.key);
```

Customers with at least one pending order:

```py
show(conn.execute('''
    SELECT c.first_name, c.last_name
    FROM customers AS c
    WHERE EXISTS (
        SELECT 1 FROM orders AS o
        WHERE o.customer_id = c.customer_id AND o.status = 'pending'
    )
    ORDER BY c.last_name, c.first_name
    LIMIT 5
'''))
```

```sh
first_name  last_name
----------  ---------
Omar        Allen
Emma        Anderson
Priya       Brown
Diego       Clark
Lena        Green
(5 rows)
```

And the categories without products, the safe way:

```py
show(conn.execute('''
    SELECT c.name
    FROM categories AS c
    WHERE NOT EXISTS (SELECT 1 FROM products AS p WHERE p.category_id = c.category_id)
'''))
```

```sh
name
------
Garden
(1 row)
```

So there are three ways to find "rows with no partner": `LEFT JOIN ... IS NULL` (Day 12), `NOT IN` (dangerous with `NULL`s), and `NOT EXISTS`. The first and third are safe. Use `NOT EXISTS` when the intent is "there is no such row", because it
reads like the question you are asking.

## Correlated Subqueries

### Slow Motion: What "For Each Row" Means

Look again at the `EXISTS` examples: the inner query mentions `c.customer_id`, a column of the **outer** query. That is a **correlated subquery**: it cannot run alone, because it depends on the outer row. An ordinary ("uncorrelated") subquery runs once; a correlated one is,
conceptually, run once **for every row of the outer query**.

Here is the same idea as a Python loop, which you already know how to read:

```py
result = []
for customer in customers:                     # the outer query: one row at a time
    orders = [o for o in all_orders            # the inner query, using THIS customer's id
              if o.customer_id == customer.customer_id and o.status == 'pending']
    if len(orders) > 0:                        # EXISTS
        result.append(customer)
```

Let's run that slow motion for three customers by hand:

```py
for cid, name in conn.execute('SELECT customer_id, first_name FROM customers WHERE customer_id IN (4, 5, 7) ORDER BY 1').fetchall():
    n = conn.execute("SELECT COUNT(*) FROM orders WHERE customer_id = ? AND status = 'pending'", (cid,)).fetchone()[0]
    print(cid, name, 'pending orders:', n, '->', 'kept' if n > 0 else 'dropped')
```

```sh
4 Noah pending orders: 0 -> dropped
5 Sam pending orders: 0 -> dropped
7 Sam pending orders: 3 -> kept
```

The database does not literally loop like this (it has clever shortcuts and indexes, Day 21), but the **meaning** is exactly this. Reading a correlated subquery as "for each outer row, ask this question" is the key to understanding it.

### A Subquery in the SELECT List

A correlated scalar subquery in the `SELECT` list is the compact way to add one computed value per row, such as "each product next to the average price of **its own category**":

```py
show(conn.execute('''
    SELECT p.name, p.price_cents,
           (SELECT CAST(AVG(p2.price_cents) AS INTEGER)
            FROM products AS p2
            WHERE p2.category_id = p.category_id) AS category_avg
    FROM products AS p
    WHERE p.category_id = 2
    ORDER BY p.product_id
'''))
```

```sh
name                      price_cents  category_avg
------------------------  -----------  ------------
Python Crash Course       3999         3215
SQL for Data Analysis     4499         3215
The Pragmatic Programmer  4999         3215
Sci-Fi Anthology          1799         3215
Cookbook Basics           2499         3215
Mystery Novel             1499         3215
(6 rows)
```

For the first product (a book) the inner query averages the prices of all products with the same `category_id` as that product. The same filter in `WHERE` finds the above-average ones:

```py
show(conn.execute('''
    SELECT p.name, p.price_cents
    FROM products AS p
    WHERE p.category_id = 2
      AND p.price_cents > (SELECT AVG(p2.price_cents) FROM products AS p2 WHERE p2.category_id = p.category_id)
    ORDER BY p.product_id
'''))
```

```sh
name                      price_cents
------------------------  -----------
Python Crash Course       3999
SQL for Data Analysis     4499
The Pragmatic Programmer  4999
(3 rows)
```

Notice the aliases: the same table appears twice (`p` outside, `p2` inside), just like in a self join. Without them, SQL could not tell which `category_id` is which.

## Subqueries in FROM (Derived Tables)

A subquery in `FROM` produces a temporary table that the outer query treats like any other table. It is the way to **aggregate twice**: "the average of the per-customer order counts" needs the counts first.

```sql
-- syntax
SELECT columns
FROM (SELECT ... FROM ... GROUP BY ...) AS alias
WHERE ...;
```

```py
print(conn.execute('''
    SELECT ROUND(AVG(n), 2)
    FROM (SELECT COUNT(*) AS n FROM orders GROUP BY customer_id)
''').fetchone())
# (7.39,)
```

The inner query gives one row per customer who has orders, with that customer's order count `n`. The outer one averages those counts. SQLite lets you omit the alias, but most databases **require** one, so always write `AS alias`.

Derived tables can be joined, too. This shows each customer's spend next to their name, and keeps only those above the average spend (a subquery in `FROM`, one in `WHERE`):

```py
show(conn.execute('''
    SELECT c.first_name || ' ' || c.last_name AS customer, s.spend_cents
    FROM (SELECT o.customer_id, SUM(i.quantity * i.unit_price_cents) AS spend_cents
          FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
          GROUP BY o.customer_id) AS s
    JOIN customers AS c ON c.customer_id = s.customer_id
    WHERE s.spend_cents > (SELECT AVG(spend_cents) FROM
                            (SELECT SUM(i.quantity * i.unit_price_cents) AS spend_cents
                             FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
                             GROUP BY o.customer_id))
    ORDER BY s.spend_cents DESC, customer
    LIMIT 3
'''))
```

```sh
customer     spend_cents
-----------  -----------
Lena Green   223857
Ines Martin  218207
Priya Brown  215530
(3 rows)
```

It works, but you must admit the same inner query is written twice, and it is getting hard to read. That is exactly what tomorrow's **CTEs** fix.

## Subquery or Join?

Many problems can be solved both ways. A few rules of thumb:

| Situation | Better tool |
|---|---|
| you need columns from the other table in the result | **join** (a subquery in `WHERE` cannot show its columns) |
| you only need to *filter* by existence in another table | `EXISTS` / `IN` (no duplicate rows to worry about) |
| the other table has several matches per row and you want each row once | `EXISTS` / `IN`, or a join with `DISTINCT` |
| "rows with no match" | `NOT EXISTS` or `LEFT JOIN ... IS NULL` |
| compare with an aggregate (average, maximum) | scalar subquery |
| aggregate the result of an aggregate | derived table (or a CTE) |

The two filters below return the same customers. The join needs `DISTINCT` because a customer with many orders would otherwise appear many times; `EXISTS` has no such problem.

```py
a = conn.execute('''
    SELECT DISTINCT c.customer_id FROM customers AS c
    JOIN orders AS o ON o.customer_id = c.customer_id AND o.status = 'cancelled'
    ORDER BY c.customer_id
''').fetchall()
b = conn.execute('''
    SELECT c.customer_id FROM customers AS c
    WHERE EXISTS (SELECT 1 FROM orders AS o WHERE o.customer_id = c.customer_id AND o.status = 'cancelled')
    ORDER BY c.customer_id
''').fetchall()
print(len(a), a == b)
# 22 True
```

Modern databases usually optimise both forms to the same plan, so choose the one that reads best.

## ANY and ALL

Standard SQL has two more operators that compare a value with a whole list: `> ALL (subquery)` means "greater than every value" and `= ANY (subquery)` means "equal to at least one value". **SQLite does not have them**, but you will meet them in other
databases and tutorials (and in DuckDB on Day 25). Luckily they are easy to rewrite:

| Standard SQL | SQLite rewrite |
|---|---|
| `x > ALL (SELECT v ...)` | `x > (SELECT MAX(v) ...)` |
| `x < ALL (SELECT v ...)` | `x < (SELECT MIN(v) ...)` |
| `x > ANY (SELECT v ...)` | `x > (SELECT MIN(v) ...)` |
| `x = ANY (SELECT v ...)` | `x IN (SELECT v ...)` |
| `x <> ALL (SELECT v ...)` | `x NOT IN (SELECT v ...)` (mind the `NULL`s) |

Products that cost more than **every** book:

```py
show(conn.execute('''
    SELECT name, price_cents
    FROM products
    WHERE price_cents > (SELECT MAX(price_cents)
                         FROM products
                         WHERE category_id = (SELECT category_id FROM categories WHERE name = 'Books'))
    ORDER BY price_cents DESC, name
    LIMIT 3
'''))
```

```sh
name                         price_cents
---------------------------  -----------
Noise-Cancelling Headphones  14999
Running Shoes                8999
Denim Jacket                 7999
(3 rows)
```

> **In other databases:** `ANY`, `SOME` and `ALL` work in PostgreSQL, MySQL, SQL Server and Oracle (`> ALL (...)` is how W3Schools teaches it). Also, in some databases a derived table must have an alias, and `LIMIT` inside an `IN` subquery is not allowed in MySQL. SQLite is more relaxed.

Queries inside queries: you can now answer questions that depend on the answer to another question. Next, do some exercises.

## Exercises: Day 13

### Exercises: Level 1

Questions 7 to 9 use your `00_practice/library.db`; the others use `shop.db`.

1. Show the average product price in dollars. Then list the 5 most expensive products that cost more than average, and count how many products are above average.

   ```sh
   ('33.64',)
   name                         price
   ---------------------------  ------
   Noise-Cancelling Headphones  149.99
   Running Shoes                89.99
   Denim Jacket                 79.99
   Chef's Knife                 69.99
   Bluetooth Speaker            59.99
   (5 rows)
   (15,)
   ```

2. Which customers have ordered "Python Crash Course"? Show the first 6 by last name, then first name, and print how many there are in total. Use `IN` with a subquery, and look the product id up with another subquery instead of typing it.

   ```sh
   first_name  last_name
   ----------  ---------
   Sam         Anderson
   Mia         Baker
   Priya       Brown
   Sam         Khan
   Amara       Kim
   Freya       Kim
   (6 rows)
   (12,)
   ```

3. Find the customers with no orders **three ways**: `LEFT JOIN ... IS NULL`, `NOT IN` and `NOT EXISTS`. Print the number each way gives, whether the three lists are identical, and the ids.

   ```sh
   6 6 6 True
   [5, 17, 23, 36, 44, 58]
   ```

4. Which product is the most expensive? Use `price_cents = (SELECT MAX(...))` and not `ORDER BY ... LIMIT 1`. What is the difference when two products share the top price?
5. How many orders were placed by customers from France? (`IN` with a subquery on `customers`.)

   ```sh
   (74,)
   ```

6. List 5 customers (by last name, then first name) with at least one pending order, using `EXISTS`.
7. Library: list the books with more pages than the average, longest first.

   ```sh
   title                 pages
   --------------------  -----
   The Name of the Wind  662
   Dune                  612
   Project Hail Mary     476
   Emma                  474
   Clean Code            464
   (5 rows)
   ```

8. Library: which members have borrowed "Dune"? Use `IN`.
9. Library: which books were never loaned? Use `NOT EXISTS`.

   ```sh
   title
   --------------------
   Brave New World
   Emma
   Project Hail Mary
   The Name of the Wind
   (4 rows)
   ```

10. In your own words: what is the difference between a correlated and an uncorrelated subquery? Which of the subqueries above in this exercise list are correlated?
11. What is the average number of orders per customer *who has ordered*? (A derived table in `FROM`.) Round to two decimals. Then explain why the number would be smaller if you divided the total number of orders by all 60 customers.

    ```sh
    (7.388888888888889,)
    (7.39,)
    ```

12. List the products that cost more than **every** product in the Books category (a rewrite of `> ALL`), most expensive first.

    ```sh
    name                         price_cents
    ---------------------------  -----------
    Noise-Cancelling Headphones  14999
    Running Shoes                8999
    Denim Jacket                 7999
    Chef's Knife                 6999
    Bluetooth Speaker            5999
    Rain Coat                    5999
    (6 rows)
    ```

13. List the products in the Toys or Garden categories, alphabetically, using a rewrite of `= ANY` (`IN` with a subquery on `categories`).

    ```sh
    name
    --------------------
    Board Game Night
    Building Blocks Set
    Jigsaw Puzzle 1000pc
    Mystery Box
    Remote Control Car
    (5 rows)
    ```

### Exercises: Level 2

1. For the products of the first two categories (ids 1 and 2), show the name, the category name, the price in cents and the average price of the product's category (rounded to a whole number of cents), using a correlated subquery. Then list, for all categories, the first five products
   priced above their category average.

   ```sh
   name                         category     price_cents  category_avg
   ---------------------------  -----------  -----------  ------------
   Wireless Mouse               Electronics  2499         5166
   USB-C Cable                  Electronics  999          5166
   Bluetooth Speaker            Electronics  5999         5166
   Noise-Cancelling Headphones  Electronics  14999        5166
   Webcam                       Electronics  4999         5166
   Phone Stand                  Electronics  1499         5166
   Python Crash Course          Books        3999         3216
   SQL for Data Analysis        Books        4499         3216
   The Pragmatic Programmer     Books        4999         3216
   Sci-Fi Anthology             Books        1799         3216
   Cookbook Basics              Books        2499         3216
   Mystery Novel                Books        1499         3216
   (12 rows)
   name                         price_cents  category
   ---------------------------  -----------  -----------
   Bluetooth Speaker            5999         Electronics
   Noise-Cancelling Headphones  14999        Electronics
   Python Crash Course          3999         Books
   SQL for Data Analysis        4499         Books
   The Pragmatic Programmer     4999         Books
   (5 rows)
   ```

2. Find the orders whose total (sum of `quantity * unit_price_cents`) is larger than the **average order total of the same customer**. Show the order id, customer id, the total and the customer's average (whole cents) for the 5 orders that beat the average by the most.
   (Hint: you need the order totals twice, once for each order and once averaged per customer, so use two derived tables and join them.)

   ```sh
   order_id  customer_id  total_cents  customer_avg
   --------  -----------  -----------  ------------
   245       14           59993        17961
   225       7            51040        10274
   48        2            62493        23579
   304       60           62393        27998
   113       57           41438        10343
   (5 rows)
   ```

3. **The NOT IN trap.** Run `SELECT COUNT(*) FROM categories WHERE category_id NOT IN (SELECT category_id FROM products)`. You expect 1 (Garden) but get 0. Explain why, then fix it in two ways (a filter inside the subquery, and `NOT EXISTS`).

   ```sh
   (0,)
   category_id  name
   -----------  ------
   8            Garden
   (1 row)
   category_id  name
   -----------  ------
   8            Garden
   (1 row)
   ```

4. Customers whose total spend (non-cancelled orders) is above the average customer spend. Show the 5 biggest spenders with their spend in dollars.

   ```sh
   customer      spend
   ------------  -------
   Lena Green    2214.60
   Amara Kim     2045.68
   Ines Martin   2044.41
   Sam Wilson    1966.91
   Freya Nguyen  1688.31
   (5 rows)
   ```

5. For customers with ids 3 to 8, show their name and the date of their last order, with a subquery in the `SELECT` list. What does the customer without orders show?

   ```sh
   customer_id  customer     last_order
   -----------  -----------  ----------
   3            Liam Wilson  2025-03-21
   4            Noah Taylor  2025-12-21
   5            Sam Patel    NULL
   6            Mia Baker    2025-10-29
   7            Sam Wilson   2025-12-28
   8            Tara Brown   2025-08-03
   (6 rows)
   ```

6. Which categories contain at least one product that has never been ordered? (An `EXISTS` containing a `NOT EXISTS`.)

   ```sh
   name
   --------
   Clothing
   Sports
   Toys
   (3 rows)
   ```

### Exercises: Level 3

1. In `datasets.db` (with the Day 10 tables): which **English-speaking** countries have a population above the average population of English-speaking countries? Show name and population, largest first, and print the average.

   ```sh
   name                                                  population
   ----------------------------------------------------  ----------
   India                                                 1295210000
   United States of America                              323947000
   Pakistan                                              194125062
   Nigeria                                               186988000
   Philippines                                           103279800
   United Kingdom of Great Britain and Northern Ireland  65110000
   South Africa                                          55653654
   Tanzania, United Republic of                          55155000
   Kenya                                                 47251000
   Sudan                                                 39598700
   Canada                                                36155487
   Uganda                                                33860700
   (12 rows)
   (29178285,)
   ```

2. In `hn_posts`: which authors with at least 10 posts have an average of points above the overall average of all posts? Show the overall average (rounded to 2 decimals), then the top 10 by average points (rounded to two decimals; ties by author).

   ```sh
   (50.3,)
   author       posts  avg_points
   -----------  -----  ----------
   temp         10     205.0
   robin_reala  16     189.06
   ivank        11     165.45
   rdl          14     161.93
   tshtf        15     158.93
   adamnemecek  42     143.05
   rfreytag     12     141.5
   antouank     13     127.54
   sinak        15     127.13
   samber       11     126.0
   (10 rows)
   ```

3. **Relational division.** Which customers have bought **every** product of the Books category (in any order, in any status)? Think of it as "customers for whom there is *no* book that they have *not* bought", a `NOT EXISTS` inside a `NOT EXISTS`.

   ```sh
   customer_id  customer
   -----------  -----------
   24           Ines Martin
   (1 row)
   ```

Tomorrow you will name the steps of a query like these, so that they read like a recipe.

CONGRATULATIONS !

[<< Day 12](../12_Day_Outer_self_cross_joins/12_outer_self_cross_joins.md) | [Day 14 >>](../14_Day_CTEs_and_temp_tables/14_ctes_and_temp_tables.md)
