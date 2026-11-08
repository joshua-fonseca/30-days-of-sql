<div align="center">
  <h1> 30 Days Of SQL: Day 11 - INNER JOIN</h1>
</div>

[<< Review 1](../10R_Review_Foundations/10R_review_foundations.md) | [Day 12 >>](../12_Day_Outer_self_cross_joins/12_outer_self_cross_joins.md)

- [Day 11](#day-11)
  - [Meet the Shop Database](#meet-the-shop-database)
    - [The Tables](#the-tables)
    - [Meet the Data](#meet-the-data)
  - [Why Joins Exist](#why-joins-exist)
  - [INNER JOIN](#inner-join)
    - [The Syntax](#the-syntax)
    - [Table Aliases](#table-aliases)
    - [What Happens to Rows Without a Match](#what-happens-to-rows-without-a-match)
    - [USING](#using)
  - [Joining More Than Two Tables](#joining-more-than-two-tables)
  - [Joins with WHERE, GROUP BY and ORDER BY](#joins-with-where-group-by-and-order-by)
  - [Two Common Traps](#two-common-traps)
    - [Ambiguous Column Names](#ambiguous-column-names)
    - [Accidental Row Multiplication](#accidental-row-multiplication)
  - [How to Build a Hard Query Step by Step](#how-to-build-a-hard-query-step-by-step)
  - [Older Code: Implicit Joins](#older-code-implicit-joins)
  - [ Exercises: Day 11](#exercises-day-11)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 11

> **Before you start:** from today the exercises use `data/shop.db`, a separate practice database that is **not** part of your `library.db`. Build it once from the repo root with `uv run python tools/build_shop_db.py` (see "Setup & data" in the [readme](../readme.md#-setup--data-what-each-day-needs)). Your normalized library from Day 10 is needed too.

## Meet the Shop Database

Since Day 10 your data lives in several small tables instead of one big one. Today you learn the query that puts the pieces back together: the **join**. To practice it we need a database with more
tables and more rows than the library, so from now on we also use **`shop.db`**: a small online shop with customers, products, orders and employees. It comes with the course, in `data/shop.sql`, and
is built into a database file with one command:

```sh
uv run python tools/build_shop_db.py
```

(Run it once from the project root. Rebuilding is safe: it deletes and recreates `data/shop.db` from the script, so the data is always the same.)

All the examples below are run from the project root, so `data/shop.db` is a valid relative path. Your own files in `00_practice/` can use `'data/shop.db'` too when you run them from there with `uv run python 00_practice/day_11.py`.

### The Tables

```
 categories                products                      customers
 +-------------+          +---------------+             +--------------+
 | category_id |<---------| category_id   |             | customer_id  |
 | name        |    1   * | product_id    |             | first_name   |
 +-------------+          | name          |             | last_name    |
                          | price_cents   |             | email        |
                          | stock         |             | city         |
                          +---------------+             | country      |
                                  ^                     | signup_date  |
                                  | *                   +--------------+
                          +---------------+                    ^ 1
                          |  order_items  |                    |
                          | order_id      |                    | *
                          | product_id    |             +--------------+
                          | quantity      |    * 1      |   orders     |
                          | unit_price_   |------------>| order_id     |
                          |   cents       |             | customer_id  |
                          +---------------+             | order_date   |
                                                        | status       |
 employees                                              +--------------+
 +--------------+
 | employee_id  |<--+      newsletter_signups (no links, used on Day 17)
 | name         |   | manager_id points back at the same table
 | title        |   |
 | manager_id   |---+
 | hire_date    |
 | salary_cents |
 +--------------+
```

Read each arrow as "one on this side, many on that side": one category has many products, one customer has many orders, one order has many order items. `order_items` is a **junction table** (Day 10): it
links orders and products in a many-to-many relationship, and also stores the `quantity` and the `unit_price_cents` paid at the time. Money is in **integer cents**, as taught on Day 2.

### Meet the Data

Before joining anything, look at the tables one at a time. This is a habit worth keeping: you cannot write a good join for tables you have never looked at.

```py
import sqlite3
from helpers import show

conn = sqlite3.connect('data/shop.db')
conn.execute('PRAGMA foreign_keys = ON')

for table in ('customers', 'categories', 'products', 'orders', 'order_items', 'employees', 'newsletter_signups'):
    print(table, conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
```

```sh
customers 60
categories 8
products 40
orders 399
order_items 984
employees 15
newsletter_signups 20
```

(The f-string is fine here: the table names are ours, they are not user input. The rule from Day 3 is about *values* from outside.)

```py
show(conn.execute('SELECT * FROM customers ORDER BY customer_id LIMIT 4'))
```

```sh
customer_id  first_name  last_name  email                     city     country  signup_date
-----------  ----------  ---------  ------------------------  -------  -------  -----------
1            Chen        King       NULL                      Austin   USA      2023-07-01
2            Diego       Clark      diego.clark2@example.com  Chicago  USA      2024-02-19
3            Liam        Wilson     liam.wilson3@example.com  London   UK       2024-01-05
4            Noah        Taylor     noah.taylor4@example.com  Toronto  Canada   2024-11-16
(4 rows)
```

```py
show(conn.execute('SELECT * FROM orders ORDER BY order_id LIMIT 4'))
```

```sh
order_id  customer_id  order_date  status
--------  -----------  ----------  ---------
1         43           2024-01-02  delivered
2         56           2024-01-10  delivered
3         57           2024-02-08  delivered
4         43           2024-02-14  delivered
(4 rows)
```

Look at `orders`: it has a `customer_id`, but no name. To print "Lena Green ordered on 2024-01-02" you have to go and find customer 43 in the other table. Doing that for every row is exactly what a join does.

## Why Joins Exist

On Day 10 you split the data up so that each fact is stored once. The price you pay is that an everyday question, such as "who bought what?", now touches several tables. You could answer it in Python:

```py
customers = {cid: f'{first} {last}' for cid, first, last in conn.execute('SELECT customer_id, first_name, last_name FROM customers')}
for order_id, customer_id, order_date in conn.execute('SELECT order_id, customer_id, order_date FROM orders ORDER BY order_id LIMIT 3'):
    print(order_id, customers[customer_id], order_date)
```

```sh
1 Lena Green 2024-01-02
2 Freya Harris 2024-01-10
3 Olivia Taylor 2024-02-08
```

That works, but it ships every customer to Python just to look three of them up. A join does the same lookup inside the database, which is far faster and one line of SQL. Think of a join as a very patient assistant who,
for every order, walks to the customers shelf, finds the row with the matching id and staples the two rows together.

## INNER JOIN

### The Syntax

```sql
-- syntax
SELECT columns
FROM table_a
INNER JOIN table_b ON table_a.column = table_b.column;
```

The `ON` clause says **when two rows belong together**. Usually that is "the foreign key in one table equals the primary key in the other":

```py
show(conn.execute('''
    SELECT orders.order_id, customers.first_name, customers.last_name, orders.order_date
    FROM orders
    INNER JOIN customers ON orders.customer_id = customers.customer_id
    ORDER BY orders.order_id
    LIMIT 5
'''))
```

```sh
order_id  first_name  last_name  order_date
--------  ----------  ---------  ----------
1         Lena        Green      2024-01-02
2         Freya       Harris     2024-01-10
3         Olivia      Taylor     2024-02-08
4         Lena        Green      2024-02-14
5         Ava         Green      2024-02-17
(5 rows)
```

For every row of `orders`, SQL finds the `customers` row whose `customer_id` matches, and glues them side by side. You can now select columns from either table. The word `INNER` is optional: a plain `JOIN` means
`INNER JOIN`, and this is how most people write it. We will write `JOIN` from here on.

### Table Aliases

Typing `customers.customer_id` all the time is tiring. Give each table a short **alias** with `AS` (the same keyword as for column aliases), and use it everywhere in the query:

```sql
-- syntax
SELECT a.column, b.column
FROM table_a AS a
JOIN table_b AS b ON a.key = b.key;
```

```py
show(conn.execute('''
    SELECT o.order_id, c.first_name || ' ' || c.last_name AS customer, o.status
    FROM orders AS o
    JOIN customers AS c ON c.customer_id = o.customer_id
    WHERE o.status = 'pending'
    ORDER BY o.order_id
    LIMIT 5
'''))
```

```sh
order_id  customer       status
--------  -------------  -------
379       Priya Brown    pending
381       Omar Lopez     pending
382       Ines Silva     pending
383       Diego Clark    pending
384       Emma Anderson  pending
(5 rows)
```

Good aliases are short but recognisable (`o` for orders, `c` for customers, `i` for order_items). Once you alias a table, you must use the alias, not the original name, in the rest of that query.

### What Happens to Rows Without a Match

An inner join keeps **only the pairs that match**. A row with no partner on the other side silently disappears. The shop has 40 products, but one of them, "Gift Card Holder", has a `NULL` category:

```py
print(conn.execute('SELECT COUNT(*) FROM products').fetchone())
print(conn.execute('SELECT COUNT(*) FROM products AS p JOIN categories AS c ON c.category_id = p.category_id').fetchone())
```

```sh
(40,)
(39,)
```

Forty products go in, thirty-nine rows come out. `NULL` is never equal to anything (Day 5), so the gift card holder found no match and vanished. No error, no warning.  **Common mistake:** trusting an inner join to keep
every row of the "main" table. If you must keep them, you need an outer join, which is tomorrow's lesson. For now, remember to ask yourself: *can some row have no partner?*

### USING

When the two columns have **the same name** in both tables, `USING (column)` is a shorter way to write the `ON`:

```sql
-- syntax
SELECT columns
FROM table_a
JOIN table_b USING (shared_column);
```

```py
show(conn.execute('''
    SELECT p.name AS product, c.name AS category
    FROM products AS p
    JOIN categories AS c USING (category_id)
    ORDER BY p.product_id
    LIMIT 3
'''))
```

```sh
product            category
-----------------  -----------
Wireless Mouse     Electronics
USB-C Cable        Electronics
Bluetooth Speaker  Electronics
(3 rows)
```

`USING` also merges the shared column into one, so a plain `category_id` is no longer ambiguous (more on that below). It only works when the names match exactly. Many teams prefer `ON` anyway because it works in every case, including
when the names differ (like `employees.manager_id = employees.employee_id` on Day 12). Pick one style and be consistent.

## Joining More Than Two Tables

A join produces a table, and a table can be joined again. To list every order line with the customer's name and the product's name you walk along the arrows of the ER diagram: `order_items` to `orders` to `customers`, and `order_items` to `products`.

```sql
-- syntax
SELECT ...
FROM a
JOIN b ON b.a_id = a.id
JOIN c ON c.b_id = b.id
JOIN d ON d.c_id = c.id;
```

```py
show(conn.execute('''
    SELECT o.order_id,
           c.first_name || ' ' || c.last_name AS customer,
           p.name                             AS product,
           i.quantity
    FROM order_items AS i
    JOIN orders      AS o ON o.order_id    = i.order_id
    JOIN customers   AS c ON c.customer_id = o.customer_id
    JOIN products    AS p ON p.product_id  = i.product_id
    ORDER BY o.order_id, p.name
    LIMIT 6
'''))
```

```sh
order_id  customer       product               quantity
--------  -------------  --------------------  --------
1         Lena Green     Gift Card Holder      2
2         Freya Harris   Water Bottle          4
3         Olivia Taylor  Bamboo Cutting Board  1
3         Olivia Taylor  Cookbook Basics       2
4         Lena Green     Running Shoes         1
4         Lena Green     USB-C Cable           2
(6 rows)
```

Each `JOIN` adds one table and one `ON`. Reading the query top to bottom is like following a trail through the diagram. Four tables is normal in real databases; ten is not unheard of.

## Joins with WHERE, GROUP BY and ORDER BY

Everything you learned before still works, because the joined result is just a bigger table. `WHERE` filters the joined rows, `GROUP BY` groups them, and aggregates summarise them. Revenue per category needs four tables:

```py
show(conn.execute('''
    SELECT cat.name AS category,
           COUNT(DISTINCT p.product_id) AS products_sold,
           SUM(i.quantity)              AS units,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) / 100.0) AS revenue
    FROM order_items AS i
    JOIN products    AS p   ON p.product_id = i.product_id
    JOIN categories  AS cat ON cat.category_id = p.category_id
    JOIN orders      AS o   ON o.order_id = i.order_id
    WHERE o.status <> 'cancelled'
    GROUP BY cat.category_id
    ORDER BY SUM(i.quantity * i.unit_price_cents) DESC
'''))
```

```sh
category        products_sold  units  revenue
--------------  -------------  -----  -------
Sports          4              192    8963.18
Electronics     6              232    8765.43
Books           6              220    7864.10
Toys            4              206    6092.94
Home & Kitchen  6              187    4959.43
Clothing        4              80     4225.30
Grocery         5              308    3696.37
(7 rows)
```

Notice three things. The money is computed in cents (`quantity * unit_price_cents`) and only divided by `100.0` for display, as taught on Day 2. We use `unit_price_cents` from `order_items`, the price paid at the time, not
today's `products.price_cents`. And we group by the category's id and not its name, which is safer if two categories ever shared a name. Remember the order SQL runs in (Day 7): `FROM` and `JOIN` come first, then `WHERE`,
then `GROUP BY`.

## Two Common Traps

### Ambiguous Column Names

`orders` and `order_items` both have an `order_id`. If you write just `order_id`, SQL does not know which one you mean, and refuses:

```py
try:
    conn.execute('SELECT order_id FROM orders JOIN order_items ON orders.order_id = order_items.order_id')
except sqlite3.OperationalError as e:
    print(e)
# ambiguous column name: order_id
```

**Common mistake:** forgetting to qualify a column that exists in more than one table. The fix is to prefix it with the table or alias: `o.order_id`. A good habit is to prefix **every** column in a join query, even the unambiguous ones. Then the reader
never has to guess which table a column comes from.

### Accidental Row Multiplication

If one row on the left matches *several* rows on the right, the left row appears several times in the result. That is correct, but it can ruin a count or a sum. One order has several lines:

```py
print(conn.execute('SELECT COUNT(*) FROM orders').fetchone())
print(conn.execute('SELECT COUNT(*) FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id').fetchone())
```

```sh
(399,)
(984,)
```

There are 399 orders but 984 joined rows. Counting orders after the join to `order_items` therefore counts **lines**, not orders. Use `COUNT(DISTINCT o.order_id)` when you need the real number:

```py
print(conn.execute('SELECT COUNT(*), COUNT(DISTINCT o.order_id) FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id').fetchone())
# (984, 399)
```

The same happens with sums: if you join `orders` to `order_items` and add up a column that belongs to `orders`, every order's value is added once per line. Whenever a join "fans out" like this, ask yourself which table's rows you are really counting.

## How to Build a Hard Query Step by Step

Nobody writes a five-table query in one go. The professional habit is to **grow the query one step at a time, and check the row count after every step**. Say we want "the five customers who spent the most".

**Step 1:** start with the table that has the facts you add up, and see what is in it.

```py
show(conn.execute('SELECT * FROM order_items LIMIT 3'))
print(conn.execute('SELECT COUNT(*) FROM order_items').fetchone())
```

```sh
order_id  product_id  quantity  unit_price_cents
--------  ----------  --------  ----------------
1         39          2         599
2         24          4         1799
3         11          2         2499
(3 rows)
(984,)
```

**Step 2:** add the join that gets you to the next table. The count should stay at 984, since every line belongs to exactly one order:

```py
print(conn.execute('''
    SELECT COUNT(*)
    FROM order_items AS i
    JOIN orders AS o ON o.order_id = i.order_id
''').fetchone())
# (984,)
```

**Step 3:** add the next join, and look at a few real rows rather than only at the count.

```py
show(conn.execute('''
    SELECT i.order_id, c.first_name, c.last_name, i.quantity, i.unit_price_cents
    FROM order_items AS i
    JOIN orders    AS o ON o.order_id = i.order_id
    JOIN customers AS c ON c.customer_id = o.customer_id
    ORDER BY i.order_id
    LIMIT 4
'''))
```

```sh
order_id  first_name  last_name  quantity  unit_price_cents
--------  ----------  ---------  --------  ----------------
1         Lena        Green      2         599
2         Freya       Harris     4         1799
3         Olivia      Taylor     2         2499
3         Olivia      Taylor     1         1999
(4 rows)
```

**Step 4:** only now add the filter, the grouping and the aggregate.

```py
show(conn.execute('''
    SELECT c.first_name || ' ' || c.last_name AS customer,
           format('%.2f', SUM(i.quantity * i.unit_price_cents) / 100.0) AS spend
    FROM order_items AS i
    JOIN orders    AS o ON o.order_id = i.order_id
    JOIN customers AS c ON c.customer_id = o.customer_id
    WHERE o.status <> 'cancelled'
    GROUP BY c.customer_id
    ORDER BY SUM(i.quantity * i.unit_price_cents) DESC, customer
    LIMIT 5
'''))
```

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

If a result looks wrong, you know exactly which step broke it, because you checked after each one. We will use this habit in every lesson from now on.

## Older Code: Implicit Joins

**Older code:** in older tutorials and code, you will see joins written with **commas** in the `FROM` clause, and the matching condition hidden in the `WHERE`:

```py
show(conn.execute('''
    SELECT o.order_id, c.first_name, o.order_date
    FROM orders o, customers c
    WHERE o.customer_id = c.customer_id
    ORDER BY o.order_id
    LIMIT 3
'''))
```

```sh
order_id  first_name  order_date
--------  ----------  ----------
1         Lena        2024-01-02
2         Freya       2024-01-10
3         Olivia      2024-02-08
(3 rows)
```

It does the same thing as `JOIN ... ON`, and you used it on Review 1 to look at the idea. But prefer the explicit `JOIN ... ON`, for three reasons. First, the rule that connects the tables sits right next to the join, instead of
being mixed with your filters in `WHERE`. Second, if you forget the `WHERE` condition, the comma version quietly returns **every pair of rows** (see the cross join on Day 12) while the explicit version will not even run without `ON`. Third, it is the only form that supports
outer joins, which you need tomorrow. From now on this course writes explicit joins only.

> **In other databases:** `INNER JOIN ... ON` is standard SQL and identical in PostgreSQL, MySQL, SQL Server, Oracle and DuckDB. W3Schools also shows it. `USING` is not supported by SQL Server.

You can now put the pieces back together: one `JOIN` per arrow in the diagram. Next, do some exercises.

## Exercises: Day 11

### Exercises: Level 1

Questions 1 to 7, 13 and 14 use `shop.db`. Questions 8 to 11 use your normalized `00_practice/library.db` from Day 10. Order your results so they match.

1. List the first 5 orders (by `order_id`) with the customer's full name (first and last, joined with `||`) and the order date.

   ```sh
   order_id  customer       order_date
   --------  -------------  ----------
   1         Lena Green     2024-01-02
   2         Freya Harris   2024-01-10
   3         Olivia Taylor  2024-02-08
   4         Lena Green     2024-02-14
   5         Ava Green      2024-02-17
   (5 rows)
   ```

2. List the first 5 order lines (order by `order_id`, then product name) showing the order id, the product's name and the quantity.
3. List the first 8 products (by `product_id`) with the name of their category.
4. How many rows does `products` have, and how many does the join from the previous exercise return? Find the product that went missing and explain why.

   ```sh
   (40,) (39,)
   product_id  name
   ----------  ----------------
   39          Gift Card Holder
   (1 row)
   ```

5. Redo exercise 3, this time with `USING`, and show 3 rows.
6. Show the lines of order 3: product name, quantity and the unit price in dollars with two decimals (`format('%.2f', ...)`), ordered by product name.

   ```sh
   product               quantity  unit_price
   --------------------  --------  ----------
   Bamboo Cutting Board  1         19.99
   Cookbook Basics       2         24.99
   (2 rows)
   ```

7. Which customers from Canada have placed at least one order? Show each person once (first and last name), ordered by last name, then first name.
8. Library: list the first 5 books by title with the name of their author.
9. Library: list the first 5 loans (by id) with the member's name and the date loaned.
10. Library: list the loans that have not been returned, with the book's title and the date loaned, ordered by loan id.

    ```sh
    id  title                     loaned_on
    --  ------------------------  ----------
    4   The Pragmatic Programmer  2025-02-20
    6   Neuromancer               2025-03-01
    7   Pride and Prejudice       2025-03-05
    8   Dune                      2025-03-08
    9   Clean Code                2025-03-10
    10  The Hobbit                2025-03-12
    (6 rows)
    ```

11. Library: rewrite the Review 1 query (books written by Andy Weir) with `JOIN ... ON` instead of the comma style.
12. In your own words: what does an `INNER JOIN` do with a row that has no matching row in the other table?
13. This query fails. Say why and fix it: `SELECT order_id, quantity FROM orders JOIN order_items ON orders.order_id = order_items.order_id`.

    ```sh
    OperationalError ambiguous column name: order_id
    order_id  quantity
    --------  --------
    1         2
    2         4
    3         1
    (3 rows)
    ```

14. List the first 3 toys (alphabetically) with their category name, filtering with a `WHERE` on the category's name.

### Exercises: Level 2

1. Revenue per category for orders that are not cancelled, highest first, with the revenue in dollars (two decimals). Only categories that were actually sold appear.

   ```sh
   category        revenue
   --------------  -------
   Sports          8963.18
   Electronics     8765.43
   Books           7864.10
   Toys            6092.94
   Home & Kitchen  4959.43
   Clothing        4225.30
   Grocery         3696.37
   (7 rows)
   ```

2. The 5 customers who spent the most (all orders except cancelled ones). Show the full name and the total in dollars. Break ties by name.

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

3. Library: every loan with the member's name, the book's title **and** the author's name (four tables), ordered by the date loaned, then loan id.

   ```sh
   member        title                     author            loaned_on
   ------------  ------------------------  ----------------  ----------
   Alice Nguyen  Dune                      Frank Herbert     2025-01-10
   Alice Nguyen  The Hobbit                J.R.R. Tolkien    2025-01-25
   Bruno Silva   1984                      George Orwell     2025-02-01
   Chloe Martin  The Martian               Andy Weir         2025-02-03
   Bruno Silva   The Pragmatic Programmer  Andrew Hunt       2025-02-20
   Chloe Martin  Neuromancer               William Gibson    2025-03-01
   Dev Patel     Pride and Prejudice       Jane Austen       2025-03-05
   Dev Patel     Dune                      Frank Herbert     2025-03-08
   Alice Nguyen  Clean Code                Robert C. Martin  2025-03-10
   Bruno Silva   The Hobbit                J.R.R. Tolkien    2025-03-12
   (10 rows)
   ```

4. For each customer country, show the number of joined rows (`COUNT(*)`) when you join `customers`, `orders` and `order_items`, next to the real number of orders. Explain the difference between the two columns.

   ```sh
   country  joined_rows  orders
   -------  -----------  ------
   USA      244          100
   Canada   193          85
   UK       218          83
   France   189          74
   Germany  140          57
   (5 rows)
   ```

5. Which products have customers from France bought? Show the first 8 names alphabetically (each product once), and then print how many different products that is in total.

   ```sh
   name
   --------------------
   Bamboo Cutting Board
   Bluetooth Speaker
   Board Game Night
   Building Blocks Set
   Cast Iron Pan
   Cookbook Basics
   Dark Chocolate Bar
   Denim Jacket
   (8 rows)
   (32,)
   ```

6. Revenue (in dollars, non-cancelled orders) for each month of 2025. Use `substr(order_date, 1, 7)` to get the month (Day 6).

   ```sh
   month    revenue
   -------  -------
   2025-01  1807.03
   2025-02  1204.11
   2025-03  1808.77
   2025-04  1609.87
   2025-05  3350.31
   2025-06  1744.89
   2025-07  1583.97
   2025-08  1415.52
   2025-09  1928.13
   2025-10  2420.33
   2025-11  3450.08
   2025-12  4326.48
   (12 rows)
   ```

7. Practice the step-by-step habit. Print the row counts after each of these four stages, and explain why the last one is smaller: `order_items`; joined to `orders`; joined to `products`; joined to `categories`.

   ```sh
   [984, 984, 984, 940]
   ```

### Exercises: Level 3

1. **The ten most spoken languages.** In `00_practice/datasets.db` you built `countries`, `languages` and `country_languages` yesterday. Now one query answers
   what would take loops and dictionaries in plain Python. Break ties alphabetically by language, so that `Portuguese` and `Russian` (both 9) come in this order.

   ```sh
   language    countries
   ----------  ---------
   English     91
   French      45
   Arabic      25
   Spanish     24
   Portuguese  9
   Russian     9
   Dutch       8
   German      7
   Chinese     5
   Italian     4
   (10 rows)
   ```


2. Which countries speak **both** English and French? Show the names, alphabetically. (Hint: join the junction table twice, once per language. Or use `GROUP BY` and `HAVING`.)

   ```sh
   name
   --------------------------
   Cameroon
   Canada
   Guernsey
   Jersey
   Rwanda
   Saint Martin (French part)
   Seychelles
   Vanuatu
   (8 rows)
   ```

3. For each customer country show the number of customers who ordered, the number of orders and the revenue in dollars (non-cancelled orders), highest revenue first.

   ```sh
   country  buyers  orders  revenue
   -------  ------  ------  --------
   USA      15      93      12715.29
   Canada   10      80      9762.49
   France   9       66      8401.72
   UK       14      81      7982.30
   Germany  6       55      6070.93
   (5 rows)
   ```

4. The 5 best-selling products by units (non-cancelled orders): the product's name, its category, the units sold and the number of different customers who bought it. Ties by product name.

   ```sh
   product                   category        units  buyers
   ------------------------  --------------  -----  ------
   Dark Chocolate Bar        Grocery         101    28
   Jigsaw Puzzle 1000pc      Toys            99     35
   Bamboo Cutting Board      Home & Kitchen  95     29
   The Pragmatic Programmer  Books           83     30
   Green Tea Box             Grocery         77     30
   (5 rows)
   ```

Tomorrow you meet the rows that an inner join throws away: customers who never ordered, products nobody bought.

CONGRATULATIONS !

[<< Review 1](../10R_Review_Foundations/10R_review_foundations.md) | [Day 12 >>](../12_Day_Outer_self_cross_joins/12_outer_self_cross_joins.md)
