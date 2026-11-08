<div align="center">
  <h1> 30 Days Of SQL: Day 15 - Set Operations & Conditional Aggregation</h1>
</div>

[<< Day 14](../14_Day_CTEs_and_temp_tables/14_ctes_and_temp_tables.md) | [Day 16 >>](../16_Day_Dates_and_times/16_dates_and_times.md)

- [Day 15](#day-15)
  - [Set Operations](#set-operations)
    - [UNION and UNION ALL](#union-and-union-all)
    - [The Rules](#the-rules)
    - [Ordering a Union](#ordering-a-union)
    - [INTERSECT](#intersect)
    - [EXCEPT](#except)
    - [Operators Evaluate Left to Right](#operators-evaluate-left-to-right)
    - [Set Operation or Join?](#set-operation-or-join)
  - [Conditional Aggregation](#conditional-aggregation)
    - [SUM(CASE WHEN ...)](#sumcase-when-)
    - [FILTER (WHERE ...)](#filter-where-)
    - [Building a Pivot Table by Hand](#building-a-pivot-table-by-hand)
  - [ Exercises: Day 15](#exercises-day-15)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 15

## Set Operations

A join puts tables **side by side** (more columns). A set operation puts query results **on top of each other** (more rows). Think of two guest lists: `UNION` merges them, `INTERSECT` keeps the people on both, and `EXCEPT` keeps the people on the first list but not the second.

```py
import sqlite3
from helpers import show

conn = sqlite3.connect('data/shop.db')
```

### UNION and UNION ALL

```sql
-- syntax
SELECT columns FROM table_a
UNION
SELECT columns FROM table_b;

SELECT columns FROM table_a
UNION ALL
SELECT columns FROM table_b;
```

`UNION` stacks the results **and removes duplicate rows**. `UNION ALL` stacks them and keeps every row. Imagine you want one list of all the people the shop knows by name: customers and employees.

```py
show(conn.execute('''
    SELECT first_name || ' ' || last_name AS name, 'customer' AS kind FROM customers
    UNION ALL
    SELECT name, 'employee' FROM employees
    ORDER BY name
    LIMIT 5
'''))
```

```sh
name          kind
------------  --------
Ada Lovelace  employee
Alan Turing   employee
Amara Kim     customer
Annie Easley  employee
Ava Garcia    customer
(5 rows)
```

The column names of the result come from the **first** `SELECT`. Notice how we added a constant column `kind` to remember where each row came from: a very common trick. Now the difference between the two forms:

```py
print(conn.execute('SELECT COUNT(*) FROM (SELECT city FROM customers UNION ALL SELECT city FROM customers)').fetchone())
print(conn.execute('SELECT COUNT(*) FROM (SELECT city FROM customers UNION SELECT city FROM customers)').fetchone())
print(conn.execute('SELECT COUNT(DISTINCT city) FROM customers').fetchone())
```

```sh
(120,)
(11,)
(10,)
```

`UNION ALL` gives 120 (60 + 60). `UNION` removes duplicates and gives 11, because a `NULL` city counts as one distinct value in a set operation (`COUNT(DISTINCT)` skips `NULL`s and says 10). Removing duplicates costs work, since the database has to compare rows. **Use `UNION ALL`
unless you really need duplicates removed.**

### The Rules

1. Every `SELECT` must return the **same number of columns**.
2. Columns are matched **by position**, never by name.
3. The types of matching columns should be compatible. (SQLite is lenient and lets you stack numbers on text, other databases are not.)

```py
try:
    conn.execute('SELECT customer_id, first_name FROM customers UNION SELECT employee_id FROM employees')
except sqlite3.OperationalError as e:
    print(e)
# SELECTs to the left and right of UNION do not have the same number of result columns
```

**Common mistake:** swapping two columns in the second `SELECT`. It runs without an error and quietly puts emails in the name column:

```py
show(conn.execute('''
    SELECT email AS contact, first_name FROM customers WHERE customer_id = 2
    UNION ALL
    SELECT first_name, email FROM customers WHERE customer_id = 2
'''))
```

```sh
contact                   first_name
------------------------  ------------------------
diego.clark2@example.com  Diego
Diego                     diego.clark2@example.com
(2 rows)
```

### Ordering a Union

`ORDER BY` and `LIMIT` apply to the **whole** combined result, so they go at the very end, and they can only use the column names (or positions) of the result:

```py
show(conn.execute('''
    SELECT name, 'employee' AS kind FROM employees WHERE employee_id <= 2
    UNION ALL
    SELECT first_name, 'customer' FROM customers WHERE customer_id <= 2
    ORDER BY kind, name
'''))
```

```sh
name          kind
------------  --------
Chen          customer
Diego         customer
Alan Turing   employee
Grace Hopper  employee
(4 rows)
```

If each part needs its own filter or limit, wrap it in a subquery or a CTE.

### INTERSECT

`INTERSECT` returns the rows that appear in **both** results (duplicates removed). Which customers bought both "Python Crash Course" and "SQL for Data Analysis"?

```sql
-- syntax
SELECT columns FROM table_a
INTERSECT
SELECT columns FROM table_b;
```

```py
buyers = '''
    SELECT o.customer_id
    FROM orders AS o
    JOIN order_items AS i ON i.order_id = o.order_id
    JOIN products AS p ON p.product_id = i.product_id
    WHERE p.name = '{}'
'''
sql = buyers.format('Python Crash Course') + ' INTERSECT ' + buyers.format('SQL for Data Analysis') + ' ORDER BY 1'
print(conn.execute(sql).fetchall())
# [(15,), (24,), (31,)]
```

(Here we build the SQL text with `str.format` from **constants that we wrote ourselves** to avoid repeating a long block. Never do this with user input.)

### EXCEPT

`EXCEPT` returns the rows of the first result that are **not** in the second. It is the set version of `NOT IN` / `NOT EXISTS`, and the order matters: `A EXCEPT B` is not `B EXCEPT A`. Products that have never been ordered:

```sql
-- syntax
SELECT columns FROM table_a
EXCEPT
SELECT columns FROM table_b;
```

```py
show(conn.execute('''
    SELECT product_id FROM products
    EXCEPT
    SELECT product_id FROM order_items
    ORDER BY product_id
'''))
```

```sh
product_id
----------
27
28
33
40
(4 rows)
```

Unlike `NOT IN`, `EXCEPT` is not tripped up by `NULL`s: it treats two `NULL`s as equal.

### Operators Evaluate Left to Right

**Common mistake:** in standard SQL `INTERSECT` binds tighter than `UNION` and `EXCEPT`, like `*` before `+`. **SQLite evaluates all of them strictly left to right**, with no precedence. The same parts give different results depending on how they are grouped:

```py
print(conn.execute('SELECT 1 UNION SELECT 2 EXCEPT SELECT 2 INTERSECT SELECT 3').fetchall())
print(conn.execute('SELECT * FROM (SELECT 1 UNION SELECT 2) EXCEPT SELECT * FROM (SELECT 2 INTERSECT SELECT 3)').fetchall())
```

```sh
[]
[(1,), (2,)]
```

SQLite does not allow parentheses around the parts of a compound query, so when the order matters, make it explicit with subqueries in `FROM`, as on the second line. A database that follows the standard (PostgreSQL, for example) would give `[(1,), (2,)]` for the first query, like the second line.

> **In other databases:** Oracle calls `EXCEPT` **`MINUS`**. MySQL only got `INTERSECT` and `EXCEPT` in version 8.0.31. All databases have `UNION`/`UNION ALL`. MySQL has no `FULL OUTER JOIN`, and the classic workaround is exactly this: `LEFT JOIN ... UNION ... RIGHT JOIN ...`.

### Set Operation or Join?

Many "both" and "not in" questions can be answered either way. The set operations are shorter when the two sides are separate queries with the same shape. A join is better when you need extra columns from the matching rows. For instance, to find customers
who bought both books, a join, a `GROUP BY ... HAVING COUNT(DISTINCT ...) = 2` and `INTERSECT` all work. Try them in the exercises.

## Conditional Aggregation

On Day 7 you counted rows per group with `GROUP BY`. But sometimes you want several counts **side by side in one row**: delivered next to cancelled, 2024 next to 2025. The technique is to put a condition *inside* the aggregate function.

### SUM(CASE WHEN ...)

`CASE` (Day 6) returns 1 for the rows you want to count and 0 for the others; `SUM` then adds up the ones:

```sql
-- syntax
SELECT SUM(CASE WHEN condition THEN 1 ELSE 0 END) AS label
FROM table_name;
```

```py
show(conn.execute('''
    SELECT SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered,
           SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled
    FROM orders
'''))
```

```sh
delivered  cancelled
---------  ---------
346        24
(1 row)
```

The same works for amounts: `SUM(CASE WHEN condition THEN amount ELSE 0 END)`. Without the `ELSE 0`, the non-matching rows are `NULL`, and `SUM` ignores `NULL`s, which is also fine (but gives `NULL` instead of 0 if no row matches).
This pattern works in every database.

### FILTER (WHERE ...)

Since SQLite 3.30 there is a shorter, standard way: put `FILTER (WHERE condition)` after any aggregate function. The function only sees the rows that satisfy the condition.

```sql
-- syntax
SELECT COUNT(*) FILTER (WHERE condition) AS label
FROM table_name;
```

```py
show(conn.execute('''
    SELECT COUNT(*) FILTER (WHERE status = 'delivered') AS delivered,
           COUNT(*) FILTER (WHERE status = 'shipped')   AS shipped,
           COUNT(*) FILTER (WHERE status = 'pending')   AS pending,
           COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
           COUNT(*)                                     AS total
    FROM orders
'''))
```

```sh
delivered  shipped  pending  cancelled  total
---------  -------  -------  ---------  -----
346        14       15       24         399
(1 row)
```

`FILTER` reads like English and works with any aggregate (`SUM`, `AVG`, `MAX`, `string_agg`, ...). The `CASE` form still matters, because MySQL and SQL Server do not have `FILTER` and you will meet `SUM(CASE ...)` in almost all existing code.

> **In other databases:** `FILTER (WHERE ...)` is standard SQL and works in PostgreSQL and DuckDB. MySQL and SQL Server need `SUM(CASE WHEN ...)`. Some databases also have a `PIVOT` keyword (SQL Server, Oracle, DuckDB). SQLite does not, so we build the pivot by hand.

### Building a Pivot Table by Hand

A **pivot table** turns the values of one column into column headings. Say you want a table with one row per status and one column per year, instead of a long list of `(status, year, count)` rows. Combine `GROUP BY` with conditional aggregation:

```py
show(conn.execute('''
    SELECT status,
           COUNT(*) FILTER (WHERE order_date <  '2025-01-01') AS y2024,
           COUNT(*) FILTER (WHERE order_date >= '2025-01-01') AS y2025,
           COUNT(*)                                          AS total
    FROM orders
    GROUP BY status
    ORDER BY total DESC
'''))
```

```sh
status     y2024  y2025  total
---------  -----  -----  -----
delivered  167    179    346
cancelled  14     10     24
pending    0      15     15
shipped    0      14     14
(4 rows)
```

`GROUP BY` makes the rows (one per status); one `FILTER` per year makes the columns. The catch is that **you must know the columns in advance**: SQL cannot create a variable number of columns on its own. If a 2026 appears, you add another line. That limitation is the reason DuckDB has a real `PIVOT` command (Day 25).

Percentages come easily, too, because a count divided by the total is a ratio: `100.0 * COUNT(*) FILTER (WHERE ...) / COUNT(*)`. Use `100.0`, not `100`, so that the division is not an integer division (Day 1).

You can now stack, intersect and subtract query results, and turn rows into columns. Next, do some exercises.

## Exercises: Day 15

### Exercises: Level 1

Questions 8 to 10 use your `00_practice/library.db`; the others use `shop.db`.

1. Make one list of all the names of customers (first and last name) and employees, without duplicates, alphabetically. Show the first 5, and print how many names there are in total.

   ```sh
   name
   ------------
   Ada Lovelace
   Alan Turing
   Amara Kim
   Annie Easley
   Ava Garcia
   (5 rows)
   (73,)
   ```

2. Count the rows of `SELECT city FROM customers` stacked on itself with `UNION ALL`, and with `UNION`, and compare with `COUNT(DISTINCT city)`. Explain the three numbers.

   ```sh
   (120,) (11,) (10,)
   ```

3. Use `EXCEPT` to list the ids of the products that have never been ordered.

   ```sh
   product_id
   ----------
   27
   28
   33
   40
   (4 rows)
   ```

4. How many products were ordered both before 2025 and in 2025? (`INTERSECT`, with a join in each part.)

   ```sh
   (36,)
   ```

5. In one row, count the delivered orders and the cancelled orders, using `SUM(CASE ...)`.

   ```sh
   delivered  cancelled
   ---------  ---------
   346        24
   (1 row)
   ```

6. Run `SELECT customer_id, first_name FROM customers UNION SELECT employee_id FROM employees`. Which rule did you break?

   ```sh
   SELECTs to the left and right of UNION do not have the same number of result columns
   ```

7. Show the employees with ids 1 and 2 and the customers with ids 1 and 2 in one list with a `kind` column, ordered by kind and then name. Keep every row.

   ```sh
   label         kind
   ------------  --------
   Chen          customer
   Diego         customer
   Alan Turing   employee
   Grace Hopper  employee
   (4 rows)
   ```

8. Library: one alphabetical list of member names and author names with a `role` column; show the first 6.

   ```sh
   name           role
   -------------  ------
   Aldous Huxley  author
   Alice Nguyen   member
   Andrew Hunt    author
   Andy Weir      author
   Bruno Silva    member
   Chloe Martin   member
   (6 rows)
   ```

9. Library: the titles of the books that were never loaned, using `EXCEPT` on ids (hint: the `EXCEPT` goes in a subquery used with `IN`).

   ```sh
   title
   --------------------
   Brave New World
   Emma
   Project Hail Mary
   The Name of the Wind
   (4 rows)
   ```

10. Library: in one row, count the short (under 300 pages), medium (300 to 500) and long (over 500) books.

    ```sh
    short  medium  long
    -----  ------  ----
    2      8       2
    (1 row)
    ```

11. In one row, count the orders in each of the four statuses and the total, using `FILTER`.

    ```sh
    delivered  shipped  pending  cancelled  total
    ---------  -------  -------  ---------  -----
    346        14       15       24         399
    (1 row)
    ```

12. In your own words: what is the difference between `UNION` and `UNION ALL`, and which should be your default?
13. Run the swapped-columns query from the lesson (the customer with id 2: email and first name, then first name and email). Why did the database not complain?

    ```sh
    contact                   first_name
    ------------------------  ------------------------
    diego.clark2@example.com  Diego
    Diego                     diego.clark2@example.com
    (2 rows)
    ```

### Exercises: Level 2

1. **A pivot table.** For each order status show the number of orders in 2024 and in 2025 and the total, most orders first. Do it once with `FILTER` and once with `SUM(CASE ...)` and check that they agree.

   ```sh
   status     y2024  y2025  total
   ---------  -----  -----  -----
   delivered  167    179    346
   cancelled  14     10     24
   pending    0      15     15
   shipped    0      14     14
   (4 rows)
   status     y2024  y2025  total
   ---------  -----  -----  -----
   delivered  167    179    346
   cancelled  14     10     24
   pending    0      15     15
   shipped    0      14     14
   (4 rows)
   ```

2. Customers who bought both "Python Crash Course" and "SQL for Data Analysis": solve it with `INTERSECT`, with a join of two derived tables, and with `GROUP BY ... HAVING COUNT(DISTINCT ...) = 2`. Print the ids from the first, and whether the other two give the same list.

   ```sh
   [(15,), (24,), (31,)]
   True 3
   True
   ```

3. Reproduce Day 12's two problem rows (the product without a category and the category without products) **without** `FULL OUTER JOIN`: a `LEFT JOIN` anti-join `UNION ALL` the other anti-join. Fill the missing side with `NULL`.

   ```sh
   product           category
   ----------------  --------
   Gift Card Holder  NULL
   NULL              Garden
   (2 rows)
   ```

4. A pivot of revenue (non-cancelled orders, in dollars): one row per customer country, one column each for Books, Toys, "other" (all remaining categories) and the total. Highest total first. (`SUM(...) FILTER (WHERE ...)`.)

   ```sh
   country  books    toys     other    total
   -------  -------  -------  -------  --------
   USA      2298.15  1437.49  8943.71  12679.35
   Canada   1448.56  1332.31  6923.52  9704.39
   France   1422.62  909.43   5987.31  8319.36
   UK       1334.39  1162.63  5343.32  7840.34
   Germany  1360.38  1251.08  3411.85  6023.31
   (5 rows)
   ```

5. A small summary report with a row per table: `customers`, `products`, `orders`, `order lines`, `employees` and the number of rows of each. (`UNION ALL` of five queries.)

   ```sh
   what         n
   -----------  ---
   customers    60
   products     40
   orders       399
   order lines  984
   employees    15
   (5 rows)
   ```

6. For each month of 2025: the number of orders, the number of cancelled orders, and the percentage of cancelled orders with one decimal.

   ```sh
   month    orders  cancelled  cancelled_pct
   -------  ------  ---------  -------------
   2025-01  20      4          20.0
   2025-02  12      1          8.3
   2025-03  12      0          0.0
   2025-04  14      0          0.0
   2025-05  23      3          13.0
   2025-06  13      0          0.0
   2025-07  13      0          0.0
   2025-08  12      0          0.0
   2025-09  13      0          0.0
   2025-10  20      1          5.0
   2025-11  31      0          0.0
   2025-12  35      1          2.9
   (12 rows)
   ```

7. Without `FULL OUTER JOIN`, the number of rows of "all customers and all orders side by side" is `LEFT JOIN ... UNION ... LEFT JOIN` with the tables swapped. Check that it gives the same count as `FULL OUTER JOIN`.

   ```sh
   (405,) (405,)
   ```

### Exercises: Level 3

1. **Hacker News, one query.** Count the lines mentioning Python, JavaScript and "Java but not JavaScript". Do it in SQL, in **one query** that returns one row with three columns. Look at the titles only, ignoring case. (Searching titles only will give smaller numbers than searching whole lines.)

   ```sh
   python  javascript  java_only
   ------  ----------  ---------
   160     170         57
   (1 row)
   python  javascript  java_only
   ------  ----------  ---------
   160     170         57
   (1 row)
   ```

   The two versions (`FILTER` and `SUM(CASE ...)` or `SUM(boolean)`) must give the same row.

2. For each product category: the number of orders that contain it, how many of those were delivered, how many were cancelled, and the percentage cancelled (one decimal). Count each order once per category (`COUNT(DISTINCT order_id)`), and order by cancelled percentage, highest first.

   ```sh
   category        delivered  cancelled  orders  cancelled_pct
   --------------  ---------  ---------  ------  -------------
   Home & Kitchen  96         10         115     8.7
   Grocery         145        13         171     7.6
   Electronics     116        8          133     6.0
   Sports          101        5          117     4.3
   Books           119        5          131     3.8
   Toys            102        3          116     2.6
   Clothing        42         7          51      13.7
   (7 rows)
   ```

3. **Customer retention with set operations.** Using `INTERSECT`, `EXCEPT` and `UNION` on the sets of customers who ordered in 2024 and in 2025, report in one result: the customers who ordered in both years, the "lost" ones (2024 only), the "new" ones (2025 only) and how many ever ordered.

   ```sh
   segment           customers
   ----------------  ---------
   both years        45
   lost (2024 only)  3
   new (2025 only)   6
   ever ordered      54
   (4 rows)
   ```

Tomorrow: dates, the topic that every real dataset has and every beginner dreads.

CONGRATULATIONS !

[<< Day 14](../14_Day_CTEs_and_temp_tables/14_ctes_and_temp_tables.md) | [Day 16 >>](../16_Day_Dates_and_times/16_dates_and_times.md)
