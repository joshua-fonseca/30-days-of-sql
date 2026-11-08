<div align="center">
  <h1> 30 Days Of SQL: Day 20 - Importing, Cleaning & Exporting Data</h1>
</div>

[<< Day 19](../19_Day_Sqlite3_in_depth/19_sqlite3_in_depth.md) | [Day 21 >>](../21_Day_Indexes/21_indexes.md)

- [Day 20](#day-20)
  - [The Staging Pattern](#the-staging-pattern)
  - [Importing a CSV File](#importing-a-csv-file)
    - [Reading with the csv Module](#reading-with-the-csv-module)
    - [Loading in Batches with executemany](#loading-in-batches-with-executemany)
    - [A TEMP Staging Table](#a-temp-staging-table)
  - [Looking at the Mess](#looking-at-the-mess)
    - [Guessing Column Types](#guessing-column-types)
    - [Finding Dirty Values in SQL](#finding-dirty-values-in-sql)
  - [Cleaning in SQL](#cleaning-in-sql)
    - [Strip, Replace, NULLIF](#strip-replace-nullif)
    - [CAST and Its Silent Failures](#cast-and-its-silent-failures)
    - [The Clean Table: INSERT INTO ... SELECT](#the-clean-table-insert-into--select)
  - [Bad Rows: Log and Skip](#bad-rows-log-and-skip)
  - [Deduplicating While Loading](#deduplicating-while-loading)
  - [JSON in SQLite](#json-in-sqlite)
    - [Storing and Validating JSON](#storing-and-validating-json)
    - [Extracting: json_extract, -> and ->>](#extracting-json_extract---and--)
    - [Unnesting Arrays: json_each](#unnesting-arrays-json_each)
    - [Building and Changing JSON](#building-and-changing-json)
    - [JSONB](#jsonb)
  - [Exporting Results](#exporting-results)
    - [To CSV](#to-csv)
    - [To JSON](#to-json)
  - [ Exercises: Day 20](#exercises-day-20)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 20

Real data does not arrive as a tidy table. It arrives as a CSV with a strange delimiter, numbers written as `"$485,873"`, dashes where values are missing and the same person typed three ways. Today is the full
data journey: **get it in, clean it up, get results out**. You will also meet SQLite's JSON functions, which give you a third way to unpack the country `languages` lists.

## The Staging Pattern

The safest way to load messy data is in two steps:

1. **Staging (raw)**: load the file as it is, every column as `TEXT`, nothing converted. Loading cannot fail because of a bad value, and you can look at exactly what the file contains.
2. **Clean**: write a typed table and fill it with `INSERT INTO ... SELECT` from the staging table, with the cleaning rules in the `SELECT`.

Why not clean in Python while reading? You can, and for small jobs that is fine. But cleaning in SQL after loading means the rules are written once, in one place, they can be tested with ordinary queries
(`COUNT` the bad values before and after), and the raw data is still there when you change your mind about a rule. It is the same idea as keeping a raw photo next to the edited one.

## Importing a CSV File

### Reading with the csv Module

Python's `csv` module does the reading. Three details matter today: the `delimiter`, `newline=''` when opening the file (so `csv` handles line breaks inside quoted fields), and the `encoding`.

```py
import csv

with open('data/F500.csv', newline='', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    header = next(reader)
    first = next(reader)
print(header)
print(first)
# ['id', 'rank', 'name', 'employees', 'previousrank', 'revenues', 'revenuechange', 'profits', 'profitschange', 'assets', 'marketvalue']
# ['2', '1', 'Walmart', '2,300,000', '1', '$485,873', '0.8%', '$13,643.0 ', '-7.2%', '$198,825', '$218,619']
```

This is the Fortune 500 file (500 companies). It uses `;` as the delimiter (common in countries where `,` is the decimal separator), quotes every value, and shows several kinds of dirt: `'2,300,000'` employees, `'$485,873'` revenue, a percent sign,
a trailing space in `'$13,643.0 '`. `csv.reader` removes the quotes and nothing else. Every value is a `str`.

### Loading in Batches with executemany

Calling `executemany` with one giant list would hold the whole file in memory. Loading one row per `execute` is slow. The middle path is **batches**, and Python 3.12 has `itertools.batched` for exactly that:

```py
# syntax
for chunk in batched(iterable, n):      # tuples of up to n items
    conn.executemany(sql, chunk)
```

### A TEMP Staging Table

Staging tables are throw-away. `CREATE TEMP TABLE` makes a table that lives in a special `temp` schema, is visible only to this connection and **vanishes when the connection closes** (you met temp tables on Day 14). Perfect for staging:

```py
import sqlite3
from itertools import batched
from helpers import show

conn = sqlite3.connect('00_practice/datasets.db')
conn.execute('''
    CREATE TEMP TABLE f500_raw (
        id TEXT, rank TEXT, name TEXT, employees TEXT, previousrank TEXT, revenues TEXT,
        revenuechange TEXT, profits TEXT, profitschange TEXT, assets TEXT, marketvalue TEXT
    )
''')
with open('data/F500.csv', newline='', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    next(reader)                                   # skip the header row
    for chunk in batched(reader, 100):
        conn.executemany('INSERT INTO f500_raw VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', chunk)

print(conn.execute('SELECT COUNT(*) FROM f500_raw').fetchone())
print(conn.execute('SELECT name, typeof(employees), employees, profits FROM f500_raw LIMIT 2').fetchall())
print(conn.execute("SELECT name, type FROM sqlite_temp_master").fetchall())
# (500,)
# [('Walmart', 'text', '2,300,000', '$13,643.0 '), ('Berkshire Hathaway', 'text', '367,700', '$24,074.0 ')]
# [('f500_raw', 'table')]
```

Temp tables are listed in `sqlite_temp_master`, not `sqlite_master`. The `datasets.db` file stays untouched. The table is all text on purpose: the number of `?` must match the number of columns, and the file has 11 columns.

>  For a CSV with a lot of columns, build the placeholders instead of typing them: `', '.join('?' * len(header))`. The column *names* of the staging table you still write by hand: a header read from a file must never be pasted into SQL (Day 27).

**In other databases:** the bulk loaders are different commands: PostgreSQL `COPY ... FROM 'file.csv' (FORMAT csv)`, MySQL `LOAD DATA INFILE`, SQL Server `BULK INSERT`. DuckDB (Day 23) reads CSV in one line with `read_csv()`, and the `sqlite3` shell has `.import file.csv table`.
Inside Python, the batch pattern above is the portable way.

## Looking at the Mess

### Guessing Column Types

Before choosing column types for the clean table, look at what each column really contains. A tiny helper tries `int`, then `float`, after stripping the decorations, and reports the narrowest type that fits every value:

```py
def guess_type(values):
    kinds = set()
    for v in values:
        v = v.strip().replace('$', '').replace(',', '').replace('%', '')
        if v == '':
            continue
        try:
            int(v); kinds.add('int'); continue
        except ValueError:
            pass
        try:
            float(v); kinds.add('float'); continue
        except ValueError:
            pass
        kinds.add('text')
    if kinds == {'int'}:
        return 'INTEGER'
    if kinds <= {'int', 'float'}:
        return 'REAL'
    return 'TEXT'

with open('data/F500.csv', newline='', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter=';'))
for col in rows[0]:
    print(f'{col:15}', guess_type(r[col] for r in rows))
```

```sh
output
id              INTEGER
rank            INTEGER
name            TEXT
employees       INTEGER
previousrank    INTEGER
revenues        INTEGER
revenuechange   TEXT
profits         TEXT
profitschange   TEXT
assets          INTEGER
marketvalue     TEXT
```

`revenuechange`, `profits`, `profitschange` and `marketvalue` are `TEXT` after stripping: they contain something that is not a number. Time to find out what.

### Finding Dirty Values in SQL

The pattern is always the same: write a `WHERE` that describes the dirt and `COUNT` it. `SUM(condition)` is a neat trick, because a true condition is `1`:

```py
show(conn.execute("""
    SELECT SUM(employees LIKE '%,%')        AS employees_comma,
           SUM(revenues LIKE '%$%')         AS revenues_dollar,
           SUM(profits LIKE '% ')           AS profits_trailing_space,
           SUM(marketvalue = '-')           AS marketvalue_dash,
           SUM(previousrank = '')           AS prev_empty
    FROM f500_raw
"""))
```

```sh
output
employees_comma  revenues_dollar  profits_trailing_space  marketvalue_dash  prev_empty
---------------  ---------------  ----------------------  ----------------  ----------
500              500              499                     30                8
(1 row)
```

Every employee count has a comma and every revenue a dollar sign, 30 companies have a `-` instead of a market value, and 8 have an empty `previousrank` (new to the list).
Missing values come in many disguises: empty strings, `-`, `N/A`, `0`, `unknown`. Find the disguises, then turn them all into a real `NULL`.

## Cleaning in SQL

### Strip, Replace, NULLIF

You know the tools from Day 6: `trim`, `replace`, `NULLIF`. Nest `replace` calls to remove several characters:

```py
print(conn.execute("""
    SELECT name,
           replace(trim(employees), ',', '')                   AS employees,
           replace(replace(trim(revenues), ',', ''), '$', '')  AS revenues,
           NULLIF(trim(previousrank), '')                      AS previous_rank
    FROM f500_raw
    WHERE name IN ('Walmart', 'Dell Technologies')
    ORDER BY name
""").fetchall())
# [('Dell Technologies', '138000', '64806', None), ('Walmart', '2300000', '485873', '1')]
```

`NULLIF(x, '')` returns `NULL` when `x` equals `''` and `x` otherwise. It is the one-word way to say "empty means missing".

### CAST and Its Silent Failures

**Common mistake:** `CAST` never complains. A value that is not a number does not raise an error. It quietly becomes `0` (or a number made from its leading digits):

```py
print(conn.execute("SELECT CAST('-' AS INTEGER), CAST('abc' AS INTEGER), CAST('12abc' AS INTEGER), CAST('' AS INTEGER)").fetchone())
print(conn.execute("SELECT CAST(replace('2,300,000', ',', '') AS INTEGER), CAST('2,300,000' AS INTEGER)").fetchone())
# (0, 0, 12, 0)
# (2300000, 2)
```

So a market value of `-` would become a market value of **0**, which is a fact about the company that is not true. Always **check that a text looks like a number before you cast it**, and turn everything else into `NULL`.
A reliable check uses `GLOB` (Day 5): "contains a digit, and contains nothing except digits, dots and minus signs":

```sql
CASE WHEN x GLOB '*[0-9]*' AND x NOT GLOB '*[^0-9.-]*' THEN CAST(x AS REAL) END    -- NULL if it fails
```

`[^0-9.-]` means "any character that is not a digit, a dot or a minus". A `CASE` without `ELSE` gives `NULL`, which is exactly what we want.

### The Clean Table: INSERT INTO ... SELECT

Repeating long `replace` chains in the final query is unreadable, so do it in two layers: a **TEMP view** (a saved query, Day 22 explains views properly) that only strips the decoration, and the final `INSERT ... SELECT` that checks and casts.

The F500 amounts are in millions of dollars. We store whole **dollars as integers** (no `REAL` for money), so `$485,873` becomes `485873000000`. 

```py
conn.execute('''
    CREATE TEMP VIEW f500_stripped AS
    SELECT CAST(rank AS INTEGER) AS rank, name,
           replace(replace(trim(employees), ',', ''), '$', '')   AS employees,
           NULLIF(trim(previousrank), '')                        AS previous_rank,
           replace(replace(trim(revenues), ',', ''), '$', '')    AS revenues,
           replace(trim(revenuechange), '%', '')                 AS revenue_change,
           replace(replace(trim(profits), ',', ''), '$', '')     AS profits,
           replace(trim(profitschange), '%', '')                 AS profits_change,
           replace(replace(trim(assets), ',', ''), '$', '')      AS assets,
           replace(replace(trim(marketvalue), ',', ''), '$', '') AS market_value
    FROM f500_raw
''')
conn.execute('''
    CREATE TABLE f500 (
        rank               INTEGER PRIMARY KEY,
        name               TEXT NOT NULL,
        employees          INTEGER NOT NULL,
        previous_rank      INTEGER,
        revenue_usd        INTEGER NOT NULL,
        revenue_change_pct REAL,
        profit_usd         INTEGER,
        profit_change_pct  REAL,
        assets_usd         INTEGER NOT NULL,
        market_value_usd   INTEGER
    ) STRICT
''')
conn.execute('''
    INSERT INTO f500
    SELECT rank, name,
           CAST(employees AS INTEGER),
           CAST(previous_rank AS INTEGER),
           CAST(revenues AS INTEGER) * 1000000,
           CASE WHEN revenue_change GLOB '*[0-9]*' AND revenue_change NOT GLOB '*[^0-9.-]*' THEN CAST(revenue_change AS REAL) END,
           CASE WHEN profits GLOB '*[0-9]*' AND profits NOT GLOB '*[^0-9.-]*'
                THEN CAST(ROUND(CAST(profits AS REAL) * 1000000) AS INTEGER) END,
           CASE WHEN profits_change GLOB '*[0-9]*' AND profits_change NOT GLOB '*[^0-9.-]*' THEN CAST(profits_change AS REAL) END,
           CAST(assets AS INTEGER) * 1000000,
           CASE WHEN market_value GLOB '*[0-9]*' AND market_value NOT GLOB '*[^0-9.-]*' THEN CAST(market_value AS INTEGER) * 1000000 END
    FROM f500_stripped
''')
conn.commit()
show(conn.execute('SELECT rank, name, employees, revenue_usd, profit_usd, market_value_usd FROM f500 WHERE rank IN (1, 34, 500) ORDER BY rank'))
```

```sh
output
rank  name            employees  revenue_usd   profit_usd   market_value_usd
----  --------------  ---------  ------------  -----------  ----------------
1     Walmart         2300000    485873000000  13643000000  218619000000
34    Phillips 66     14800      72396000000   1555000000   40954000000
500   ABM Industries  110000     5145000000    57200000     2428000000
(3 rows)
```

The `STRICT` table is the safety net: if a value that should be an integer were still text, the insert would fail loudly instead of storing nonsense. The staging table and the view disappear when the connection closes; `f500` stays.

## Bad Rows: Log and Skip

Sometimes a whole row is broken: too few fields, or a price of `nine`. You have two options: stop the whole import, or **log the bad rows and skip them**, then look at the log. For a one-off import the second is usually better, as long as you never lose the information silently.

```py
import io

text = '''sku,name,price
PEN,Pen,1.50
NOTE,Notebook,4.00
BAD1,Broken row
STAP,Stapler,nine
GLUE,Glue stick,2.25
'''
good, rejects = [], []
for line_no, row in enumerate(csv.reader(io.StringIO(text)), start=1):
    if line_no == 1:
        continue                                   # header
    try:
        if len(row) != 3:
            raise ValueError(f'expected 3 fields, got {len(row)}')
        good.append((row[0], row[1], round(float(row[2]) * 100)))   # price to integer cents
    except ValueError as e:
        rejects.append((line_no, row, str(e)))

t = sqlite3.connect(':memory:')
t.execute('CREATE TABLE products (sku TEXT PRIMARY KEY, name TEXT NOT NULL, price_cents INTEGER NOT NULL) STRICT')
t.executemany('INSERT INTO products VALUES (?, ?, ?)', good)
print(t.execute('SELECT COUNT(*) FROM products').fetchone())
for r in rejects:
    print('rejected', r)
# (3,)
# rejected (4, ['BAD1', 'Broken row'], 'expected 3 fields, got 2')
# rejected (5, ['STAP', 'Stapler', 'nine'], "could not convert string to float: 'nine'")
```

(`io.StringIO` makes a string behave like a file, handy for examples and tests.) In a real import you would write `rejects` to a `rejected.csv` file. The SQL way of the same idea, inside the database, is the `GLOB` check above: the rows that fail the check are your reject report.
Here are the F500 values that did not convert, by field:

```py
show(conn.execute("""
    SELECT 'revenue_change' AS field, COUNT(*) AS failed FROM f500_stripped
        WHERE NOT (revenue_change GLOB '*[0-9]*' AND revenue_change NOT GLOB '*[^0-9.-]*')
    UNION ALL
    SELECT 'profits', COUNT(*) FROM f500_stripped WHERE NOT (profits GLOB '*[0-9]*' AND profits NOT GLOB '*[^0-9.-]*')
    UNION ALL
    SELECT 'profits_change', COUNT(*) FROM f500_stripped WHERE NOT (profits_change GLOB '*[0-9]*' AND profits_change NOT GLOB '*[^0-9.-]*')
    UNION ALL
    SELECT 'market_value', COUNT(*) FROM f500_stripped WHERE NOT (market_value GLOB '*[0-9]*' AND market_value NOT GLOB '*[^0-9.-]*')
"""))
```

```sh
output
field           failed
--------------  ------
revenue_change  6
profits         1
profits_change  66
market_value    30
(4 rows)
```

These did not fail the import. They became honest `NULL`s in `f500`, and now you know exactly how many.

## Deduplicating While Loading

You met duplicates on Day 17. The best moment to remove them is while loading, with a `UNIQUE` or `PRIMARY KEY` column and an upsert (Day 9) that ignores repeats. The `newsletter_signups` table in `shop.db` has the same person typed with different case and stray spaces.
The cleaning rule goes in the insert: `lower(trim(email))`.

```py
shop = sqlite3.connect('data/shop.db')
rows = shop.execute('SELECT email, signed_up_at FROM newsletter_signups ORDER BY signed_up_at').fetchall()

d = sqlite3.connect(':memory:')
d.execute('CREATE TABLE subscribers (email TEXT PRIMARY KEY, first_signup TEXT NOT NULL) STRICT')
d.executemany('''
    INSERT INTO subscribers (email, first_signup) VALUES (lower(trim(?)), ?)
    ON CONFLICT (email) DO NOTHING
''', rows)
print(len(rows), d.execute('SELECT COUNT(*) FROM subscribers').fetchone())
# 20 (12,)
```

Because we feed the rows **oldest first**, the first signup of each person is the one that survives and the later ones are ignored. If the input is not ordered, use the Day 17 route instead:
`SELECT lower(trim(email)), MIN(signed_up_at) ... GROUP BY lower(trim(email))`.

## JSON in SQLite

JSON is how web APIs and many files deliver data, and the `languages` list in `countries_data.json` is a JSON array. SQLite has had JSON functions built in since 3.38 (3.45 for the binary `JSONB`). They let you keep a document in one column and still query inside it.

### Storing and Validating JSON

SQLite has no JSON column type. JSON is stored as `TEXT`. Add a `CHECK` with `json_valid` so that garbage is refused:

```py
conn = sqlite3.connect(':memory:')
conn.execute('''CREATE TABLE people (id INTEGER PRIMARY KEY, profile TEXT NOT NULL CHECK (json_valid(profile))) STRICT''')
conn.executemany('INSERT INTO people (profile) VALUES (?)', [
    ('{"name": "Ana", "age": 31, "langs": ["Python", "SQL"], "address": {"city": "Toronto"}}',),
    ('{"name": "Ben", "age": 28, "langs": ["SQL"], "address": {"city": "London", "zip": null}}',),
    ('{"name": "Cy", "langs": []}',),
])
try:
    conn.execute("INSERT INTO people (profile) VALUES ('{oops')")
except sqlite3.IntegrityError as e:
    print(e)
# CHECK constraint failed: json_valid(profile)
```

From Python, create the text with `json.dumps(obj)` and read it back with `json.loads(text)`.

### Extracting: json_extract, -> and ->>

A **path** starts with `$` (the whole document), then `.key` for object keys and `[0]` for array positions: `$.address.city`, `$.langs[0]`.

```sql
-- syntax
json_extract(doc, '$.path')     -- the value as an SQL value (text, number or NULL)
doc -> '$.path'                 -- the value as JSON text   ("Ana" with quotes, arrays as text)
doc ->> '$.path'                -- the value as an SQL value (Ana, 31): the one you usually want
```

```py
show(conn.execute("""
    SELECT id,
           json_extract(profile, '$.name') AS name,
           profile ->> '$.age'             AS age,
           profile ->> '$.address.city'    AS city,
           profile -> '$.langs'            AS langs,
           profile ->> '$.langs[0]'        AS first_lang
    FROM people ORDER BY id
"""))
print(conn.execute("SELECT profile -> '$.name', profile ->> '$.name', typeof(profile -> '$.age'), typeof(profile ->> '$.age') FROM people WHERE id = 1").fetchone())
```

```sh
output
id  name  age   city     langs             first_lang
--  ----  ----  -------  ----------------  ----------
1   Ana   31    Toronto  ["Python","SQL"]  Python
2   Ben   28    London   ["SQL"]           SQL
3   Cy    NULL  NULL     []                NULL
(3 rows)
('"Ana"', 'Ana', 'text', 'integer')
```

A missing key gives `NULL`, not an error (Cy has no age). `->` returns JSON (a string comes back **with quotes**), `->>` returns a plain SQL value. As a shortcut, `profile ->> 'name'` is allowed instead of `'$.name'`.
Other handy functions: `json_array_length(doc, path)`, `json_type(doc, path)`, and `json_valid(doc)`.

**In other databases:** `->` and `->>` came to SQLite from PostgreSQL and MySQL, with the same meaning, so this syntax carries over. SQL Server uses `JSON_VALUE()` and `JSON_QUERY()`. DuckDB supports `->` and `->>` too.

### Unnesting Arrays: json_each

`json_each(doc, path)` is a **table-valued function**: it returns one row per element of an array (or per key of an object), with the columns `key` (the position), `value` and `type`. Join it to its parent row and the JSON array becomes rows, which you can then group, count and join like any others:

```py
show(conn.execute("""
    SELECT p.profile ->> 'name' AS name, l.key, l.value
    FROM people AS p
    JOIN json_each(p.profile, '$.langs') AS l
    ORDER BY name, l.key
"""))
show(conn.execute("""
    SELECT l.value AS language, COUNT(*) AS people, json_group_array(p.profile ->> 'name') AS who
    FROM people AS p JOIN json_each(p.profile, '$.langs') AS l
    GROUP BY l.value ORDER BY people DESC, language
"""))
```

```sh
output
name  key  value
----  ---  ------
Ana   0    Python
Ana   1    SQL
Ben   0    SQL
(3 rows)
language  people  who
--------  ------  -------------
SQL       2       ["Ana","Ben"]
Python    1       ["Ana"]
(2 rows)
```

Cy has an empty list, so Cy produces no rows (an inner join). This is the same normalization you did by hand on Day 10 when you created `country_languages`, only done on the fly. `json_group_array` is the opposite direction: an aggregate that collects values into a JSON array.

### Building and Changing JSON

```py
print(conn.execute("SELECT json_set(profile, '$.age', 32, '$.address.zip', 'M5V') FROM people WHERE id = 1").fetchone()[0])
print(conn.execute("SELECT json_remove(profile, '$.langs') FROM people WHERE id = 3").fetchone()[0])
print(conn.execute("SELECT json_object('id', id, 'name', profile ->> 'name') FROM people WHERE id = 1").fetchone()[0])
print(conn.execute("SELECT json_array(1, 'a', NULL)").fetchone()[0])
# {"name":"Ana","age":32,"langs":["Python","SQL"],"address":{"city":"Toronto","zip":"M5V"}}
# {"name":"Cy"}
# {"id":1,"name":"Ana"}
# [1,"a",null]
```

`json_set` (set or add), `json_insert` (add only), `json_replace` (change only), `json_remove` and `json_patch` update a document **as a value**: they return a new text, so combine them with `UPDATE ... SET profile = json_set(profile, ...)` to save the change.
`json_object`, `json_array` and `json_group_array` build JSON from rows, which is useful for exports.

**Common mistake:** putting everything in a JSON column "to stay flexible". You lose type checks, foreign keys and simple indexes. Use JSON for data whose shape really varies (settings, API payloads, event details) and normal columns for everything you filter and join on every day.
(You *can* index a JSON path: `CREATE INDEX ON people (profile ->> '$.address.city')`. Day 21 shows expression indexes.)

### JSONB

SQLite 3.45 added **JSONB**: the same JSON in a compact *binary* form. Text JSON has to be parsed every time a function reads it; JSONB is stored pre-parsed, so reading from it is faster and it takes a bit less space. Create it with `jsonb(text)`; read it back with `json(blob)`;
every JSON function has a `jsonb_` twin (`jsonb_set`, ...) and also accepts JSONB as input.

```py
print(conn.execute('SELECT typeof(jsonb(profile)), length(jsonb(profile)) FROM people WHERE id = 1').fetchone())
print(conn.execute('SELECT json(jsonb(profile)) FROM people WHERE id = 1').fetchone()[0])
print(conn.execute("SELECT jsonb(profile) ->> '$.name' FROM people WHERE id = 1").fetchone())
# ('blob', 59)
# {"name":"Ana","age":31,"langs":["Python","SQL"],"address":{"city":"Toronto"}}
# ('Ana',)
```

The catch: a JSONB value is a `BLOB`, unreadable in a plain `SELECT`, so your table viewer shows bytes. Use text JSON when people need to read it and JSONB for large documents that are queried a lot.
Python receives JSONB as `bytes`.

## Exporting Results

### To CSV

Use `csv.writer`, take the header from `cursor.description` (the same trick your `show()` helper uses), and write the rows straight from the cursor:

```py
cur = shop.execute('''
    SELECT lower(trim(email)) AS email, MIN(signed_up_at) AS first_signup
    FROM newsletter_signups GROUP BY 1 ORDER BY 2, 1
''')
with open('00_practice/subscribers.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([col[0] for col in cur.description])
    writer.writerows(cur)

with open('00_practice/subscribers.csv', newline='', encoding='utf-8') as f:
    back = list(csv.DictReader(f))
print(len(back), back[0])
# 12 {'email': 'kira@example.com', 'first_signup': '2025-01-05 11:46:00'}
```

`NULL` is written as an empty field. Reading the file back and checking is a good habit: an export you never reopened is an export you do not know works.

### To JSON

Zip the column names with each row to get dictionaries, then `json.dump`. Or let SQLite build the text with `json_group_array(json_object(...))`:

```py
import json

cur = shop.execute("SELECT customer_id AS id, first_name FROM customers ORDER BY customer_id LIMIT 2")
cols = [c[0] for c in cur.description]
print(json.dumps([dict(zip(cols, row)) for row in cur]))
print(shop.execute("SELECT json_group_array(json_object('id', customer_id, 'first_name', first_name)) FROM (SELECT * FROM customers ORDER BY customer_id LIMIT 2)").fetchone()[0])
# [{"id": 1, "first_name": "Chen"}, {"id": 2, "first_name": "Diego"}]
# [{"id":1,"first_name":"Chen"},{"id":2,"first_name":"Diego"}]
```

You can now take a messy file from a stranger, understand it, clean it, query it and hand the answer back in a format somebody else can open. That is a real data skill, and it is most of what "data work" actually is.

## Exercises: Day 20

### Exercises: Level 1

Work with `data/F500.csv`. Use one connection for the whole exercise set, so the TEMP table stays available. Put your work in `00_practice/day_20.py`.

1. Read the first two lines of `data/F500.csv` as plain text with `pathlib` and print them. What is the delimiter? Are the values quoted?
2. Open the file with `csv.reader` and the right delimiter. Print the header list and the first data row.
3. Count the data rows with Python (expected `500`).
4. Create the TEMP table `f500_raw` (all `TEXT`) and load the file in batches of 100 with `executemany`. Print the row count (expected `500`).
5. Print `typeof()` of `employees`, `revenues` and `rank` for the first row. Expected: `('text', 'text', 'text')`. Why is that what we want in a staging table?
6. Count how many `employees` values contain a comma, and how many `revenues` values contain a `$`. Expected `(500, 500)`.
7. One company has a `profits` value without a dollar sign. Find it.

   ```sh
   name           profits
   -------------  -------
   Vistra Energy  -
   (1 row)
   ```

8. How many companies have a negative profit (a `profits` value starting with `-$`)? Expected `(62,)`.
9. Count the `marketvalue` values equal to `'-'` and the `previousrank` values equal to `''`. Expected `(30, 8)`.
10. Run `SELECT CAST('-' AS INTEGER), CAST('12abc' AS INTEGER), CAST('2,300,000' AS INTEGER)`. Predict the three numbers first. Expected `(0, 12, 2)`. What does this tell you about trusting `CAST`?
11. Write the expression that turns Walmart's `revenues` into the clean text `485873` (using `trim` and nested `replace`).
12. Add up the `revenues` of all 500 companies as integers (in millions of dollars). Expected `(12055874,)`.
13. Use `NULLIF` to count the companies whose `previousrank` is empty. Expected `(8,)`.
14. In your own words: why do we load into an all-`TEXT` staging table first instead of creating the final typed table directly?
15. Close the connection, reconnect to the same file and try to count `f500_raw`. What happens, and why? (Expected: `OperationalError: no such table: f500_raw`.)

### Exercises: Level 2

1. Create the typed `STRICT` table `f500` as shown in the lesson (money as whole dollars, `NULL` for values that are not numbers), using a TEMP view for stripping and `INSERT INTO ... SELECT`. Print the row count and the rows with rank 1, 34 and 500.

   ```sh
   (500,)
   rank  name            employees  revenue_usd   profit_usd   market_value_usd
   ----  --------------  ---------  ------------  -----------  ----------------
   1     Walmart         2300000    485873000000  13643000000  218619000000
   34    Phillips 66     14800      72396000000   1555000000   40954000000
   500   ABM Industries  110000     5145000000    57200000     2428000000
   (3 rows)
   ```

2. **Report the failures.** Count, for `revenue_change`, `profits`, `profits_change` and `market_value`, how many raw values did not look like a number, and list the companies (rank and name) whose `revenue_change` failed. Then count the rows of `f500` that have at least one `NULL` among the four converted columns.

   ```sh
   field           failed
   --------------  ------
   revenue_change  6
   profits         1
   profits_change  66
   market_value    30
   (4 rows)
   rank  name
   ----  --------------------------
   59    Hewlett Packard Enterprise
   300   Alcoa
   399   Yum China Holdings
   435   Harley-Davidson
   482   Chemours
   499   Vistra Energy
   (6 rows)
   (93,)
   ```

3. **Deduplicate while loading.** Load `newsletter_signups` from `data/shop.db` into a new table `subscribers (email PRIMARY KEY, first_signup)` in an in-memory database, cleaning with `lower(trim(...))` and ignoring repeats. Print how many rows went in and how many survived, then the five earliest subscribers.

   ```sh
   20 (12,)
   email              first_signup
   -----------------  -------------------
   kira@example.com   2025-01-05 11:46:00
   ben@example.com    2025-01-13 15:02:00
   jules@example.com  2025-01-15 11:30:00
   ana@example.com    2025-02-07 13:50:00
   elif@example.com   2025-02-15 11:38:00
   (5 rows)
   ```

4. **Log and skip.** This text is a CSV of products. Parse it with `csv.reader` over `io.StringIO`, convert the price to integer cents, insert the good rows into a table and print every rejected row with its line number and a reason.

   ```
   sku,name,price
   PEN,Pen,1.50
   NOTE,Notebook,4.00
   BAD1,Broken row
   STAP,Stapler,nine
   GLUE,Glue stick,2.25
   ```

   ```sh
   (3,)
   rejected (4, ['BAD1', 'Broken row'], 'expected 3 fields, got 2')
   rejected (5, ['STAP', 'Stapler', 'nine'], "could not convert string to float: 'nine'")
   ```

5. **JSON basics.** For this document (pass it as a parameter), use SQL only: (a) the customer's name, the number of items and the tags array; (b) how many of the customer's tags equal `'vip'`; (c) the order total in cents (the sum of `qty * price_cents` over the items, using `json_each`); (d) the items as rows `sku, qty`, ordered by sku.

   ```py
   doc = ('{"order": 1001, "customer": {"name": "Ana", "tags": ["vip", "newsletter"]}, '
          '"items": [{"sku": "PEN", "qty": 2, "price_cents": 150}, {"sku": "NOTE", "qty": 1, "price_cents": 400}]}')
   ```

   ```sh
   ('Ana', 2, '["vip","newsletter"]')
   (1,)
   (700,)
   sku   qty
   ----  ---
   NOTE  1
   PEN   2
   (2 rows)
   ```

6. **Round trip.** Export the 12 distinct subscribers from Q3 (email, first signup) to `00_practice/subscribers.csv` with a header row, read the file back with `csv.DictReader`, and print the number of rows and the first one.

   ```sh
   12 {'email': 'kira@example.com', 'first_signup': '2025-01-05 11:46:00'}
   ```

### Exercises: Level 3

1. **Most profitable companies.** From your clean `f500` table, list the 10 most profitable companies (skip `NULL` profits; ties by name) with their profit in millions of dollars and their revenue per employee in whole dollars.

   ```sh
   rank  name                   profit_millions  revenue_per_employee_usd
   ----  ---------------------  ---------------  ------------------------
   3     Apple                  45687            1858956
   21    J.P. Morgan Chase      24733            433465
   2     Berkshire Hathaway     24074            608115
   25    Wells Fargo            21938            349966
   27    Alphabet               19478            1252855
   26    Bank of America Corp.  17906            450246
   28    Microsoft              16798            748421
   35    Johnson & Johnson      16540            568750
   30    Citigroup              14912            376191
   148   Altria Group           14239            2329759
   (10 rows)
   ```

2. **Languages from raw JSON.** Create a table `countries_raw (doc TEXT NOT NULL CHECK (json_valid(doc)))` and insert each country from `data/countries_data.json` as one JSON document (`json.dumps`). Get the ten most spoken languages with `json_each`, ties by language name. It is the same answer you got on Day 11 with the `country_languages` table.
   Then add a `BLOB` column filled with `jsonb(doc)` and show that the same query on the binary column gives the same ten rows.

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

3. **Export.** Write the ten-language result to `00_practice/top_languages.csv` (with header) and to `00_practice/top_languages.json` (a list of objects, indented). Read both files back and print the first three lines of the CSV and the first object of the JSON. As a bonus, build the JSON for the first three rows in SQL with `json_group_array(json_object(...))`.

   ```sh
   ['language,countries', 'English,91', 'French,45']
   {'language': 'English', 'countries': 91}
   [{"language":"English","countries":91},{"language":"French","countries":45},{"language":"Arabic","countries":25}]
   ```

CONGRATULATIONS !

[<< Day 19](../19_Day_Sqlite3_in_depth/19_sqlite3_in_depth.md) | [Day 21 >>](../21_Day_Indexes/21_indexes.md)
