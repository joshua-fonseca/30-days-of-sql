<div align="center">
  <h1> 30 Days Of SQL: Day 26 - DuckDB with pandas, Polars & SQLite</h1>
</div>

[<< Day 25](../25_Day_Duckdb_friendly_sql/25_duckdb_friendly_sql.md) | [Day 26 Review >>](../26R_Review_Duckdb/26R_review_duckdb.md)

- [Day 26](#day-26)
  - [DuckDB Meets DataFrames](#duckdb-meets-dataframes)
    - [Setup: pyarrow](#setup-pyarrow)
  - [pandas](#pandas)
    - [Querying a DataFrame by Its Variable Name](#querying-a-dataframe-by-its-variable-name)
    - [Getting a DataFrame Back](#getting-a-dataframe-back)
    - [Where Does DuckDB Look for the Name?](#where-does-duckdb-look-for-the-name)
  - [Polars](#polars)
  - [Arrow: The Shared Format](#arrow-the-shared-format)
  - [SQL or DataFrame Code?](#sql-or-dataframe-code)
  - [The Relational API](#the-relational-api)
  - [From a DataFrame to a Table](#from-a-dataframe-to-a-table)
  - [Reading SQLite from DuckDB](#reading-sqlite-from-duckdb)
    - [ATTACH](#attach)
    - [Types Across the Bridge](#types-across-the-bridge)
    - [Joining a DataFrame with a SQLite Table](#joining-a-dataframe-with-a-sqlite-table)
    - [Copying SQLite Tables into DuckDB](#copying-sqlite-tables-into-duckdb)
    - [Writing Results Back to SQLite](#writing-results-back-to-sqlite)
  - [ Exercises: Day 26](#exercises-day-26)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 26

You now know three places data can live: a **SQLite file**, a **file** (CSV, JSON, Parquet) and a **DataFrame** in memory. DuckDB's best trick is that it can query all three with the same SQL, and
join them to each other. Today is the bridge day: DuckDB with pandas, with its modern rival Polars, and with the SQLite databases you built in Part 1.

## DuckDB Meets DataFrames

A DataFrame is a table in Python's memory. You could analyse it with its own methods (`df.groupby(...)`) or with SQL. Having both is a superpower: use the one that makes the question clearest.

### Setup: pyarrow

Moving data between DuckDB and Polars (and between DuckDB and Arrow tables, below) goes through a library called **pyarrow**. With the DuckDB 2.0 used in this course, pyarrow is required for everything that touches Polars or
Arrow. pandas itself does not need it. Install it once into your project:

```sh
uv add pyarrow
```

If you ever see `ModuleNotFoundError: No module named 'pyarrow'` from a `.pl()` call or a Polars query, this is why.

## pandas

### Querying a DataFrame by Its Variable Name

Make a small DataFrame from a list of dictionaries:

```py
import duckdb
import pandas as pd
from helpers import show

people = [
    {'name': 'Ana', 'age': 31, 'city': 'Oslo'},
    {'name': 'Ben', 'age': 25, 'city': 'Rome'},
    {'name': 'Cy',  'age': 42, 'city': 'Oslo'},
    {'name': 'Di',  'age': 37, 'city': 'Rome'},
    {'name': 'Eli', 'age': 29, 'city': 'Lima'},
]
df = pd.DataFrame(people)
print(df)
```

```sh
  name  age  city
0  Ana   31  Oslo
1  Ben   25  Rome
2   Cy   42  Oslo
3   Di   37  Rome
4  Eli   29  Lima
```

Now write SQL and use the **variable name `df` as the table name**:

```py
show(duckdb.sql('''
    SELECT city, COUNT(*) AS people, round(AVG(age), 1) AS avg_age
    FROM df
    GROUP BY city
    ORDER BY people DESC, city
'''))
```

```sh
city  people  avg_age
----  ------  -------
Oslo  2       36.5
Rome  2       31.0
Lima  1       29.0
(3 rows)
```

There is no `CREATE TABLE`, no `INSERT`, no `register`. When DuckDB meets a table name it does not know, it looks for a **Python variable** with that name holding a DataFrame, and reads it in place. This is called a
*replacement scan*. Everything from the last three days works on it: joins, window functions, `QUALIFY`, `PIVOT`.

### Getting a DataFrame Back

The result of a query is a relation. `.df()` converts it to a pandas DataFrame (pandas calls it a "DataFrame", DuckDB calls the method `df`):

```py
result = duckdb.sql('SELECT city, COUNT(*) AS people FROM df GROUP BY city ORDER BY city').df()
print(result)
print(type(result))
```

```sh
   city  people
0  Lima       1
1  Oslo       2
2  Rome       2
<class 'pandas.DataFrame'>
```

Then you carry on in pandas with `result.plot()`, `result.to_csv(...)`, scikit-learn, and so on. The typical workflow: **SQL for the heavy lifting** (filter, join and aggregate millions of rows), then pandas for the last mile.

### Where Does DuckDB Look for the Name?

For the Python variable scan, DuckDB checks the variables in the scope of the code that ran the query: first the local ones, then the global ones. A DataFrame that is a local variable inside a function works inside that function:

```py
def oldest(frame):
    adults = frame[frame.age > 30]
    return duckdb.sql('SELECT name FROM adults ORDER BY age DESC').fetchall()

print(oldest(df))  # [('Cy',), ('Di',), ('Ana',)]
```

If you want to pick the table name yourself (or the DataFrame is not in scope, for instance when you pass it around), **register** it on a connection:

```py
con = duckdb.connect()
con.register('people_view', df)
print(con.execute('SELECT COUNT(*), MAX(age) FROM people_view').fetchall())  # [(5, 42)]
```

**Common mistake:** a typo in the variable name gives the usual "Table with name ... does not exist" error. DuckDB cannot tell a mistyped Python variable from a mistyped table. The error message
lists candidate names, so read it.

## Polars

**Polars** is a newer DataFrame library, written in Rust, that is often much faster than pandas on big data and has a more consistent API. It works with DuckDB exactly like pandas does: query by variable name, and ask for a Polars result with `.pl()`.

```py
import polars as pl

pdf = pl.DataFrame(people)
print(pdf)
print(duckdb.sql('SELECT name, age FROM pdf WHERE age >= 30 ORDER BY age DESC').pl())
```

```sh
shape: (5, 3)
┌──────┬─────┬──────┐
│ name ┆ age ┆ city │
│ ---  ┆ --- ┆ ---  │
│ str  ┆ i64 ┆ str  │
╞══════╪═════╪══════╡
│ Ana  ┆ 31  ┆ Oslo │
│ Ben  ┆ 25  ┆ Rome │
│ Cy   ┆ 42  ┆ Oslo │
│ Di   ┆ 37  ┆ Rome │
│ Eli  ┆ 29  ┆ Lima │
└──────┴─────┴──────┘
shape: (3, 2)
┌──────┬─────┐
│ name ┆ age │
│ ---  ┆ --- │
│ str  ┆ i64 │
╞══════╪═════╡
│ Cy   ┆ 42  │
│ Di   ┆ 37  │
│ Ana  ┆ 31  │
└──────┴─────┘
```

Polars prints its DataFrames as boxes with the column types under the names. A lazy Polars query (`pdf.lazy()`) can be queried the same way. Both libraries can also be loaded straight from files, `pl.read_csv('data/hacker_news.csv')`
or `pd.read_csv(...)`, and DuckDB can then query them. And the other way around: DuckDB can be the reader, if you ask it to turn a file into a DataFrame:

```py
countries = duckdb.sql("SELECT name, currency, population, languages FROM 'data/countries_data.json'").df()
print(countries.dtypes)
print(duckdb.sql("SELECT name, len(languages) AS how_many FROM countries WHERE name LIKE 'S%' ORDER BY how_many DESC, name LIMIT 3").fetchall())  # [('South Africa', 10), ('Singapore', 4), ('Saint Martin (French part)', 3)]
```

```sh
name             str
currency         str
population     int64
languages     object
dtype: object
[('South Africa', 10), ('Singapore', 4), ('Saint Martin (French part)', 3)]
```

The list column `languages` arrives in pandas as an `object` column holding arrays, and DuckDB turns it back into a proper list when you query the DataFrame.

## Arrow: The Shared Format

Why do these libraries talk to each other so smoothly? They agree on how a table looks in memory: **Apache Arrow**, a standard *columnar* layout. DuckDB, Polars and (optionally) pandas can all read an Arrow table
**without copying or converting** the data, which is why querying a big frame this way is cheap. Compare that with exporting to CSV and reading it again.

```py
arrow_table = duckdb.sql('SELECT * FROM df ORDER BY name').to_arrow_table()
print(type(arrow_table))
print(arrow_table.num_rows, arrow_table.column_names)
print(duckdb.sql('SELECT AVG(age) FROM arrow_table').fetchall())  # [(32.8,)]
```

```sh
<class 'pyarrow.lib.Table'>
5 ['name', 'age', 'city']
[(32.8,)]
```

The same variable-name trick works for Arrow tables (just like for DataFrames). In practice you will rarely handle Arrow yourself; it is the plumbing that makes the rest fast. It is also why the Polars and Arrow conversions need `pyarrow`.

## SQL or DataFrame Code?

The same question, "how many people and what average age per city?", in three styles. Compare the answers and the code:

```py
# pandas
print(df.groupby('city').agg(people=('name', 'size'), avg_age=('age', 'mean')).sort_values(['people', 'avg_age'], ascending=[False, False]))
# Polars
print(pdf.group_by('city').agg(pl.len().alias('people'), pl.col('age').mean().alias('avg_age')).sort(['people', 'city'], descending=[True, False]))
# SQL
print(duckdb.sql('SELECT city, COUNT(*) AS people, AVG(age) AS avg_age FROM df GROUP BY city ORDER BY people DESC, city').df())
```

```sh
      people  avg_age
city                 
Oslo       2     36.5
Rome       2     31.0
Lima       1     29.0
shape: (3, 3)
┌──────┬────────┬─────────┐
│ city ┆ people ┆ avg_age │
│ ---  ┆ ---    ┆ ---     │
│ str  ┆ u32    ┆ f64     │
╞══════╪════════╪═════════╡
│ Oslo ┆ 2      ┆ 36.5    │
│ Rome ┆ 2      ┆ 31.0    │
│ Lima ┆ 1      ┆ 29.0    │
└──────┴────────┴─────────┘
   city  people  avg_age
0  Oslo       2     36.5
1  Rome       2     31.0
2  Lima       1     29.0
```

All three agree (Oslo and Rome tie on 2 people; the SQL and Polars versions break the tie by city, which matters when you want a stable result). A rough guide:

| Prefer SQL when | Prefer pandas / Polars when |
|---|---|
| joining several tables, or a table with a file | cleaning a few columns row by row with Python logic |
| grouping, ranking, windows, top-N per group | plotting, machine learning, anything that wants an array |
| the data is bigger than memory (query a Parquet file) | reshaping nested or irregular data |
| the question is "ask a question of a table" | the work is a long chain of small transformations |
| you want the same query to run on SQLite, PostgreSQL, DuckDB | you want to stay inside Python |

They do not exclude each other: it is normal to load with SQL, clean with pandas and finish with SQL. Today's exercises redo a pandas-style analysis in SQL.

## The Relational API

Besides SQL text, a DuckDB relation has Python **methods** that return a new relation, so you can chain them: `filter`, `project`, `aggregate`, `order`, `limit`, `join`. Each step takes SQL fragments as strings.

```py
rel = duckdb.sql('SELECT * FROM df')
chained = rel.filter('age > 28').aggregate('city, count(*) AS n').order('city')
show(chained)
```

```sh
city  n
----  -
Lima  1
Oslo  2
Rome  1
(3 rows)
```

This is the same plan as `SELECT city, count(*) AS n FROM df WHERE age > 28 GROUP BY city ORDER BY city`; DuckDB optimizes both identically. Choose it when you build a query piece by piece in a loop or a function, and prefer plain SQL elsewhere, because
the SQL text is easier to read, test and take to another database. Like all relations, a chain is lazy: nothing runs until you call `show()`, `fetchall()`, `.df()` and so on.

## From a DataFrame to a Table

A scan reads the DataFrame as it is *now*. To keep a copy inside the database (for example in a file), create a table from it, and add more rows later with `INSERT ... SELECT`:

```py
con.execute('CREATE TABLE people AS SELECT * FROM df')
con.execute("INSERT INTO people SELECT * FROM df WHERE city = 'Lima'")
print(con.execute('SELECT COUNT(*) FROM people').fetchall())  # [(6,)]
show(con.execute('DESCRIBE people'))
```

```sh
[(6,)]
column_name  column_type  null  key   default  extra
-----------  -----------  ----  ----  -------  -----
name         VARCHAR      YES   NULL  NULL     NULL
age          BIGINT       YES   NULL  NULL     NULL
city         VARCHAR      YES   NULL  NULL     NULL
(3 rows)
```

pandas' `int64` became `BIGINT` and its text became `VARCHAR`, as you would expect.

## Reading SQLite from DuckDB

Your shop is in a SQLite file, and you copied it table by table on Day 23. DuckDB's **sqlite extension** gives you a shortcut: attach the SQLite file as a second database and query its tables in place.

### ATTACH

```sql
-- syntax
ATTACH 'path/to/file.db' AS alias (TYPE sqlite);
ATTACH 'path/to/file.db' AS alias (TYPE sqlite, READ_ONLY);
```

DuckDB downloads the `sqlite` extension the first time you use it, so the very first `ATTACH ... (TYPE sqlite)` needs an internet connection. After that it is cached on your machine. (If you work offline,
run `INSTALL sqlite;` once while you are online.)

Always attach a database you only want to read with `READ_ONLY`: a mistake can then not change it.

```py
lite = duckdb.connect()
lite.execute("ATTACH 'data/shop.db' AS shop (TYPE sqlite, READ_ONLY)")
show(lite.execute("SELECT database_name FROM duckdb_databases() WHERE NOT internal ORDER BY 1"))
print([r[0] for r in lite.execute("SELECT table_name FROM duckdb_tables() WHERE database_name = 'shop' ORDER BY table_name").fetchall()])  # ['categories', 'customers', 'employees', 'newsletter_signups', 'order_items', 'orders', 'products']
```

```sh
database_name
-------------
memory
shop
(2 rows)
['categories', 'customers', 'employees', 'newsletter_signups', 'order_items', 'orders', 'products']
```

Tables of an attached database are named `alias.table`. Query them with all the DuckDB SQL you know, even though the data is stored by SQLite:

```py
show(lite.execute('''
    SELECT c.country, COUNT(DISTINCT o.order_id) AS orders, SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS revenue
    FROM shop.customers AS c
    JOIN shop.orders AS o USING (customer_id)
    JOIN shop.order_items AS oi USING (order_id)
    GROUP BY ALL
    ORDER BY revenue DESC
'''))
```

```sh
country  orders  revenue
-------  ------  --------
USA      100     13274.11
Canada   85      10614.85
France   74      9519.14
UK       83      8276.21
Germany  57      6372.48
(5 rows)
```

`GROUP BY ALL` on a SQLite file, and the aggregation runs in DuckDB's fast engine. With `USE shop` you make the attached database the default so you can leave out the prefix, and `USE memory` returns:

```py
lite.execute('USE shop')
print(lite.execute('SELECT COUNT(*) FROM orders').fetchall())  # [(399,)]
lite.execute('USE memory')
```

Trying to change a read-only database is refused:

```py
try:
    lite.execute("INSERT INTO shop.categories (name) VALUES ('Nope')")
except duckdb.Error as e:
    print(type(e).__name__, '-', str(e).splitlines()[0])
```

```sh
InvalidInputException - Invalid Input Error: Cannot execute statement of type "INSERT" on database "shop" which is attached in read-only mode!
```

### Types Across the Bridge

SQLite stores no real dates, and DuckDB sees that:

```py
show(lite.execute('DESCRIBE shop.orders'))
```

```sh
column_name  column_type  null  key   default  extra
-----------  -----------  ----  ----  -------  -----
order_id     BIGINT       YES   PRI   NULL     NULL
customer_id  BIGINT       NO    NULL  NULL     NULL
order_date   VARCHAR      NO    NULL  NULL     NULL
status       VARCHAR      NO    NULL  NULL     NULL
(4 rows)
```

`order_date` is `VARCHAR`, and the integers are `BIGINT`. Cast when you need a date: `CAST(order_date AS DATE)`. ISO text converts cleanly, which is one more reason for the ISO habit of Day 16:

```py
show(lite.execute('''
    SELECT strftime(CAST(order_date AS DATE), '%Y-%m') AS month, COUNT(*) AS orders
    FROM shop.orders
    WHERE order_date >= '2025-01-01'
    GROUP BY ALL
    ORDER BY ALL
    LIMIT 3
'''))
```

```sh
month    orders
-------  ------
2025-01  20
2025-02  12
2025-03  12
(3 rows)
```

### Joining a DataFrame with a SQLite Table

Because DataFrames and attached databases are both just "tables" to DuckDB, one query can join them. Here are exchange rates in a pandas DataFrame and revenue from SQLite:

```py
rates = pd.DataFrame({'currency': ['USD', 'EUR', 'GBP'], 'per_usd': [1.00, 0.92, 0.79]})

show(lite.execute('''
    WITH revenue AS (
        SELECT SUM(oi.quantity * oi.unit_price_cents) / 100.0 AS usd
        FROM shop.orders AS o JOIN shop.order_items AS oi USING (order_id)
        WHERE o.status <> 'cancelled'
    )
    SELECT x.currency, round(revenue.usd * x.per_usd, 2) AS revenue
    FROM revenue CROSS JOIN rates AS x
    ORDER BY x.per_usd DESC
'''))
```

```sh
currency  revenue
--------  --------
USD       44932.73
EUR       41338.11
GBP       35496.86
(3 rows)
```

`rates` (a Python variable on the default scope) and `shop.orders` (a SQLite file) met in one statement. A `CROSS JOIN` (Day 12) paired the total with every row of `rates`. This kind of "glue" job, small reference data from here, big facts from there, is
where DuckDB shines.

### Copying SQLite Tables into DuckDB

Heavy analysis runs faster when the data lives in DuckDB's own columnar storage. `CREATE TABLE AS` copies a table across, and you can fix the types while doing it:

```py
lite.execute('''
    CREATE TABLE local_orders AS
    SELECT order_id, customer_id, CAST(order_date AS DATE) AS order_date, status FROM shop.orders
''')
show(lite.execute('SELECT COUNT(*) AS rows, typeof(order_date) AS type FROM local_orders GROUP BY type'))
```

```sh
rows  type
----  ----
399   DATE
(1 row)
```

This is the one-line version of what you wrote by hand on Day 23 with `executemany`. For a one-off read of a single table you can also use the function `sqlite_scan('data/shop.db', 'orders')` instead of attaching.

### Writing Results Back to SQLite

Attached databases are not read-only unless you say so. You can create a table in a SQLite file from a DuckDB query. This is the "do the analytics in DuckDB, store the result where your application can read it" step. **Do it on a copy**, never on your original:

```py
import shutil
import sqlite3

shutil.copy('data/shop.db', '00_practice/shop_copy.db')

lite.execute("ATTACH '00_practice/shop_copy.db' AS app (TYPE sqlite)")
lite.execute('''
    CREATE TABLE app.top_customers AS
    SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer,
           CAST(SUM(oi.quantity * oi.unit_price_cents) AS BIGINT) AS spend_cents
    FROM shop.customers AS c
    JOIN shop.orders AS o USING (customer_id)
    JOIN shop.order_items AS oi USING (order_id)
    WHERE o.status <> 'cancelled'
    GROUP BY ALL
    ORDER BY spend_cents DESC, customer_id
    LIMIT 3
''')
lite.execute('DETACH app')

check = sqlite3.connect('00_practice/shop_copy.db')
print(check.execute('SELECT * FROM top_customers ORDER BY spend_cents DESC, customer_id').fetchall())  # [(43, 'Lena Green', 221460), (18, 'Amara Kim', 204568), (24, 'Ines Martin', 204441)]
print(check.execute("SELECT sql FROM sqlite_master WHERE name = 'top_customers'").fetchone()[0])
check.close()
```

```sh
[(43, 'Lena Green', 221460), (18, 'Amara Kim', 204568), (24, 'Ines Martin', 204441)]
CREATE TABLE top_customers(customer_id BIGINT, customer VARCHAR, spend_cents BIGINT)
```

The plain `sqlite3` module reads the table DuckDB just wrote, because it really is a SQLite table now. Notice the `CAST(... AS BIGINT)`: in DuckDB `SUM` of an integer column produces a wide integer type (`HUGEINT`), and
SQLite has no such type. Without the cast the column would be created as text (`VARCHAR`) in SQLite, which is a classic surprise. Look at the column types of what you write.

SQLite for the application, DuckDB for the analysis, pandas and Polars for the last mile: you now have the whole toolkit. Next, a review checkpoint.

## Exercises: Day 26

### Exercises: Level 1

Use this list for the first exercises:

```py
people = [
    {'name': 'Ana', 'age': 31, 'city': 'Oslo'},
    {'name': 'Ben', 'age': 25, 'city': 'Rome'},
    {'name': 'Cy',  'age': 42, 'city': 'Oslo'},
    {'name': 'Di',  'age': 37, 'city': 'Rome'},
    {'name': 'Eli', 'age': 29, 'city': 'Lima'},
]
```

1. Build a pandas DataFrame `df` from `people` and, with DuckDB SQL on it, show for each city the number of people and the average age (1 decimal), most people first, ties by city.
2. Run the query `SELECT city, COUNT(*) AS people FROM df GROUP BY city ORDER BY city` and get the result both as a pandas DataFrame and as a Polars DataFrame. Check the types with `isinstance`.
3. Build a Polars DataFrame `pdf` from `people` and query it with DuckDB: the names and ages of people aged 30 or more, oldest first. Return the result as a Polars DataFrame.
4. Use a **named parameter** (`$min`) on the DataFrame query: names of people older than 28, alphabetical.
5. Register `df` on a new connection as `people_view` and print the number of rows and the maximum age.
6. Write a function `oldest(frame)` that filters a DataFrame to people over 30 in pandas and then uses SQL (on that local variable) to return their names, oldest first.
7. Create a DuckDB table `people` from `df`, insert the people from Lima a second time with `INSERT ... SELECT`, and print the count. `DESCRIBE` the table.
8. With the relational API, chain `filter`, `aggregate` and `order` to count the people older than 28 per city. Check that the result equals the SQL version's.
9. Convert `df` to an Arrow table with `.to_arrow_table()` and print its number of rows and column names.
10. Query the Polars frame `pdf` for each city's oldest age (`MAX(age)`) and get the result as a pandas DataFrame. What is its shape?
11. Attach `data/shop.db` as `shop` in read-only mode and print the sorted list of its tables.
12. Print the row count of each of those tables as a list of `(table, count)` pairs.
13. Try to insert a row into the read-only database, catch the error and print its type and first line.
14. `USE shop` and count the orders without a prefix. Then `USE memory`.
15. List the first three months of 2025 with their order counts (cast the text dates).
16. Copy the attached `orders` into a DuckDB table `local_orders`, with `order_date` converted to `DATE`, and show the row count and the date type.
17. In your own words: what is Arrow, and why does it make DuckDB, pandas and Polars work well together?

```sh
# expected for exercise 1
city  people  avg_age
----  ------  -------
Oslo  2       36.5
Rome  2       31.0
Lima  1       29.0
(3 rows)

# expected for exercise 3
shape: (3, 2)
┌──────┬─────┐
│ name ┆ age │
│ ---  ┆ --- │
│ str  ┆ i64 │
╞══════╪═════╡
│ Cy   ┆ 42  │
│ Di   ┆ 37  │
│ Ana  ┆ 31  │
└──────┴─────┘

# expected for exercises 4, 5, 6, 7
[('Ana',), ('Cy',), ('Di',), ('Eli',)]
[(5, 42)]
[('Cy',), ('Di',), ('Ana',)]
[(6,)]

# expected for exercises 11 and 12
['categories', 'customers', 'employees', 'newsletter_signups', 'order_items', 'orders', 'products']
[('categories', 8), ('customers', 60), ('employees', 15), ('newsletter_signups', 20), ('order_items', 984), ('orders', 399), ('products', 40)]

# expected for exercise 15
month    orders
-------  ------
2025-01  20
2025-02  12
2025-03  12
(3 rows)
```

### Exercises: Level 2

1. **Hacker News, in SQL.** Load `data/hacker_news.csv` into a pandas DataFrame with `pd.read_csv` (add a column `row` that numbers the rows from 0 with `.reset_index(names='row')`). Then, using only DuckDB SQL on the DataFrame:
   (a) the first five rows (`row`, `id`, `num_points`, `author`), (b) the last five rows, (c) the `title` column of the first 3 rows, (d) the number of rows and of columns, (e) how many titles contain `python` (lower case) and how many contain `JavaScript`,
   compared with `hn.title.str.contains(..., na=False).sum()` in pandas, (f) how many titles contain `python` in any case (`ILIKE`). Why did we need the `row` column for (a) and (b)?

   ```sh
   row  id        num_points  author
   ---  --------  ----------  ----------
   0    12224879  386         ne0phyte
   1    11964716  2           vezycash
   2    11919867  3           hswarna
   3    10301696  8           walterbell
   4    10482257  53          Deinos
   (5 rows)
   row    id        num_points  author
   -----  --------  ----------  -------------
   20098  11680777  182         pmoriarty
   20097  10739875  695         brw12
   20096  10824382  169         vezzy-fnord
   20095  10339284  4           zreitano
   20094  12379592  10          AdmiralAsshat
   (5 rows)
   [(20099,)] 8
   12 169 True
   [(160,)]
   ```

   (In SQL, "first" and "last" mean nothing without an `ORDER BY`. The extra `row` column gives the table an order that you can sort by.)

2. **Agree with pandas.** Load `data/weight-height.csv` with pandas. Compute per gender the count and the mean height and weight (2 decimals) with SQL on the DataFrame, and again with `groupby(...).agg(...)`. Check that the numbers agree.

   ```sh
      Gender     n  avg_height  avg_weight
   0  Female  5000       63.71      135.86
   1    Male  5000       69.03      187.02
   ```

3. **Polars.** Load the Hacker News file with `pl.read_csv`. With SQL, find the 3 authors with the most total points (number of posts and points as integers; ties by author), and get the result as a Polars DataFrame.

   ```sh
   shape: (3, 3)
   ┌─────────────┬───────┬────────┐
   │ author      ┆ posts ┆ points │
   │ ---         ┆ ---   ┆ ---    │
   │ str         ┆ i64   ┆ i64    │
   ╞═════════════╪═══════╪════════╡
   │ ingve       ┆ 198   ┆ 16733  │
   │ prostoalex  ┆ 123   ┆ 7868   │
   │ adamnemecek ┆ 42    ┆ 6008   │
   └─────────────┴───────┴────────┘
   ```

4. **Pandas meets Polars.** Create a Polars DataFrame `cities` with `city` and `country` (`Oslo`/`Norway`, `Rome`/`Italy`, `Lima`/`Peru`). Join it to the pandas `people` frame in **one SQL query** and list name, age and country, ordered by country, then name.

   ```sh
   name  age  country
   ----  ---  -------
   Ben   25   Italy
   Di    37   Italy
   Ana   31   Norway
   Cy    42   Norway
   Eli   29   Peru
   (5 rows)
   ```

5. **Write back, safely.** Copy `data/shop.db` to a new file. Attach the copy (read-write) in DuckDB and create a table `top_customers` in it with the five customers who spent most (cancelled orders excluded): `customer_id`, `customer` (first and last name), `spend_cents` as `BIGINT`. Verify with the plain
   `sqlite3` module that the table exists, print its rows and its `CREATE TABLE` statement, and confirm that the original `data/shop.db` has no such table.

   ```sh
   [(43, 'Lena Green', 221460), (18, 'Amara Kim', 204568), (24, 'Ines Martin', 204441), (7, 'Sam Wilson', 196691), (31, 'Freya Nguyen', 168831)]
   CREATE TABLE top_customers(customer_id BIGINT, customer VARCHAR, spend_cents BIGINT)
   (0,)
   ```

6. **Two ways to write it.** Write "the names and ages of people from Oslo, oldest first" once in SQL and once with the relational API (`filter`, `project`, `order`). Check that both return the same list.

   ```sh
   [('Cy', 42), ('Ana', 31)] True
   ```

### Exercises: Level 3

1. **Revenue in three currencies.** Create a pandas DataFrame of exchange rates (per US dollar): `USD` 1.00, `EUR` 0.92, `GBP` 0.79. Attach `data/shop.db` read-only. For each year (from `order_date`), report the revenue of all orders that are **not cancelled** in each of the three currencies, rounded to 2 decimals, in one query that joins the DataFrame with the SQLite tables.
   (Revenue is `SUM(quantity * unit_price_cents) / 100.0`, in dollars; multiply by the rate. Cast the text dates.) Order by year, then rate descending.

   ```sh
   year  currency  revenue
   ----  --------  --------
   2024  USD       18283.24
   2024  EUR       16820.58
   2024  GBP       14443.76
   2025  USD       26649.49
   2025  EUR       24517.53
   2025  GBP       21053.1
   (6 rows)
   ```

2. **A report that travels.** Using the same rates and the attached shop, build a table with **one row per customer country and one column per currency** (`USD`, `EUR`, `GBP`) containing the revenue of non-cancelled orders, rounded to 2 decimals. Hint: a `PIVOT` over (country, currency, revenue) rows.
   Get it as a pandas DataFrame and print it. Then store it as the table `revenue_by_country` in a **copy** of `shop.db`, read it back with `sqlite3`, and print the `CREATE TABLE` statement SQLite recorded.

   ```sh
      country       USD       EUR       GBP
   0   Canada   9762.49   8981.49   7712.37
   1   France   8401.72   7729.58   6637.36
   2  Germany   6070.93   5585.26   4796.03
   3       UK   7982.30   7343.72   6306.02
   4      USA  12715.29  11698.07  10045.08
   [('Canada', 9762.49, 8981.49, 7712.37), ('France', 8401.72, 7729.58, 6637.36), ('Germany', 6070.93, 5585.26, 4796.03), ('UK', 7982.3, 7343.72, 6306.02), ('USA', 12715.29, 11698.07, 10045.08)]
   CREATE TABLE revenue_by_country(country VARCHAR, USD DOUBLE, EUR DOUBLE, GBP DOUBLE)
   ```

CONGRATULATIONS !

[<< Day 25](../25_Day_Duckdb_friendly_sql/25_duckdb_friendly_sql.md) | [Day 26 Review >>](../26R_Review_Duckdb/26R_review_duckdb.md)
