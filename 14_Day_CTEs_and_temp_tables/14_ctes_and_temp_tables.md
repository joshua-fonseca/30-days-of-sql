<div align="center">
  <h1> 30 Days Of SQL: Day 14 - CTEs & Temporary Tables</h1>
</div>

[<< Day 13](../13_Day_Subqueries/13_subqueries.md) | [Day 15 >>](../15_Day_Set_operations/15_set_operations.md)

- [Day 14](#day-14)
  - [CTEs: Naming the Steps of a Query](#ctes-naming-the-steps-of-a-query)
    - [WITH](#with)
    - [Refactoring a Nested Subquery](#refactoring-a-nested-subquery)
    - [Several CTEs, and CTEs That Use Earlier CTEs](#several-ctes-and-ctes-that-use-earlier-ctes)
  - [Recursive CTEs](#recursive-ctes)
    - [Generating a Series of Numbers](#generating-a-series-of-numbers)
    - [Generating Dates](#generating-dates)
    - [Walking a Hierarchy](#walking-a-hierarchy)
  - [Temporary Tables](#temporary-tables)
    - [CREATE TEMP TABLE](#create-temp-table)
    - [CREATE TABLE ... AS SELECT](#create-table--as-select)
    - [Where Temp Tables Live](#where-temp-tables-live)
    - [Lifetime: Only This Connection](#lifetime-only-this-connection)
    - [Shadowing](#shadowing)
    - [Indexing a Temp Table](#indexing-a-temp-table)
  - [CTE or Temp Table?](#cte-or-temp-table)
  - [ Exercises: Day 14](#exercises-day-14)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 14

## CTEs: Naming the Steps of a Query

### WITH

Yesterday's last query repeated an inner query twice and was hard to read. A **CTE** (Common Table Expression) fixes that: you give a query a name with `WITH`, then use the name like a table in the main query. It is a variable for a result, and it makes
the query read from top to bottom like a recipe.

```sql
-- syntax
WITH name AS (
    SELECT ...
)
SELECT ...
FROM name;
```

```py
import sqlite3
from helpers import show

conn = sqlite3.connect('data/shop.db')
show(conn.execute('''
    WITH order_totals AS (
        SELECT order_id, SUM(quantity * unit_price_cents) AS total_cents
        FROM order_items
        GROUP BY order_id
    )
    SELECT order_id, format('%.2f', total_cents / 100.0) AS total
    FROM order_totals
    ORDER BY total_cents DESC, order_id
    LIMIT 3
'''))
```

```sh
order_id  total
--------  ------
48        624.93
304       623.93
245       599.93
(3 rows)
```

The CTE `order_totals` exists **only for this one statement**. It is not stored anywhere (we come to storing results in a moment). The database is free to run it the way it likes: a CTE is for readability, not a performance trick.

### Refactoring a Nested Subquery

Remember the derived-table query from Day 13, "customers whose spend is above the average spend"? Here it is as a CTE. The inner query is written **once** and used twice:

```py
show(conn.execute('''
    WITH spend AS (
        SELECT o.customer_id, SUM(i.quantity * i.unit_price_cents) AS spend_cents
        FROM orders AS o
        JOIN order_items AS i ON i.order_id = o.order_id
        GROUP BY o.customer_id
    )
    SELECT c.first_name || ' ' || c.last_name AS customer, s.spend_cents
    FROM spend AS s
    JOIN customers AS c ON c.customer_id = s.customer_id
    WHERE s.spend_cents > (SELECT AVG(spend_cents) FROM spend)
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

Compare it with Day 13: same answer, but now each part has a name, and a reader can follow it step by step. A good rule: **if a subquery is nested more than one level deep or used twice, make it a CTE.**

### Several CTEs, and CTEs That Use Earlier CTEs

Separate several CTEs with commas (only one `WITH`). Each CTE may use the ones defined **before** it. This is how you write a data pipeline: customers → orders → spend → tier.

```sql
-- syntax
WITH
step_one AS (SELECT ...),
step_two AS (SELECT ... FROM step_one ...),
step_three AS (SELECT ... FROM step_two ...)
SELECT ... FROM step_three;
```

```py
show(conn.execute('''
    WITH
    paid_orders AS (
        SELECT o.order_id, o.customer_id, SUM(i.quantity * i.unit_price_cents) AS total_cents
        FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.order_id
    ),
    customer_stats AS (
        SELECT customer_id, COUNT(*) AS orders, SUM(total_cents) AS spend_cents
        FROM paid_orders
        GROUP BY customer_id
    ),
    labelled AS (
        SELECT customer_id, orders, spend_cents,
               CASE WHEN orders >= 10 THEN 'frequent' ELSE 'occasional' END AS kind
        FROM customer_stats
    )
    SELECT kind, COUNT(*) AS customers, format('%.2f', AVG(spend_cents) / 100.0) AS avg_spend
    FROM labelled
    GROUP BY kind
    ORDER BY kind
'''))
```

```sh
kind        customers  avg_spend
----------  ---------  ---------
frequent    15         1511.43
occasional  39         570.80
(2 rows)
```

**Common mistake:** a CTE can only use CTEs defined *above* it, not below. And a CTE cannot be used in a *second* statement: when the statement ends, the name is gone.

## Recursive CTEs

A CTE can refer to **itself**. This sounds like magic, but it is just a loop: start with some rows, then repeatedly use the rows you got last time to make new ones, until nothing new appears. You write it in two parts joined by `UNION ALL`
(Day 15 explains `UNION` properly; for now read it as "and then add these rows"):

```sql
-- syntax
WITH RECURSIVE name(columns) AS (
    SELECT ...                 -- the anchor: where we start
    UNION ALL
    SELECT ... FROM name ...   -- the recursive step: uses the previous rows of 'name'
    WHERE ...                  -- the stop condition
)
SELECT ... FROM name;
```

### Generating a Series of Numbers

This is the `while` loop of SQL. Start at 1, add 1 each time, stop at 10. It is what Python's `range(1, 11)` does:

```py
show(conn.execute('''
    WITH RECURSIVE n(x) AS (
        SELECT 1                              -- anchor
        UNION ALL
        SELECT x + 1 FROM n WHERE x < 10      -- step, with a stop condition
    )
    SELECT x, x * x AS square FROM n
    LIMIT 5
'''))
```

```sh
x  square
-  ------
1  1
2  4
3  9
4  16
5  25
(5 rows)
```

(The comments `--` inside the SQL are fine.) Round by round: the anchor gives `1`. The step sees the row `1` and produces `2`. Then it sees `2` and produces `3`, and so on, until `x < 10` is false and no new row is produced.

**Common mistake:** forgetting the stop condition. Then the recursion never ends and your program hangs. As a seat belt, add a `LIMIT` to the final `SELECT` while you are experimenting; SQLite stops asking for rows once the limit is reached.

### Generating Dates

The same trick makes a calendar. SQLite's `date(x, '+1 day')` adds a day to a date (Day 16 is all about dates; for now just use it). A calendar table is how you get rows for days that had no data:

```py
show(conn.execute('''
    WITH RECURSIVE d(day) AS (
        SELECT '2025-01-01'
        UNION ALL
        SELECT date(day, '+1 day') FROM d WHERE day < '2025-01-31'
    )
    SELECT COUNT(*) AS days, MIN(day) AS first_day, MAX(day) AS last_day FROM d
'''))
```

```sh
days  first_day   last_day
----  ----------  ----------
31    2025-01-01  2025-01-31
(1 row)
```

Because dates are ISO text (`YYYY-MM-DD`), comparing them with `<` works as you'd hope. The exercises combine this calendar with a `LEFT JOIN` to report zero-revenue days.

### Walking a Hierarchy

Yesterday's self join could only reach a fixed number of levels. A recursive CTE follows a chain of **any** length. The anchor is the CEO (the employee with no manager), and each step adds the people who report to someone already found, and counts the level:

```py
show(conn.execute('''
    WITH RECURSIVE org(employee_id, name, level) AS (
        SELECT employee_id, name, 1
        FROM employees
        WHERE manager_id IS NULL
        UNION ALL
        SELECT e.employee_id, e.name, o.level + 1
        FROM employees AS e
        JOIN org AS o ON e.manager_id = o.employee_id
    )
    SELECT level, COUNT(*) AS people, group_concat(name, ', ') AS names
    FROM org
    GROUP BY level
    ORDER BY level
'''))
```

```sh
level  people  names
-----  ------  ----------------------------------------------------------------------------------------------------------
1      1       Grace Hopper
2      3       Ada Lovelace, Alan Turing, Edsger Dijkstra
3      4       Margaret Hamilton, Barbara Liskov, Donald Knuth, Linus Torvalds
4      7       Hedy Lamarr, Katherine Johnson, Radia Perlman, Tim Berners-Lee, Ken Thompson, Annie Easley, Dennis Ritchie
(4 rows)
```

The `JOIN org` is the key line: "find employees whose manager is already in `org`". You can carry any extra information down the tree, such as a **path** that grows at each level:

```py
show(conn.execute('''
    WITH RECURSIVE org(employee_id, name, level, path) AS (
        SELECT employee_id, name, 1, name
        FROM employees
        WHERE manager_id IS NULL
        UNION ALL
        SELECT e.employee_id, e.name, o.level + 1, o.path || ' > ' || e.name
        FROM employees AS e
        JOIN org AS o ON e.manager_id = o.employee_id
    )
    SELECT name, level, path
    FROM org
    WHERE level >= 3
    ORDER BY path
    LIMIT 4
'''))
```

```sh
name               level  path
-----------------  -----  -------------------------------------------------------------------
Margaret Hamilton  3      Grace Hopper > Ada Lovelace > Margaret Hamilton
Hedy Lamarr        4      Grace Hopper > Ada Lovelace > Margaret Hamilton > Hedy Lamarr
Katherine Johnson  4      Grace Hopper > Ada Lovelace > Margaret Hamilton > Katherine Johnson
Barbara Liskov     3      Grace Hopper > Alan Turing > Barbara Liskov
(4 rows)
```

> **In other databases:** PostgreSQL, MySQL 8, DuckDB, Oracle and SQL Server all support recursive CTEs. The keyword `RECURSIVE` is required in SQLite, PostgreSQL, MySQL and DuckDB, but SQL Server and Oracle leave it out (and SQL Server uses `UNION ALL` the same way).

## Temporary Tables

### CREATE TEMP TABLE

A CTE disappears after one statement. Sometimes you want to compute something **once**, then ask several questions about it. For that you store the intermediate result in a **temporary table**: a real table that only you can see, and that SQLite deletes for you.

```sql
-- syntax
CREATE TEMP TABLE table_name (column1 TYPE, column2 TYPE);
-- or, from a query:
CREATE TEMP TABLE table_name AS SELECT ...;
```

### CREATE TABLE ... AS SELECT

`CREATE TABLE ... AS SELECT` (often shortened to **CTAS**) creates a table and fills it with the result of a query in one go. The column names come from the query, so give computed columns an alias.

```py
conn.execute('''
    CREATE TEMP TABLE customer_spend AS
    SELECT c.customer_id,
           c.first_name || ' ' || c.last_name AS customer,
           c.country,
           SUM(i.quantity * i.unit_price_cents) AS spend_cents
    FROM customers AS c
    JOIN orders      AS o ON o.customer_id = c.customer_id
    JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.status <> 'cancelled'
    GROUP BY c.customer_id
''')
print(conn.execute('SELECT COUNT(*) FROM customer_spend').fetchone())
# (54,)
```

The join ran **once**. Now several questions can be answered from the small table without repeating the join:

```py
show(conn.execute('''
    SELECT country, COUNT(*) AS customers, format('%.2f', SUM(spend_cents) / 100.0) AS total
    FROM customer_spend GROUP BY country ORDER BY SUM(spend_cents) DESC
'''))
show(conn.execute('SELECT customer, spend_cents FROM customer_spend ORDER BY spend_cents LIMIT 3'))
```

```sh
country  customers  total
-------  ---------  --------
USA      15         12715.29
Canada   10         9762.49
France   9          8401.72
UK       14         7982.30
Germany  6          6070.93
(5 rows)
customer      spend_cents
------------  -----------
Olivia Scott  2999
Ryan Baker    3397
Omar Lopez    8814
(3 rows)
```

A table made with CTAS has the column names but **no constraints**: no primary key, no `NOT NULL`, no `CHECK`. That's fine for a scratch table. For a permanent table you would write the `CREATE TABLE` yourself (Day 2) and use `INSERT INTO ... SELECT` (Day 10).

> **In other databases:** `CREATE TABLE ... AS SELECT` works in SQLite, PostgreSQL, MySQL, Oracle and DuckDB. SQL Server and MS Access write it as **`SELECT ... INTO new_table FROM ...`** instead, and that form is what W3Schools teaches. Temp tables in SQL Server are named with a `#` prefix (`#spend`), and in MySQL/PostgreSQL you also write `CREATE TEMPORARY TABLE`. SQLite accepts both `TEMP` and `TEMPORARY`.

### Where Temp Tables Live

Temp tables live in a separate, hidden database called **`temp`**, next to `main` (your real file). Each has its own catalogue table (the `sqlite_master` you met on Day 2):

```py
show(conn.execute('SELECT type, name FROM temp.sqlite_master'))
show(conn.execute("SELECT type, name FROM main.sqlite_master WHERE name = 'customer_spend'"))
```

```sh
type   name
-----  --------------
table  customer_spend
(1 row)
type  name
----  ----
(0 rows)
```

Our table is in `temp`, and nothing was added to the real database (the query on `main` finds no rows). You can also write `temp.customer_spend` to be explicit.

### Lifetime: Only This Connection

A temp table belongs to the **connection** that created it. Another connection to the very same file cannot see it, and when the connection closes, the table is dropped. Let's prove both:

```py
other = sqlite3.connect('data/shop.db')
try:
    other.execute('SELECT COUNT(*) FROM customer_spend')
except sqlite3.OperationalError as e:
    print('second connection:', e)
other.close()

conn.close()
conn = sqlite3.connect('data/shop.db')
try:
    conn.execute('SELECT COUNT(*) FROM customer_spend')
except sqlite3.OperationalError as e:
    print('after reopening:', e)
```

```sh
second connection: no such table: customer_spend
after reopening: no such table: customer_spend
```

This is a feature. Temp tables never clutter the real database, and two programs working at the same time cannot trip over each other's scratch tables. It also means that you can `CREATE TEMP TABLE` on a database you opened read-only.

### Shadowing

**Common mistake:** a temp table with the same name as a real table **hides** the real one. When SQLite looks up a name, it checks `temp` first.

```py
conn.execute("CREATE TEMP TABLE products AS SELECT 1 AS product_id, 'oops' AS name")
print(conn.execute('SELECT COUNT(*) FROM products').fetchone())
print(conn.execute('SELECT COUNT(*) FROM main.products').fetchone())
conn.execute('DROP TABLE temp.products')
print(conn.execute('SELECT COUNT(*) FROM products').fetchone())
```

```sh
(1,)
(40,)
(40,)
```

The unqualified `products` silently meant the temp table. Writing `main.products` reaches the real one. Avoid reusing real names, and prefer names like `tmp_orders`.

### Indexing a Temp Table

A temp table is an ordinary table, so you can index it (Day 21 explains indexes properly: the short version is "a sorted lookup structure that makes searching faster"). It is worth it when you will query a big temp table several times. The index goes in the `temp` schema too:

```py
conn.execute('''
    CREATE TEMP TABLE lines_2025 AS
    SELECT o.order_id, o.order_date, i.product_id, i.quantity * i.unit_price_cents AS cents
    FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
    WHERE o.order_date >= '2025-01-01' AND o.status <> 'cancelled'
''')
conn.execute('CREATE INDEX temp.idx_lines_product ON lines_2025 (product_id)')
print(conn.execute('SELECT COUNT(*) FROM lines_2025').fetchone())
for row in conn.execute('EXPLAIN QUERY PLAN SELECT SUM(cents) FROM lines_2025 WHERE product_id = 5'):
    print(row[3])
```

```sh
(519,)
SEARCH lines_2025 USING INDEX idx_lines_product (product_id=?)
```

(`EXPLAIN QUERY PLAN` asks SQLite how it would run a query without running it; Day 21 covers it in depth.) `SEARCH ... USING INDEX` means SQLite jumped straight to the right rows instead of scanning the whole table (`SCAN`). A CTE cannot be indexed, because it is not stored. You can also `INSERT`, `UPDATE` and `DELETE` on a temp table, and drop it early with `DROP TABLE`.

## CTE or Temp Table?

| | CTE | Temp table |
|---|---|---|
| Lives for | one statement | until the connection closes (or `DROP`) |
| Stored? | no (it is a name for a query) | yes, in the `temp` database |
| Reusable in many statements | no | yes |
| Can be indexed | no | yes |
| Can be modified (`INSERT`, `UPDATE`, `DELETE`) | no | yes |
| Appears in the schema | no | yes, in `temp.sqlite_master` |
| Recursion | yes | no (but you can store a recursive result in one) |
| Best for | readability inside one query | reusing an expensive result, debugging a step, indexing |

Reach for a **CTE** first: it needs no clean-up and it reads well. Switch to a **temp table** when (a) several later queries reuse the same intermediate result, (b) you want to look at the data of a step while debugging, or (c) an expensive step should not be recomputed
every time. Day 22 introduces **views**, a third option (a saved query with a permanent name), and finishes this table.

You can now give every step of a query a name, loop in SQL, and keep scratch results around. Next, do some exercises.

## Exercises: Day 14

### Exercises: Level 1

Questions 4 and 5 use your `00_practice/library.db`, the others `shop.db`. Temp tables never change the file, so you can use `shop.db` directly.

1. Rewrite yesterday's "customers above average spend" query as a CTE (non-cancelled orders, 3 biggest spenders, spend in dollars).

   ```sh
   customer     spend
   -----------  -------
   Lena Green   2214.60
   Amara Kim    2045.68
   Ines Martin  2044.41
   (3 rows)
   ```

2. Generate the numbers 1 to 10 with a recursive CTE and print them on one line with `group_concat(x, ' ')`.

   ```sh
   1 2 3 4 5 6 7 8 9 10
   ```

3. Generate all dates in January 2025 and report how many there are, with the first and the last.

   ```sh
   days  first_day   last_day
   ----  ----------  ----------
   31    2025-01-01  2025-01-31
   (1 row)
   ```

4. Library: create a temp table `unread_books` holding the books that have never been loaned. Print how many it has. Open a second connection to the same file and prove that it cannot see the table. Then close the first connection, reopen the file and prove that the table is gone.

   ```sh
   (4,)
   second connection: no such table: unread_books
   after reopening: no such table: unread_books
   ```

5. In your own words: when would you choose a temp table over a CTE?
6. Use two CTEs: `per_category` (the number of products and the average price in cents of every category) and `big` (the categories with 6 or more products). Show the name, product count and average price (a whole number of cents) of the big categories.

   ```sh
   name            products  avg_cents
   --------------  --------  ---------
   Books           6         3216
   Electronics     6         5166
   Home & Kitchen  6         3449
   Sports          6         3449
   (4 rows)
   ```

7. Create a temp table `top_products` of the products costing more than 5000 cents. Show that it is in `temp.sqlite_master` and not in `main.sqlite_master`.

   ```sh
   type   name
   -----  ------------
   table  top_products
   (1 row)
   type  name
   ----  ----
   (0 rows)
   ```

8. Create a temp table called `products` (just one row), count `products` and `main.products`, then drop it and count again. What did you learn?

   ```sh
   (1,) (40,)
   (40,)
   ```

9. **(Stretch: uses the index idea from the end of this lesson; Day 21 covers it fully.)** Create a temp table `lines_2025` with the order lines of 2025 (non-cancelled orders; `order_id`, `order_date`, `product_id` and `cents = quantity * unit_price_cents`), index `product_id`, and check with `EXPLAIN QUERY PLAN` that a lookup by product uses the index.

   ```sh
   name               tbl_name
   -----------------  ----------
   idx_lines_product  lines_2025
   (1 row)
   (519,)
   SEARCH lines_2025 USING INDEX idx_lines_product (product_id=?)
   ```

10. With a CTE `totals` (the total of every order), list the 3 biggest orders.

    ```sh
    order_id  total
    --------  ------
    48        624.93
    304       623.93
    245       599.93
    (3 rows)
    ```

11. Generate the squares of 1 to 10 with a recursive CTE (two columns `n` and `square`) and print the squares on one line.

    ```sh
    1, 4, 9, 16, 25, 36, 49, 64, 81, 100
    ```

12. Count down from 5 to 0 with a recursive CTE.

    ```sh
    5 4 3 2 1 0
    ```

### Exercises: Level 2

1. **Org chart.** List every employee with their level (CEO = 1) and the chain of titles from the CEO down to them (like `CEO > VP Sales > Sales Manager`). Order by the chain, then by `employee_id`. Indent the names by two spaces per level below the CEO
   (`printf('%*s%s', (level - 1) * 2, '', name)`).

   ```sh
   employee                 level  chain
   -----------------------  -----  --------------------------------------------------------------
   Grace Hopper             1      CEO
     Alan Turing            2      CEO > VP Engineering
       Barbara Liskov       3      CEO > VP Engineering > Engineering Manager
       Donald Knuth         3      CEO > VP Engineering > Engineering Manager
         Tim Berners-Lee    4      CEO > VP Engineering > Engineering Manager > Software Engineer
         Radia Perlman      4      CEO > VP Engineering > Engineering Manager > Software Engineer
         Ken Thompson       4      CEO > VP Engineering > Engineering Manager > Software Engineer
     Edsger Dijkstra        2      CEO > VP Operations
       Linus Torvalds       3      CEO > VP Operations > Warehouse Manager
         Dennis Ritchie     4      CEO > VP Operations > Warehouse Manager > Warehouse Associate
         Annie Easley       4      CEO > VP Operations > Warehouse Manager > Warehouse Associate
     Ada Lovelace           2      CEO > VP Sales
       Margaret Hamilton    3      CEO > VP Sales > Sales Manager
         Hedy Lamarr        4      CEO > VP Sales > Sales Manager > Sales Associate
         Katherine Johnson  4      CEO > VP Sales > Sales Manager > Sales Associate
   (15 rows)
   ```

2. **Three-step CTE.** Build `paid_orders` (non-cancelled order totals), `customer_spend` (per customer: orders and spend) and `tiers` (`gold` from 1000.00 dollars, `silver` from 400.00, otherwise `bronze`). Show for each tier the number of customers and their average spend, gold first.

   ```sh
   tier    customers  avg_spend
   ------  ---------  ---------
   gold    20         1484.62
   silver  16         703.09
   bronze  18         221.71
   (3 rows)
   ```

3. Save the `customer_spend` step as a temp table (with the customer's name and country, the number of orders and the spend). Then answer these from the temp table, without repeating the joins: the top 3 spenders; the number of customers and average spend by country (highest average first);
   and the 3 customers with at least 8 orders with the highest average spend per order.

   ```sh
   (54,)
   -- top 3
   customer     spend
   -----------  -------
   Lena Green   2214.60
   Amara Kim    2045.68
   Ines Martin  2044.41
   (3 rows)
   -- per country
   country  customers  avg_spend
   -------  ---------  ---------
   Germany  6          1011.82
   Canada   10         976.25
   France   9          933.52
   USA      15         847.69
   UK       14         570.16
   (5 rows)
   -- orders vs spend
   customer     orders  per_order
   -----------  ------  ---------
   Lena Scott   8       205.85
   Priya Brown  11      141.40
   Lena Green   16      138.41
   (3 rows)
   ```

4. Generate the powers of 2 up to 1000 (1, 2, 4, ...) with a recursive CTE.

   ```sh
   1 2 4 8 16 32 64 128 256 512
   ```

5. List Alan Turing and everybody who works under him, directly or indirectly, with the depth below him (he is 0). Order by depth, then name.

   ```sh
   name             depth
   ---------------  -----
   Alan Turing      0
   Barbara Liskov   1
   Donald Knuth     1
   Ken Thompson     2
   Radia Perlman    2
   Tim Berners-Lee  2
   (6 rows)
   ```

6. For every employee who manages someone: the number of people below them (directly and indirectly) and the total payroll of the team, **including the manager** in dollars. Most people first, ties by name.
   (Hint: a recursive CTE with a `top_id` column that you carry down unchanged.)

   ```sh
   manager            people_below  team_payroll
   -----------------  ------------  ------------
   Grace Hopper       14            1450000.00
   Alan Turing        5             610000.00
   Ada Lovelace       3             343000.00
   Edsger Dijkstra    3             312000.00
   Barbara Liskov     2             276000.00
   Linus Torvalds     2             182000.00
   Margaret Hamilton  2             208000.00
   Donald Knuth       1             194000.00
   (8 rows)
   ```

### Exercises: Level 3

1. **Daily revenue for every day of 2025, including the days with no sales.** Generate the calendar with a recursive CTE, `LEFT JOIN` the revenue of non-cancelled orders per day, and show 0 for empty days. Print the first 6 days, then the number of days, the number
   of days with no revenue and the total revenue of the year (verify the total with a second, simpler query).

   ```sh
   day         revenue
   ----------  -------
   2025-01-01  0.00
   2025-01-02  369.93
   2025-01-03  0.00
   2025-01-04  90.93
   2025-01-05  0.00
   2025-01-06  59.98
   (6 rows)
   (365, 206, '26649.49')
   ('26649.49',)
   ```

2. **Fibonacci** (a classic puzzle). Generate the Fibonacci numbers up to 1000 on one line with a recursive CTE. (Hint: carry two columns, `a` and `b`.)

   ```sh
   0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987
   ```

3. Load the 2025 order lines (category, month as `YYYY-MM`, and `cents`; non-cancelled) into an indexed temp table `lines_2025`. Then answer, from the temp table: (a) the best month for every category (highest revenue), and (b) the best category for every month. Order the answers by category and by month.
   (Hint: first make a second temp table `monthly` with revenue per category and month. Use a correlated subquery with `MAX` to find the best row. Window functions will make this easier on Day 17.)

   ```sh
   (502,)
   -- best month per category
   category        month    revenue
   --------------  -------  -------
   Books           2025-12  677.07
   Clothing        2025-10  537.90
   Electronics     2025-09  947.86
   Grocery         2025-11  416.33
   Home & Kitchen  2025-12  500.57
   Sports          2025-05  1408.29
   Toys            2025-11  515.84
   (7 rows)
   -- best category per month
   month    category        revenue
   -------  --------------  -------
   2025-01  Electronics     409.84
   2025-02  Home & Kitchen  449.84
   2025-03  Sports          521.89
   2025-04  Clothing        463.94
   2025-05  Sports          1408.29
   2025-06  Books           547.84
   2025-07  Electronics     386.90
   2025-08  Sports          364.46
   2025-09  Electronics     947.86
   2025-10  Electronics     922.27
   2025-11  Electronics     699.82
   2025-12  Sports          1367.34
   (12 rows)
   ```

Tomorrow: stacking results on top of each other.

CONGRATULATIONS !

[<< Day 13](../13_Day_Subqueries/13_subqueries.md) | [Day 15 >>](../15_Day_Set_operations/15_set_operations.md)
