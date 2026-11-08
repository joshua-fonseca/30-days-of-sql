<div align="center">
  <h1> 30 Days Of SQL: Day 30 - Conclusions</h1>
</div>

[<< Day 29](../29_Day_Project_analytics_report/29_project_analytics_report.md)

- [Day 30](#day-30)
  - [What You Learned](#what-you-learned)
  - [The One-Page Cheat Sheet](#the-one-page-cheat-sheet)
  - [Reading SQL From Other Databases](#reading-sql-from-other-databases)
    - [Dialect Translation Table](#dialect-translation-table)
    - [Translating Automatically with sqlglot](#translating-automatically-with-sqlglot)
    - [W3Schools Topic Map](#w3schools-topic-map)
  - [SQLite vs DuckDB: When to Pick Which](#sqlite-vs-duckdb-when-to-pick-which)
  - [Classic SQL Patterns: A Problem Bank](#classic-sql-patterns-a-problem-bank)
  - [Final Review: 20 Mixed Questions](#final-review-20-mixed-questions)
  - [Where to Go Next](#where-to-go-next)
  - [Final Checklist](#final-checklist)

# Day 30

You made it. This last lesson has no new syntax. It is a map: what you covered, a cheat sheet to keep, a translation guide so you can read SQL written for other databases, a bank of the classic interview-style problems, a final review, and some directions for what to learn next.

## What You Learned

**Part 1: SQL foundations with `sqlite3`**

| Day | You learned |
|---|---|
| 1 | What a database and SQL are; `sqlite3` and `connect()`; your first `SELECT` |
| 2 | `CREATE TABLE`, types and affinity, `STRICT`, keys, `ALTER`, generated columns, money as integer cents |
| 3 | `INSERT`, `commit()`, placeholders, `executemany`, loading JSON and CSV |
| 4 | `SELECT`, `ORDER BY`, `LIMIT`, `DISTINCT`, and the `show()` helper |
| 5 | `WHERE`, `AND/OR/NOT`, `IN`, `BETWEEN`, `LIKE`, and NULL's three-valued logic |
| 6 | String, number and conditional functions: `CASE`, `COALESCE`, `NULLIF`, `CAST` |
| 7 | Aggregates, `GROUP BY`, `HAVING`, and the logical order of a query |
| 8 | `UPDATE`, `DELETE`, `RETURNING`, transactions and ACID |
| 9 | Constraints, foreign keys, `IntegrityError`, upsert |
| 10 | Database design: normalization, one-to-many, many-to-many |
| R1 | Review 1: foundations |

**Part 2: Combining data**

| Day | You learned |
|---|---|
| 11 | `INNER JOIN`, aliases, multi-table joins, building a hard query step by step |
| 12 | `LEFT/RIGHT/FULL` joins, anti-joins, self joins, `CROSS JOIN` |
| 13 | Subqueries: scalar, `IN`, `EXISTS`, correlated, derived tables |
| 14 | CTEs, recursive CTEs, temporary tables |
| 15 | `UNION`/`INTERSECT`/`EXCEPT`, conditional aggregation, hand-made pivots |
| 16 | Dates and times in ISO text, `strftime`, `julianday` |
| R2 | Review 2: combining data |

**Part 3: Analytical SQL**

| Day | You learned |
|---|---|
| 17 | Window functions I: `ROW_NUMBER`, `RANK`, `NTILE`, top-N per group, removing duplicates |
| 18 | Window functions II: running totals, `LAG/LEAD`, frames, gaps and islands |
| R3 | Review 3: analytical SQL |

**Part 4: Python and SQLite in depth**

| Day | You learned |
|---|---|
| 19 | The `sqlite3` module in depth, `row_factory`, backups, `ATTACH`, WAL, threads, the `LibraryRepository` |
| 20 | Importing, cleaning and exporting CSV and JSON; staging tables |
| 21 | Indexes, `EXPLAIN QUERY PLAN`, keyset pagination, FTS5 full-text search |
| 22 | Views and triggers |
| R4 | Review 4: Python and SQLite |

**Part 5: DuckDB**

| Day | You learned |
|---|---|
| 23 | OLTP vs OLAP, DuckDB basics, what changes from SQLite |
| 24 | Querying CSV, JSON and Parquet files directly |
| 25 | Friendly SQL (`GROUP BY ALL`, `QUALIFY`, `EXCLUDE`), lists, structs, `PIVOT`, macros |
| 26 | DuckDB with pandas, Polars and SQLite |
| R5 | Review 5: DuckDB |

**Part 6: Craft and projects**

| Day | You learned |
|---|---|
| 27 | Injection and parameters, read-only connections, backups, migrations, pytest, SQLFluff |
| 28 | A tested command line application over the repository |
| 29 | A two-engine analytics report with Parquet in the middle |
| 30 | This map |

You also kept meeting the same data on purpose: `library.db`, `shop.db`, countries and Hacker News. The "ten most spoken languages" you computed with joins (Day 11), with `json_each` (Day 20) and finally with one DuckDB query (Day 25) is the best summary of this course: **the same question, many tools, and you now know which one to reach for.**

## The One-Page Cheat Sheet

Every line below was executed against `shop.db` (on a copy) while writing this lesson, so you can paste any of them into your own code. Names such as `t_notes` are scratch tables created for the occasion.

| What | Example |
|---|---|
| Create a table | `CREATE TABLE t_notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL, stars INTEGER DEFAULT 0 CHECK (stars >= 0)) STRICT` |
| Change a table | `ALTER TABLE t_notes ADD COLUMN created_on TEXT` |
| Insert | `INSERT INTO t_notes (body, stars) VALUES ('first', 3), ('second', 5)` |
| Upsert | `INSERT INTO categories (name) VALUES ('Books') ON CONFLICT (name) DO UPDATE SET name = excluded.name` |
| Update | `UPDATE t_notes SET stars = stars + 1 WHERE body = 'first'` |
| Update from another table | `UPDATE products SET stock = stock + 1 FROM (SELECT product_id FROM order_items GROUP BY product_id) AS sold WHERE products.product_id = sold.product_id` |
| Delete and see what went | `DELETE FROM t_notes WHERE stars < 5 RETURNING id` |
| Select, alias, distinct | `SELECT DISTINCT country AS nation FROM customers` |
| Filter and sort | `SELECT name, price_cents FROM products WHERE price_cents BETWEEN 1000 AND 5000 AND name LIKE '%a%' ORDER BY price_cents DESC, name LIMIT 5 OFFSET 2` |
| IN, NULL tests | `SELECT first_name FROM customers WHERE country IN ('USA', 'UK') AND city IS NOT NULL` |
| CASE, COALESCE | `SELECT name, CASE WHEN price_cents < 1000 THEN 'cheap' ELSE 'normal' END AS band, coalesce(category_id, 0) FROM products` |
| Aggregates | `SELECT count(*), count(DISTINCT country), sum(stock), avg(price_cents), min(price_cents), max(price_cents) FROM customers, products LIMIT 1` |
| Group and having | `SELECT country, count(*) AS n FROM customers GROUP BY country HAVING count(*) > 5 ORDER BY n DESC, country` |
| Conditional aggregate | `SELECT count(*) FILTER (WHERE status = 'delivered') AS delivered, sum(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending FROM orders` |
| Inner join | `SELECT o.order_id, c.first_name FROM orders o JOIN customers c ON c.customer_id = o.customer_id` |
| Left join (anti-join) | `SELECT c.customer_id FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE o.order_id IS NULL` |
| Self join | `SELECT e.name, m.name AS manager FROM employees e LEFT JOIN employees m ON m.employee_id = e.manager_id` |
| Cross join | `SELECT c.name, s.n FROM categories c CROSS JOIN (SELECT 1 AS n UNION ALL SELECT 2) s` |
| Subquery | `SELECT name FROM products WHERE price_cents > (SELECT avg(price_cents) FROM products)` |
| EXISTS | `SELECT first_name FROM customers c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id)` |
| CTE | `WITH big AS (SELECT order_id FROM order_items GROUP BY order_id HAVING sum(quantity) > 5) SELECT count(*) FROM big` |
| Recursive CTE | `WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 10) SELECT sum(i) FROM n` |
| Temp table | `CREATE TEMP TABLE spend AS SELECT customer_id, count(*) AS orders FROM orders GROUP BY customer_id` |
| Set operations | `SELECT city FROM customers WHERE city IS NOT NULL EXCEPT SELECT 'Paris'` |
| Window: ranking | `SELECT name, price_cents, RANK() OVER (ORDER BY price_cents DESC) AS r FROM products` |
| Window: running total | `SELECT order_date, sum(count(*)) OVER (ORDER BY order_date) FROM orders GROUP BY order_date` |
| Window: previous row | `SELECT order_date, LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) FROM orders` |
| Dates | `SELECT date('2025-03-14', '+7 days'), strftime('%Y-%m', '2025-03-14'), julianday('2025-03-14') - julianday('2025-01-01')` |
| Strings | `SELECT upper('abc') \|\| '-' \|\| substr('hello', 2, 3), length('abc'), replace('a-b', '-', '+'), instr('hello', 'l'), trim('  x ')` |
| JSON | `SELECT json_extract('{"a": [1, 2]}', '$.a[1]'), '{"a": 5}' ->> '$.a'` |
| Index | `CREATE INDEX idx_orders_customer ON orders (customer_id, order_date)` |
| Query plan | `EXPLAIN QUERY PLAN SELECT * FROM orders WHERE customer_id = 7` |
| View | `CREATE VIEW v_big_orders AS SELECT order_id, sum(quantity * unit_price_cents) AS cents FROM order_items GROUP BY order_id HAVING cents > 50000` |
| Trigger | `CREATE TRIGGER trg_note_default AFTER INSERT ON t_notes BEGIN UPDATE t_notes SET created_on = date('now') WHERE id = NEW.id; END` |
| Transaction | `BEGIN; ... COMMIT;` or `ROLLBACK;` (in Python: `with conn:`) |
| Settings | `PRAGMA foreign_keys = ON` |
| Drop | `DROP TABLE IF EXISTS t_notes` |

And the **logical order** that explains most surprises: `FROM/JOIN` → `WHERE` → `GROUP BY` → `HAVING` → window functions → `SELECT` (aliases born here) → `DISTINCT` → `ORDER BY` → `LIMIT`.

## Reading SQL From Other Databases

Most tutorials, Stack Overflow answers and job interviews use PostgreSQL, MySQL or SQL Server. About 90 % of what you learned is the same everywhere (`SELECT`, `WHERE`, `JOIN`, `GROUP BY`, CTEs, window functions). The remaining 10 % is dialect, mostly in the places below.

### Dialect Translation Table

First, the everyday differences (the last two columns are written from the documentation of those databases; the first two you ran yourself during this course):

| | SQLite | DuckDB | PostgreSQL | MySQL | SQL Server |
|---|---|---|---|---|---|
| First n rows | `LIMIT n` | `LIMIT n` | `LIMIT n` (or `FETCH FIRST n ROWS ONLY`) | `LIMIT n` | `SELECT TOP n` (or `OFFSET 0 ROWS FETCH NEXT n ROWS ONLY`) |
| Auto-increment key | `INTEGER PRIMARY KEY` (rowid alias) | `CREATE SEQUENCE` + `DEFAULT nextval('seq')` | `GENERATED ALWAYS AS IDENTITY` (or `SERIAL`) | `AUTO_INCREMENT` | `IDENTITY(1,1)` |
| Copy a query into a table | `CREATE TABLE t AS SELECT ...` | same | same | same | `SELECT ... INTO t FROM ...` |
| Replace NULL | `COALESCE`, `IFNULL` | `COALESCE`, `IFNULL` | `COALESCE` | `COALESCE`, `IFNULL` | `COALESCE`, `ISNULL` (Oracle: `NVL`) |
| Join strings | `a \|\| b`, `concat()` | `a \|\| b`, `concat()` | `a \|\| b`, `concat()` | `CONCAT(a, b)` | `a + b`, `CONCAT(a, b)` |
| List of values as one string | `string_agg(x, ', ')` (older: `group_concat`) | `string_agg` | `string_agg` | `GROUP_CONCAT(x SEPARATOR ', ')` | `STRING_AGG` |
| Upsert | `ON CONFLICT (k) DO UPDATE` | `ON CONFLICT (k) DO UPDATE` | `ON CONFLICT (k) DO UPDATE` | `ON DUPLICATE KEY UPDATE` | `MERGE` |
| Boolean | integers 0/1 (`TRUE`/`FALSE` are aliases) | `BOOLEAN` | `BOOLEAN` | `BOOLEAN` is `TINYINT(1)` | `BIT` |
| `7 / 2` | `3` (integers) | `3.5` (`7 // 2` is `3`) | `3` | `3.5000` (`7 DIV 2` is `3`) | `3` |
| Quote an identifier | `"name"` | `"name"` | `"name"` | `` `name` `` | `[name]` (or `"name"`) |
| Case in `LIKE` | insensitive (ASCII) | sensitive (`ILIKE` is not) | sensitive (`ILIKE` is not) | depends on the collation, usually insensitive | depends on the collation, usually insensitive |
| `FULL OUTER JOIN` | yes (3.39+) | yes | yes | **no** (emulate with `UNION`) | yes |
| Stored procedures | none (use Python) | none (macros, Day 25) | functions and procedures | procedures | procedures (T-SQL) |
| Types | flexible (affinity); `STRICT` tables | strict | strict | strict | strict |

Then dates and times, where the dialects differ most:

| | SQLite | DuckDB | PostgreSQL | MySQL | SQL Server |
|---|---|---|---|---|---|
| Today | `date('now')` | `current_date` | `CURRENT_DATE` | `CURDATE()` | `CAST(GETDATE() AS DATE)` |
| Add 7 days | `date(d, '+7 days')` | `d + INTERVAL 7 DAY` | `d + INTERVAL '7 days'` | `DATE_ADD(d, INTERVAL 7 DAY)` | `DATEADD(day, 7, d)` |
| Year of a date | `strftime('%Y', d)` | `year(d)` | `EXTRACT(YEAR FROM d)` | `YEAR(d)` | `YEAR(d)` |
| Days between | `julianday(a) - julianday(b)` | `a - b` or `date_diff('day', b, a)` | `a - b` | `DATEDIFF(a, b)` | `DATEDIFF(day, b, a)` |
| Format a date | `strftime('%Y-%m', d)` | `strftime(d, '%Y-%m')` | `TO_CHAR(d, 'YYYY-MM')` | `DATE_FORMAT(d, '%Y-%m')` | `FORMAT(d, 'yyyy-MM')` |

Spot the trap: SQLite's `strftime` takes the **format first**, DuckDB's takes the **date first**. Both exist; neither is wrong.

> **Common mistake:** copying a query from a tutorial and trusting the result. Check the dialect first. A query that *runs* on another database can still give a different answer (`7 / 2`, `LIKE` and NULL ordering all do).

### Translating Automatically with sqlglot

**sqlglot** (installed by `uv sync` as a dev tool, used on Day 27) reads SQL in one dialect and writes it in another:

```py
import sqlglot

SQL = 'SELECT name, price_cents FROM products WHERE price_cents > 5000 ORDER BY price_cents DESC LIMIT 5'
for dialect in ('tsql', 'postgres', 'mysql', 'duckdb', 'oracle'):
    print(f'{dialect:9}', sqlglot.transpile(SQL, read='sqlite', write=dialect)[0])
```

```sh
output
tsql      SELECT TOP 5 name, price_cents FROM products WHERE price_cents > 5000 ORDER BY price_cents DESC
postgres  SELECT name, price_cents FROM products WHERE price_cents > 5000 ORDER BY price_cents DESC NULLS LAST LIMIT 5
mysql     SELECT name, price_cents FROM products WHERE price_cents > 5000 ORDER BY price_cents DESC LIMIT 5
duckdb    SELECT name, price_cents FROM products WHERE price_cents > 5000 ORDER BY price_cents DESC LIMIT 5
oracle    SELECT name, price_cents FROM products WHERE price_cents > 5000 ORDER BY price_cents DESC NULLS LAST FETCH FIRST 5 ROWS ONLY
```

It turned `LIMIT` into `TOP` for SQL Server and into `FETCH FIRST` for Oracle. Notice `NULLS LAST` for PostgreSQL: SQLite sorts NULLs as the *smallest* value, PostgreSQL as the *largest*, and sqlglot adds the keyword to keep the same order. More examples with functions:

```py
for sql in ("SELECT iif(stock > 0, 'in stock', 'sold out') FROM products",
            "SELECT group_concat(name, ', ') FROM categories",
            "SELECT date('now', '+7 days')",
            "SELECT strftime('%Y-%m', order_date) FROM orders"):
    print('tsql    ', sqlglot.transpile(sql, read='sqlite', write='tsql')[0])
    print('postgres', sqlglot.transpile(sql, read='sqlite', write='postgres')[0])
```

```sh
output
tsql     SELECT IIF(stock > 0, 'in stock', 'sold out') FROM products
postgres SELECT CASE WHEN stock > 0 THEN 'in stock' ELSE 'sold out' END FROM products
tsql     SELECT STRING_AGG(name, ', ') FROM categories
postgres SELECT STRING_AGG(name, ', ') FROM categories
tsql     SELECT DATE('now', '+7 days')
postgres SELECT DATE('now', '+7 days')
tsql     SELECT FORMAT(CAST(order_date AS DATETIME2), 'yyyy-MM') FROM orders
postgres SELECT TO_CHAR(CAST(order_date AS TIMESTAMP), 'YYYY-MM') FROM orders
```

Look at the third pair: `date('now', '+7 days')` came out **unchanged**, and neither SQL Server nor PostgreSQL has a function that works like that. sqlglot translates what it understands and passes the rest through. **Always read and test the result.** Treat it as a very good first draft, not a guarantee.

### W3Schools Topic Map

W3Schools is where many people look SQL up, and it teaches MySQL/SQL Server flavours. Every topic of its SQL tutorial is in this course or has a direct equivalent:

| W3Schools topic | Where in this course | Notes for SQLite / DuckDB |
|---|---|---|
| Home, Intro, Syntax | Day 1 | `;` ends a statement; keywords are case-insensitive |
| SELECT, SELECT DISTINCT | Day 4 | |
| WHERE, AND / OR / NOT | Day 5 | |
| ORDER BY | Day 4 | NULL order differs: Day 4 |
| INSERT INTO | Day 3 | |
| NULL Values | Day 5 | `IS NULL`, never `= NULL` |
| UPDATE, DELETE | Day 8 | `RETURNING` is a bonus |
| SELECT TOP, LIMIT, FETCH FIRST | Day 4 |  `TOP` is SQL Server; here `LIMIT` |
| MIN, MAX, COUNT, AVG, SUM | Day 7 | |
| LIKE, Wildcards | Day 5 | `%` and `_`; `GLOB` and `ILIKE` (DuckDB) |
| IN, BETWEEN | Day 5 | |
| Aliases | Day 4 | |
| Joins, INNER JOIN | Day 11 | |
| LEFT, RIGHT, FULL JOIN | Day 12 | RIGHT/FULL need SQLite 3.39+ |
| Self Join | Day 12 | |
| UNION | Day 15 | also `INTERSECT`, `EXCEPT` |
| GROUP BY, HAVING | Day 7 | |
| EXISTS | Day 13 | |
| ANY, ALL | Days 13 and 25 | SQLite lacks them (rewrites on Day 13); DuckDB has them |
| SELECT INTO | Day 14 |  SQL Server only; use `CREATE TABLE ... AS SELECT` |
| INSERT INTO SELECT | Day 10 | |
| CASE | Day 6 | |
| NULL Functions (`ISNULL`, `IFNULL`, `COALESCE`) | Day 6 |  `ISNULL` is SQL Server, `NVL` is Oracle |
| Stored Procedures | Days 19, 22, 25 | none in SQLite; Python functions, and `CREATE MACRO` in DuckDB |
| Comments | Day 1 | `--` and `/* */` |
| Operators | Day 6 | `<>` and `!=` both work |
| Create / Drop Database | Day 1 | a SQLite database is a file: create or delete it |
| Backup Database | Days 19 and 27 | `backup()`, `VACUUM INTO`, `iterdump()` |
| Create Table, Drop Table, Alter Table | Day 2 | |
| Constraints: NOT NULL, UNIQUE, PRIMARY KEY, FOREIGN KEY, CHECK, DEFAULT | Days 2 and 9 | `PRAGMA foreign_keys = ON` |
| Create Index | Day 21 | |
| Auto Increment | Day 2 |  `AUTO_INCREMENT` (MySQL), `IDENTITY` (SQL Server) |
| Dates | Days 16 and 23 | text in SQLite, real types in DuckDB |
| Views | Day 22 | |
| SQL Injection | Days 3 and 27 | |
| SQL Hosting | not needed | SQLite and DuckDB are libraries, not servers; see "Where to Go Next" for server databases |
| Data Types | Days 2 and 23 | |
| Functions reference (MySQL / SQL Server / MS Access) | Days 6, 7, 16 and the table above | the dialect table translates the common ones |

The course also covers a lot that W3Schools does not: window functions (Days 17-18), CTEs (Day 14), triggers, FTS5, and everything about DuckDB.

## SQLite vs DuckDB: When to Pick Which

| | SQLite | DuckDB |
|---|---|---|
| Built for | **OLTP**: many small reads and writes (an app's data) | **OLAP**: a few big scans and aggregations (analysis) |
| Storage | rows | columns |
| Typical question | "update this member's email" | "revenue per category per month" |
| Concurrency | many readers, one writer | one process writes; many threads read |
| Files directly | CSV via import | CSV, JSON, Parquet, even URLs: `SELECT * FROM 'x.parquet'` |
| Extra SQL | the standard core, window functions, JSON, FTS5 | `GROUP BY ALL`, `QUALIFY`, `PIVOT`, lists, structs, macros |
| Types | flexible (use `STRICT`) | strict and rich (`DATE`, `DECIMAL`, `LIST`) |
| Pick it for | apps, config, small data stores, tests, mobile | notebooks, reports, ETL, data on disk too big for pandas |

A good rule: **SQLite is where an application keeps its data; DuckDB is where an analyst looks at it.** Using both, as on Day 29, is normal.

## Classic SQL Patterns: A Problem Bank

These problems keep coming back in real work and in interviews. Seventeen of them, easy first, all on `shop.db` and **all run for real**. Try to write each one yourself from the title before you read the query. (The queries use deterministic tie-breakers; results come from `solutions/day_30.py`.)

### P1: Second-highest value (second most expensive price)

```sql
SELECT max(price_cents) AS second_highest_price FROM products
WHERE price_cents < (SELECT max(price_cents) FROM products)
```

```sh
output
second_highest_price
--------------------
8999
(1 row)
```

Alternative: `ORDER BY price_cents DESC LIMIT 1 OFFSET 1` (but that counts ties as separate rows).

### P2: Nth highest with DENSE_RANK (third highest salary)

```sql
SELECT name, salary_cents FROM (
    SELECT name, salary_cents, DENSE_RANK() OVER (ORDER BY salary_cents DESC) AS r FROM employees)
WHERE r = 3 ORDER BY name
```

```sh
output
name          salary_cents
------------  ------------
Ada Lovelace  13500000
(1 row)
```

`DENSE_RANK` handles ties: if two people share the top salary, the "second highest" is still the next distinct value.

### P3: Top-N per group (2 priciest products per category)

```sql
SELECT category, product, price_cents FROM (
    SELECT c.name AS category, p.name AS product, p.price_cents,
           ROW_NUMBER() OVER (PARTITION BY c.category_id ORDER BY p.price_cents DESC, p.name) AS rn
    FROM products p JOIN categories c ON c.category_id = p.category_id)
WHERE rn <= 2 ORDER BY category, rn
```

```sh
output
category        product                      price_cents
--------------  ---------------------------  -----------
Books           The Pragmatic Programmer     4999
Books           SQL for Data Analysis        4499
Clothing        Denim Jacket                 7999
Clothing        Rain Coat                    5999
Electronics     Noise-Cancelling Headphones  14999
Electronics     Bluetooth Speaker            5999
Grocery         Espresso Beans 1kg           2299
Grocery         Olive Oil 500ml              1499
Home & Kitchen  Chef's Knife                 6999
Home & Kitchen  Cast Iron Pan                3499
Sports          Running Shoes                8999
Sports          Camping Hammock              3999
Toys            Remote Control Car           4499
Toys            Board Game Night             3999
(14 rows)
```

`ROW_NUMBER` with a tie-breaker (`p.name`) gives exactly two rows per category. DuckDB does it without the subquery using `QUALIFY` (Day 25).

### P4: Find duplicates (case-insensitive emails)

```sql
SELECT lower(trim(email)) AS email, count(*) AS copies FROM newsletter_signups
GROUP BY lower(trim(email)) HAVING count(*) > 1 ORDER BY copies DESC, email LIMIT 5
```

```sh
output
email              copies
-----------------  ------
ana@example.com    2
ben@example.com    2
carla@example.com  2
dev@example.com    2
gina@example.com   2
(5 rows)
```

`GROUP BY` the normalised value, keep groups bigger than one.

### P5: Remove duplicates (keep the earliest signup)

Always run this on a copy first, and look at the count before and after.

```sql
DELETE FROM newsletter_signups WHERE rowid IN (
    SELECT rowid FROM (
        SELECT rowid, ROW_NUMBER() OVER (PARTITION BY lower(trim(email)) ORDER BY signed_up_at, rowid) AS rn
        FROM newsletter_signups)
    WHERE rn > 1)
```

```sh
output
rows before: 20, rows after: 12
```

(Then prevent the problem for good with a `UNIQUE` index on `lower(trim(email))`, Day 17.)

### P6: Running total (cumulative revenue, first months of 2025)

```sql
WITH monthly AS (
    SELECT strftime('%Y-%m', o.order_date) AS month, sum(i.quantity * i.unit_price_cents) AS cents
    FROM orders o JOIN order_items i ON i.order_id = o.order_id
    WHERE o.status != 'cancelled' AND o.order_date >= '2025-01-01' GROUP BY month)
SELECT month, cents, sum(cents) OVER (ORDER BY month) AS running_cents FROM monthly ORDER BY month LIMIT 4
```

```sh
output
month    cents   running_cents
-------  ------  -------------
2025-01  180703  180703
2025-02  120411  301114
2025-03  180877  481991
2025-04  160987  642978
(4 rows)
```

### P7: Month-over-month change (%)

```sql
WITH monthly AS (
    SELECT strftime('%Y-%m', o.order_date) AS month, sum(i.quantity * i.unit_price_cents) AS cents
    FROM orders o JOIN order_items i ON i.order_id = o.order_id
    WHERE o.status != 'cancelled' AND o.order_date >= '2025-01-01' GROUP BY month)
SELECT month, cents, round(100.0 * (cents - LAG(cents) OVER (ORDER BY month)) / LAG(cents) OVER (ORDER BY month), 1) AS mom_pct
FROM monthly ORDER BY month LIMIT 4
```

```sh
output
month    cents   mom_pct
-------  ------  -------
2025-01  180703  NULL
2025-02  120411  -33.4
2025-03  180877  50.2
2025-04  160987  -11.0
(4 rows)
```

### P8: Pivot with conditional aggregation (status by year)

```sql
SELECT substr(order_date, 1, 4) AS year,
       count(*) FILTER (WHERE status = 'delivered') AS delivered,
       count(*) FILTER (WHERE status = 'shipped') AS shipped,
       count(*) FILTER (WHERE status = 'pending') AS pending,
       count(*) FILTER (WHERE status = 'cancelled') AS cancelled
FROM orders GROUP BY year ORDER BY year
```

```sh
output
year  delivered  shipped  pending  cancelled
----  ---------  -------  -------  ---------
2024  167        0        0        14
2025  179        14       15       10
(2 rows)
```

### P9: Median (order totals, odd or even count)

```sql
WITH totals AS (
    SELECT order_id, sum(quantity * unit_price_cents) AS cents FROM order_items GROUP BY order_id),
ranked AS (
    SELECT cents, ROW_NUMBER() OVER (ORDER BY cents, order_id) AS rn, count(*) OVER () AS n FROM totals)
SELECT avg(cents) AS median_cents FROM ranked WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
```

```sh
output
median_cents
------------
8997.0
(1 row)
```

SQLite has no `MEDIAN`. Number the rows, then average the one or two middle ones: `(n + 1) / 2` and `(n + 2) / 2` are the same row when `n` is odd and the two middle rows when `n` is even. DuckDB has `median(x)`.

### P10: Gaps and islands (longest run of consecutive order days)

```sql
WITH days AS (SELECT DISTINCT customer_id, order_date FROM orders),
marked AS (
    SELECT customer_id, order_date,
           julianday(order_date) - ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS grp
    FROM days)
SELECT customer_id, min(order_date) AS first_day, count(*) AS streak_days FROM marked
GROUP BY customer_id, grp ORDER BY streak_days DESC, customer_id, first_day LIMIT 3
```

```sh
output
customer_id  first_day   streak_days
-----------  ----------  -----------
3            2024-03-11  5
12           2025-02-03  4
29           2025-11-20  3
(3 rows)
```

Subtracting the row number from the date gives the same value for each run of consecutive days (Day 18), so the value identifies the run.

### P11: Cohort retention (first-order month vs ordering again the next month)

```sql
WITH firsts AS (
    SELECT customer_id, strftime('%Y-%m', min(order_date)) AS cohort FROM orders GROUP BY customer_id),
next_month AS (
    SELECT f.customer_id, f.cohort,
           EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = f.customer_id
                   AND strftime('%Y-%m', o.order_date) = strftime('%Y-%m', date(f.cohort || '-01', '+1 month'))) AS came_back
    FROM firsts f)
SELECT cohort, count(*) AS customers, sum(came_back) AS returned_next_month FROM next_month
GROUP BY cohort ORDER BY cohort LIMIT 5
```

```sh
output
cohort   customers  returned_next_month
-------  ---------  -------------------
2024-01  2          2
2024-02  5          1
2024-03  6          0
2024-04  6          1
2024-05  4          1
(5 rows)
```

### P12: Sessionization by inactivity gap (a new 'streak of activity' after 60 quiet days)

```sql
WITH flagged AS (
    SELECT customer_id, order_date,
           CASE WHEN julianday(order_date) - julianday(LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id)) > 60
                THEN 1 ELSE 0 END AS new_session
    FROM orders),
numbered AS (
    SELECT customer_id, order_date, sum(new_session) OVER (PARTITION BY customer_id ORDER BY order_date) AS session_no FROM flagged)
SELECT customer_id, count(DISTINCT session_no) AS sessions FROM numbered
GROUP BY customer_id ORDER BY sessions DESC, customer_id LIMIT 3
```

```sh
output
customer_id  sessions
-----------  --------
14           8
13           6
15           6
(3 rows)
```

Flag a row when the gap to the previous row is more than the allowed quiet time, then a running `SUM` of the flags numbers the sessions.

### P13: Bought X but never Y (bought Books, never bought Toys)

```sql
SELECT count(DISTINCT o.customer_id) AS customers FROM orders o
JOIN order_items i ON i.order_id = o.order_id JOIN products p ON p.product_id = i.product_id
JOIN categories c ON c.category_id = p.category_id
WHERE c.name = 'Books' AND o.customer_id NOT IN (
    SELECT o2.customer_id FROM orders o2 JOIN order_items i2 ON i2.order_id = o2.order_id
    JOIN products p2 ON p2.product_id = i2.product_id JOIN categories c2 ON c2.category_id = p2.category_id
    WHERE c2.name = 'Toys')
```

```sh
output
customers
---------
8
(1 row)
```

`NOT IN` is safe here because `customer_id` in `orders` is never NULL (Day 13 explains when it is not).

### P14: Anti-join (products never ordered)

```sql
SELECT p.name FROM products p LEFT JOIN order_items i ON i.product_id = p.product_id
WHERE i.product_id IS NULL ORDER BY p.name
```

```sh
output
name
---------------
Beanie
Camping Hammock
Jump Rope
Mystery Box
(4 rows)
```

### P15: Ranking with ties (customers by order count, DENSE_RANK, top 3 ranks)

```sql
SELECT customer_id, orders, rnk FROM (
    SELECT customer_id, count(*) AS orders, DENSE_RANK() OVER (ORDER BY count(*) DESC) AS rnk
    FROM orders GROUP BY customer_id)
WHERE rnk <= 3 ORDER BY rnk, customer_id
```

```sh
output
customer_id  orders  rnk
-----------  ------  ---
7            20      1
18           19      2
24           18      3
(3 rows)
```

### P16: Relational division (ordered in all four quarters of 2025)

```sql
SELECT customer_id FROM orders WHERE order_date BETWEEN '2025-01-01' AND '2025-12-31'
GROUP BY customer_id
HAVING count(DISTINCT (CAST(substr(order_date, 6, 2) AS INTEGER) + 2) / 3) = 4
ORDER BY customer_id LIMIT 5
```

```sh
output
customer_id
-----------
6
7
14
15
18
(5 rows)
```

Relational division: "has all of the X" becomes `HAVING COUNT(DISTINCT x) = (number of Xs)`. The expression `(month + 2) / 3` maps months 1-12 to quarters 1-4.

### P17: Recursive CTE (org chart with level)

```sql
WITH RECURSIVE chart(employee_id, name, level) AS (
    SELECT employee_id, name, 1 FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.employee_id, e.name, chart.level + 1 FROM employees e JOIN chart ON e.manager_id = chart.employee_id)
SELECT level, count(*) AS people FROM chart GROUP BY level ORDER BY level
```

```sh
output
level  people
-----  ------
1      1
2      3
3      4
4      7
(4 rows)
```

## Final Review: 20 Mixed Questions

No new ideas, no order by day: this is the "which tool fits?" test. Use `shop.db` (on a copy) unless it says otherwise; "the library" means the normalized library of Day 10. Answers are below, and the code is in `solutions/day_30.py`. Questions 1-8 are Level 1, 9-15 Level 2, 16-20 Level 3.

1. How many products cost more than 5,000 cents?
2. How many customers have no `city`?
3. The three cheapest products by price (ties by name).
4. How many orders were placed in December 2025?
5. Which country has the most customers, and how many?
6. **Predict first:** `SELECT 7 / 2, 7 / 2.0, 7 % 2` in SQLite.
7. **Predict first:** `SELECT NULL = NULL, NULL IS NULL, 1 + NULL, coalesce(NULL, 5)`.
8. Total units in stock across all products.
9. Revenue in cents from the category `Books`, not counting cancelled orders.
10. How many customers have never placed an order? Use `NOT EXISTS`.
11. Which employee has the most direct reports, and how many?
12. How many products cost more than the average price of **their own category**?
13. Which month has the highest revenue overall (cancelled orders excluded), and how much?
14. **Find the bug.** "How many employees are not managers?" was written as `SELECT count(*) FROM employees WHERE employee_id NOT IN (SELECT manager_id FROM employees)` and returns `0`. Why, and what is the right answer?
15. In **DuckDB**, attach `shop.db` read-only and count orders per status with `GROUP BY ALL`, most frequent first.
16. Which customer went the longest between two consecutive orders, and how many days was the gap (all orders, any status)?
17. On the Day 10 library with today = `2025-03-14`, use `LibraryRepository.overdue()`. What does it return?
18. In DuckDB, using `QUALIFY`, the best-selling product (by units) of each category, first three categories alphabetically.
19. Translate `SELECT name FROM products LIMIT 3` to SQL Server with sqlglot.
20. **In your own words:** in three sentences, why must a program never build SQL with an f-string, and what do you use instead?

**Answers**

```sh
Q1   6
Q2   7
Q3   Dark Chocolate Bar, Gift Card Holder, USB-C Cable
Q4   35
Q5   USA, 17
Q6   (3, 3.5, 1)            -- integer division, real division, remainder
Q7   (None, 1, None, 5)     -- NULL = NULL is NULL (None in Python), IS NULL is true, NULL poisons arithmetic
Q8   2193
Q9   786410                 -- $7,864.10
Q10  6
Q11  Grace Hopper, 3
Q12  16
Q13  2025-12, 432648        -- $4,326.48
Q14  buggy: 0   fixed: 7
Q15  [('delivered', 346), ('cancelled', 24), ('pending', 15), ('shipped', 14)]
Q16  customer 2, 375 days
Q17  [('The Pragmatic Programmer', 8)]
Q18  [('Books', 'The Pragmatic Programmer', 88), ('Clothing', 'Denim Jacket', 45), ('Electronics', 'USB-C Cable', 80)]
Q19  SELECT TOP 3 name FROM products
```

**Q14, the explanation:** the CEO has `manager_id = NULL`. `x NOT IN (..., NULL)` can never be true (it is true or unknown), so the whole query returns no rows. The fix is `WHERE manager_id IS NOT NULL` inside the subquery (or `NOT EXISTS`); then 7 employees manage nobody.

**Q20, a model answer:** An f-string pastes user text *into* the SQL, so text like `' OR '1'='1` becomes part of the statement and is run as SQL (injection). A parameterized query sends the statement and the values separately (`conn.execute('... WHERE name = ?', (name,))`), so a value can never be executed. Names of tables and columns cannot be parameters, so for those you choose from an allowlist of known-good names.

## Where to Go Next

**Go deeper in what you already use**

- **SQLite itself.** Read the official documentation: it is excellent, short and honest. Topics we only touched: `WITHOUT ROWID` tables, partial and expression indexes, JSONB, the `sqlite3` command line shell, `PRAGMA optimize`, and **FTS5**.
- **FTS5 full-text search** (Day 21's bonus). `CREATE VIRTUAL TABLE docs USING fts5(title, body)` gives you `MATCH` queries, ranking with `bm25()` and `highlight()`: search that understands words, much faster than `LIKE '%word%'`. If you skipped the bonus, go back to it now. DuckDB has a similar `fts` extension.
- **DuckDB.** More window functions, `ASOF` joins, spatial and geospatial extensions, the `httpfs`/S3 readers, and Parquet datasets with partitioning. For data that has outgrown one file, look at **DuckLake** and **MotherDuck** (DuckDB in the cloud).
- **Query performance.** Read how the planner works (`EXPLAIN`, statistics, join order). *Use The Index, Luke* (use-the-index-luke.com) is a free book on indexing that applies to every database.

**A server database: PostgreSQL**

Most companies run PostgreSQL, MySQL/MariaDB or SQL Server. **PostgreSQL** is the best next step: it is free, standard-compliant and very capable. What is new: users and `GRANT`, many writers at once (MVCC), real `DATE`/`TIMESTAMPTZ`/`NUMERIC` types, `JSONB`, arrays, `LATERAL` joins, materialized views, stored functions, extensions such as PostGIS. The dialect table above is your cheat sheet; almost everything else from this course carries over unchanged. Connect from Python with `psycopg` (the same placeholder idea, `%s`).

**Python and SQL together**

- **SQLAlchemy 2.0**: a toolkit that builds SQL from Python objects, handles connection pools and works with every database; its ORM maps rows to classes (the next step after your `LibraryRepository`).
- **Alembic**: migrations for SQLAlchemy (Day 27's idea, industrial strength).
- **Polars and pandas** with DuckDB for analysis; **Datasette** to publish a SQLite file as a browsable website.
- **dbt**: version-controlled SQL transformations for analytics warehouses, "software engineering for SQL" (CTEs, tests and documentation, everything of Days 14 and 27, scaled up).

**Data warehouses and the business side**

BigQuery, Snowflake and Redshift speak a SQL close to DuckDB's. Learn **dimensional modelling** (facts and dimensions, star schemas, *The Data Warehouse Toolkit* by Kimball and Ross) and how data teams build reports like your Day 29 project.

**Practice**

- Solve problems: LeetCode's database section, HackerRank SQL, StrataScratch, and "SQL Murder Mystery" for fun. Time yourself on the pattern bank above.
- Pick a dataset you care about (your own bank export, a sports season, a game's logs), load it into DuckDB, and ask ten questions of it. Nothing teaches like your own question.
- Read other people's schemas and queries: open-source apps use SQLite everywhere (browsers, phones, Home Assistant, Jupyter).
- Books: *SQL Antipatterns* (Karwin), *Designing Data-Intensive Applications* (Kleppmann), *Database Internals* (Petrov) when you are curious about how it works inside.

## Final Checklist

Tick these off honestly. If one is shaky, the day in brackets is where to revisit it.

- [ ] I can create tables with sensible types, keys and constraints, and store money as integer cents. (2, 9)
- [ ] I never build SQL from user input; I use parameters and allowlists. (3, 27)
- [ ] I handle NULL deliberately: `IS NULL`, `COALESCE`, and I know why `NOT IN` can fail. (5, 6, 13)
- [ ] I can write a query step by step: one table, then one join at a time, checking row counts. (11)
- [ ] I can choose between a join, a subquery, a CTE and a temp table. (11-14)
- [ ] I can explain the logical order of a query, and why `WHERE` cannot use an aggregate. (7)
- [ ] I can use window functions for ranking, running totals, `LAG` and gaps-and-islands. (17, 18)
- [ ] I use transactions for changes that must succeed or fail together. (8, 19)
- [ ] I can read a query plan and know when an index helps. (21)
- [ ] I can load, clean and export data with Python and SQL. (3, 20)
- [ ] I can query files with DuckDB and move data between DuckDB, pandas, Polars and SQLite. (24-26)
- [ ] I know when to pick SQLite and when DuckDB. (23, 30)
- [ ] I can change a schema with migrations, back up a database and test my queries with pytest. (27)
- [ ] I can read SQL written for other databases and translate the common differences. (30)
- [ ] I built two projects from a blank file: a CLI and a report. (28, 29)

Thirty lessons ago a database was a mystery and `SELECT` was a word. Now you design schemas, write analytical queries, defend your data, test your code, and move between two engines and several languages' worth of SQL. Keep a database project going, however small. SQL is one of the very few skills that stays useful for a whole career, and you now have it.

CONGRATULATIONS !

[<< Day 29](../29_Day_Project_analytics_report/29_project_analytics_report.md)
