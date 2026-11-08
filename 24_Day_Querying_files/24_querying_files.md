<div align="center">
  <h1> 30 Days Of SQL: Day 24 - Querying Files Directly</h1>
</div>

[<< Day 23](../23_Day_Meet_duckdb/23_meet_duckdb.md) | [Day 25 >>](../25_Day_Duckdb_friendly_sql/25_duckdb_friendly_sql.md)

- [Day 24](#day-24)
  - [A File Is a Table](#a-file-is-a-table)
    - [CSV, the Short Way](#csv-the-short-way)
    - [read_csv and Its Options](#read_csv-and-its-options)
    - [What Did DuckDB Find? DESCRIBE and SUMMARIZE](#what-did-duckdb-find-describe-and-summarize)
    - [Dates in CSV Files](#dates-in-csv-files)
    - [Dirty CSV Files](#dirty-csv-files)
  - [JSON Files](#json-files)
  - [Many Files at Once: Globs](#many-files-at-once-globs)
  - [Load Once, Query Many Times](#load-once-query-many-times)
  - [Writing Files with COPY](#writing-files-with-copy)
  - [Parquet](#parquet)
    - [Why Parquet?](#why-parquet)
    - [Parquet in Practice](#parquet-in-practice)
  - [Files on the Web](#files-on-the-web)
  - [ Exercises: Day 24](#exercises-day-24)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 24

On Day 3 and Day 20 you loaded a CSV into SQLite the long way: open the file, read the rows with the `csv` module, build tuples, call `executemany`, and only then query. DuckDB removes
the middle. You point a query at the **file**, and DuckDB reads it as if it were a table. CSV, JSON and Parquet files all work. Nothing to create, nothing to load, nothing to clean up.

The examples use the `duckdb.sql()` shortcut from yesterday and file paths relative to your project folder (run your scripts from the project root).

## A File Is a Table

### CSV, the Short Way

```sql
-- syntax
SELECT columns FROM 'path/to/file.csv';
```

When the name in `FROM` is a quoted file name ending in `.csv`, DuckDB reads the file. Here is the Hacker News file from Day 3 (20,099 posts) without loading anything:

```py
import duckdb
from helpers import show

show(duckdb.sql("SELECT id, num_points, num_comments, author, created_at FROM 'data/hacker_news.csv' LIMIT 3"))
```

```sh
id        num_points  num_comments  author    created_at
--------  ----------  ------------  --------  ---------------
12224879  386         52            ne0phyte  8/4/2016 11:52
11964716  2           1             vezycash  6/23/2016 22:20
11919867  3           1             hswarna   6/17/2016 0:01
(3 rows)
```

DuckDB opened the file, found the header line, worked out the delimiter and the quoting, and **guessed a type for every column**. This guessing is called *sniffing*. It reads a sample of rows
(not the whole file) and picks the narrowest type that fits all of them. All the SQL you know works on the result:

```py
show(duckdb.sql('''
    SELECT author, COUNT(*) AS posts, round(AVG(num_points), 1) AS avg_points
    FROM 'data/hacker_news.csv'
    GROUP BY author
    ORDER BY posts DESC, author
    LIMIT 3
'''))
```

```sh
author      posts  avg_points
----------  -----  ----------
ingve       198    84.5
prostoalex  123    64.0
dnetesn     98     47.2
(3 rows)
```

### read_csv and Its Options

The quoted-name shortcut is a friendly form of the function `read_csv`. Use the function when sniffing needs help:

```sql
-- syntax
SELECT * FROM read_csv('file.csv', option => value, ...);
```

(In Python-flavoured SQL you will usually see `option = value`; both spellings work.) The options you will meet most:

| Option | Meaning | Example |
|---|---|---|
| `delim` | the separator between values | `delim = ';'` |
| `header` | does the first line hold column names? | `header = false` |
| `names` | give your own column names (with `header = false`, and `skip = 1` to jump over a header line) | `names = ['a', 'b']` |
| `skip` | lines to skip at the top | `skip = 1` |
| `types` | force the type of some columns | `types = {'id': 'VARCHAR'}` |
| `all_varchar` | read everything as text, convert yourself later | `all_varchar = true` |
| `timestampformat` | how timestamps are written in the file | `'%m/%d/%Y %H:%M'` |
| `dateformat` | how **dates** are written (date only, see below!) | `'%d/%m/%Y'` |
| `null_padding`, `ignore_errors` | tolerate short or broken lines | `ignore_errors = true` |
| `filename` | add a column with the name of the source file | `filename = true` |
| `encoding` | the text encoding, default UTF-8 | `encoding = 'utf-16'` |

Reading the same file with every column as text shows what the options do:

```py
show(duckdb.sql("DESCRIBE SELECT * FROM read_csv('data/hacker_news.csv', all_varchar = true)"))
```

```sh
column_name   column_type  null  key   default  extra
------------  -----------  ----  ----  -------  -----
id            VARCHAR      YES   NULL  NULL     NULL
title         VARCHAR      YES   NULL  NULL     NULL
url           VARCHAR      YES   NULL  NULL     NULL
num_points    VARCHAR      YES   NULL  NULL     NULL
num_comments  VARCHAR      YES   NULL  NULL     NULL
author        VARCHAR      YES   NULL  NULL     NULL
created_at    VARCHAR      YES   NULL  NULL     NULL
(7 rows)
```

If you give an option the file cannot satisfy, you get an error and not a silent mess, which is better than a half-loaded table:

```py
try:
    duckdb.sql("SELECT * FROM read_csv('data/hacker_news.csv', delim = '|')").fetchall()
except duckdb.Error as e:
    print(type(e).__name__)
try:
    duckdb.sql("SELECT * FROM 'data/nothere.csv'").fetchall()
except duckdb.Error as e:
    print(type(e).__name__, '-', str(e).splitlines()[0])
```

```sh
InvalidInputException
IOException - IO Error: No files found that match the pattern "data/nothere.csv"
```

### What Did DuckDB Find? DESCRIBE and SUMMARIZE

Before you query an unfamiliar file, ask what is in it. `DESCRIBE` lists the columns and the types DuckDB inferred:

```py
show(duckdb.sql("DESCRIBE SELECT * FROM 'data/hacker_news.csv'"))
```

```sh
column_name   column_type  null  key   default  extra
------------  -----------  ----  ----  -------  -----
id            BIGINT       YES   NULL  NULL     NULL
title         VARCHAR      YES   NULL  NULL     NULL
url           VARCHAR      YES   NULL  NULL     NULL
num_points    BIGINT       YES   NULL  NULL     NULL
num_comments  BIGINT       YES   NULL  NULL     NULL
author        VARCHAR      YES   NULL  NULL     NULL
created_at    VARCHAR      YES   NULL  NULL     NULL
(7 rows)
```

Note that `created_at` is `VARCHAR`: the dates in this file look like `8/4/2016 11:52` and DuckDB (rightly) will not guess whether that is 8 April or 4 August. More on that in a moment.

`SUMMARIZE` goes further and gives a one-row profile per column: the minimum and maximum, the number of distinct values (approximate), the average, the quartiles, the row count and the percentage of NULLs.
It is the fastest way to get to know a new dataset:

```py
show(duckdb.sql("SUMMARIZE SELECT num_points, num_comments FROM 'data/hacker_news.csv'"))
```

```sh
column_name   column_type  min  max   approx_unique  avg                 std                 q25  q50  q75  count  null_percentage
------------  -----------  ---  ----  -------------  ------------------  ------------------  ---  ---  ---  -----  ---------------
num_points    BIGINT       1    2553  605            50.296631673217576  107.11032177641022  3    9    54   20099  0.00
num_comments  BIGINT       1    1733  388            24.803025026120704  56.10863908385852   1    3    21   20099  0.00
(2 rows)
```

Posts have between 1 and 2,553 points, but half of them have 9 or fewer (`q50`): a very skewed distribution. That took no code at all.

Both commands accept a table name, a file or a full query. For a table, `DESCRIBE table_name` is the shorthand.

### Dates in CSV Files

On Day 16 you had to turn `8/4/2016 11:52` into ISO text with string functions or Python. DuckDB has proper date parsing. There are two ways, and you pick one.

**1. Parse in the query with `strptime`** (the same format codes as Python's `datetime.strptime`):

```py
show(duckdb.sql('''
    SELECT created_at, strptime(created_at, '%m/%d/%Y %H:%M') AS parsed
    FROM 'data/hacker_news.csv'
    LIMIT 3
'''))
```

```sh
created_at       parsed
---------------  -------------------
8/4/2016 11:52   2016-08-04 11:52:00
6/23/2016 22:20  2016-06-23 22:20:00
6/17/2016 0:01   2016-06-17 00:01:00
(3 rows)
```

**2. Tell `read_csv` how timestamps are written**, so the column is born with the right type:

```py
show(duckdb.sql('''
    SELECT created_at, typeof(created_at) AS type
    FROM read_csv('data/hacker_news.csv', timestampformat = '%m/%d/%Y %H:%M')
    LIMIT 2
'''))
```

```sh
created_at           type
-------------------  ---------
2016-08-04 11:52:00  TIMESTAMP
2016-06-23 22:20:00  TIMESTAMP
(2 rows)
```

**Common mistake:** `dateformat` and `timestampformat` are **different options**. `dateformat` describes columns that hold a *date only*. Hand it a date-and-time format and DuckDB will happily
treat the column as a `DATE` and **throw away the time**, without any error:

```py
show(duckdb.sql('''
    SELECT created_at, typeof(created_at) AS type
    FROM read_csv('data/hacker_news.csv', dateformat = '%m/%d/%Y %H:%M')
    LIMIT 2
'''))
```

```sh
created_at  type
----------  ----
2016-08-04  DATE
2016-06-23  DATE
(2 rows)
```

Always look at the `DESCRIBE` of a file after setting format options. With the proper timestamps in place, questions about time become one-liners. At what hour of the day do posts get the most points on average?

```py
show(duckdb.sql('''
    SELECT hour(strptime(created_at, '%m/%d/%Y %H:%M')) AS hour, COUNT(*) AS posts, round(AVG(num_points), 1) AS avg_points
    FROM 'data/hacker_news.csv'
    GROUP BY hour
    ORDER BY avg_points DESC, hour
    LIMIT 3
'''))
```

```sh
hour  posts  avg_points
----  -----  ----------
13    1102   56.2
15    1234   55.6
10    686    54.7
(3 rows)
```

Compare that with the string slicing of Day 16. Time zone note: the file does not say which time zone these times are in, so neither can we.

### Dirty CSV Files

Remember `F500.csv` from Day 20: semicolons, `"$485,873"` revenues and `"2,300,000"` employees. DuckDB's sniffer finds the semicolons on its own, but stating the delimiter is clearer and safer:

```py
show(duckdb.sql("SELECT rank, name, employees, revenues FROM read_csv('data/F500.csv', delim = ';') LIMIT 3"))
show(duckdb.sql("DESCRIBE SELECT rank, name, employees, revenues FROM read_csv('data/F500.csv', delim = ';')"))
```

```sh
rank  name                employees  revenues
----  ------------------  ---------  --------
1     Walmart             2,300,000  $485,873
2     Berkshire Hathaway  367,700    $223,604
3     Apple               116,000    $215,639
(3 rows)
column_name  column_type  null  key   default  extra
-----------  -----------  ----  ----  -------  -----
rank         BIGINT       YES   NULL  NULL     NULL
name         VARCHAR      YES   NULL  NULL     NULL
employees    VARCHAR      YES   NULL  NULL     NULL
revenues     VARCHAR      YES   NULL  NULL     NULL
(4 rows)
```

`employees` and `revenues` are `VARCHAR`, because `$` and `,` are not part of a number. The cleaning you did with `replace` and `CAST` in SQLite works unchanged, and now it runs straight on the file:

```py
show(duckdb.sql('''
    SELECT name, CAST(replace(replace(revenues, '$', ''), ',', '') AS INTEGER) AS revenue_millions
    FROM read_csv('data/F500.csv', delim = ';')
    ORDER BY revenue_millions DESC, name
    LIMIT 3
'''))
```

```sh
name                revenue_millions
------------------  ----------------
Walmart             485873
Berkshire Hathaway  223604
Apple               215639
(3 rows)
```

> **In other databases:** loading a file normally needs a special tool or statement: `COPY ... FROM` in PostgreSQL, `LOAD DATA INFILE` in MySQL, `BULK INSERT` in SQL Server, `.import` in the SQLite shell. In DuckDB reading a file is just a `SELECT`.

## JSON Files

`read_json` (or simply the quoted `.json` file name) does for JSON what `read_csv` does for CSV. It works on a JSON array of objects, like `countries_data.json`, and also on **JSON Lines** files with one object per line:

```py
show(duckdb.sql("DESCRIBE SELECT * FROM read_json('data/countries_data.json')"))
```

```sh
column_name  column_type  null  key   default  extra
-----------  -----------  ----  ----  -------  -----
name         VARCHAR      YES   NULL  NULL     NULL
capital      VARCHAR      YES   NULL  NULL     NULL
languages    VARCHAR[]    YES   NULL  NULL     NULL
population   BIGINT       YES   NULL  NULL     NULL
flag         VARCHAR      YES   NULL  NULL     NULL
currency     VARCHAR      YES   NULL  NULL     NULL
(6 rows)
```

The `languages` list became a real **list** column, `VARCHAR[]`. Remember how Day 10 needed a whole extra table for it? We will unpack it on Day 25. A list column can already be measured:

```py
show(duckdb.sql('''
    SELECT name, languages, len(languages) AS how_many
    FROM 'data/countries_data.json'
    WHERE name IN ('Finland', 'Switzerland', 'Australia')
    ORDER BY name
'''))
```

```sh
name         languages                        how_many
-----------  -------------------------------  --------
Australia    ['English']                      1
Finland      ['Finnish', 'Swedish']           2
Switzerland  ['German', 'French', 'Italian']  3
(3 rows)
```

This is the same JSON file you could read with Python's `json.load`, queried in place.

## Many Files at Once: Globs

Real data often arrives as many files: one per day, per month, per region. A **glob** pattern with `*` matches many file names, and DuckDB reads them all as **one table**.
First, make three small files to play with:

```py
import csv
from pathlib import Path

folder = Path('00_practice/sales')
folder.mkdir(exist_ok=True)
files = {
    'sales_2025-01.csv': [('day', 'product', 'units'), ('2025-01-05', 'tea', 3), ('2025-01-20', 'coffee', 5)],
    'sales_2025-02.csv': [('day', 'product', 'units'), ('2025-02-02', 'tea', 4), ('2025-02-17', 'cake', 2)],
    'sales_2025-03.csv': [('day', 'units', 'product', 'discount'), ('2025-03-03', 6, 'coffee', 0.1)],
}
for name, rows in files.items():
    with (folder / name).open('w', newline='') as f:
        csv.writer(f).writerows(rows)

show(duckdb.sql("SELECT * FROM glob('00_practice/sales/*.csv')"))
```

```sh
file
-----------------------------------
00_practice/sales/sales_2025-01.csv
00_practice/sales/sales_2025-02.csv
00_practice/sales/sales_2025-03.csv
(3 rows)
```

`glob()` is a table function that lists the matching files. Now read them as one table. The special column `filename=true` tells you where each row came from:

```py
show(duckdb.sql('''
    SELECT *
    FROM read_csv('00_practice/sales/sales_2025-0[12].csv', filename = true)
    ORDER BY day
'''))
```

```sh
day         product  units  filename
----------  -------  -----  -----------------------------------
2025-01-05  tea      3      00_practice/sales/sales_2025-01.csv
2025-01-20  coffee   5      00_practice/sales/sales_2025-01.csv
2025-02-02  tea      4      00_practice/sales/sales_2025-02.csv
2025-02-17  cake     2      00_practice/sales/sales_2025-02.csv
(4 rows)
```

The pattern `[12]` matched only January and February (`*`, `?` and `[...]` work like in your shell). The third file has its columns in a different order and an extra `discount` column. Read all three
without any help and look at what comes out:

```py
show(duckdb.sql("SELECT * FROM read_csv('00_practice/sales/*.csv') ORDER BY day"))
```

```sh
day         product  units
----------  -------  -----
2025-01-05  tea      3
2025-01-20  coffee   5
2025-02-02  tea      4
2025-02-17  cake     2
2025-03-03  coffee   6
(5 rows)
```

The extra column quietly vanished, because DuckDB took the layout from the first files. When files may differ, add `union_by_name = true`: DuckDB then lines the columns up by **name**, keeps every
column that appears in any file, and fills the holes with NULL:

```py
show(duckdb.sql('''
    SELECT day, product, units, discount
    FROM read_csv('00_practice/sales/*.csv', union_by_name = true)
    ORDER BY day
'''))
```

```sh
day         product  units  discount
----------  -------  -----  --------
2025-01-05  tea      3      NULL
2025-01-20  coffee   5      NULL
2025-02-02  tea      4      NULL
2025-02-17  cake     2      NULL
2025-03-03  coffee   6      0.1
(5 rows)
```

Totals over all files, with no loop in Python:

```py
show(duckdb.sql('''
    SELECT product, SUM(units) AS units
    FROM read_csv('00_practice/sales/*.csv', union_by_name = true)
    GROUP BY product
    ORDER BY units DESC, product
'''))
```

```sh
product  units
-------  -----
coffee   11
tea      7
cake     2
(3 rows)
```

You can also pass a **list** of file names, and `**` matches folders at any depth: `read_csv('data/**/*.csv')`. The same globs work for `read_json` and `read_parquet`.

## Load Once, Query Many Times

Every query on a file reads and parses that file again. That is fine for small files and for one-off questions. For a file you will question many times, load it **once** into a table:

```sql
-- syntax
CREATE TABLE table_name AS SELECT * FROM 'file.csv';
CREATE TEMP TABLE table_name AS SELECT * FROM 'file.csv';
CREATE VIEW view_name AS SELECT * FROM 'file.csv';
```

You met `CREATE TABLE AS` and `CREATE TEMP TABLE` on Day 14, and `CREATE VIEW` on Day 22; they behave exactly the same here.

```py
db_path = Path('00_practice/datasets.duckdb')
db_path.unlink(missing_ok=True)

con = duckdb.connect(str(db_path))
con.execute("CREATE TABLE hn AS SELECT * FROM 'data/hacker_news.csv'")
con.execute("CREATE TEMP TABLE hn_python AS SELECT * FROM hn WHERE title LIKE '%Python%'")
con.execute("CREATE VIEW hn_view AS SELECT * FROM 'data/hacker_news.csv'")
print(con.execute('SELECT (SELECT COUNT(*) FROM hn), (SELECT COUNT(*) FROM hn_python), (SELECT COUNT(*) FROM hn_view)').fetchall())  # [(20099, 149, 20099)]
con.close()

con = duckdb.connect(str(db_path))
show(con.execute("SELECT table_name, temporary FROM duckdb_tables() ORDER BY table_name"))
show(con.execute("SELECT view_name FROM duckdb_views() WHERE NOT internal ORDER BY view_name"))
```

```sh
[(20099, 149, 20099)]
table_name  temporary
----------  ---------
hn          False
(1 row)
view_name
---------
hn_view
(1 row)
```

After reconnecting: the table `hn` was stored in the file; the temp table `hn_python` is gone; and the view `hn_view` survived (it is just the saved query, so it reads the CSV again each time and breaks if the CSV moves).

| | Query the file | `CREATE VIEW` over the file | `CREATE TABLE AS` |
|---|---|---|---|
| Setup | none | one statement | one statement |
| Speed of later queries | re-reads the file each time | re-reads the file each time | fast, data is inside the database |
| Sees changes to the file | yes | yes | no, it is a snapshot |
| Needs the file later | yes | yes | no |

Note that `LIKE '%Python%'` is case-**sensitive** in DuckDB, as you saw yesterday.

## Writing Files with COPY

The reverse of reading is `COPY ... TO`. It writes a table or the result of a query to a file; the format follows from the extension or from `FORMAT`:

```sql
-- syntax
COPY (SELECT ...) TO 'file.csv' (HEADER, DELIMITER ',');
COPY (SELECT ...) TO 'file.json' (FORMAT json, ARRAY true);
COPY (SELECT ...) TO 'file.parquet' (FORMAT parquet);
COPY table_name TO 'file.csv';
```

```py
duckdb.sql('''
    COPY (SELECT author, COUNT(*) AS posts FROM 'data/hacker_news.csv' GROUP BY author ORDER BY posts DESC, author LIMIT 3)
    TO '00_practice/top_authors.csv' (HEADER, DELIMITER ',')
''')
print(Path('00_practice/top_authors.csv').read_text())

duckdb.sql("COPY (SELECT * FROM '00_practice/top_authors.csv') TO '00_practice/top_authors.json' (FORMAT json, ARRAY true)")
print(Path('00_practice/top_authors.json').read_text())
```

```sh
author,posts
ingve,198
prostoalex,123
dnetesn,98

[
	{"author":"ingve","posts":198},
	{"author":"prostoalex","posts":123},
	{"author":"dnetesn","posts":98}
]
```

Without `ARRAY true` the JSON file is written as JSON Lines (one object per line), which is the better format for big files because it can be read line by line.

`COPY` can also split the output into **folders** by the values of a column with `PARTITION_BY`, which Level 3 uses:

```py
duckdb.sql('''
    COPY (SELECT Gender, Height, Weight FROM 'data/weight-height.csv')
    TO '00_practice/people_by_gender' (FORMAT csv, PARTITION_BY (Gender), OVERWRITE_OR_IGNORE)
''')
show(duckdb.sql("SELECT file FROM glob('00_practice/people_by_gender/*/*.csv') ORDER BY file"))
```

```sh
file
-----------------------------------------------------
00_practice/people_by_gender/Gender=Female/data_0.csv
00_practice/people_by_gender/Gender=Male/data_0.csv
(2 rows)
```

Each folder is named `column=value`. This naming is called **Hive partitioning**, and DuckDB can read it back and turn the folder name into a column again:

```py
show(duckdb.sql('''
    SELECT Gender, COUNT(*) AS n, round(AVG(Height), 2) AS avg_height
    FROM read_csv('00_practice/people_by_gender/*/*.csv', hive_partitioning = true)
    GROUP BY Gender
    ORDER BY Gender
'''))
```

```sh
Gender  n     avg_height
------  ----  ----------
Female  5000  63.71
Male    5000  69.03
(2 rows)
```

## Parquet

### Why Parquet?

CSV is wonderful because anything can read it, but it is a poor format for big data: it is plain text, so numbers take more space than they need; every type has to be guessed again on every read; and to read one
column you still have to read every line. **Parquet** is the standard answer in the data world. It is a binary, **columnar** file format (the file-sized cousin of what DuckDB does in memory):

- values are stored **column by column** and compressed, so files are small;
- the **types are stored in the file**, so there is no guessing and a timestamp stays a timestamp;
- a query reads only the columns it needs, and statistics inside the file let DuckDB skip parts that cannot match your `WHERE`.

### Parquet in Practice

Convert the big Hacker News file (about 293,000 posts, 47 MB) to Parquet, parsing the dates on the way:

```py
duckdb.sql('''
    COPY (SELECT * FROM read_csv('data/HN_posts_year_to_Sep_26_2016.csv', timestampformat = '%m/%d/%Y %H:%M'))
    TO '00_practice/hn_2016.parquet' (FORMAT parquet)
''')
csv_size = Path('data/HN_posts_year_to_Sep_26_2016.csv').stat().st_size
pq_size = Path('00_practice/hn_2016.parquet').stat().st_size
print(f'CSV {csv_size / 1e6:.1f} MB, Parquet {pq_size / 1e6:.1f} MB')
```

```sh
CSV 47.4 MB, Parquet 29.8 MB
```

Parquet is smaller even though most of this file is text, which compresses worst. (Files with more numbers shrink far more: the one-million-row `big_events.csv` goes from about 42 MB to about 15 MB.)
Read it back like any other file, and notice the types:

```py
show(duckdb.sql("DESCRIBE SELECT * FROM '00_practice/hn_2016.parquet'"))
print(duckdb.sql("SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM '00_practice/hn_2016.parquet'").fetchall())  # [(293119, datetime.datetime(2015, 9, 6, 5, 50), datetime.datetime(2016, 9, 26, 3, 26))]
```

```sh
column_name   column_type  null  key   default  extra
------------  -----------  ----  ----  -------  -----
id            BIGINT       YES   NULL  NULL     NULL
title         VARCHAR      YES   NULL  NULL     NULL
url           VARCHAR      YES   NULL  NULL     NULL
num_points    BIGINT       YES   NULL  NULL     NULL
num_comments  BIGINT       YES   NULL  NULL     NULL
author        VARCHAR      YES   NULL  NULL     NULL
created_at    TIMESTAMP    YES   NULL  NULL     NULL
(7 rows)
[(293119, datetime.datetime(2015, 9, 6, 5, 50), datetime.datetime(2016, 9, 26, 3, 26))]
```

`created_at` is a `TIMESTAMP` straight away, with no format string. Parquet also records how many rows and "row groups" a file has, which you can query:

```py
show(duckdb.sql("SELECT num_rows, num_row_groups FROM parquet_file_metadata('00_practice/hn_2016.parquet')"))
```

```sh
num_rows  num_row_groups
--------  --------------
293119    3
(1 row)
```

Now the same question asked of the CSV and of the Parquet file. Timing details depend on your machine, so just compare:

```py
import time

ask = "SELECT author, SUM(num_points) AS points FROM {} GROUP BY author ORDER BY points DESC, author LIMIT 3"
t = time.perf_counter()
from_csv = duckdb.sql(ask.format("read_csv('data/HN_posts_year_to_Sep_26_2016.csv')")).fetchall()
csv_seconds = time.perf_counter() - t

t = time.perf_counter()
from_parquet = duckdb.sql(ask.format("'00_practice/hn_2016.parquet'")).fetchall()
parquet_seconds = time.perf_counter() - t

print('same answer:', from_csv == from_parquet)
print('Parquet faster:', parquet_seconds < csv_seconds)
print(from_parquet)
```

```sh
same answer: True
Parquet faster: True
[('ingve', 69465), ('prostoalex', 32510), ('jonbaer', 26157)]
```

Typical data-engineering practice: keep raw CSV files as they arrived, convert them once to Parquet, and run all queries on the Parquet. You can choose a stronger compression with `COMPRESSION zstd`,
for a smaller file that is a bit slower to write: `COPY ... TO 'file.parquet' (FORMAT parquet, COMPRESSION zstd)`.

## Files on the Web

The `httpfs` extension lets DuckDB read files from `https://` addresses. It is **installed and loaded automatically** the first time you need it, which requires an internet connection once.
DuckDB reads only the parts of the file it needs, so even large Parquet files on a server can be queried cheaply.

```py
try:
    show(duckdb.sql("SELECT * FROM 'https://duckdb.org/data/flights.csv' LIMIT 2"))
except duckdb.Error as e:
    print('no internet?', type(e).__name__)
```

```sh
FlightDate  UniqueCarrier  OriginCityName  DestCityName
----------  -------------  --------------  ---------------
1988-01-01  AA             New York, NY    Los Angeles, CA
1988-01-02  AA             New York, NY    Los Angeles, CA
(2 rows)
```

Web files are only as stable as the web: addresses move and servers go away, so use this for exploration and download a copy (`COPY ... TO 'local.parquet'`) for anything you rely on.

Files are tables now. Time to open them up.

## Exercises: Day 24

### Exercises: Level 1

Run your scripts from the project root so the relative `data/` paths work.

1. Select `id`, `num_points`, `num_comments`, `author` and `created_at` of the first 5 rows of `data/hacker_news.csv` directly, without loading it.
2. `DESCRIBE` the file. Which columns did DuckDB make numeric, and which one would you want to be a timestamp?
3. `SUMMARIZE` the columns `num_points` and `num_comments`. What is the maximum number of comments of any post?
4. In one row, count the posts and the posts without a `url`.
5. Show the 3 authors with the most posts, ties by author.
6. Read `data/F500.csv` with `delim = ';'`. Show `name`, `employees` and `revenues` for the first 3 rows, and `DESCRIBE` the columns `rank`, `name`, `employees`, `revenues`. Why are `employees` and `revenues` text?
7. Show the 3 companies with the highest revenue (in millions), with `revenue_millions` as an integer: clean the `$` and `,` with `replace` and `CAST`.
8. From `data/weight-height.csv` show, per gender, the number of people and the average height and weight (2 decimals). Compare with Day 7.
9. `DESCRIBE` `data/countries_data.json` (what type is `languages`?). List the countries with more than 100 million people, largest first.
10. How many countries use the Euro?
11. `DESCRIBE` `hacker_news.csv` again, now read with `all_varchar = true`. What changed?
12. Read `hacker_news.csv` with `delim = '|'`. Catch the error and print only its type. Then read `data/nothere.csv`, catch the error and print its type and the first line of its message.
13. How many `.csv` files are in `data/`? (Use `glob`.)
14. In a DuckDB file `00_practice/datasets.duckdb`: create a table `hn` from the CSV, a temp table `hn_python` with the posts whose title contains `Python` and a view `hn_view` over the CSV. Print the three row counts. Reconnect and list the tables (name and whether temporary) to see what survived.
15. In your own words: when would you query the file directly, when create a view over it, and when create a table from it?
16. Write the 10 authors with the most posts to `00_practice/top_authors.csv` with `COPY ... TO`, print the first 3 lines of the file, then write the same rows to a JSON array file and count the objects with `read_json`.

```sh
# expected for exercise 1
id        num_points  num_comments  author      created_at
--------  ----------  ------------  ----------  ---------------
12224879  386         52            ne0phyte    8/4/2016 11:52
11964716  2           1             vezycash    6/23/2016 22:20
11919867  3           1             hswarna     6/17/2016 0:01
10301696  8           2             walterbell  9/30/2015 4:12
10482257  53          22            Deinos      10/31/2015 9:48
(5 rows)

# expected for exercise 4 (a list of one tuple)
[(20099, 2440)]

# expected for exercise 7
name                revenue_millions
------------------  ----------------
Walmart             485873
Berkshire Hathaway  223604
Apple               215639
(3 rows)

# expected for exercise 8
Gender  n     avg_height  avg_weight
------  ----  ----------  ----------
Female  5000  63.71       135.86
Male    5000  69.03       187.02
(2 rows)

# expected for exercise 14
[(20099, 149, 20099)]
[('hn', False)]
```

### Exercises: Level 2

1. **Dates at read time.** (a) Read `hacker_news.csv` with `dateformat = '%m/%d/%Y %H:%M'` and `DESCRIBE` the `created_at` column: what type is it, and what happened to the time? (b) Read it correctly with `timestampformat`. (c) Show that the `strptime` approach in the `SELECT` and
   `types = {'created_at': 'TIMESTAMP'}` with `timestampformat` produce identical timestamps for every row. (d) Find the three hours of the day with the highest average points (ties by hour; average to 1 decimal). This is the Day 16 question.

   ```sh
   column_name  column_type  null  key   default  extra
   -----------  -----------  ----  ----  -------  -----
   created_at   DATE         YES   NULL  NULL     NULL
   (1 row)
   strptime == read_csv types: True
   hour  posts  avg_points
   ----  -----  ----------
   13    1102   56.2
   15    1234   55.6
   10    686    54.7
   (3 rows)
   ```

2. **CSV to Parquet.** Convert `data/HN_posts_year_to_Sep_26_2016.csv` to `00_practice/hn_2016.parquet` (parse `created_at` as a timestamp). Print both file sizes in MB and confirm that Parquet is smaller. `DESCRIBE` the Parquet file. Then ask the same question of the CSV and of the Parquet file (the three authors with the most total points, ties by author), time both with `time.perf_counter()`, and print whether the answers agree and whether Parquet was faster.

   ```sh
   csv 47.4 MB, parquet 29.8 MB, parquet is smaller: True
   ...
   same answer: True   parquet faster: True
   author      pts
   ----------  -----
   ingve       69465
   prostoalex  32510
   jonbaer     26157
   (3 rows)
   ```

3. **Compression.** Write the Parquet file again with `COMPRESSION zstd` to a second file. Is it smaller than the default one?

4. **JSON lists.** In `countries_data.json`, how many countries speak 1, 2, 3, ... languages? Then list the countries that speak 6 or more languages, with their language lists.

   ```sh
   languages_spoken  countries
   ----------------  ---------
   1                 167
   2                 61
   3                 16
   4                 4
   5                 1
   10                1
   (6 rows)
   name          languages
   ------------  ---------------------------------------------------------------------------------------------------------------------
   South Africa  ['Afrikaans', 'English', 'Southern Ndebele', 'Southern Sotho', 'Swati', 'Tswana', 'Tsonga', 'Venda', 'Xhosa', 'Zulu']
   (1 row)
   ```

5. **Round trip.** Write `name, capital, population` of all countries (ordered by name) to a CSV, a JSON array and a Parquet file. Read each file back and print the row count and the sum of the population from each. All three must agree: `(250, 7349137231)`.

6. *(Optional, needs internet.)* Query `https://duckdb.org/data/flights.csv` and print the first two rows.

   ```sh
   FlightDate  UniqueCarrier  OriginCityName  DestCityName
   ----------  -------------  --------------  ---------------
   1988-01-01  AA             New York, NY    Los Angeles, CA
   1988-01-02  AA             New York, NY    Los Angeles, CA
   (2 rows)
   ```

### Exercises: Level 3

1. **Twelve months, one glob.** Take `data/big_events.csv` (generate it with `tools/make_big_events.py` if you do not have it). Split it into 12 monthly CSV files in `00_practice/months/`: with `COPY ... PARTITION_BY`, after adding a `month` column made with `strftime(ts, '%Y-%m')`, or with a plain Python loop if you prefer.
   Then, **without loading anything into a table**, query all 12 files with one glob and report, for each month, the number of events, the number of purchases and the total purchase amount (as `DECIMAL(12, 2)`). Check that the 12 files hold exactly 1,000,000 rows together.

   ```sh
   month    events  purchases  purchase_total
   -------  ------  ---------  --------------
   2025-01  85328   5862       1183841.87
   2025-02  76371   5299       1071958.65
   2025-03  85324   5915       1198387.11
   2025-04  82053   5730       1153826.53
   2025-05  84609   5866       1198482.76
   2025-06  82134   5741       1163809.97
   2025-07  84453   5934       1211946.23
   2025-08  84816   5865       1182476.16
   2025-09  82407   5924       1200506.65
   2025-10  84762   5956       1212399.29
   2025-11  82480   5894       1201964.47
   2025-12  85263   6005       1206197.36
   (12 rows)
   [(1000000,)]
   ```

2. **A year of Hacker News.** Using only the Parquet file from Level 2 (no CSV), report per month (from `created_at`): the number of posts, the average points (1 decimal) and the best post's points. Then list the 5 authors with at least 100 posts who collected the most points in total.

   ```sh
   month    posts  avg_points  best
   -------  -----  ----------  ----
   2015-09  18233  13.5        1952
   2015-10  24662  13.0        1776
   2015-11  21959  14.7        1740
   2015-12  21081  15.0        1824
   2016-01  23509  15.3        1876
   2016-02  24236  14.8        5771
   2016-03  24481  16.1        2049
   2016-04  24108  15.3        1610
   2016-05  23765  15.6        1832
   2016-06  22966  15.2        3125
   2016-07  21461  15.6        2381
   2016-08  23731  15.2        1323
   2016-09  18927  15.9        2553
   (13 rows)
   author       posts  points
   -----------  -----  ------
   ingve        2487   69465
   prostoalex   1656   32510
   jonbaer      2731   26157
   nkurz        462    21085
   adamnemecek  622    21071
   (5 rows)
   ```

CONGRATULATIONS !

[<< Day 23](../23_Day_Meet_duckdb/23_meet_duckdb.md) | [Day 25 >>](../25_Day_Duckdb_friendly_sql/25_duckdb_friendly_sql.md)
