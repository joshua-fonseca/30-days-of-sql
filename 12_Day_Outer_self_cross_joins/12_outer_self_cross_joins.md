<div align="center">
  <h1> 30 Days Of SQL: Day 12 - Outer, Self & Cross Joins</h1>
</div>

[<< Day 11](../11_Day_Inner_join/11_inner_join.md) | [Day 13 >>](../13_Day_Subqueries/13_subqueries.md)

- [Day 12](#day-12)
  - [LEFT JOIN](#left-join)
    - [Keeping the Unmatched Rows](#keeping-the-unmatched-rows)
    - [The Venn Diagram, and Where It Misleads](#the-venn-diagram-and-where-it-misleads)
    - [Anti-Join: Finding What Is Missing](#anti-join-finding-what-is-missing)
    - [Counting With a LEFT JOIN](#counting-with-a-left-join)
    - [ON vs WHERE](#on-vs-where)
  - [RIGHT and FULL OUTER JOIN](#right-and-full-outer-join)
  - [Self Join](#self-join)
  - [CROSS JOIN](#cross-join)
  - [Joins That Are Not Equalities](#joins-that-are-not-equalities)
  - [Which Join Do I Need?](#which-join-do-i-need)
  - [ Exercises: Day 12](#exercises-day-12)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 12

## LEFT JOIN

### Keeping the Unmatched Rows

Yesterday you saw that an `INNER JOIN` throws away rows that have no partner. Sometimes the unmatched rows are exactly what you want. A **`LEFT JOIN`** keeps *every* row of the left table (the one written before the word `JOIN`).
When a left row has no match on the right, its right-hand columns are filled with `NULL`.

```sql
-- syntax
SELECT columns
FROM left_table
LEFT JOIN right_table ON left_table.key = right_table.key;
```

(`LEFT OUTER JOIN` means the same; the word `OUTER` is optional, just like `INNER`.) Here are customers 5 and 6 with their orders (the first four rows):

```py
import sqlite3
from helpers import show

conn = sqlite3.connect('data/shop.db')
show(conn.execute('''
    SELECT c.customer_id, c.first_name, o.order_id, o.order_date
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE c.customer_id IN (5, 6)
    ORDER BY c.customer_id, o.order_id
    LIMIT 4
'''))
```

```sh
customer_id  first_name  order_id  order_date
-----------  ----------  --------  ----------
5            Sam         NULL      NULL
6            Mia         163       2024-12-17
6            Mia         188       2025-01-12
6            Mia         253       2025-05-18
(4 rows)
```

Customer 5 (Sam Patel) has never ordered, but still appears, with `NULL` where the order columns would be, followed by the orders of customer 6. With an `INNER JOIN`, Sam would not be in the result at all.

### The Venn Diagram, and Where It Misleads

Many tutorials draw joins as overlapping circles:

```
   INNER JOIN             LEFT JOIN              FULL OUTER JOIN
   (only the middle)      (all of the left)      (everything)

   ( A  (##)  B )         (###### ) B )          (######(##)######)
```

The picture is a good first idea: *inner* is the overlap, *left* is all of A plus the overlap, *full* is everything. But it can mislead, because circles suggest that joins work like set operations on **whole rows** (that is Day 15). A join does not
subtract or add rows: it makes **pairs** of rows. If a customer has 12 orders, that customer appears 12 times in the result, and no Venn diagram shows that. Use the picture to remember *which side is kept*, and
the "pairs of rows" idea to predict the *number of rows*.

### Anti-Join: Finding What Is Missing

Because unmatched rows get `NULL` on the right, you can find "things with no partner" by keeping only those rows. This pattern is called an **anti-join**: left join, then `WHERE` the right side's key `IS NULL`.

```sql
-- syntax
SELECT left_table.*
FROM left_table
LEFT JOIN right_table ON left_table.key = right_table.key
WHERE right_table.key IS NULL;
```

Customers who never ordered:

```py
show(conn.execute('''
    SELECT c.customer_id, c.first_name, c.last_name, c.country
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE o.order_id IS NULL
    ORDER BY c.customer_id
'''))
```

```sh
customer_id  first_name  last_name  country
-----------  ----------  ---------  -------
5            Sam         Patel      Canada
17           Mia         Thomas     Canada
23           Sofia       Green      Canada
36           Diego       Scott      USA
44           Tara        Kim        USA
58           Isla        Clark      Germany
(6 rows)
```

Test for `NULL` in a column that can **never** be `NULL` in real matched rows (the right table's primary key or a `NOT NULL` column, like `o.order_id`). If you tested a nullable column, you could not tell a missing row from a row whose value happens to be `NULL`.
Products that nobody ever ordered work the same way:

```py
show(conn.execute('''
    SELECT p.product_id, p.name
    FROM products AS p
    LEFT JOIN order_items AS i ON i.product_id = p.product_id
    WHERE i.order_id IS NULL
    ORDER BY p.product_id
'''))
```

```sh
product_id  name
----------  ---------------
27          Jump Rope
28          Camping Hammock
33          Beanie
40          Mystery Box
(4 rows)
```

### Counting With a LEFT JOIN

An outer join mixes real rows and "filler" rows, so counting needs care. `COUNT(*)` counts every row, including the filler ones. `COUNT(column)` skips `NULL`s (Day 7), which makes it the right tool for "how many matches".

```py
show(conn.execute('''
    SELECT c.first_name || ' ' || c.last_name AS customer,
           COUNT(*)          AS count_star,
           COUNT(o.order_id) AS orders
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE c.customer_id IN (5, 17, 43)
    GROUP BY c.customer_id
    ORDER BY c.customer_id
'''))
```

```sh
customer    count_star  orders
----------  ----------  ------
Sam Patel   1           0
Mia Thomas  1           0
Lena Green  17          17
(3 rows)
```

Sam Patel has `COUNT(*)` = 1 because of the filler row, but really 0 orders.  **Common mistake:** using `COUNT(*)` after a `LEFT JOIN` and reporting 1 for customers with nothing. Count a column from the right table.

### ON vs WHERE

With an `INNER JOIN` it makes no difference whether a filter sits in `ON` or in `WHERE`. With a `LEFT JOIN` it makes a **big** difference:

- A condition in `ON` decides **which right-hand rows match**. Left rows that find no match are still kept (with `NULL`s).
- A condition in `WHERE` is applied **after** the join and removes whole result rows, including the filler rows.

Say we want every customer with the number of their *cancelled* orders (zero for most):

```py
print(conn.execute('''
    SELECT COUNT(*)
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id AND o.status = 'cancelled'
''').fetchone())
print(conn.execute('''
    SELECT COUNT(*)
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE o.status = 'cancelled'
''').fetchone())
```

```sh
(62,)
(24,)
```

The first query puts the filter in `ON`: all 60 customers survive, and 24 cancelled orders are attached to them (62 rows: 38 customers with no cancelled order each give one filler row, and the 22 customers with cancelled orders give 24 rows between them). The second puts the filter in `WHERE`: the
filler rows have `status = NULL`, which is not `'cancelled'`, so they are removed, and only the 24 cancelled orders remain. The `LEFT JOIN` has quietly turned into an `INNER JOIN`.

**Common mistake:** writing a `LEFT JOIN` and then a `WHERE` on a column of the right table (other than `IS NULL`). Ask: "do I want to remove customers, or only to restrict which orders count?" The first is `WHERE`, the second is `ON`.

## RIGHT and FULL OUTER JOIN

A `RIGHT JOIN` is a `LEFT JOIN` seen in a mirror: it keeps every row of the **right** table. A `FULL OUTER JOIN` keeps every row of **both** tables, filling `NULL` on whichever side has no match. SQLite only supports these since version 3.39 (2022). Check yours first (Day 1):

```py
print(sqlite3.sqlite_version)
# 3.45.1
```

```sql
-- syntax
SELECT columns
FROM a
RIGHT JOIN b ON a.key = b.key;      -- every row of b

SELECT columns
FROM a
FULL OUTER JOIN b ON a.key = b.key; -- every row of a and every row of b
```

The shop has a product with no category (the gift card holder) and a category with no products (Garden). A full join of the two shows both problems in one query:

```py
show(conn.execute('''
    SELECT p.name AS product, c.name AS category
    FROM products AS p
    FULL OUTER JOIN categories AS c ON c.category_id = p.category_id
    WHERE p.product_id IS NULL OR c.category_id IS NULL
'''))
```

```sh
product           category
----------------  --------
Gift Card Holder  NULL
NULL              Garden
(2 rows)
```

> **In other databases:** `RIGHT` and `FULL OUTER JOIN` exist in PostgreSQL, SQL Server, Oracle and DuckDB. MySQL has `RIGHT JOIN` but **no** `FULL OUTER JOIN`. There it is simulated with a `LEFT JOIN` plus a `RIGHT JOIN`
> glued together (Day 15). In practice most people use `LEFT JOIN` only and swap the table order, because it reads left to right.

## Self Join

A table can be joined **to itself**. It sounds odd, but it is natural whenever a table contains a reference to its own rows. `employees.manager_id` holds the `employee_id` of another employee. To print each employee next to their boss's *name*, join the table to itself, using two
different aliases, as if there were two copies:

```sql
-- syntax
SELECT e.name AS employee, m.name AS manager
FROM employees AS e
LEFT JOIN employees AS m ON m.employee_id = e.manager_id;
```

```py
show(conn.execute('''
    SELECT e.employee_id, e.name AS employee, e.title, m.name AS manager
    FROM employees AS e
    LEFT JOIN employees AS m ON m.employee_id = e.manager_id
    ORDER BY e.employee_id
    LIMIT 6
'''))
```

```sh
employee_id  employee         title                manager
-----------  ---------------  -------------------  ------------
1            Grace Hopper     CEO                  NULL
2            Alan Turing      VP Engineering       Grace Hopper
3            Ada Lovelace     VP Sales             Grace Hopper
4            Edsger Dijkstra  VP Operations        Grace Hopper
5            Barbara Liskov   Engineering Manager  Alan Turing
6            Donald Knuth     Engineering Manager  Alan Turing
(6 rows)
```

Think of `e` as "the employee" and `m` as "the manager". We used `LEFT JOIN` because the CEO has `manager_id = NULL`: an inner join would drop the CEO. Aliases are **required** here, since both sides have the same table name. Another self-join question: who has no one reporting to them?

```py
show(conn.execute('''
    SELECT e.name, e.title
    FROM employees AS e
    LEFT JOIN employees AS r ON r.manager_id = e.employee_id
    WHERE r.employee_id IS NULL
    ORDER BY e.employee_id
    LIMIT 3
'''))
```

```sh
name             title
---------------  -----------------
Tim Berners-Lee  Software Engineer
Radia Perlman    Software Engineer
Ken Thompson     Software Engineer
(3 rows)
```

A self join only reaches a fixed number of levels (one join per level). To follow a chain of any length, you will use a recursive CTE on Day 14.

## CROSS JOIN

A `CROSS JOIN` pairs **every row of one table with every row of the other**, with no `ON` at all. With 3 sizes and 2 colours you get 3 × 2 = 6 combinations. It is the mathematical *Cartesian product*.

```sql
-- syntax
SELECT columns
FROM table_a
CROSS JOIN table_b;
```

```py
toy = sqlite3.connect(':memory:')
toy.execute('CREATE TABLE sizes (size TEXT)')
toy.execute('CREATE TABLE colours (colour TEXT)')
toy.executemany('INSERT INTO sizes VALUES (?)', [('S',), ('M',), ('L',)])
toy.executemany('INSERT INTO colours VALUES (?)', [('red',), ('blue',)])
show(toy.execute('SELECT size, colour FROM sizes CROSS JOIN colours ORDER BY colour, size DESC'))
```

```sh
size  colour
----  ------
S     blue
M     blue
L     blue
S     red
M     red
L     red
(6 rows)
```

That looks like a toy, but a cross join is the standard way to **build a grid**: every product × every month, every day × every store. The grid is then used as the left side of a `LEFT JOIN` to show zeros for combinations that had no data (you will do exactly this in the exercises).
That is also why the old comma join without a `WHERE` (Day 11) was dangerous: it silently did a cross join, and 40 products × 60 customers is 2,400 rows. When both tables are big, a cross join explodes, so always ask how many rows to expect (rows in A × rows in B).

For the grid example we need a small table of months. We don't write into the shared `shop.db`; we make a **copy** and work in the copy (like the copy exercises on Day 8):

```py
import shutil
shutil.copy('data/shop.db', '00_practice/shop_play.db')
play = sqlite3.connect('00_practice/shop_play.db')
play.execute('CREATE TABLE months (month TEXT PRIMARY KEY)')
play.executemany('INSERT INTO months VALUES (?)', [('2025-01',), ('2025-02',), ('2025-03',)])
play.commit()
show(play.execute('''
    SELECT c.name AS category, m.month
    FROM categories AS c
    CROSS JOIN months AS m
    WHERE c.category_id <= 2
    ORDER BY c.category_id, m.month
'''))
```

```sh
category     month
-----------  -------
Electronics  2025-01
Electronics  2025-02
Electronics  2025-03
Books        2025-01
Books        2025-02
Books        2025-03
(6 rows)
```

## Joins That Are Not Equalities

`ON` accepts any condition, not only `a.id = b.id`. Joining on `<`, `>`, `BETWEEN` or other tests is called a **non-equi join**. Two typical uses:

**Banding.** Put each product into a price band. We make a table of bands in the copy:

```py
play.execute('CREATE TABLE price_bands (label TEXT, low_cents INTEGER, high_cents INTEGER)')
play.executemany('INSERT INTO price_bands VALUES (?, ?, ?)', [
    ('budget', 0, 1999), ('mid', 2000, 4999), ('premium', 5000, 999999),
])
show(play.execute('''
    SELECT b.label, COUNT(*) AS products
    FROM products AS p
    JOIN price_bands AS b ON p.price_cents BETWEEN b.low_cents AND b.high_cents
    GROUP BY b.label
    ORDER BY b.low_cents
'''))
```

```sh
label    products
-------  --------
budget   17
mid      17
premium  6
(3 rows)
```

**Pairs of rows from the same table.** Combine a self join with `<` to list each pair of customers who live in the same city exactly once. (`a.customer_id < b.customer_id` removes the pairs where a customer is paired with themselves
and the mirrored duplicates `(x, y)` and `(y, x)`.)

```py
show(conn.execute('''
    SELECT a.first_name || ' ' || a.last_name AS customer_1,
           b.first_name || ' ' || b.last_name AS customer_2,
           a.city
    FROM customers AS a
    JOIN customers AS b ON b.city = a.city AND b.customer_id > a.customer_id
    WHERE a.city = 'Montreal'
    ORDER BY a.customer_id, b.customer_id
'''))
```

```sh
customer_1   customer_2    city
-----------  ------------  --------
Priya Brown  Mia Thomas    Montreal
Priya Brown  Sofia Green   Montreal
Priya Brown  Mason Thomas  Montreal
Mia Thomas   Sofia Green   Montreal
Mia Thomas   Mason Thomas  Montreal
Sofia Green  Mason Thomas  Montreal
(6 rows)
```

## Which Join Do I Need?

| I want... | Use |
|---|---|
| only the rows that have a partner in both tables | `JOIN` (inner) |
| all rows of A, with B's data when it exists | `LEFT JOIN` |
| the rows of A that have **no** partner in B | `LEFT JOIN ... WHERE b.key IS NULL` (anti-join) |
| all rows of both tables | `FULL OUTER JOIN` |
| a row for every combination | `CROSS JOIN` |
| to relate a table to itself | self join with two aliases |

Now you know how to keep the rows that others throw away. Next, do some exercises.

## Exercises: Day 12

### Exercises: Level 1

Question 8 uses your `00_practice/library.db`, question 12 uses the toy tables from the lesson, and the others use `shop.db`. Order by the columns shown so that your output matches.

1. List the customers who have never placed an order (id, first name, last name, country).

   ```sh
   customer_id  first_name  last_name  country
   -----------  ----------  ---------  -------
   5            Sam         Patel      Canada
   17           Mia         Thomas     Canada
   23           Sofia       Green      Canada
   36           Diego       Scott      USA
   44           Tara        Kim        USA
   58           Isla        Clark      Germany
   (6 rows)
   ```

2. List the products that have never been ordered.

   ```sh
   product_id  name
   ----------  ---------------
   27          Jump Rope
   28          Camping Hammock
   33          Beanie
   40          Mystery Box
   (4 rows)
   ```

3. Which category has no products?
4. Show every employee with the name of their manager, ordered by `employee_id`. The CEO must appear too.
5. Print four counts: the rows in `customers`; the rows of `customers JOIN orders`; the rows of `customers LEFT JOIN orders`; and, for the left join, `COUNT(*)` next to `COUNT(o.order_id)`. Explain each number.

   ```sh
   (60,) (399,) (405,) (405, 399)
   ```

6. List the products that have no category (use `LEFT JOIN`, then test the category's key for `NULL`).
7. List the last 4 products (highest `product_id` first) with their category name, showing `'Uncategorised'` for the one without a category (`COALESCE`, Day 6).

   ```sh
   name              category
   ----------------  -------------
   Mystery Box       Toys
   Gift Card Holder  Uncategorised
   Mixed Nuts 500g   Grocery
   Olive Oil 500ml   Grocery
   (4 rows)
   ```

8. Library: which books have never been loaned? Order them by title.
9. Which employees manage nobody? Show name and title ordered by `employee_id`.
10. Count the rows of `customers LEFT JOIN orders` when the `status = 'cancelled'` condition is in `ON`, and again when it is in `WHERE`. Explain the two numbers.

    ```sh
    (62,) (24,)
    ```

11. Write the category/product-count query with a `RIGHT JOIN`: for each category (in `category_id` order) the number of products, so that Garden shows 0. Count a column of `products`, not `*`.
12. Using the toy `sizes` and `colours` tables from the lesson, produce all 6 combinations, ordered by colour and then `S`, `M`, `L`. (Hint: ordering the sizes needs a `CASE`.)
13. This query is meant to count customers while ignoring cancelled orders, and every customer should still be counted. It prints 54 instead of 60. Why? Fix it.

    ```sql
    SELECT COUNT(DISTINCT c.customer_id)
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE o.status <> 'cancelled'
    ```

    ```sh
    (54,)
    (60,)
    ```

### Exercises: Level 2

Make a copy of `shop.db` (as in the lesson) for any exercise that needs a helper table.

1. For every customer, count their orders, **including zeros**. Show the 8 customers with the fewest orders (ties by name). Also report how many customers have exactly zero.

   ```sh
   customer      orders
   ------------  ------
   Diego Scott   0
   Isla Clark    0
   Mia Thomas    0
   Sam Patel     0
   Sofia Green   0
   Tara Kim      0
   Olivia White  1
   Ethan Nguyen  2
   (8 rows)
   (6,)
   ```

2. Generate all combinations of the first three products (by `product_id`) and the months `2025-01`, `2025-02`, `2025-03` with a `CROSS JOIN`. Show the 9 rows, and then print how many rows you would get with *all* products and these months.

   ```sh
   product            month
   -----------------  -------
   Wireless Mouse     2025-01
   Wireless Mouse     2025-02
   Wireless Mouse     2025-03
   USB-C Cable        2025-01
   USB-C Cable        2025-02
   USB-C Cable        2025-03
   Bluetooth Speaker  2025-01
   Bluetooth Speaker  2025-02
   Bluetooth Speaker  2025-03
   (9 rows)
   (120,)
   ```

3. Library: which members have never borrowed a book?

   ```sh
   id  name
   --  -----------
   5   Elena Rossi
   (1 row)
   ```

4. In one query using `FULL OUTER JOIN`, list the products without a category together with the categories without products.

   ```sh
   product           category
   ----------------  --------
   Gift Card Holder  NULL
   NULL              Garden
   (2 rows)
   ```

5. Find the five cities with the most pairs of customers living there (every pair counted once). Ties by city.

   ```sh
   city     pairs
   -------  -----
   Lyon     36
   Austin   15
   Berlin   15
   London   15
   Seattle  15
   (5 rows)
   ```

6. For each employee who manages someone, show the number of direct reports. Most reports first, ties by name.

   ```sh
   manager            reports
   -----------------  -------
   Grace Hopper       3
   Alan Turing        2
   Barbara Liskov     2
   Linus Torvalds     2
   Margaret Hamilton  2
   Ada Lovelace       1
   Donald Knuth       1
   Edsger Dijkstra    1
   (8 rows)
   ```

7. For each product, count its **delivered** order lines (status `'delivered'`), including products with none. List the 5 with the fewest, ties by product name. Which exercise from Level 1 does this remind you of? Where does the `status` condition have to go?

   ```sh
   product          delivered_lines
   ---------------  ---------------
   Beanie           0
   Camping Hammock  0
   Jump Rope        0
   Mystery Box      0
   Chef's Knife     5
   (5 rows)
   ```

### Exercises: Level 3

1. **Monthly sales per category, with the zeros.** For every category and every month of 2025 show the revenue in dollars (two decimals) of non-cancelled orders; months without sales must appear with `0.00`. Build the 12 months in a helper table (in your copy of the database),
   `CROSS JOIN` it with `categories`, then `LEFT JOIN` the sales. Order by category name, then month. Show the first 12 rows, and report how many rows the full result has and how many of them are zero.

   Hint: after the grid, `LEFT JOIN` `products`, `order_items` and `orders` one after the other, and put the conditions on the order (not cancelled, same month) in the `ON` of the last join. Then sum only the lines whose order matched, for example with `SUM(CASE WHEN o.order_id IS NOT NULL THEN ... END)`.

   ```sh
   category        month    revenue
   --------------  -------  -------
   Books           2025-01  322.43
   Books           2025-02  149.97
   Books           2025-03  164.95
   Books           2025-04  319.91
   Books           2025-05  363.90
   Books           2025-06  547.84
   Books           2025-07  321.16
   Books           2025-08  140.70
   Books           2025-09  349.89
   Books           2025-10  436.14
   Books           2025-11  502.86
   Books           2025-12  677.07
   ...
   ```

   ```sh
   (96,)
   (15,)
   ```

2. Which products has **no customer from France** ever bought? List id and name. This is an anti-join where the "right side" is itself the result of a join. Think about where the `France` condition belongs.

   ```sh
   product_id  name
   ----------  ------------------
   6           Phone Stand
   13          Chef's Knife
   21          Remote Control Car
   27          Jump Rope
   28          Camping Hammock
   29          Cotton T-Shirt
   33          Beanie
   40          Mystery Box
   (8 rows)
   ```

3. Show every employee with their manager and their manager's manager (the "grand manager"), ordered by `employee_id`. Why do you need `LEFT JOIN` twice?

   ```sh
   employee           manager            grand_manager
   -----------------  -----------------  ---------------
   Grace Hopper       NULL               NULL
   Alan Turing        Grace Hopper       NULL
   Ada Lovelace       Grace Hopper       NULL
   Edsger Dijkstra    Grace Hopper       NULL
   Barbara Liskov     Alan Turing        Grace Hopper
   Donald Knuth       Alan Turing        Grace Hopper
   Margaret Hamilton  Ada Lovelace       Grace Hopper
   Linus Torvalds     Edsger Dijkstra    Grace Hopper
   Tim Berners-Lee    Barbara Liskov     Alan Turing
   Radia Perlman      Barbara Liskov     Alan Turing
   Ken Thompson       Donald Knuth       Alan Turing
   Hedy Lamarr        Margaret Hamilton  Ada Lovelace
   Katherine Johnson  Margaret Hamilton  Ada Lovelace
   Dennis Ritchie     Linus Torvalds     Edsger Dijkstra
   Annie Easley       Linus Torvalds     Edsger Dijkstra
   (15 rows)
   ```

Next: queries inside queries.

CONGRATULATIONS !

[<< Day 11](../11_Day_Inner_join/11_inner_join.md) | [Day 13 >>](../13_Day_Subqueries/13_subqueries.md)
