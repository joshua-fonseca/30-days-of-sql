<div align="center">
  <h1> 30 Days Of SQL: Day 25 - DuckDB's Friendly SQL & Nested Types</h1>
</div>

[<< Day 24](../24_Day_Querying_files/24_querying_files.md) | [Day 26 >>](../26_Day_Duckdb_with_dataframes/26_duckdb_with_dataframes.md)

- [Day 25](#day-25)
  - [Friendly SQL](#friendly-sql)
    - [GROUP BY ALL and ORDER BY ALL](#group-by-all-and-order-by-all)
    - [SELECT * EXCLUDE and REPLACE](#select--exclude-and-replace)
    - [COLUMNS: Many Columns at Once](#columns-many-columns-at-once)
    - [QUALIFY: Filtering on Window Functions](#qualify-filtering-on-window-functions)
    - [DISTINCT ON](#distinct-on)
    - [FROM First and Trailing Commas](#from-first-and-trailing-commas)
  - [Nested Types](#nested-types)
    - [Lists](#lists)
    - [Building Lists from Rows](#building-lists-from-rows)
    - [Lambdas and List Comprehensions](#lambdas-and-list-comprehensions)
    - [unnest: From a List to Rows](#unnest-from-a-list-to-rows)
    - [Structs](#structs)
  - [Reshaping: PIVOT and UNPIVOT](#reshaping-pivot-and-unpivot)
    - [PIVOT](#pivot)
    - [UNPIVOT](#unpivot)
  - [More Tools for Analysts](#more-tools-for-analysts)
    - [SAMPLE](#sample)
    - [ASOF JOIN](#asof-join)
    - [ANY and ALL](#any-and-all)
    - [Series Without Recursion](#series-without-recursion)
    - [CREATE MACRO](#create-macro)
  - [ Exercises: Day 25](#exercises-day-25)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 25

DuckDB's authors read a lot of other people's SQL and noticed what is tedious: writing the same column twice, wrapping a query in a CTE only to filter a window function, listing every column
except one. So they added shortcuts, collectively called **friendly SQL**. None of them gives you power you did not have: each one is a shorter way to say something you already can. The second
half of today is about DuckDB's **nested types** (lists and structs), which let a single cell hold several values, something SQLite never offered.

Today's examples use the shop database you copied into DuckDB on Day 23:

```py
import duckdb
from helpers import show

con = duckdb.connect('00_practice/shop.duckdb')
show(con.execute('SELECT COUNT(*) AS orders, MIN(order_date) AS first, MAX(order_date) AS last FROM orders'))
```

```sh
orders  first       last
------  ----------  ----------
399     2024-01-02  2025-12-31
(1 row)
```

## Friendly SQL

### GROUP BY ALL and ORDER BY ALL

On Day 7 you learned the rule: every selected column that is not an aggregate must be repeated in `GROUP BY`. DuckDB can work that out for you:

```sql
-- syntax
SELECT col1, col2, AGGREGATE(...) FROM t GROUP BY ALL;
SELECT ... ORDER BY ALL;
```

`GROUP BY ALL` groups by every selected column that is not an aggregate. `ORDER BY ALL` sorts by all the selected columns, left to right.

```py
show(con.execute('''
    SELECT status, COUNT(*) AS orders
    FROM orders
    GROUP BY ALL
    ORDER BY ALL
'''))
```

```sh
status     orders
---------  ------
cancelled  24
delivered  346
pending    15
shipped    14
(4 rows)
```

It shines when the select list is long or when you group by an expression, because you no longer type the expression twice:

```py
show(con.execute('''
    SELECT year(order_date) AS year, strftime(order_date, '%m') AS month, COUNT(*) AS orders
    FROM orders
    GROUP BY ALL
    ORDER BY ALL
    LIMIT 4
'''))
```

```sh
year  month  orders
----  -----  ------
2024  01     2
2024  02     7
2024  03     15
2024  04     9
(4 rows)
```

You can still group by position (`GROUP BY 1, 2`) and by an alias, like in SQLite. One limit: `GROUP BY ALL` cannot group on an `unnest(...)` call; we will go around that below.
Use `ORDER BY ALL` for quick looks; when the order matters, name the columns, and add tie-breakers.

> **In other databases:** `GROUP BY ALL` also exists in Snowflake, Databricks and a few others, but not in PostgreSQL, MySQL or SQL Server.

### SELECT * EXCLUDE and REPLACE

`SELECT *` is discouraged in application code (Day 4), but in analysis you often want "all columns except one" or "all columns, with one of them cleaned". DuckDB has two modifiers for `*`:

```sql
-- syntax
SELECT * EXCLUDE (col1, col2) FROM t;
SELECT * REPLACE (expression AS col) FROM t;
```

```py
show(con.execute("SELECT * EXCLUDE (email, signup_date) FROM customers ORDER BY customer_id LIMIT 3"))
show(con.execute('''
    SELECT * REPLACE (upper(country) AS country, coalesce(city, 'unknown') AS city)
    FROM customers WHERE customer_id IN (1, 8) ORDER BY customer_id
'''))
```

```sh
customer_id  first_name  last_name  city     country
-----------  ----------  ---------  -------  -------
1            Chen        King       Austin   USA
2            Diego       Clark      Chicago  USA
3            Liam        Wilson     London   UK
(3 rows)
customer_id  first_name  last_name  email                    city     country  signup_date
-----------  ----------  ---------  -----------------------  -------  -------  -----------
1            Chen        King       NULL                     Austin   USA      2023-07-01
8            Tara        Brown      tara.brown8@example.com  unknown  UK       2023-06-25
(2 rows)
```

They combine, in the order `EXCLUDE` then `REPLACE`:

```py
show(con.execute('''
    SELECT * EXCLUDE (email, signup_date) REPLACE (lower(country) AS country)
    FROM customers ORDER BY customer_id LIMIT 2
'''))
```

```sh
customer_id  first_name  last_name  city     country
-----------  ----------  ---------  -------  -------
1            Chen        King       Austin   usa
2            Diego       Clark      Chicago  usa
(2 rows)
```

Before this, you had to list the other six columns by hand, and forgot to update the list when someone added a column.

> **In other databases:** `EXCEPT (...)` in BigQuery, `EXCLUDE` in Snowflake. SQLite, PostgreSQL, MySQL and SQL Server have no equivalent.

### COLUMNS: Many Columns at Once

`COLUMNS(...)` expands to several columns that you select by **pattern**, so one expression can be applied to all of them.

```sql
-- syntax
SELECT COLUMNS('regex') FROM t;
SELECT MIN(COLUMNS(*)) FROM t;
SELECT COLUMNS(lambda c: condition_on_c) FROM t;
```

```py
show(con.execute("SELECT COLUMNS('.*_name') FROM customers ORDER BY customer_id LIMIT 2"))
show(con.execute("SELECT MAX(COLUMNS('.*_cents')) FROM products"))
show(con.execute("SELECT MIN(COLUMNS(*)) FROM products"))
```

```sh
first_name  last_name
----------  ---------
Chen        King
Diego       Clark
(2 rows)
price_cents
-----------
14999
(1 row)
product_id  name                  category_id  price_cents  stock
----------  --------------------  -----------  -----------  -----
1           Bamboo Cutting Board  1            399          1
(1 row)
```

The regex form picked the two columns ending in `_name`. `MAX(COLUMNS('.*_cents'))` applied `MAX` to the one column matching `_cents`. `MIN(COLUMNS(*))` applied `MIN` to *every* column, including text ones, where
"minimum" means "first alphabetically". A genuinely useful application is counting the NULLs in every column of a table in one go:

```py
show(con.execute('SELECT COUNT(*) - COUNT(COLUMNS(*)) FROM customers'))
```

```sh
customer_id  first_name  last_name  email  city  country  signup_date
-----------  ----------  ---------  -----  ----  -------  -----------
0            0           0          3      7     0        0
(1 row)
```

`COUNT(*)` counts rows and `COUNT(column)` counts non-NULL values, so the difference is the number of NULLs: 3 customers without an email and 7 without a city, exactly the quirks of Day 5.

You can choose columns with a condition too. The `lambda c: ...` form (a small function that receives each column name) keeps the columns whose name contains `cents`:

```py
show(con.execute("SELECT COLUMNS(lambda c: c LIKE '%cents%') FROM products ORDER BY product_id LIMIT 2"))
```

```sh
price_cents
-----------
2499
999
(2 rows)
```

### QUALIFY: Filtering on Window Functions

On Day 17 you found the top 3 products per category with a window function **inside a CTE** and a `WHERE rn <= 3` outside, because `WHERE` runs *before* window functions exist.
DuckDB adds a clause that runs *after* them, called `QUALIFY`:

```sql
-- syntax
SELECT ... FROM t
QUALIFY window_function() OVER (...) <= n;
```

```py
show(con.execute('''
    SELECT c.name AS category, p.name AS product, p.price_cents
    FROM products AS p
    JOIN categories AS c USING (category_id)
    QUALIFY ROW_NUMBER() OVER (PARTITION BY c.name ORDER BY p.price_cents DESC, p.product_id) <= 2
    ORDER BY category, p.price_cents DESC
    LIMIT 6
'''))
```

```sh
category     product                      price_cents
-----------  ---------------------------  -----------
Books        The Pragmatic Programmer     4999
Books        SQL for Data Analysis        4499
Clothing     Denim Jacket                 7999
Clothing     Rain Coat                    5999
Electronics  Noise-Cancelling Headphones  14999
Electronics  Bluetooth Speaker            5999
(6 rows)
```

No CTE, no helper column. You can even name the window function in the select list and use its alias in `QUALIFY`. The updated order of execution, which you drew on Day 7, is now:

```
FROM / JOIN  ->  WHERE  ->  GROUP BY  ->  HAVING  ->  window functions  ->  QUALIFY  ->  SELECT list  ->  DISTINCT  ->  ORDER BY  ->  LIMIT
```

(`WHERE` filters rows, `HAVING` filters groups, `QUALIFY` filters window results.) "The latest order of each customer", also from Day 17, is one clause:

```py
show(con.execute('''
    SELECT customer_id, order_id, order_date
    FROM orders
    QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) = 1
    ORDER BY customer_id
    LIMIT 4
'''))
```

```sh
customer_id  order_id  order_date
-----------  --------  ----------
1            331       2025-10-27
2            383       2025-12-17
3            219       2025-03-21
4            388       2025-12-21
(4 rows)
```

> **In other databases:** `QUALIFY` exists in Snowflake, BigQuery, Teradata and Databricks. In PostgreSQL, MySQL and SQL Server you still need the CTE.

### DISTINCT ON

"The first row of each group" is so common that PostgreSQL invented `DISTINCT ON`, and DuckDB has it. It keeps the first row for each distinct value of the expression in the parentheses, where "first" is decided by `ORDER BY`:

```py
show(con.execute('''
    SELECT DISTINCT ON (category_id) category_id, name, price_cents
    FROM products
    WHERE category_id IS NOT NULL
    ORDER BY category_id, price_cents DESC, product_id
    LIMIT 3
'''))
```

```sh
category_id  name                         price_cents
-----------  ---------------------------  -----------
1            Noise-Cancelling Headphones  14999
2            The Pragmatic Programmer     4999
3            Chef's Knife                 6999
(3 rows)
```

The dearest product per category. Use `QUALIFY` when you need the top *n*, and `DISTINCT ON` when you need exactly the top one. The `ORDER BY` must start with the `DISTINCT ON` expression.

### FROM First and Trailing Commas

DuckDB lets you start a query with `FROM`. Selecting everything is then implicit, which makes quick looks short, and it reads in the order the data flows:

```py
show(con.sql('FROM categories ORDER BY name LIMIT 3'))
show(con.sql('FROM products SELECT COUNT(*) AS products, MIN(price_cents) AS cheapest'))
```

```sh
category_id  name
-----------  -----------
2            Books
6            Clothing
1            Electronics
(3 rows)
products  cheapest
--------  --------
40        399
(1 row)
```

A small kindness: a trailing comma in a select list is allowed, so you can comment out or reorder the last column without a syntax error:

```py
show(con.sql('''
    SELECT first_name,
           last_name,
    FROM customers ORDER BY customer_id LIMIT 2
'''))
```

```sh
first_name  last_name
----------  ---------
Chen        King
Diego       Clark
(2 rows)
```

## Nested Types

### Lists

A **list** holds any number of values of one type in a single cell. Square brackets create one, positions start at **1**, and negative positions count from the end:

```sql
-- syntax
[1, 2, 3]            -- a list of integers
my_list[1]           -- the first element
my_list[2:3]         -- a slice, both ends included
len(my_list)
```

```py
show(con.sql('''
    SELECT [10, 20, 30, 40]        AS nums,
           [10, 20, 30, 40][1]     AS first,
           [10, 20, 30, 40][-1]    AS last,
           [10, 20, 30, 40][2:3]   AS slice,
           len([10, 20, 30, 40])   AS length,
           list_contains([10, 20, 30, 40], 30) AS has_30,
           30 IN [10, 20, 30, 40]  AS also_has_30
'''))
```

```sh
nums              first  last  slice     length  has_30  also_has_30
----------------  -----  ----  --------  ------  ------  -----------
[10, 20, 30, 40]  10     40    [20, 30]  4       True    True
(1 row)
```

Compare with Python lists on Day 5: the same ideas, but 1-based and with the slice end included. A few more list functions (`list_` prefix, many with shorter aliases): `list_sort`, `list_reverse`,
`list_distinct`, `list_concat` (or `||`), `list_position`, `flatten` and `list_aggregate(list, 'sum')`. Note that `list_distinct` makes **no promise about the order** of its result, so sort afterwards if you print it:

```py
show(con.sql('''
    SELECT list_sort([3, 1, 2]) AS sorted,
           list_sort(list_distinct([1, 1, 2, 3, 3])) AS distinct_sorted,
           [1, 2] || [3] AS joined,
           list_aggregate([1, 2, 3, 4], 'sum') AS total,
           list_position(['a', 'b', 'c'], 'b') AS position
'''))
```

```sh
sorted     distinct_sorted  joined     total  position
---------  ---------------  ---------  -----  --------
[1, 2, 3]  [1, 2, 3]        [1, 2, 3]  10     2
(1 row)
```

### Building Lists from Rows

The aggregate `list(x)` collects the values of a group into a list. It is DuckDB's friendlier `string_agg`: you keep the structure. Give it an `ORDER BY` inside the parentheses to control the order:

```py
show(con.execute('''
    SELECT c.name AS category, COUNT(*) AS products, list(p.name ORDER BY p.name)[1:2] AS first_two
    FROM products AS p
    JOIN categories AS c USING (category_id)
    GROUP BY ALL
    ORDER BY category
    LIMIT 3
'''))
```

```sh
category     products  first_two
-----------  --------  ----------------------------------------------------
Books        6         ['Cookbook Basics', 'Mystery Novel']
Clothing     5         ['Beanie', 'Cotton T-Shirt']
Electronics  6         ['Bluetooth Speaker', 'Noise-Cancelling Headphones']
(3 rows)
```

Here a list is built per category and then sliced to its first two elements. When you want the list as text, `string_agg(name, ', ' ORDER BY name)` (Day 7) is still there.

### Lambdas and List Comprehensions

To change or filter every element of a list you pass a small function, a **lambda**. DuckDB's current syntax is Python's: `lambda x: expression`.

```sql
-- syntax
list_transform(list, lambda x: expression)
list_filter(list, lambda x: condition)
list_reduce(list, lambda a, b: expression)
```

```py
show(con.sql('''
    SELECT list_transform([1, 2, 3, 4], lambda x: x * x)         AS squares,
           list_filter(range(1, 11), lambda x: x % 3 = 0)        AS multiples_of_3,
           list_reduce([1, 2, 3, 4], lambda a, b: a * b)          AS product,
           list_transform(['a', 'b'], lambda x, i: x || i)       AS with_position
'''))
```

```sh
squares        multiples_of_3  product  with_position
-------------  --------------  -------  -------------
[1, 4, 9, 16]  [3, 6, 9]       24       ['a1', 'b2']
(1 row)
```

`range(1, 11)` makes the list `[1, ..., 10]` (the end is excluded, as in Python). The last example shows that a second parameter receives the position of the element.

Because DuckDB wants to feel like Python, there is also a **list comprehension**: `[expression FOR x IN list IF condition]`, in capital letters:

```py
show(con.sql('SELECT [x * x FOR x IN range(1, 11) IF x % 2 = 0] AS even_squares'))
```

```sh
even_squares
--------------------
[4, 16, 36, 64, 100]
(1 row)
```

**Older code:** you will find DuckDB examples online that use an arrow: `list_transform(l, x -> x * 2)`. That older syntax is deprecated, and in DuckDB 2.0 it is an error. Read it as `lambda x: x * 2`:

```py
try:
    con.execute('SELECT list_transform([1, 2, 3], x -> x * 2)')
except duckdb.Error as e:
    print(type(e).__name__)
    print(str(e).splitlines()[0])
```

```sh
BinderException
Binder Error: Deprecated lambda arrow (->) detected. Please transition to the new lambda syntax, i.e.., lambda x, i: x + i, before DuckDB's next release.
```

DuckDB moves fast: this is exactly why you check the documentation of the version you have installed (`duckdb.__version__`), as we did on Day 23.

### unnest: From a List to Rows

`unnest` is the opposite of `list`: it turns a list into **one row per element**, repeating the other columns. That is how you flatten a list column like `languages` without the separate table of Day 10:

```sql
-- syntax
SELECT other_col, unnest(list_col) AS item FROM t;
```

```py
show(con.execute('''
    SELECT name, unnest(languages) AS language
    FROM 'data/countries_data.json'
    WHERE name IN ('Finland', 'Switzerland')
    ORDER BY name, language
'''))
```

```sh
name         language
-----------  --------
Finland      Finnish
Finland      Swedish
Switzerland  French
Switzerland  German
Switzerland  Italian
(5 rows)
```

Remember that `GROUP BY ALL` cannot group on the `unnest` call itself. Unnest in a subquery (or CTE) first, then group on the result. Here are the languages spoken by countries that use the Euro, counted:

```py
show(con.execute('''
    SELECT language, COUNT(*) AS euro_countries
    FROM (SELECT unnest(languages) AS language FROM 'data/countries_data.json' WHERE currency = 'Euro')
    GROUP BY ALL
    ORDER BY euro_countries DESC, language
    LIMIT 5
'''))
```

```sh
language  euro_countries
--------  --------------
French    14
German    5
Dutch     3
English   3
Italian   3
(5 rows)
```

### Structs

A **struct** is a record: a cell holding several named fields, a bit like a Python dict whose keys are fixed. Create one with curly braces; read a field with a dot. `unnest` on a struct (or `s.*`) spreads it into columns.

```sql
-- syntax
{'field1': value1, 'field2': value2}
struct_column.field1
struct_column.*
```

```py
show(con.execute('''
    SELECT item.name AS name, item.dollars AS dollars, item
    FROM (SELECT {'name': name, 'dollars': price_cents / 100} AS item FROM products ORDER BY product_id LIMIT 3)
'''))
show(con.execute("SELECT s.* FROM (SELECT {'a': 1, 'b': 'two'} AS s)"))
```

```sh
name               dollars  item
-----------------  -------  -----------------------------------------------
Wireless Mouse     24.99    {'name': 'Wireless Mouse', 'dollars': 24.99}
USB-C Cable        9.99     {'name': 'USB-C Cable', 'dollars': 9.99}
Bluetooth Speaker  59.99    {'name': 'Bluetooth Speaker', 'dollars': 59.99}
(3 rows)
a  b
-  ---
1  two
(1 row)
```

Structs and lists nest: a list of structs is how DuckDB represents a JSON array of objects. When `read_json` meets such data, you get these types automatically, and you can dig in with dots and `unnest`.
There is also a `MAP` type (a dictionary with any keys): `MAP {'red': 1}['red']` returns the value. Structs are the one to know, since JSON loads into them.

## Reshaping: PIVOT and UNPIVOT

### PIVOT

On Day 15 you built a status-by-year table by hand with `SUM(CASE WHEN ...)`: one expression per column. `PIVOT` turns the **values** of a column into **columns**, in one statement:

```sql
-- syntax
PIVOT table_or_subquery
ON pivot_column
USING aggregate(...)
GROUP BY row_column;
```

```py
status_year = 'SELECT status, year(order_date)::VARCHAR AS year FROM orders'
show(con.execute(f'''
    PIVOT ({status_year})
    ON year
    USING COUNT(*)
    GROUP BY status
    ORDER BY status
'''))
```

```sh
status     2024  2025
---------  ----  ----
cancelled  14    10
delivered  167   179
pending    0     15
shipped    0     14
(4 rows)
```

`ON year` created a column per year found, `USING COUNT(*)` filled each cell, and `GROUP BY status` made the rows. Pending and shipped orders only exist in 2025, and the missing counts are 0.
(The f-string here only pastes in a fixed piece of SQL that we wrote ourselves, not user input.) A wide pivot only needs a list of the columns you want:

```py
show(con.execute('''
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
'''))
```

```sh
month    Electronics  Books  Sports
-------  -----------  -----  ------
2025-01  61231        32243  37501
2025-02  15544        14997  27594
2025-03  36396        16495  52189
2025-04  14797        31991  38390
(4 rows)
```

Revenue in cents per month (rows) for three categories (columns). Without the `IN (...)` list you get one column per category. A combination that has no rows gives `NULL`, which you can wrap in `COALESCE`.

### UNPIVOT

`UNPIVOT` goes the other way: columns become rows. It is how you tidy a wide table into the long form that `GROUP BY` and charts like. Save the pivot first as a table:

```py
con.execute(f'''
    CREATE OR REPLACE TABLE status_by_year AS
    PIVOT ({status_year}) ON year USING COUNT(*) GROUP BY status ORDER BY status
''')
show(con.execute('''
    UNPIVOT status_by_year
    ON "2024", "2025"
    INTO NAME year VALUE orders
'''))
```

```sh
status     year  orders
---------  ----  ------
cancelled  2024  14
cancelled  2025  10
delivered  2024  167
delivered  2025  179
pending    2024  0
pending    2025  15
shipped    2024  0
shipped    2025  14
(8 rows)
```

`ON` lists the columns to turn into rows (the years are quoted because they look like numbers), `NAME` is the new column that receives the old column names, and `VALUE` the one that receives the cells.
Instead of listing the columns you can say "everything except `status`": `ON COLUMNS(* EXCLUDE (status))`.

> **In other databases:** `PIVOT`/`UNPIVOT` also exist in SQL Server, Oracle and Snowflake (with a different, more verbose syntax). PostgreSQL and MySQL use the `SUM(CASE ...)` trick, as in Day 15.

## More Tools for Analysts

### SAMPLE

A random sample of rows is a great way to explore a huge table. `USING SAMPLE` takes a number of rows or a percentage; with a **seed** the sample is repeatable:

```sql
-- syntax
SELECT ... FROM t USING SAMPLE 100 ROWS;
SELECT ... FROM t USING SAMPLE 10 PERCENT (bernoulli, 42);
SELECT ... FROM t USING SAMPLE reservoir(5 ROWS) REPEATABLE (7);
```

```py
sample = 'SELECT order_id FROM orders USING SAMPLE reservoir(5 ROWS) REPEATABLE (7) ORDER BY order_id'
first = con.execute(sample).fetchall()
second = con.execute(sample).fetchall()
print(first)  # [(118,), (184,), (221,), (371,), (389,)]
print('repeatable:', first == second)  # repeatable: True
print(con.execute('SELECT COUNT(*) FROM orders USING SAMPLE 10 PERCENT (bernoulli, 42)').fetchall())  # [(43,)]
```

Without a seed you get different rows every time. `bernoulli` includes each row with a 10% chance, so the size varies around 10% (about 40 of the 399 orders); `reservoir` returns exactly the number of rows you asked for.
Careful with a bare `USING SAMPLE 10%` on a small table: the default method works in chunks and can return nothing at all. Name the method.

### ASOF JOIN

Many real questions are about "the most recent value *as of* a moment": which price was valid when this trade happened, which exchange rate on that day. A normal join needs an exact match. An **ASOF JOIN** matches
each row on the equal keys and then to the nearest earlier row on an ordered column:

```sql
-- syntax
SELECT ... FROM a ASOF JOIN b ON a.key = b.key AND a.ts >= b.ts;
```

```py
con.execute('CREATE TEMP TABLE trades (sym VARCHAR, ts TIMESTAMP, qty INTEGER)')
con.execute('CREATE TEMP TABLE quotes (sym VARCHAR, ts TIMESTAMP, price_cents INTEGER)')
con.execute("INSERT INTO trades VALUES ('A', '2025-01-01 10:00:05', 10), ('A', '2025-01-01 10:01:30', 5), ('B', '2025-01-01 10:00:50', 7)")
con.execute("""INSERT INTO quotes VALUES ('A', '2025-01-01 10:00:00', 10000), ('A', '2025-01-01 10:01:00', 10150),
                                        ('B', '2025-01-01 10:00:00', 2000),  ('B', '2025-01-01 10:02:00', 2100)""")
show(con.execute('''
    SELECT t.sym, t.ts AS traded_at, t.qty, q.ts AS quoted_at, q.price_cents
    FROM trades AS t
    ASOF JOIN quotes AS q ON t.sym = q.sym AND t.ts >= q.ts
    ORDER BY t.sym, t.ts
'''))
```

```sh
sym  traded_at            qty  quoted_at            price_cents
---  -------------------  ---  -------------------  -----------
A    2025-01-01 10:00:05  10   2025-01-01 10:00:00  10000
A    2025-01-01 10:01:30  5    2025-01-01 10:01:00  10150
B    2025-01-01 10:00:50  7    2025-01-01 10:00:00  2000
(3 rows)
```

Each trade picked the latest quote at or before its own time. The second trade of `A` (10:01:30) used the 10:01:00 quote, not the 10:00:00 one. Trade `B` at 10:00:50 did not see the 10:02:00 quote, because it lies in the future.
Without `ASOF` you would write a correlated subquery or a window function (Day 13/18). With `ASOF LEFT JOIN` trades with no earlier quote are kept, with NULLs.

### ANY and ALL

On Day 13 SQLite could not run `> ALL (subquery)` and `= ANY (subquery)`, and you used rewrites. DuckDB runs them as written:

```py
show(con.execute('''
    SELECT name, price_cents
    FROM products
    WHERE price_cents > ALL (SELECT price_cents FROM products WHERE category_id = (SELECT category_id FROM categories WHERE name = 'Books'))
    ORDER BY name
'''))
```

```sh
name                         price_cents
---------------------------  -----------
Bluetooth Speaker            5999
Chef's Knife                 6999
Denim Jacket                 7999
Noise-Cancelling Headphones  14999
Rain Coat                    5999
Running Shoes                8999
(6 rows)
```

These are the products dearer than **every** book. It is the same as `> (SELECT MAX(...))`. And `= ANY (subquery)` is the same as `IN (subquery)`; `> ANY` means "greater than at least one", i.e. greater than the minimum.

There is a famous trap, and the shop data shows it: the category *Garden* has no products. "Greater than all of nothing" is vacuously true, so every product qualifies. "Greater than any of nothing" is false:

```py
garden = "(SELECT price_cents FROM products WHERE category_id = (SELECT category_id FROM categories WHERE name = 'Garden'))"
print(con.execute(f'SELECT COUNT(*) FROM products WHERE price_cents > ALL {garden}').fetchall())  # [(40,)]
print(con.execute(f'SELECT COUNT(*) FROM products WHERE price_cents > ANY {garden}').fetchall())  # [(0,)]
```

(The f-string again only pastes a fixed fragment of our own.) The rewrite with `MAX` would give 0 in the first case, because `price > NULL` is never true. The two forms are not identical on empty sets, so know which question you are asking.

### Series Without Recursion

On Day 14 you generated 1..10 and a range of dates with a `WITH RECURSIVE` query. DuckDB has table functions that do the same:

```py
show(con.sql('SELECT * FROM range(1, 6) AS t(n)'))
show(con.sql("SELECT d::DATE AS day FROM generate_series(DATE '2025-01-30', DATE '2025-02-02', INTERVAL 1 DAY) AS t(d)"))
print(con.execute("SELECT COUNT(*) FROM generate_series(DATE '2025-01-01', DATE '2025-01-31', INTERVAL 1 DAY)").fetchall())  # [(31,)]
```

```sh
n
-
1
2
3
4
5
(5 rows)
day
----------
2025-01-30
2025-01-31
2025-02-01
2025-02-02
(4 rows)
[(31,)]
```

`range` excludes the end and `generate_series` includes it. The date series returns timestamps, hence the `::DATE`. This is the calendar table you need for "include the days with zero sales" queries (Day 12 and Day 14).

### CREATE MACRO

A **macro** is a named expression (or a named query) that you define once and reuse, DuckDB's nearest thing to a stored function. SQLite had no equivalent, and you wrote Python functions instead.

```sql
-- syntax
CREATE MACRO name(param1, param2) AS expression;
CREATE MACRO name(param) AS TABLE SELECT ...;
```

```py
con.execute("""
    CREATE OR REPLACE MACRO price_label(cents) AS
        '$' || (cents // 100) || '.' || lpad((cents % 100)::VARCHAR, 2, '0')
""")
show(con.execute('SELECT name, price_label(price_cents) AS price FROM products ORDER BY price_cents DESC, name LIMIT 3'))

con.execute('CREATE OR REPLACE MACRO customers_in(c) AS TABLE SELECT customer_id, first_name FROM customers WHERE country = c')
show(con.execute("SELECT * FROM customers_in('UK') ORDER BY customer_id LIMIT 3"))
```

```sh
name                         price
---------------------------  -------
Noise-Cancelling Headphones  $149.99
Running Shoes                $89.99
Denim Jacket                 $79.99
(3 rows)
customer_id  first_name
-----------  ----------
3            Liam
8            Tara
21           Emma
(3 rows)
```

The first macro formats cents as dollars (the `lpad` pads the cents with a leading zero, so 5 cents become `05`). The second is a **table macro**: it returns a whole result, and you use it like a table.
A macro is expanded into your query like a text replacement, so it is not a function with its own variables; for real programs in Python you can also register Python functions with `con.create_function`.

Shorter SQL, plus lists, structs and reshaping, that is a lot of new vocabulary. Practise it.

## Exercises: Day 25

### Exercises: Level 1

Use `00_practice/shop.duckdb` from Day 23 (Level 2, exercise 1). Add `ORDER BY` tie-breakers wherever the order matters.

1. Rewrite these with `GROUP BY ALL` (and `ORDER BY ALL` or your own order): (a) orders per `status`; (b) customers per `country`, most first, ties by country; (c) revenue per customer `country` (`SUM(quantity * unit_price_cents) / 100.0`, joining `order_items`, `orders`, `customers`; highest first); (d) employees per `title` with the average salary in dollars (2 decimals), the first four titles alphabetically.
2. Select all columns of `customers` except `email` and `signup_date`; show the first 3 rows by id.
3. Select all columns of `customers`, upper-casing `country` and replacing a NULL `city` with `'unknown'`, for customers 1 and 8. Then combine `EXCLUDE` and `REPLACE` in one query: drop `email` and `signup_date`, lower-case `country`, first 2 customers.
4. With `COLUMNS`: (a) select the two columns of `customers` whose names end in `_name`; (b) the maximum of every column of `products` whose name ends in `_cents`; (c) the number of NULLs in every column of `customers`.
5. With `QUALIFY`: the 3 dearest products of each category (ties by `product_id`), showing the category name, product name and price; show the first 6 rows ordered by category, then price descending.
6. With `QUALIFY`: each customer's most recent order (ties by the highest `order_id`); show the first 5 customers by id, then print how many customers have at least one order.
7. Use FROM-first syntax to list the first 3 categories by name, and to show the number of products and the lowest price in one row.
8. With `DISTINCT ON`: the cheapest product of each category (ties by `product_id`, skip the product without a category); show the first 3 categories.
9. For each category, show the number of products and a list of its first two product names alphabetically. First three categories by name.
10. Compute `[4, 16, 36, 64, 100]` (the squares of the even numbers up to 10) with a list comprehension. Then `list_filter` the multiples of 3 up to 10 with a lambda. Then write `list_transform([1, 2, 3], x -> x * 2)` with the old arrow, catch the error and print its type and first line.
11. Use `unnest` on `languages` in `data/countries_data.json` to list the languages of Finland, one row each.
12. For the first three products (by id), create a struct column `item` with fields `name` and `dollars` (`price_cents / 100`), and select `name` and `dollars` back out of it.
13. Take a **seeded** sample of 5 `order_id`s (`reservoir`, seed 7), sorted. Run it twice and print the list and whether both runs agree.
14. Count the days in January 2025 with `generate_series`.
15. Create a macro `price_label(cents)` that returns text like `$149.99`, and use it on the 3 dearest products (ties by name).

```sh
# expected for exercise 1, (a) to (d)
status     orders
---------  ------
cancelled  24
delivered  346
pending    15
shipped    14
(4 rows)
country  customers
-------  ---------
USA      17
UK       14
Canada   13
France   9
Germany  7
(5 rows)
country  revenue
-------  --------
USA      13274.11
Canada   10614.85
France   9519.14
UK       8276.21
Germany  6372.48
(5 rows)
title                people  avg_salary
-------------------  ------  ----------
CEO                  1       185000.0
Engineering Manager  2       109000.0
Sales Associate      2       55000.0
Sales Manager        1       98000.0
(4 rows)

# expected for exercise 4 (c)
customer_id  first_name  last_name  email  city  country  signup_date
-----------  ----------  ---------  -----  ----  -------  -----------
0            0           0          3      7     0        0
(1 row)

# expected for exercise 5
category  product                   price_cents
--------  ------------------------  -----------
Books     The Pragmatic Programmer  4999
Books     SQL for Data Analysis     4499
Books     Python Crash Course       3999
Clothing  Denim Jacket              7999
Clothing  Rain Coat                 5999
Clothing  Cotton T-Shirt            1899
(6 rows)

# expected for exercise 6
customer_id  order_id  order_date
-----------  --------  ----------
1            331       2025-10-27
2            383       2025-12-17
3            219       2025-03-21
4            388       2025-12-21
6            333       2025-10-29
(5 rows)
[(54,)]

# expected for exercises 10, 13 and 14
[([4, 16, 36, 64, 100],)]
[([3, 6, 9],)]
BinderException - Binder Error: Deprecated lambda arrow (->) detected. Please transition to the new lambda syntax, i.e.., lambda x, i: x + i, before DuckDB's next release.
[118, 184, 221, 371, 389] True
[(31,)]
```

### Exercises: Level 2

1. **Pivot and back.** (a) `PIVOT` the orders into a table of `status` (rows) by year (columns) with the counts, like the Day 15 pivot you built by hand. Compare the result with Day 15. (b) Save it as a table `status_by_year`, then `UNPIVOT` it back into the long form `status, year, orders` and show the first 4 rows ordered by status then year.

   ```sh
   status     2024  2025
   ---------  ----  ----
   cancelled  14    10
   delivered  167   179
   pending    0     15
   shipped    0     14
   (4 rows)
   status     year  orders
   ---------  ----  ------
   cancelled  2024  14
   cancelled  2025  10
   delivered  2024  167
   delivered  2025  179
   (4 rows)
   ```

2. **Revenue pivot.** For 2025, pivot the revenue **in cents** of `order_items` (quantity times unit price) into months (rows, as `'YYYY-MM'`) by the three categories Electronics, Books and Sports (columns). Show the first four months.

   ```sh
   month    Electronics  Books  Sports
   -------  -----------  -----  ------
   2025-01  61231        32243  37501
   2025-02  15544        14997  27594
   2025-03  36396        16495  52189
   2025-04  14797        31991  38390
   (4 rows)
   ```

3. **ASOF.** Create two temporary tables: `trades (sym, ts, qty)` with `('A', '2025-01-01 10:00:05', 10)`, `('A', '2025-01-01 10:01:30', 5)`, `('B', '2025-01-01 10:00:50', 7)`, and `quotes (sym, ts, price_cents)` with `('A', '2025-01-01 10:00:00', 10000)`, `('A', '2025-01-01 10:01:00', 10150)`, `('B', '2025-01-01 10:00:00', 2000)`, `('B', '2025-01-01 10:02:00', 2100)`.
   For every trade find the quote in force when it happened and compute the trade value in cents.

   ```sh
   sym  traded_at            qty  quoted_at            price_cents  value_cents
   ---  -------------------  ---  -------------------  -----------  -----------
   A    2025-01-01 10:00:05  10   2025-01-01 10:00:00  10000        100000
   A    2025-01-01 10:01:30  5    2025-01-01 10:01:00  10150        50750
   B    2025-01-01 10:00:50  7    2025-01-01 10:00:00  2000         14000
   (3 rows)
   ```

4. **ANY / ALL.** (a) List the products dearer than **all** products of the Books category, by name. (b) Rewrite it with `> (SELECT MAX(...))` and check that it returns the same number of rows. (c) Count the products that are `> ALL` the prices of the Garden category, and those `> ANY` of them. Explain both numbers.

   ```sh
   name                         price_cents
   ---------------------------  -----------
   Bluetooth Speaker            5999
   Chef's Knife                 6999
   Denim Jacket                 7999
   Noise-Cancelling Headphones  14999
   Rain Coat                    5999
   Running Shoes                8999
   (6 rows)
   6
   [(40,)]
   [(0,)]
   ```

5. **Comprehension.** Build the initials of each employee (the first letter of each word of `name`) with `string_split`, a list comprehension and `array_to_string`. Show the first four employees by id.

   ```sh
   name             initials
   ---------------  --------
   Grace Hopper     GH
   Alan Turing      AT
   Ada Lovelace     AL
   Edsger Dijkstra  ED
   (4 rows)
   ```

6. **NULL profile.** With one query using `COLUMNS(*)`, count the NULLs in each column of `customers`, and of `products`. Which column of `products` has a NULL, and which shop quirk from Day 11 does it explain?

   ```sh
   customer_id  first_name  last_name  email  city  country  signup_date
   -----------  ----------  ---------  -----  ----  -------  -----------
   0            0           0          3      7     0        0
   (1 row)
   product_id  name  category_id  price_cents  stock
   ----------  ----  -----------  -----------  -----
   0           0     1            0            0
   (1 row)
   ```

### Exercises: Level 3

1. **The ten most spoken languages, a third time.** In plain Python this takes loops and a dictionary. On Day 11 you did it with a join over the tables `languages` and `country_languages` that you normalized on Day 10. Do it now in **one query on the file itself**:
   `read_json` (or the quoted file name) plus `unnest(languages)`, with no normalization. Ties by language. Afterwards, write down which of the three approaches was easiest to write, which was easiest to read, and which would you choose for a table that gets updated every day. (An honest answer: the normalized tables win for data that changes and is shared; the one-query version wins for analysing a file once.)

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

2. **Revenue per month and category, wide and long.** For 2025, excluding cancelled orders, produce (a) a pivot of revenue **in dollars** (`SUM(...) / 100.0`, `0` for a missing combination) by month for Electronics, Books and Sports, and (b) the three biggest month-and-category cells overall, using `UNPIVOT` on the pivot result and then `QUALIFY RANK()`.
   (Hint: put the pivot query inside `UNPIVOT ( ... ) ON Electronics, Books, Sports INTO NAME category VALUE dollars`, wrap that in `SELECT * FROM ( ... )` and add the `QUALIFY` after it; or save the pivot as a table first and unpivot the table. Use `COALESCE(SUM(cents), 0)` inside `USING`.)

   ```sh
   month    Electronics  Books   Sports
   -------  -----------  ------  -------
   2025-01  409.84       322.43  357.02
   2025-02  145.45       149.97  275.94
   2025-03  363.96       164.95  521.89
   2025-04  147.97       319.91  383.9
   2025-05  633.57       363.9   1408.29
   2025-06  529.9        547.84  285.96
   2025-07  386.9        321.16  179.98
   2025-08  189.87       140.7   364.46
   2025-09  947.86       349.89  113.95
   2025-10  922.27       436.14  17.99
   2025-11  699.82       502.86  666.44
   2025-12  766.76       677.07  1367.34
   (12 rows)
   month    category     dollars
   -------  -----------  -------
   2025-05  Sports       1408.29
   2025-12  Sports       1367.34
   2025-09  Electronics  947.86
   (3 rows)
   ```

CONGRATULATIONS !

[<< Day 24](../24_Day_Querying_files/24_querying_files.md) | [Day 26 >>](../26_Day_Duckdb_with_dataframes/26_duckdb_with_dataframes.md)
