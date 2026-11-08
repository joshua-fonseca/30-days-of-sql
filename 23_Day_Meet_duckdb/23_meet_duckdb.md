<div align="center">
  <h1> 30 Days Of SQL: Day 23 - Meet DuckDB</h1>
</div>

[<< Day 22 Review](../22R_Review_Python_and_sqlite/22R_review_python_and_sqlite.md) | [Day 24 >>](../24_Day_Querying_files/24_querying_files.md)

- [Day 23](#day-23)
  - [Two Kinds of Database Work](#two-kinds-of-database-work)
    - [OLTP and OLAP](#oltp-and-olap)
    - [Rows vs Columns](#rows-vs-columns)
    - [SQLite or DuckDB?](#sqlite-or-duckdb)
  - [Getting Started](#getting-started)
    - [Your First Query](#your-first-query)
    - [Getting the Result Out](#getting-the-result-out)
    - [Relations Are Lazy](#relations-are-lazy)
  - [Connections: In Memory and on File](#connections-in-memory-and-on-file)
    - [Creating Tables and Inserting Rows](#creating-tables-and-inserting-rows)
    - [A Database in a File](#a-database-in-a-file)
    - [Parameters](#parameters)
  - [Types: DuckDB Is Strict](#types-duckdb-is-strict)
    - [Strict, but Friendly](#strict-but-friendly)
    - [Numbers: Division and DECIMAL](#numbers-division-and-decimal)
    - [Real Dates and Times](#real-dates-and-times)
    - [Lists, Structs and Maps](#lists-structs-and-maps)
    - [Auto-increment with Sequences](#auto-increment-with-sequences)
  - [Getting Data In](#getting-data-in)
    - [From SQLite with Python](#from-sqlite-with-python)
    - [A First Taste of Files](#a-first-taste-of-files)
  - [Almost Everything You Learned Still Works](#almost-everything-you-learned-still-works)
  - [What Is Different](#what-is-different)
  - [Looking Inside a Query: EXPLAIN](#looking-inside-a-query-explain)
  - [ Tool Tips](#tool-tips)
  - [ Exercises: Day 23](#exercises-day-23)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 23

> **Before you start:** run `uv sync` so DuckDB, pandas, polars and pyarrow are installed, and make sure `data/big_events.csv` exists (`uv run python tools/make_big_events.py`). Day 23 Level 2 builds `00_practice/shop.duckdb`, which Days 25 and 26 and Review 5 reuse. See "Setup & data" in the [readme](../readme.md#-setup--data-what-each-day-needs).

For 22 days you used **SQLite**, the database that ships with Python. Today the course changes engine. From Day 23 to Day 26 we use **DuckDB**, a
second embedded database that you also run as a Python library, without a server. The good news: you already know about 95% of what you need. The same
`SELECT`, `JOIN`, `GROUP BY`, CTEs and window functions work. What changes is *what the engine is built for*, a few types, and a handful of details.

## Two Kinds of Database Work

### OLTP and OLAP

Think of a supermarket. At the checkout, thousands of tiny things happen all day: scan one item, update its stock, print one receipt. In the head office, one analyst
asks a very different question: "what was the total revenue per product category over the last two years?". The first kind of work touches **a few rows at a time, and
changes them**. The second touches **millions of rows, but only a few columns, and just reads**.

| | OLTP (online transaction processing) | OLAP (online analytical processing) |
|---|---|---|
| Typical work | insert/update/delete one order, look up one customer | totals, averages, trends over a whole table |
| Rows touched per query | a handful | millions |
| Columns touched per query | most of them | a few |
| Many users at once | yes | usually one analyst |
| Example engines | SQLite, PostgreSQL, MySQL | DuckDB, ClickHouse, BigQuery |

SQLite is a superb OLTP engine. DuckDB is built for OLAP, and it is to analytics what SQLite is to application data: a library, a single file, no server.

### Rows vs Columns

The big difference is how the data is laid out in storage. SQLite keeps each **row** together. DuckDB keeps each **column** together.

```
The table                   Row store (SQLite)             Column store (DuckDB)

 id  name  city  age        [1 Ana Oslo 31]                id:    1    2    3
 1   Ana   Oslo  31         [2 Ben Rome 25]                name:  Ana  Ben  Cy
 2   Ben   Rome  25         [3 Cy  Oslo 42]                city:  Oslo Rome Oslo
 3   Cy    Oslo  42                                        age:   31   25   42
```

Fetching *one whole person* is quick in a row store: everything about Ana sits side by side. But `SELECT AVG(age)` over a million rows has to wade through names and
cities it does not need. A column store reads **only the `age` column**, in one straight line, and can also compress it well (a column of similar values squeezes much
better than a row of mixed ones). DuckDB then processes the values in batches ("vectorised execution") and spreads the work over all CPU cores. That is why it can be
many times faster on aggregations. Today's exercises measure it yourself.

The price: changing a single row in a column store is more work, and DuckDB is not meant for lots of tiny concurrent writes.

### SQLite or DuckDB?

| Situation | Reach for |
|---|---|
| The storage of an app: users, orders, settings, a to-do list | SQLite |
| Many small reads and writes, several programs writing | SQLite |
| Totals, group-bys and joins over big tables (millions of rows) | DuckDB |
| "I have a CSV/Parquet/JSON file and want to ask SQL questions about it" | DuckDB (tomorrow's topic) |
| Analysing a pandas or Polars DataFrame with SQL | DuckDB (Day 26) |
| A tiny table you look up by key | either, SQLite is simpler |

They are not rivals: many projects keep their data in SQLite (or PostgreSQL) and analyse it with DuckDB. By Day 26 you will do exactly that.

## Getting Started

DuckDB is already in your project (`uv add duckdb` put it into `pyproject.toml`). The version matters because DuckDB moves quickly, and this course was written against the
one printed here:

```py
import duckdb

print(duckdb.__version__)  # 2.0.0
```

### Your First Query

```py
# syntax
duckdb.sql(query)          # returns a "relation": a query you can show, fetch or convert
relation.show()            # print it as a table
relation.fetchall()        # a list of tuples, like sqlite3
```

```py
rel = duckdb.sql('SELECT 42 AS answer, 6 * 7 AS product, upper(\'duck\') AS word')
rel.show()
```

```sh
┌────────┬─────────┬─────────┐
│ answer │ product │  word   │
│ int32  │  int32  │ varchar │
├────────┼─────────┼─────────┤
│     42 │      42 │ DUCK    │
└────────┴─────────┴─────────┘
```

`duckdb.sql()` runs on a hidden, in-memory **default connection**, so there is no `connect()` and no cursor. It is perfect for quick experiments. Notice that DuckDB prints
the **type** of each column under its name (`int32`, `varchar`). SQLite never did, because SQLite's types live in the *values*; in DuckDB they live in the *columns*.

### Getting the Result Out

```py
print(rel.fetchall())  # [(42, 42, 'DUCK')]
print(rel.columns)  # ['answer', 'product', 'word']
print(rel.types)  # [INTEGER, INTEGER, VARCHAR]
```

DuckDB speaks the same dialect as `sqlite3` here: `fetchall()` returns a list of tuples, and the result carries `description`. That means **the `show()` helper you wrote on Day 4
works on DuckDB results unchanged**:

```py
from helpers import show

show(rel)
```

```sh
answer  product  word
------  -------  ----
42      42       DUCK
(1 row)
```

DuckDB's own `.show()` draws a boxed table with types, which is lovely for a quick look. Your `show()` is plainer but identical for SQLite and DuckDB. Use whichever you like.
A third way out is a pandas DataFrame:

```py
print(rel.df())
```

```sh
   answer  product  word
0      42       42  DUCK
```

(Day 26 is all about DataFrames.)

### Relations Are Lazy

A relation is not a stored result, it is a **recipe**. Every time you ask for the rows, DuckDB runs the query again. That is why a relation has no `fetchone()`: there
is no "current position" in a result that does not exist yet.

```py
try:
    rel.fetchone()
except AttributeError as e:
    print(e)
```

```sh
Relations no longer have fetchone(): a relation keeps no result between calls, so every call runs it again. Use rel.limit(1).fetchall() instead.
```

If you want to step through a result one row at a time, use a connection and `execute`, as in the next section.

## Connections: In Memory and on File

```py
# syntax
con = duckdb.connect()                      # a new, private, in-memory database
con = duckdb.connect('path/to/file.duckdb')  # a database stored in a file (created if missing)
con.sql(query)                              # returns a lazy relation
con.execute(query, parameters)              # runs now; then fetchone / fetchall / fetchmany
```

`duckdb.connect()` is the sibling of `sqlite3.connect(':memory:')`. Two things to keep apart:

- `con.sql(...)` builds a **relation** (lazy, can be shown, converted, chained).
- `con.execute(...)` **runs the statement now** and gives you the familiar `fetchone()` / `fetchall()`. Use it for `CREATE`, `INSERT` and anything with parameters.

### Creating Tables and Inserting Rows

```py
con = duckdb.connect()
con.execute('CREATE TABLE fruits (id INTEGER, name VARCHAR, price DECIMAL(10, 2))')
con.execute("INSERT INTO fruits VALUES (1, 'apple', 1.20), (2, 'banana', 0.50)")
con.executemany('INSERT INTO fruits VALUES (?, ?, ?)', [(3, 'cherry', 7.25), (4, 'date', 3)])

con.sql('SELECT * FROM fruits ORDER BY id').show()
```

```sh
┌───────┬─────────┬───────────────┐
│  id   │  name   │     price     │
│ int32 │ varchar │ decimal(10,2) │
├───────┼─────────┼───────────────┤
│     1 │ apple   │          1.20 │
│     2 │ banana  │          0.50 │
│     3 │ cherry  │          7.25 │
│     4 │ date    │          3.00 │
└───────┴─────────┴───────────────┘
```

`executemany` works as on Day 3. Reading rows one at a time:

```py
con.execute('SELECT name, price FROM fruits ORDER BY id')
print(con.fetchone())  # ('apple', Decimal('1.20'))
print(con.fetchall())  # [('banana', Decimal('0.50')), ('cherry', Decimal('7.25')), ('date', Decimal('3.00'))]
```

**Common mistake:** a result you started reading with `fetchone()` stays *open* until you read it to the end. While it is open, the connection refuses new work:

```py
con.execute('SELECT name FROM fruits ORDER BY id')
print(con.fetchone())  # ('apple',)
try:
    con.sql('SELECT 1').show()
except duckdb.Error as e:
    print(type(e).__name__)
print(con.fetchall())  # [('banana',), ('cherry',), ('date',)]
con.sql('SELECT 1 AS now_it_works').show()
```

```sh
('apple',)
ResourceInUseException
[('banana',), ('cherry',), ('date',)]
┌──────────────┐
│ now_it_works │
│    int32     │
├──────────────┤
│            1 │
└──────────────┘
```

Either read to the end with `fetchall()`, or just use `fetchall()` for results of a sensible size, as you did in `sqlite3`.

> **In other databases:** DuckDB tries to follow PostgreSQL's SQL dialect, so PostgreSQL tutorials are the closest match for what you read online.

### A Database in a File

Give `connect()` a path and the database lives in that file, just like a SQLite file. The file extension is up to you. `.duckdb` and `.db` are common.

```py
from pathlib import Path

path = Path('00_practice/day23.duckdb')
path.unlink(missing_ok=True)       # start clean so you can re-run this script

with duckdb.connect(str(path)) as db:
    db.execute('CREATE TABLE notes (id INTEGER, note VARCHAR)')
    db.execute("INSERT INTO notes VALUES (1, 'DuckDB keeps this in a file')")

print(path.exists())  # True

with duckdb.connect(str(path)) as db:
    print(db.execute('SELECT * FROM notes').fetchall())  # [(1, 'DuckDB keeps this in a file')]
```

`with` closes the connection at the end. DuckDB commits for you (it is in autocommit mode until you say `BEGIN`), so there is no `commit()` to forget. Remember that a file
database can be opened for writing by one process at a time.

### Parameters

Parameters work as on Day 3: **never** put values into the SQL with an f-string. DuckDB accepts positional `?` placeholders and named `$name` placeholders (note the dollar
sign instead of SQLite's colon):

```py
print(con.execute('SELECT name FROM fruits WHERE price > ? ORDER BY id', [1]).fetchall())  # [('apple',), ('cherry',), ('date',)]
print(con.execute('SELECT name FROM fruits WHERE price > $min AND name <> $skip ORDER BY id',
                  {'min': 1, 'skip': 'date'}).fetchall())  # [('apple',), ('cherry',)]
```

## Types: DuckDB Is Strict

### Strict, but Friendly

On Day 2 you saw SQLite store the text `'abc'` in an `INTEGER` column unless you used a `STRICT` table. In DuckDB **every** table is strict:

```py
con.execute('CREATE TABLE t (n INTEGER)')
try:
    con.execute("INSERT INTO t VALUES ('abc')")
except duckdb.Error as e:
    print(type(e).__name__, '-', str(e).splitlines()[0])
```

```sh
ConversionException - Conversion Error: Could not convert string 'abc' to INT32
```

"Strict" does not mean "pedantic": when a value can be converted sensibly, DuckDB converts it.

```py
con.execute("INSERT INTO t VALUES ('12'), (7.6)")
print(con.execute('SELECT n, typeof(n) FROM t ORDER BY n').fetchall())  # [(8, 'INTEGER'), (12, 'INTEGER')]
```

The text `'12'` became 12 and `7.6` was **rounded** to 8. Be aware that converting a decimal number to an integer rounds rather than cuts off. Expressions are stricter than inserts:
adding a number to a piece of text is an error (SQLite quietly turned `'5' + 1` into 6):

```py
try:
    duckdb.sql("SELECT '5' + 1").fetchall()
except duckdb.Error as e:
    print(type(e).__name__)
print(duckdb.sql("SELECT '5'::INTEGER + 1 AS ok, CAST('5' AS INTEGER) + 1 AS also_ok").fetchall())  # [(6, 6)]
```

`value::TYPE` is a short form of `CAST(value AS TYPE)`. If you would rather get NULL than an error for a value that does not convert, use `TRY_CAST`:

```py
print(duckdb.sql("SELECT TRY_CAST('abc' AS INTEGER) AS bad, TRY_CAST('12' AS INTEGER) AS good").fetchall())  # [(None, 12)]
```

Common DuckDB types, next to what you know:

| DuckDB type | Meaning | SQLite equivalent |
|---|---|---|
| `INTEGER`, `BIGINT` (also `SMALLINT`, `TINYINT`, `HUGEINT`) | whole numbers of 32, 64 (... 128) bits | `INTEGER` |
| `DOUBLE` (also `REAL`/`FLOAT`) | floating point | `REAL` |
| `DECIMAL(p, s)` | exact decimals: `p` digits in total, `s` after the point | none (we used integer cents) |
| `VARCHAR` (alias `TEXT`) | text of any length | `TEXT` |
| `BOOLEAN` | `true` / `false` | `INTEGER` 0 / 1 |
| `DATE`, `TIME`, `TIMESTAMP`, `INTERVAL` | real dates and times | `TEXT` in ISO format |
| `type[]` such as `INTEGER[]` | a list | none (JSON text) |
| `STRUCT(...)`, `MAP(k, v)` | a record, a dictionary | none (JSON text) |

### Numbers: Division and DECIMAL

Remember `SELECT 10 / 3` giving `3` in SQLite? In DuckDB `/` is always a real division, and the integer division is a separate operator, `//`:

```py
show(duckdb.sql('SELECT 7 / 2 AS slash, 7 // 2 AS int_div, 7 % 2 AS remainder, -7 // 2 AS negative'))
```

```sh
slash  int_div  remainder  negative
-----  -------  ---------  --------
3.5    3        1          -3
(1 row)
```

Two more behaviours worth knowing: `7 // 0` and `7 % 0` raise an error, while a *real* division by zero such as `7 / 0` gives `inf`, not NULL (see the table of differences below).

Now money. On Day 2 you saw that floating point cannot store 0.1 exactly, and we used integer cents. DuckDB offers the other classic remedy that other databases have: `DECIMAL(p, s)`,
an exact decimal number. `DECIMAL(10, 2)` holds up to 10 digits of which 2 come after the decimal point, which is a good shape for prices.

```py
show(duckdb.sql('''
    SELECT 0.1::DOUBLE + 0.2::DOUBLE                 AS as_double,
           0.1::DECIMAL(10, 2) + 0.2::DECIMAL(10, 2) AS as_decimal,
           typeof(0.1::DECIMAL(10, 2) + 0.2::DECIMAL(10, 2)) AS decimal_type
'''))
```

```sh
as_double            as_decimal  decimal_type
-------------------  ----------  -------------
0.30000000000000004  0.30        DECIMAL(11,2)
(1 row)
```

The `DOUBLE` sum is the familiar `0.30000000000000004`. The `DECIMAL` sum is exactly `0.30`. Python gets the exact value back as a `decimal.Decimal`.
Our shop data stays in integer cents (both approaches are fine, and `*_cents` columns are safe in every database); in the exercises you will also see `DECIMAL` in use.

### Real Dates and Times

SQLite had no date type, so you stored ISO text and used `date()`, `strftime()` and `julianday()` (Day 16). DuckDB has real `DATE`, `TIME`, `TIMESTAMP` and `INTERVAL` types,
and arithmetic simply works:

```py
show(duckdb.sql('''
    SELECT DATE '2025-03-14'                                    AS d,
           DATE '2025-03-14' + 30                               AS plus_30_days,
           DATE '2025-03-14' - DATE '2025-01-01'                AS days_between,
           DATE '2025-01-31' + INTERVAL 1 MONTH                 AS plus_1_month,
           TIMESTAMP '2025-03-14 10:30:00' + INTERVAL 90 MINUTE AS plus_90_min
'''))
```

```sh
d           plus_30_days  days_between  plus_1_month         plus_90_min
----------  ------------  ------------  -------------------  -------------------
2025-03-14  2025-04-13    72            2025-02-28 00:00:00  2025-03-14 12:00:00
(1 row)
```

Subtracting two dates gives a number of days. Adding a month to 31 January lands on 28 February, the last day of that month, and `INTERVAL` arithmetic on a date returns a `TIMESTAMP`.
Extracting parts has plain function names, and `strftime` takes the date **first**, the reverse of SQLite's argument order:

```py
show(duckdb.sql('''
    SELECT year(DATE '2025-03-14') AS year, month(DATE '2025-03-14') AS month,
           dayname(DATE '2025-03-14') AS weekday,
           strftime(DATE '2025-03-14', '%d %B %Y') AS pretty,
           date_trunc('month', DATE '2025-03-14') AS first_of_month
'''))
```

```sh
year  month  weekday  pretty         first_of_month
----  -----  -------  -------------  -------------------
2025  3      Friday   14 March 2025  2025-03-01 00:00:00
(1 row)
```

An ISO string is converted to a date when needed, and a wrongly formatted one is rejected instead of being stored:

```py
con.execute('CREATE TABLE birthdays (who VARCHAR, day DATE)')
con.execute("INSERT INTO birthdays VALUES ('Ana', '2000-02-29')")
try:
    con.execute("INSERT INTO birthdays VALUES ('Ben', '14/03/2000')")
except duckdb.Error as e:
    print(str(e).splitlines()[0])
print(con.execute('SELECT * FROM birthdays').fetchall())  # [('Ana', datetime.date(2000, 2, 29))]
```

```sh
Conversion Error: invalid date field format: "14/03/2000", expected format is (YYYY-MM-DD)
[('Ana', datetime.date(2000, 2, 29))]
```

Python gets real `datetime.date` objects back, so there is nothing to parse.

### Lists, Structs and Maps

DuckDB columns can hold structured values, which SQLite could only fake with JSON text. Day 25 explores them; here is a first look:

```py
show(duckdb.sql('''
    SELECT [1, 2, 3]                       AS a_list,
           {'name': 'Ana', 'age': 31}      AS a_struct,
           MAP {'red': 1, 'blue': 2}       AS a_map,
           [10, 20, 30][2]                 AS second_item,
           {'name': 'Ana', 'age': 31}.name AS struct_field
'''))
```

```sh
a_list     a_struct                    a_map                  second_item  struct_field
---------  --------------------------  ---------------------  -----------  ------------
[1, 2, 3]  {'name': 'Ana', 'age': 31}  {'red': 1, 'blue': 2}  20           Ana
(1 row)
```

Lists are indexed from **1**, like SQL positions everywhere (not from 0 like Python).

### Auto-increment with Sequences

In SQLite, `INTEGER PRIMARY KEY` quietly became an auto-numbering rowid alias. DuckDB has no such magic; you ask for numbers explicitly with a **sequence**, and use
it as the column default. `RETURNING` (Day 8) works here too.

```sql
-- syntax
CREATE SEQUENCE sequence_name START 1;
CREATE TABLE t (id INTEGER PRIMARY KEY DEFAULT nextval('sequence_name'), ...);
```

```py
con.execute('CREATE SEQUENCE visitor_ids START 1')
con.execute("CREATE TABLE visitors (id INTEGER PRIMARY KEY DEFAULT nextval('visitor_ids'), name VARCHAR)")
show(con.execute("INSERT INTO visitors (name) VALUES ('Ana'), ('Ben') RETURNING id, name"))
```

```sh
id  name
--  ----
1   Ana
2   Ben
(2 rows)
```

> **In other databases:** MySQL has `AUTO_INCREMENT`, SQL Server has `IDENTITY`, PostgreSQL has `SERIAL` or `GENERATED ... AS IDENTITY`, and underneath they are all sequences like this one.

## Getting Data In

An empty database is not much fun. Two ways to fill one today (more tomorrow).

### From SQLite with Python

You already have data in SQLite: your `library.db` and `shop.db`. With plain Python you can copy it: read the rows with `sqlite3`, write them with `executemany`. The
pattern is three lines:

```py
import sqlite3

lite = sqlite3.connect('data/shop.db')
rows = lite.execute('SELECT category_id, name FROM categories ORDER BY category_id').fetchall()

con.execute('CREATE TABLE categories (category_id INTEGER PRIMARY KEY, name VARCHAR NOT NULL UNIQUE)')
con.executemany('INSERT INTO categories VALUES (?, ?)', rows)
show(con.execute('SELECT * FROM categories ORDER BY category_id LIMIT 3'))
```

```sh
category_id  name
-----------  --------------
1            Electronics
2            Books
3            Home & Kitchen
(3 rows)
```

While copying you can choose better types. For example, `shop.db` stores `order_date` as ISO text. In DuckDB you declare the column as `DATE`, and the very same ISO strings
go in unchanged and come out as real dates:

```py
con.execute('CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, order_date DATE NOT NULL, status VARCHAR NOT NULL)')
con.executemany('INSERT INTO orders VALUES (?, ?, ?, ?)', lite.execute('SELECT * FROM orders').fetchall())
show(con.execute("SELECT order_id, order_date, typeof(order_date) AS type, order_date + 7 AS plus_week FROM orders ORDER BY order_id LIMIT 2"))
```

```sh
order_id  order_date  type  plus_week
--------  ----------  ----  ----------
1         2024-01-02  DATE  2024-01-09
2         2024-01-10  DATE  2024-01-17
(2 rows)
```

In the exercises you will copy *every* shop table this way into a DuckDB file, which Days 24 and 25 reuse. (Day 26 shows a one-line shortcut, `ATTACH`.)

### A First Taste of Files

DuckDB can also read a CSV file straight into a table, with no `csv` module and no `executemany`:

```sql
-- syntax
CREATE TABLE table_name AS SELECT * FROM 'path/to/file.csv';
```

```py
con.execute("CREATE TABLE people AS SELECT * FROM 'data/weight-height.csv'")
print(con.execute('SELECT COUNT(*) FROM people').fetchall())  # [(10000,)]
show(con.execute('DESCRIBE people'))
```

```sh
[(10000,)]
column_name  column_type  null  key   default  extra
-----------  -----------  ----  ----  -------  -----
Gender       VARCHAR      YES   NULL  NULL     NULL
Height       DOUBLE       YES   NULL  NULL     NULL
Weight       DOUBLE       YES   NULL  NULL     NULL
(3 rows)
```

DuckDB looked at the file, found the header, and guessed the column types (`VARCHAR`, `DOUBLE`, `DOUBLE`). Tomorrow is entirely about this superpower. For now it is all you need
to load a big file for the exercises.

## Almost Everything You Learned Still Works

Here is Day 7's `students` table, created in DuckDB. Only the type names changed (`TEXT` became `VARCHAR`), and there is no `STRICT` because DuckDB is always strict.

```py
con.execute('''
    CREATE TABLE students (
        id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, age INTEGER, city VARCHAR, score INTEGER
    )
''')
con.executemany('INSERT INTO students VALUES (?, ?, ?, ?, ?)', [
    (1, 'Ana', 21, 'Toronto', 82), (2, 'Ben', 23, 'London', 67), (3, 'Cy', 22, 'Toronto', 91),
    (4, 'Di', 20, 'Paris', 74),    (5, 'Eli', 24, 'London', 74), (6, 'Fay', 22, 'Oslo', None),
    (7, 'Gus', None, 'Paris', 88), (8, 'Hal', 21, None, 59),
])
```

Now Day 7's aggregates, a Day 7 `GROUP BY ... HAVING`, a CTE from Day 14 and a window function from Day 17, all written exactly as before:

```py
show(con.execute('''
    SELECT COUNT(*) AS students, COUNT(score) AS scores, COUNT(DISTINCT city) AS distinct_cities,
           round(AVG(score), 2) AS avg_score
    FROM students
'''))
show(con.execute('''
    SELECT city, COUNT(*) AS students, round(AVG(score), 1) AS avg_score
    FROM students
    WHERE city IS NOT NULL
    GROUP BY city
    HAVING COUNT(*) >= 2
    ORDER BY students DESC, city
'''))
show(con.execute('''
    WITH scored AS (SELECT name, city, score FROM students WHERE score IS NOT NULL)
    SELECT name, city, score,
           RANK() OVER (ORDER BY score DESC)                   AS overall_rank,
           score - round(AVG(score) OVER (PARTITION BY city))  AS vs_city_average
    FROM scored
    ORDER BY overall_rank, name
    LIMIT 4
'''))
```

```sh
students  scores  distinct_cities  avg_score
--------  ------  ---------------  ---------
8         7       4                76.43
(1 row)
city     students  avg_score
-------  --------  ---------
London   2         70.5
Paris    2         81.0
Toronto  2         86.5
(3 rows)
name  city     score  overall_rank  vs_city_average
----  -------  -----  ------------  ---------------
Cy    Toronto  91     1             4.0
Gus   Paris    88     2             7.0
Ana   Toronto  82     3             -5.0
Di    Paris    74     4             -7.0
(4 rows)
```

Nothing needed changing. `string_agg`, `COALESCE`, `CASE`, subqueries, `UNION`, recursive CTEs and `FILTER (WHERE ...)` also carry over. The differences are in the details, which the next
section collects. Two of them already show here: SQLite put `NULL` **first** when sorting ascending (Day 4), DuckDB puts it **last** by default:

```py
show(con.execute('SELECT name, score FROM students ORDER BY score, name'))
```

```sh
name  score
----  -----
Hal   59
Ben   67
Di    74
Eli   74
Ana   82
Gus   88
Cy    91
Fay   NULL
(8 rows)
```

You can still say `NULLS FIRST` or `NULLS LAST` explicitly, which is a good habit when the order matters.

## What Is Different

A checklist for translating SQLite habits. Every row below was checked against DuckDB 2.0.0 for this lesson.

| Topic | SQLite | DuckDB |
|---|---|---|
| Column types | flexible (affinity), `STRICT` is opt-in | always strict, with sensible implicit conversions |
| `7 / 2` | `3` (integer division) | `3.5`; use `7 // 2` for `3` |
| `CAST(3.7 AS INTEGER)` | `3` (cuts off) | `4` (rounds) |
| Dividing by zero | `NULL` | `7 / 0` gives `inf`; `7 // 0` and `7 % 0` are errors |
| Dates | ISO `TEXT`, `date()`, `julianday()`, `strftime(fmt, x)` | `DATE`/`TIMESTAMP`, `+ INTERVAL`, `date_diff()`, `strftime(x, fmt)` |
| `LIKE` | case-insensitive for ASCII | case-**sensitive**; use `ILIKE` for case-insensitive |
| `NULL` in `ORDER BY ... ASC` | first | last |
| A bare column next to `GROUP BY` | accepted (picks some row) | an error that suggests `ANY_VALUE(col)` |
| Auto-increment | `INTEGER PRIMARY KEY` | `CREATE SEQUENCE` + `nextval()` |
| `iif(c, a, b)` | exists | not available; use `if(c, a, b)` or `CASE` |
| Double quotes | tolerated as strings if nothing else matches | always an identifier; strings use single quotes |
| Reading rows | `cursor.fetchone()` | `con.execute(...).fetchone()` (relations have no `fetchone`) |
| Several writers | one writer, many readers, in one file | one writing process per file |

The error for a bare column is worth seeing once (it runs on the `orders` table we copied above), because it replaces SQLite's silent leniency from Day 7:

```py
try:
    con.execute('SELECT status, order_id FROM orders GROUP BY status')
except duckdb.Error as e:
    print(type(e).__name__)
    print(str(e).splitlines()[0])
```

```sh
BinderException
Binder Error: column "order_id" must appear in the GROUP BY clause or must be part of an aggregate function.
```

> **In other databases:** this strictness is how PostgreSQL, SQL Server and Oracle behave too. In MySQL it depends on a setting (`ONLY_FULL_GROUP_BY`).

## Looking Inside a Query: EXPLAIN

On Day 21 you used `EXPLAIN QUERY PLAN` to see whether SQLite scanned a table or used an index. DuckDB has `EXPLAIN` (the plan) and `EXPLAIN ANALYZE` (run the query and
measure each step). First load a bigger table, the million-row `big_events.csv` from Day 21 (generate it with `uv run python tools/make_big_events.py` if you do not have it):

```py
con.execute("CREATE TABLE events AS SELECT * FROM 'data/big_events.csv'")
print(con.execute('SELECT COUNT(*) FROM events').fetchall())  # [(1000000,)]
show(con.execute('DESCRIBE events'))
```

```sh
[(1000000,)]
column_name  column_type  null  key   default  extra
-----------  -----------  ----  ----  -------  -----
event_id     BIGINT       YES   NULL  NULL     NULL
user_id      BIGINT       YES   NULL  NULL     NULL
event_type   VARCHAR      YES   NULL  NULL     NULL
ts           TIMESTAMP    YES   NULL  NULL     NULL
amount       DOUBLE       YES   NULL  NULL     NULL
(5 rows)
```

```py
plan = con.execute('''
    EXPLAIN SELECT event_type, COUNT(*)
    FROM events WHERE ts >= TIMESTAMP '2025-06-01' GROUP BY event_type
''').fetchall()
print(plan[0][1])
```

```sh
╭─ Projection ────────────────────────────╮
│ Projections:                            │
│ __internal_decompress_string(#0), #1    │
│ ~5 rows                                 │
╰────────────────────┬────────────────────╯
╭─ Hash Group By ────┴────────────────────╮
│ Groups: #0                              │
│ Aggregates: count_star()                │
│ ~5 rows                                 │
╰────────────────────┬────────────────────╯
╭─ Projection ───────┴────────────────────╮
│ Projections: event_type                 │
│ ~200,000 rows                           │
╰────────────────────┬────────────────────╯
╭─ Projection ───────┴────────────────────╮
│ Projections:                            │
│ __internal_compress_string_uhugeint(#0) │
│ ~200,000 rows                           │
╰────────────────────┬────────────────────╯
╭─ Seq Scan ─────────┴────────────────────╮
│ Table: memory.main.events               │
│ Type: Sequential Scan                   │
│ Projections: event_type                 │
│ Filters:                                │
│ ts >= '2025-06-01 00:00:00'::TIMESTAMP  │
│ ~200,000 rows                           │
╰─────────────────────────────────────────╯
```

Read the plan from the **bottom up**, as the data flows. The bottom box is the table scan: `Seq Scan` reads the table `events`, takes only the column `event_type`
(`Projections`) and applies the `ts` filter while scanning. DuckDB shows rough row estimates with `~`. The `Hash Group By` box builds one group per event type. Notice there is no
mention of an index: for scans like this DuckDB does not need one, because it reads the columns it needs very quickly. (DuckDB does support `CREATE INDEX`, but it is rarely the
tool for speeding up analytics, unlike in SQLite.)

`EXPLAIN ANALYZE` has the same layout but actually runs the query and adds the **time and the number of rows** for every box. The numbers change on every run and
every machine, so run it yourself:

```py
print(con.execute('EXPLAIN ANALYZE SELECT event_type, COUNT(*) FROM events GROUP BY event_type').fetchall()[0][1])
```

## Tool Tips

- **The DuckDB CLI.** The `duckdb` command (a separate download from <https://duckdb.org>) opens an interactive SQL prompt, like `python -m sqlite3` did. `duckdb 00_practice/shop.duckdb` opens your file directly,
  and inside it you can type `.tables`, `.schema` or any SQL.
- **The local web UI.** The `ui` extension gives DuckDB a notebook-style interface in your browser. In the CLI it starts with `duckdb -ui`. From Python you can install and start it with
  `con.execute('INSTALL ui')` and `con.execute('CALL start_ui()')` (the `start_ui` function exists in the extension version used for this course; the browser part is not something these lessons run automatically).
- **Harlequin** is a terminal SQL IDE with a DuckDB adapter (`uv tool install harlequin`, then `harlequin 00_practice/shop.duckdb`; `harlequin -a sqlite 00_practice/library.db` for SQLite). Handy for exploring a database
  while you write code. These commands come from the tools' own documentation; they are not run by the lessons.

None of the exercises depend on them.

You moved to a new engine and almost nothing in your queries had to change. Now put it to work on a million rows.

## Exercises: Day 23

### Exercises: Level 1

Keep your SQLite `00_practice/library.db`. The running thread continues in a DuckDB file, `00_practice/library.duckdb`.

1. Print the installed DuckDB version. Then run `SELECT 42 AS answer` three ways: with `.show()`, with `.fetchall()`, and with your `show()` helper.
2. In DuckDB compute `7 / 2`, `7 // 2` and `7 % 2` in one row. Run `SELECT 7 / 2, 7 % 2` in SQLite too. Which of the two gives a different answer, and why?
3. Connect to `00_practice/library.duckdb` (a file) and use `pathlib` to confirm the file exists.
4. Create a sequence `book_ids` and a table `books` in it with the columns `id` (auto-numbered from the sequence, primary key), `title` and `author` (both required), `year`, `pages`, `genre`, `price` as `DECIMAL(10, 2)` and `rating` as `DECIMAL(2, 1)`. `DESCRIBE` it.
5. Copy your 12 books from `library.db` into the new table with `executemany`. Convert `price_cents` to `price` while selecting (divide by `100.0`). Let the sequence number the ids.
6. Print the number of books and the first four rows (`id`, `title`, `price`, `rating`) ordered by id.
7. List the titles with more than 600 pages (largest first) using a `?` placeholder, then the Sci-Fi books published before 2000 with **named** `$genre` and `$year` parameters.
8. Try to insert a book with `pages` equal to `'many'`. Catch the `duckdb.Error` and print the error type and the first line of the message.
9. Inside a transaction (`BEGIN` ... `ROLLBACK`), insert a book with `year` `'2024'` (as text) and `pages` `300.7`. What are the stored values and types? Then try the year `'last year'`, and roll back so the table has 12 books again.
10. Show `SUM(price)` and its type. Why can you trust this total to be exact?
11. Add a `DATE` column `added`, set it to `2025-03-14` for every book, and show for the first two books how many days remain until `2025-12-25` and the date 30 days after `added`.
12. In one row, select a list, a struct (for example a book with a title and a year) and a map.
13. `EXPLAIN SELECT title FROM books WHERE pages > 600`. Which table is scanned and where is the filter?
14. Explain in your own words why a column store is faster than a row store for `AVG(age)` over millions of rows, but not for fetching one customer.
15. Close the connection, reopen the file and check that the 12 books are still there.

```sh
# expected for exercise 6
(12,)
id  title                 price  rating
--  --------------------  -----  ------
1   Dune                  10.99  4.5
2   Neuromancer           8.99   4.0
3   The Hobbit            7.99   4.7
4   The Name of the Wind  12.99  4.4
(4 rows)

# expected for exercise 7
title                 pages
--------------------  -----
The Name of the Wind  662
Dune                  612
(2 rows)
title        genre
-----------  ------
Dune         Sci-Fi
Neuromancer  Sci-Fi
(2 rows)

# expected for exercise 10
total   type
------  -------------
187.88  DECIMAL(38,2)
(1 row)
```

### Exercises: Level 2

1. **Copy the whole shop into DuckDB.** Create `00_practice/shop.duckdb` with all seven tables of `data/shop.db`. Write a function `load_shop(path)` that does it. Use these types: ids, quantities, cents and stock stay
   `INTEGER`; text columns become `VARCHAR`; `signup_date`, `order_date` and `hire_date` become `DATE`; `newsletter_signups.signed_up_at` becomes `TIMESTAMP`. Keep the primary keys and `NOT NULL`s. Money stays in integer cents. Days 24 and 25 reuse this file.
   Print the row count of each table and the types of `signup_date` and `price_cents`.

   ```sh
   customers 60
   categories 8
   products 40
   orders 399
   order_items 984
   employees 15
   newsletter_signups 20
   signup  price
   ------  -------
   DATE    INTEGER
   (1 row)
   ```

2. Run these three queries from earlier days against your DuckDB shop **exactly as you wrote them in SQLite**: (a) the three categories with the highest revenue (revenue = `SUM(quantity * unit_price_cents) / 100.0`, joining `order_items`, `products`, `categories`; ties by category), (b) the number of customers who have never ordered
   (`LEFT JOIN` ... `IS NULL`), (c) the five customers who spent the most, with `RANK()` (in cents, ties by name).

   ```sh
   category     revenue
   -----------  -------
   Electronics  9677.81
   Sports       9311.1
   Books        8209.0
   (3 rows)
   customers_without_orders
   ------------------------
   6
   (1 row)
   customer     spend_cents  rnk
   -----------  -----------  ---
   Lena Green   223857       1
   Ines Martin  218207       2
   Priya Brown  215530       3
   Sam Wilson   205487       4
   Amara Kim    204568       5
   (5 rows)
   ```

3. **Predict, then run.** Write down the result of each, then check in DuckDB: (a) `SELECT 5 / 2`, (b) `SELECT 'a' LIKE 'A'`, (c) `SELECT CAST(2.5 AS INTEGER), CAST(3.5 AS INTEGER)`, (d) `SELECT x FROM (VALUES (2), (NULL), (1)) AS t(x) ORDER BY x`, (e) `SELECT '5' + 1`. Which of the five give a different answer in SQLite?

   ```sh
   # (a), (b), (c) in one row
   a    b      c  d
   ---  -----  -  -
   2.5  False  3  4
   # (d)
   x
   ----
   1
   2
   NULL
   # (e) raises an error (a BinderException)
   ```

4. **DuckDB vs SQLite on a million rows.** Load `data/big_events.csv` into SQLite (table `events (event_id, user_id, event_type, ts, amount)` as on Day 21) **and** into a DuckDB table with `CREATE TABLE events AS SELECT * FROM 'data/big_events.csv'`. Run these three queries on each, measure each with `time.perf_counter()`, and check that both engines return the same rows:
   - events per `event_type` (ordered by type),
   - the 5 users with the most events (ties by `user_id`),
   - events per month (`strftime`; remember the argument order differs).

   Print the timings. Expect DuckDB to be many times faster on all three. In your own words, why? (Do **not** run the DuckDB loading step inside the timing.)

   ```sh
   event_type   n
   -----------  ------
   add_to_cart  120086
   click        250602
   purchase     69991
   refund       9852
   view         549469
   (5 rows)
   user_id  n
   -------  --
   5252     43
   32240    39
   7640     38
   20070    38
   25699    38
   (5 rows)
   ```

5. **Money, exactly.** (a) Sum the two values `0.1` and `0.2` as `DOUBLE` and as `DECIMAL(10, 2)` in one row. (b) On the DuckDB `events` table, compute the total of all `purchase` amounts as `SUM(CAST(amount AS DECIMAL(10, 2)))`, and the net total of all non-NULL amounts (purchases plus the negative refunds). What is the type of the sum?

   ```sh
   as_double            as_decimal
   -------------------  ----------
   0.30000000000000004  0.30
   (1 row)
   purchases_total  type
   ---------------  -------------
   14185797.05      DECIMAL(38,2)
   (1 row)
   net_total
   -----------
   13184966.05
   (1 row)
   ```

### Exercises: Level 3

1. **The busiest week, in DuckDB.** On Day 18 you found the busiest 7-day window of Hacker News posts in SQLite. Here is a version of that query for a table `hn_iso` that has an ISO `created_at` text column (`YYYY-MM-DD HH:MM:SS`):

   ```sql
   WITH daily AS (
       SELECT date(created_at) AS day, COUNT(*) AS posts
       FROM hn_iso
       GROUP BY day
   )
   SELECT a.day AS start_day, SUM(b.posts) AS posts_in_window
   FROM daily AS a
   JOIN daily AS b ON b.day >= a.day AND b.day < date(a.day, '+7 days')
   GROUP BY a.day
   ORDER BY posts_in_window DESC, a.day
   LIMIT 3
   ```

   Build `hn_iso` in **both** engines from `data/hacker_news.csv`, converting `created_at` to ISO in Python as you did on Day 16 (`datetime.strptime(text, '%m/%d/%Y %H:%M')`). Create the DuckDB table with `VARCHAR`
   for `created_at`, so that the data are the same in both. Run the query **unchanged** in DuckDB, read the error, change the one thing that needs changing, and check that the answers agree. Which part of the query had to change, and why?

   ```sh
   start_day   posts_in_window
   ----------  ---------------
   2016-01-10  445
   2016-01-13  442
   2016-01-11  439
   (3 rows)
   ParserException - Parser Error: Wrong number of arguments provided to DATE function
   ```

2. **SQLite-isms to DuckDB.** Here are six expressions in SQLite dialect. Write the DuckDB equivalent of each, run both, and print them side by side as below. Which ones give a *different* answer when you
   do the "obvious" translation?

   ```sql
   iif(7 > 5, 'big', 'small')
   julianday('2025-03-14') - julianday('2025-01-01')
   date('2025-03-14', '+30 days')
   strftime('%Y-%m', '2025-03-14')
   CAST(3.7 AS INTEGER)
   'Hello' LIKE 'hello'
   ```

   ```sh
   iif(7 > 5, 'big', 'small')                           SQLite -> big          DuckDB -> big
   julianday('2025-03-14') - julianday('2025-01-01')    SQLite -> 72.0         DuckDB -> 72
   date('2025-03-14', '+30 days')                       SQLite -> 2025-04-13   DuckDB -> 2025-04-13
   strftime('%Y-%m', '2025-03-14')                      SQLite -> 2025-03      DuckDB -> 2025-03
   CAST(3.7 AS INTEGER)                                 SQLite -> 3            DuckDB -> 3
   'Hello' LIKE 'hello'                                 SQLite -> 1            DuckDB -> True
   ```

   (The fifth line shows the result you get from a faithful translation, `CAST(trunc(3.7) AS INTEGER)`. The plain `CAST(3.7 AS INTEGER)` gives 4 in DuckDB.)

CONGRATULATIONS !

[<< Day 22 Review](../22R_Review_Python_and_sqlite/22R_review_python_and_sqlite.md) | [Day 24 >>](../24_Day_Querying_files/24_querying_files.md)
