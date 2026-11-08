<div align="center">
  <h1> 30 Days Of SQL: Day 21 - Indexes & Query Performance</h1>
</div>

[<< Day 20](../20_Day_Import_clean_export/20_import_clean_export.md) | [Day 22 >>](../22_Day_Views_and_triggers/22_views_and_triggers.md)

- [Day 21](#day-21)
  - [Why Queries Get Slow](#why-queries-get-slow)
  - [Meet big_events](#meet-big_events)
  - [Reading a Query Plan](#reading-a-query-plan)
  - [Measuring Time](#measuring-time)
  - [CREATE INDEX](#create-index)
    - [Your First Index](#your-first-index)
    - [Seeing and Dropping Indexes](#seeing-and-dropping-indexes)
    - [UNIQUE Indexes and the Primary Key](#unique-indexes-and-the-primary-key)
  - [Composite Indexes](#composite-indexes)
  - [Covering Indexes](#covering-indexes)
  - [Partial Indexes](#partial-indexes)
  - [Expression Indexes](#expression-indexes)
  - [When an Index Does Not Help](#when-an-index-does-not-help)
    - [Functions on the Column](#functions-on-the-column)
    - [LIKE and Leading Wildcards](#like-and-leading-wildcards)
    - [Low Selectivity](#low-selectivity)
  - [The Costs of Indexes](#the-costs-of-indexes)
  - [ANALYZE and PRAGMA optimize](#analyze-and-pragma-optimize)
  - [Keyset Pagination](#keyset-pagination)
  - [Bonus: Full-Text Search with FTS5](#bonus-full-text-search-with-fts5)
  - [ Exercises: Day 21](#exercises-day-21)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 21

> **Before you start:** today needs `data/big_events.csv` (one million rows, not stored in git). Build it once from the repo root with `uv run python tools/make_big_events.py` (about 40 MB). See "Setup & data" in the [readme](../readme.md#-setup--data-what-each-day-needs).

Every query you have written so far ran on tables with a few hundred rows, so speed never mattered. Today the table has **a million rows**, and the question changes from "is my answer right?" to "how long does it take, and why?". You will learn
how SQLite finds rows, how to ask it for its plan, and how an **index** turns a search that reads everything into one that jumps straight to the answer.

## Why Queries Get Slow

Think of a phone book. To find "Nguyen, Alice" you do not read every page from "Aaron": the names are **sorted**, so you open the book near the middle, see you are too early or too late, and halve the range again. A few steps and you are there.
Now imagine the book is sorted by *address* and you want a *name*: the only way is to read every entry. That is a **full table scan**.

A database table is stored in the order rows were inserted (strictly, in `rowid` order). Searching it by any other column means reading every row. An **index** is a second, sorted structure (a **B-tree**) that stores the values of one or more columns
together with the location of their rows, exactly like the sorted phone book. Finding a value takes a handful of steps even for a million rows, because a B-tree has very few levels.

## Meet big_events

`big_events.csv` is a seeded file with a million web-shop events: who did what and when.

| column | meaning |
|---|---|
| `event_id` | 1 to 1,000,000, in time order |
| `user_id` | 1 to 50,000 |
| `event_type` | `view`, `click`, `add_to_cart`, `purchase`, `refund` |
| `ts` | ISO text, `'2025-01-01 00:00:26'` |
| `amount` | dollars with cents for purchases and refunds (refunds are negative), empty otherwise |

It is not in the repository (41 MB). Create it once from the repository root:

```sh
uv run python tools/make_big_events.py
```

Then load it into a SQLite file. This is the Day 20 recipe: `csv`, batches, `executemany`, and money converted to integer cents on the way in.

```py
import csv
import sqlite3
from itertools import batched
from helpers import show

conn = sqlite3.connect('00_practice/events.db')
conn.execute('''
    CREATE TABLE events (
        event_id     INTEGER PRIMARY KEY,
        user_id      INTEGER NOT NULL,
        event_type   TEXT NOT NULL,
        ts           TEXT NOT NULL,
        amount_cents INTEGER
    ) STRICT
''')
with open('data/big_events.csv', newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)
    rows = ((int(i), int(u), t, ts, round(float(a) * 100) if a else None) for i, u, t, ts, a in reader)
    for chunk in batched(rows, 50_000):
        conn.executemany('INSERT INTO events VALUES (?, ?, ?, ?, ?)', chunk)
conn.commit()

print(conn.execute('SELECT COUNT(*) FROM events').fetchone())
print(conn.execute('SELECT * FROM events ORDER BY event_id LIMIT 1').fetchone())
# (1000000,)
# (1, 33474, 'view', '2025-01-01 00:00:26', None)
```

(`rows` is a generator, so the million rows are never in memory at once. It takes a few seconds.) Every example below uses this `conn`.

## Reading a Query Plan

Before a query runs, SQLite's **query planner** decides *how* to run it. You can ask it to show its decision by putting `EXPLAIN QUERY PLAN` in front of any statement. It does not run the query:

```sql
-- syntax
EXPLAIN QUERY PLAN SELECT ... ;
```

```py
def plan(conn, sql, params=()):
    """The detail column of EXPLAIN QUERY PLAN, one string per step."""
    return [row[3] for row in conn.execute('EXPLAIN QUERY PLAN ' + sql, params)]

Q = 'SELECT COUNT(*), SUM(amount_cents) FROM events WHERE user_id = ?'
print(conn.execute(Q, (12345,)).fetchone())
print(plan(conn, Q, (12345,)))
# (18, 89299)
# ['SCAN events']
```

Each plan row has four columns; the last one is the sentence you read. The two words to know:

| Plan says | Meaning |
|---|---|
| `SCAN events` | reads **every row** of the table. Cost grows with the table. |
| `SEARCH events USING INDEX idx (col=?)` | jumps to the matching rows through an index. Cost grows very slowly. |
| `SEARCH events USING INTEGER PRIMARY KEY (rowid=?)` | the same, using the primary key (no extra index needed) |
| `SCAN events USING INDEX idx` | reads the whole index in order: it can avoid sorting, but it is still a full read |
| `USE TEMP B-TREE FOR ORDER BY` / `GROUP BY` | no index could deliver the order, so SQLite sorts the rows in a temporary structure |

User 12345 has only 18 events, but SQLite has to look at all 1,000,000 rows to find them.

**In other databases:** PostgreSQL and MySQL use `EXPLAIN` (and `EXPLAIN ANALYZE` to actually run and time it). SQL Server has "Display Estimated Execution Plan". DuckDB has `EXPLAIN` and `EXPLAIN ANALYZE` too (Day 23). SQLite's own plain `EXPLAIN` shows
low-level virtual machine code: not what you want here.

## Measuring Time

Time a query with `time.perf_counter()`. A single run is noisy (the first run also warms the disk cache), so take the **best of a few runs**:

```py
import time

def best_time(conn, sql, params=(), repeat=3):
    """Smallest wall-clock time of `repeat` runs, in seconds."""
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        conn.execute(sql, params).fetchall()
        times.append(time.perf_counter() - start)
    return min(times)

before = best_time(conn, Q, (12345,))
print('took', round(before * 1000, 1), 'ms')
# took 36.8 ms          (yours will differ: it depends on your machine)
```

Exact times differ on every machine and every run, so **never compare your numbers with anyone else's**. Compare *ratios* on your own machine ("30,000 times faster"), and check the plan: the plan is the same everywhere.

## CREATE INDEX

### Your First Index

```sql
-- syntax
CREATE INDEX [IF NOT EXISTS] index_name ON table_name (column1 [, column2, ...]);
DROP INDEX [IF EXISTS] index_name;
```

```py
conn.execute('CREATE INDEX idx_events_user ON events (user_id)')
print(plan(conn, Q, (12345,)))
after = best_time(conn, Q, (12345,))
print('more than 100x faster:', before / after > 100)
# ['SEARCH events USING INDEX idx_events_user (user_id=?)']
# more than 100x faster: True
```

The plan changed from `SCAN` to `SEARCH`, and the query went from tens of milliseconds to microseconds (a ratio of thousands on a typical machine). The result is identical: **an index changes how fast, never what**. You do not mention the index in your query;
the planner picks it by itself whenever it helps. Building it took a second or two, because SQLite had to read and sort all million values once.

Name indexes `idx_<table>_<columns>` so you can find them later.

### Seeing and Dropping Indexes

```py
print(conn.execute("PRAGMA index_list('events')").fetchall())
print(conn.execute("SELECT name, tbl_name FROM sqlite_master WHERE type = 'index'").fetchall())
# [(0, 'idx_events_user', 0, 'c', 0)]
# [('idx_events_user', 'events')]
```

`PRAGMA index_list` columns: position, name, `unique` (0/1), origin (`c` = created by `CREATE INDEX`, `u` = from a `UNIQUE` constraint, `pk` = primary key), `partial` (0/1). Indexes live in `sqlite_master` as `type = 'index'`.
`PRAGMA index_info('name')` lists the columns of one index.

### UNIQUE Indexes and the Primary Key

A `UNIQUE` constraint is implemented *by* an index. You can also create the index directly, which is handy to add uniqueness to an existing table:

```py
toy = sqlite3.connect(':memory:')
toy.execute('CREATE TABLE people (id INTEGER PRIMARY KEY, email TEXT) STRICT')
toy.execute('CREATE UNIQUE INDEX idx_people_email ON people (email)')
toy.execute("INSERT INTO people (email) VALUES ('a@x.com')")
try:
    toy.execute("INSERT INTO people (email) VALUES ('a@x.com')")
except sqlite3.IntegrityError as e:
    print('IntegrityError:', e)
# IntegrityError: UNIQUE constraint failed: people.email
```

And what about the primary key? An `INTEGER PRIMARY KEY` is the `rowid`: the table *itself* is a B-tree sorted by it, so lookups by id are fast with no extra index:

```py
print(plan(conn, 'SELECT * FROM events WHERE event_id = 500000'))
# ['SEARCH events USING INTEGER PRIMARY KEY (rowid=?)']
```

## Composite Indexes

An index can cover **several columns**, sorted by the first, then (within equal first values) by the second, and so on, like a phone book sorted by last name and then first name. The **order of the columns matters**:

```py
conn.execute('DROP INDEX idx_events_user')
conn.execute('CREATE INDEX idx_events_user_ts ON events (user_id, ts)')

queries = {
    'user_id =':              "SELECT event_id FROM events WHERE user_id = 777",
    'user_id = and ts range': "SELECT event_id FROM events WHERE user_id = 777 AND ts >= '2025-06-01'",
    'user_id = order by ts':  "SELECT event_id FROM events WHERE user_id = 777 ORDER BY ts",
    'ts range only':          "SELECT event_id FROM events WHERE ts >= '2025-06-01' AND ts < '2025-06-02'",
    'event_type =':           "SELECT event_id FROM events WHERE event_type = 'refund'",
}
for name, sql in queries.items():
    print(f'{name:24} {plan(conn, sql)[0]}')
```

```sh
output
user_id =                SEARCH events USING COVERING INDEX idx_events_user_ts (user_id=?)
user_id = and ts range   SEARCH events USING COVERING INDEX idx_events_user_ts (user_id=? AND ts>?)
user_id = order by ts    SEARCH events USING COVERING INDEX idx_events_user_ts (user_id=?)
ts range only            SCAN events USING COVERING INDEX idx_events_user_ts
event_type =             SCAN events
```

The rule is the **leftmost prefix**: an index on `(user_id, ts)` can serve a search on `user_id`, or on `user_id` and `ts` together, but *not* a search on `ts` alone (the data is sorted by user first; the timestamps are scattered through the book).
Inside the index, the equality columns should come first and a range column last.

A second benefit: because entries for one user are already in `ts` order, `ORDER BY ts` needs **no sorting step**. Compare with the single-column index, where the plan had an extra `USE TEMP B-TREE FOR ORDER BY`.

How to choose the order: put the columns tested with `=` first, then the one tested with a range (`>`, `<`, `BETWEEN`) or used for `ORDER BY`. A composite index on `(a, b)` makes a separate index on `(a)` redundant, but not one on `(b)`.

## Covering Indexes

Notice the words `COVERING INDEX` above. When every column the query needs is **inside the index**, SQLite never touches the table at all: it answers from the index alone. Selecting `user_id` and `ts` is covered by `(user_id, ts)`; selecting `*` is not,
because the other columns live only in the table:

```py
print(plan(conn, 'SELECT user_id, ts FROM events WHERE user_id = 777')[0])
print(plan(conn, 'SELECT * FROM events WHERE user_id = 777')[0])
# SEARCH events USING COVERING INDEX idx_events_user_ts (user_id=?)
# SEARCH events USING INDEX idx_events_user_ts (user_id=?)
```

Covering indexes are the reason to list columns instead of `SELECT *`, and a classic trick for hot queries: add one extra trailing column to an index so a frequent query is fully covered. (Every extra column also makes the index bigger.)

## Partial Indexes

If a query only ever touches a **slice** of the table, index only that slice. A partial index has a `WHERE` clause, and it is smaller and cheaper to maintain. Purchases are only 7% of the events:

```py
conn.execute("CREATE INDEX idx_purchases_user ON events (user_id) WHERE event_type = 'purchase'")
print(plan(conn, "SELECT COUNT(*) FROM events WHERE event_type = 'purchase' AND user_id = 777")[0])
print(plan(conn, "SELECT COUNT(*) FROM events WHERE event_type = 'view' AND user_id = 777")[0])
# SEARCH events USING COVERING INDEX idx_purchases_user (user_id=?)
# SEARCH events USING INDEX idx_events_user_ts (user_id=?)
```

The planner uses the partial index only when the query's `WHERE` clearly implies the index's `WHERE`. For `'view'` it falls back to the other index. A common use: `CREATE UNIQUE INDEX ... ON t (email) WHERE deleted_at IS NULL` ("emails are unique among *active* users").

## Expression Indexes

What if you search by a *computed* value, like the date part of the timestamp? An index on the plain column cannot help, because the stored values are not the values you compare. Index the **expression** itself:

```py
Q5 = "SELECT COUNT(*) FROM events WHERE date(ts) = '2025-06-01'"
conn.execute('CREATE INDEX idx_events_ts ON events (ts)')
print(plan(conn, Q5)[0])
conn.execute('CREATE INDEX idx_events_date ON events (date(ts))')
print(plan(conn, Q5)[0])
print(conn.execute(Q5).fetchone())
# SCAN events USING COVERING INDEX idx_events_ts
# SEARCH events USING INDEX idx_events_date (<expr>=?)
# (2703,)
```

The query must use **exactly the same expression** as the index (`date(ts)`, not `substr(ts, 1, 10)`). This also works for JSON paths (`profile ->> '$.address.city'`, Day 20) and `lower(email)`. The expression must be deterministic: it cannot call `random()` or read the clock.

Often there is an even better fix: rewrite the query so the plain column is compared with a range. `ts >= '2025-06-01' AND ts < '2025-06-02'` returns the same rows and uses the ordinary index on `ts`. Prefer that when you can; use an expression index when you cannot.

## When an Index Does Not Help

### Functions on the Column

Wrapping the indexed column in a function hides it from the index: `WHERE date(ts) = ...`, `WHERE substr(ts, 1, 10) = ...` and `WHERE user_id + 0 = 5` all end in a scan (unless an expression index matches). **Keep the column bare on one side of the comparison** and move the computation to the other side.

### LIKE and Leading Wildcards

```py
for label, sql in [
    ("ts LIKE 'x%'", "SELECT COUNT(*) FROM events WHERE ts LIKE '2025-06-01%'"),
    ("ts LIKE '%x'", "SELECT COUNT(*) FROM events WHERE ts LIKE '%01'"),
    ("ts GLOB 'x*'", "SELECT COUNT(*) FROM events WHERE ts GLOB '2025-06-01*'"),
    ('range',         "SELECT COUNT(*) FROM events WHERE ts >= '2025-06-01' AND ts < '2025-06-02'"),
]:
    print(f'{label:14} {plan(conn, sql)[0]}')
```

```sh
output
ts LIKE 'x%'   SCAN events USING COVERING INDEX idx_events_ts
ts LIKE '%x'   SCAN events USING COVERING INDEX idx_events_ts
ts GLOB 'x*'   SEARCH events USING COVERING INDEX idx_events_ts (ts>? AND ts<?)
range          SEARCH events USING COVERING INDEX idx_events_ts (ts>? AND ts<?)
```

- A **leading wildcard** (`LIKE '%x'`, `LIKE '%python%'`) can never use an index: the sorted order only helps if you know how the value *starts*. The best you get is reading the whole index.
- Even `LIKE 'x%'` does not search here. SQLite's `LIKE` ignores case, and the default index is case-sensitive, so they disagree. `GLOB 'x*'` (case-sensitive, Day 5) does use the index. A `LIKE 'x%'` can use an index only if the column was declared `COLLATE NOCASE`.
- For real word search inside text, use full-text search (the bonus section at the end).

### Low Selectivity

An index pays off when it narrows the search to a **small fraction** of the table. An index on `event_type` has only five distinct values:

```py
conn.execute('CREATE INDEX idx_events_type ON events (event_type)')
def t(sql): return best_time(conn, sql)
view_indexed   = t("SELECT * FROM events WHERE event_type = 'view'")
view_scan      = t("SELECT * FROM events NOT INDEXED WHERE event_type = 'view'")      # NOT INDEXED = ignore all indexes
refund_indexed = t("SELECT * FROM events WHERE event_type = 'refund'")
refund_scan    = t("SELECT * FROM events NOT INDEXED WHERE event_type = 'refund'")
print("'view' (55% of rows): index faster by more than 1.5x:", view_scan / view_indexed > 1.5)
print("'refund' (1% of rows): index faster by more than 1.5x:", refund_scan / refund_indexed > 1.5)
# 'view' (55% of rows): index faster by more than 1.5x: False
# 'refund' (1% of rows): index faster by more than 1.5x: True
```

When half the table matches, jumping around through an index is no better (it is often slower) than reading straight through. So do not index every column "just in case". Index the columns you filter, join or sort by, **and** that narrow things down.
Joins deserve special mention: SQLite does not index foreign key columns for you, so `loans.member_id` and `loans.book_id` are good candidates (Exercise L1 Q14).

## The Costs of Indexes

Indexes are not free. Every `INSERT`, `UPDATE` of an indexed column and `DELETE` must update the table **and every index**, and each index takes disk space:

```py
from pathlib import Path

size_before = Path('00_practice/events.db').stat().st_size
conn.execute('CREATE INDEX idx_events_ts_user ON events (ts, user_id)')
conn.commit()
size_after = Path('00_practice/events.db').stat().st_size
print('the file got bigger:', size_after > size_before)
# the file got bigger: True
```

One more index on a million rows added tens of megabytes to the file, roughly a fifth of what was already there, and the table itself is only about 39 MB. The index of two columns holds a copy of both values for every row.

Indexes make reads faster and writes slower. A table that is read constantly and written rarely (a catalogue) can carry many; a table that takes thousands of inserts per second (a log) should carry few. The honest procedure is: find a slow query, read its plan,
add the **one** index that fixes it, check that the plan changed, and drop indexes that no query uses.

## ANALYZE and PRAGMA optimize

The planner chooses between plans using guesses about your data. `ANALYZE` reads the tables and stores statistics in the table `sqlite_stat1`, so the guesses get better:

```py
conn.execute('ANALYZE')
show(conn.execute("SELECT idx, stat FROM sqlite_stat1 WHERE idx IN ('idx_events_ts', 'idx_events_user_ts') ORDER BY idx"))
```

```sh
output
idx                 stat
------------------  ------------
idx_events_ts       1000000 1
idx_events_user_ts  1000000 20 1
(2 rows)
```

Read `stat` as: the table has 1,000,000 rows; one value of `user_id` matches about 20 rows; one `(user_id, ts)` pair matches about 1 row. Those numbers tell the planner that `user_id` is selective. You rarely need to run `ANALYZE` on a small database. For an application, the
modern habit is to run **`PRAGMA optimize`** just before closing a long-lived connection: SQLite then decides by itself whether re-analysing is useful, and does it cheaply.

```py
conn.execute('PRAGMA optimize')
conn.close()
```

## Keyset Pagination

On Day 4 you paged with `LIMIT n OFFSET m`. It works, but there is a catch: to give you page 40,000, SQLite must walk past the 800,000 rows before it and throw them away. Page 1 is instant, page 40,000 is slow, and the cost keeps growing.

**Keyset pagination** (also called the seek method) remembers the *last key you showed* and asks for rows after it. The `WHERE` lets the index (here the primary key) jump straight to the right place:

```py
# syntax
SELECT ... FROM t WHERE key > :last_seen ORDER BY key LIMIT :page_size
```

```py
conn = sqlite3.connect('00_practice/events.db')       # reopen: we closed it above
offset_sql = 'SELECT event_id FROM events ORDER BY event_id LIMIT 20 OFFSET 799980'
keyset_sql = 'SELECT event_id FROM events WHERE event_id > 799980 ORDER BY event_id LIMIT 20'
print(plan(conn, offset_sql))
print(plan(conn, keyset_sql))
print(conn.execute(offset_sql).fetchall() == conn.execute(keyset_sql).fetchall())
print('keyset is more than 100x faster:', best_time(conn, offset_sql) / best_time(conn, keyset_sql) > 100)
# ['SCAN events']
# ['SEARCH events USING INTEGER PRIMARY KEY (rowid>?)']
# True
# keyset is more than 100x faster: True
```

Same twenty rows, a very different amount of work. A function that pages through the table remembers the last id it returned:

```py
def next_page(conn, last_id, size=3):
    return conn.execute(
        'SELECT event_id, user_id, event_type FROM events WHERE event_id > ? ORDER BY event_id LIMIT ?',
        (last_id, size),
    ).fetchall()

last = 0
for _ in range(3):
    page = next_page(conn, last)
    print(page)
    last = page[-1][0]
# [(1, 33474, 'view'), (2, 6998, 'view'), (3, 31045, 'view')]
# [(4, 48674, 'click'), (5, 6351, 'view'), (6, 9769, 'view')]
# [(7, 24359, 'view'), (8, 12571, 'click'), (9, 29392, 'purchase')]
```

The trade-offs: you can go "next" (and "previous", with the opposite comparison) but not jump to "page 7,000" directly, and the sort key must be **unique**. If you sort by a non-unique column such as `ts`, use a pair `(ts, event_id)` as the key:
`WHERE (ts, event_id) > (?, ?) ORDER BY ts, event_id` (SQLite supports comparing tuples, called row values). `OFFSET` is fine for small tables and for "page 1 to 5"; keyset is for big tables and infinite scroll.

## Bonus: Full-Text Search with FTS5

*Optional. Nothing later depends on it.*

Searching text for a word with `LIKE '%python%'` has two problems: it scans every row (a leading wildcard cannot use an index), and it matches *parts* of words (`LIKE '%rust%'` also finds "trust" and "frustrating").
SQLite ships a full-text search engine, **FTS5**. A *virtual table* keeps an index of every word, and `MATCH` looks words up in it.

```sql
-- syntax
CREATE VIRTUAL TABLE table_name USING fts5(column1, column2, ...);
SELECT ... FROM table_name WHERE table_name MATCH 'query';
```

```py
hn = sqlite3.connect('00_practice/datasets.db')            # the Day 3 database with the hn_posts table
hn.execute('CREATE VIRTUAL TABLE hn_fts USING fts5(title)')
hn.execute('INSERT INTO hn_fts (rowid, title) SELECT id, title FROM hn_posts')      # copy the titles, keeping the id as rowid
print(hn.execute('SELECT COUNT(*) FROM hn_fts').fetchone())
like = hn.execute("SELECT COUNT(*) FROM hn_posts WHERE title LIKE '%python%' OR title LIKE '%rust%'").fetchone()
fts = hn.execute("SELECT COUNT(*) FROM hn_fts WHERE hn_fts MATCH 'python OR rust'").fetchone()
print('LIKE:', like, 'FTS5:', fts)
# (20099,)
# LIKE: (265,) FTS5: (207,)
```

The counts differ because `LIKE` found `trust`, `frustrated`, `Pythonic` and friends, while FTS5 matches whole words (case-insensitively). The query language supports `OR`, `AND`, `NOT`, phrases in double quotes and prefixes (`pyth*`). Next, **ranking** with `bm25()` (smaller, more negative, means more relevant)
and **highlighting** the hit with `highlight()`:

```py
show(hn.execute("""
    SELECT hn_posts.title, round(bm25(hn_fts), 2) AS score
    FROM hn_fts JOIN hn_posts ON hn_posts.id = hn_fts.rowid
    WHERE hn_fts MATCH 'python OR rust'
    ORDER BY bm25(hn_fts), hn_posts.id
    LIMIT 5
"""))
print(hn.execute("SELECT highlight(hn_fts, 0, '[', ']') FROM hn_fts WHERE hn_fts MATCH 'rust' ORDER BY rowid LIMIT 2").fetchall())
```

```sh
output
title                                        score
-------------------------------------------  -----
Intellij-Rust Rust Plugin for IntelliJ IDEA  -8.36
Rust Mutation Testing                        -7.86
Alternative Rust Compiler                    -7.86
Ceph Rust Plugin                             -7.86
See Python, See Python Go, Go Python Go      -7.78
(5 rows)
[('Asynchronous IO in [Rust]',), ('Announcing [Rust] 1.3',)]
```

Shorter titles where the word matters more rank higher. FTS5 is also much faster than `LIKE` on large text tables, because it looks words up instead of scanning. The cost: the FTS table is a separate copy of the text that you must keep up to date (triggers, next lesson,
are the usual way).

**In other databases:** PostgreSQL has `tsvector` / `to_tsquery` and GIN indexes, MySQL has `FULLTEXT` indexes with `MATCH ... AGAINST`, SQL Server has full-text catalogs. DuckDB has an FTS extension.

You can now look inside a query, see what it costs, and make it a thousand times faster with one line. This single skill separates people who write SQL from people who can be trusted with a production database.

## Exercises: Day 21

### Exercises: Level 1

Use your `00_practice/events.db`. All timings in these exercises vary by machine: **check the plan, and compare ratios on your own machine**.

1. Generate `data/big_events.csv` with `tools/make_big_events.py` (skip if it exists). With `pathlib`, print whether the file exists and whether it is larger than 40 MB. Expected: `True True`.
2. Create `00_practice/events.db` with the `events` table (as in the lesson, `STRICT`, `amount_cents` as integer cents) and load the file in batches of 50,000. Print the row count and the first row by `event_id`.

   ```sh
   (1000000,)
   (1, 33474, 'view', '2025-01-01 00:00:26', None)
   ```

3. Count the events of user `12345` and sum their `amount_cents`. Expected: `(18, 89299)`.
4. Print the query plan of that query. Expected: `['SCAN events']`.
5. Time the query with `time.perf_counter()` (best of 3). Print the time in milliseconds.
6. Create an index `idx_events_user` on `user_id` and print the plan again. Expected: `['SEARCH events USING INDEX idx_events_user (user_id=?)']`.
7. Time the query again and print whether it became at least 100 times faster. (Expected `True`.)
8. Print the result of `PRAGMA index_list('events')`. Expected: `[(0, 'idx_events_user', 0, 'c', 0)]`.
9. Print the plan for `SELECT * FROM events WHERE event_id = 500000`. Why does it use no index you created? Expected: `['SEARCH events USING INTEGER PRIMARY KEY (rowid=?)']`.
10. Count events per `event_type`, most frequent first, ties by name, and print the plan of the grouping query.

    ```sh
    event_type   n
    -----------  ------
    view         549469
    click        250602
    add_to_cart  120086
    purchase     69991
    refund       9852
    (5 rows)
    ['SCAN events', 'USE TEMP B-TREE FOR GROUP BY']
    ```

11. Drop `idx_events_user` and create it again with `IF NOT EXISTS`; run the `CREATE` twice and note that the second does nothing. List the index names from `sqlite_master`. Expected: `[('idx_events_user',)]`.
12. In an in-memory database, create a table `people (id INTEGER PRIMARY KEY, email TEXT)`, add a `UNIQUE` index on `email`, insert the same email twice and catch the error. Expected: `IntegrityError: UNIQUE constraint failed: people.email`.
13. In your own words: what is the difference between `SCAN` and `SEARCH` in a query plan?
14. On the normalized library (Day 10), print the plan of `SELECT id, book_id FROM loans WHERE member_id = 1`. Create indexes on `loans(member_id)` and `loans(book_id)` and print the plan again.

    ```sh
    ['SCAN loans']
    ['SEARCH loans USING INDEX idx_loans_member (member_id=?)']
    ```

    (Name them `idx_loans_member` and `idx_loans_book`.)
15. In your own words: why is it usually a good idea to index a foreign key column such as `loans.member_id`? (Two reasons: joins, and what SQLite must do when you delete a parent row.)

### Exercises: Level 2

Replace the single-column index by `CREATE INDEX idx_events_user_ts ON events (user_id, ts)` and, where a question says so, add more.

1. **Which queries use the composite index?** Print the first plan line for each of these five queries, and say which could not use it as a search.

   ```
   user_id =                 WHERE user_id = 777
   user_id = and ts range    WHERE user_id = 777 AND ts >= '2025-06-01'
   user_id = order by ts     WHERE user_id = 777 ORDER BY ts
   ts range only             WHERE ts >= '2025-06-01' AND ts < '2025-06-02'
   event_type =              WHERE event_type = 'refund'
   ```

   (Each is `SELECT event_id FROM events ...`.)

   ```sh
   user_id =                SEARCH events USING COVERING INDEX idx_events_user_ts (user_id=?)
   user_id = and ts range   SEARCH events USING COVERING INDEX idx_events_user_ts (user_id=? AND ts>?)
   user_id = order by ts    SEARCH events USING COVERING INDEX idx_events_user_ts (user_id=?)
   ts range only            SCAN events USING COVERING INDEX idx_events_user_ts
   event_type =             SCAN events
   ```

2. **LIKE cannot use it.** Create `idx_events_ts` on `ts`. Print the first plan line of four queries that count the events on 2025-06-01: with `ts LIKE '2025-06-01%'`, with `ts LIKE '%01'`, with `ts GLOB '2025-06-01*'`, and with a range (`ts >= '2025-06-01' AND ts < '2025-06-02'`). Also check that the `LIKE` and `GLOB` versions return the same count. Explain why `LIKE 'x%'` still scans.

   ```sh
   ts LIKE 'x%'   SCAN events USING COVERING INDEX idx_events_ts
   ts LIKE '%x'   SCAN events USING COVERING INDEX idx_events_ts
   ts GLOB 'x*'   SEARCH events USING COVERING INDEX idx_events_ts (ts>? AND ts<?)
   range          SEARCH events USING COVERING INDEX idx_events_ts (ts>? AND ts<?)
   (2703,) (2703,)
   ```

3. **Covering.** Print the plan of `SELECT user_id, ts FROM events WHERE user_id = 777` and `SELECT * FROM events WHERE user_id = 777`. Which one says `COVERING`, and why?

   ```sh
   user_id, ts  SEARCH events USING COVERING INDEX idx_events_user_ts (user_id=?)
   *            SEARCH events USING INDEX idx_events_user_ts (user_id=?)
   ```

4. **Partial index.** Create `idx_purchases_user` on `user_id` only for purchases. Print the plan of a purchase count for user 777, then of the same count for `'view'` events, then the count of purchases (expected `(4,)`).

   ```sh
   SEARCH events USING COVERING INDEX idx_purchases_user (user_id=?)
   SEARCH events USING INDEX idx_events_user_ts (user_id=?)
   (4,)
   ```

5. **Expression index.** `SELECT COUNT(*) FROM events WHERE date(ts) = '2025-06-01'` scans. Create an index that fixes it, print the plan before and after, and the count.

   ```sh
   SCAN events USING COVERING INDEX idx_events_ts
   SEARCH events USING INDEX idx_events_date (<expr>=?)
   (2703,)
   ```

6. **Indexes slow writes down.** Read 200,000 rows from `events`. Insert them into an empty in-memory table of the same shape (a) with no indexes, (b) with three indexes (`user_id`; `ts`; `event_type, user_id`), timing each insert. Print whether (b) took longer and whether it took more than 1.5 times as long. Expected: `True` and `True`.

7. **ANALYZE.** Run `ANALYZE` and print the contents of `sqlite_stat1` for the three indexes `idx_events_date`, `idx_events_ts`, `idx_events_user_ts`. In your own words, what does `1000000 20 1` mean for `idx_events_user_ts`?

   ```sh
   idx                 stat
   ------------------  ------------
   idx_events_date     1000000 2740
   idx_events_ts       1000000 1
   idx_events_user_ts  1000000 20 1
   (3 rows)
   ```

8. **Keyset pagination.** Write `next_page(conn, last_id, size=3)` that returns `(event_id, user_id, event_type)` for the rows after `last_id`. Print three consecutive pages, starting after id 0.

   ```sh
   [(1, 33474, 'view'), (2, 6998, 'view'), (3, 31045, 'view')]
   [(4, 48674, 'click'), (5, 6351, 'view'), (6, 9769, 'view')]
   [(7, 24359, 'view'), (8, 12571, 'click'), (9, 29392, 'purchase')]
   ```

### Exercises: Level 3

1. **Five slow queries.** Drop the indexes you made in Level 2. For each query below, (1) confirm that the plan starts with `SCAN events`, (2) design **one** index that fixes it, named `idx_q1` to `idx_q5`, (3) print the plan after, and (4) check that the query became at least 10 times faster (best of 3). Drop each index after testing it, so they do not help each other.
   Print one row per query in the format shown. The timings vary, so the table only shows whether the speedup passed 10x; **your index design is checked by the `plan after` column**.

   ```
   Q1  all events of user 777, in time order:            SELECT event_id, ts FROM events WHERE user_id = 777 ORDER BY ts
   Q2  number of events on 2025-03-14:                   SELECT COUNT(*) FROM events WHERE date(ts) = '2025-03-14'
   Q3  count and total of refunds during March 2025:     SELECT COUNT(*), SUM(amount_cents) FROM events
                                                         WHERE event_type = 'refund' AND ts >= '2025-03-01' AND ts < '2025-04-01'
   Q4  the latest purchase of user 777:                  SELECT event_id, ts FROM events
                                                         WHERE user_id = 777 AND event_type = 'purchase' ORDER BY ts DESC LIMIT 1
   Q5  which event types user 777 has produced:          SELECT DISTINCT event_type FROM events WHERE user_id = 777
   ```

   ```sh
   query                plan after                                                               faster
   Q1 user 777 by time  SEARCH events USING COVERING INDEX idx_q1 (user_id=?)                    >10x
   Q2 events on a day   SEARCH events USING INDEX idx_q2 (<expr>=?)                              >10x
   Q3 March refunds     SEARCH events USING INDEX idx_q3 (event_type=? AND ts>? AND ts<?)        >10x
   Q4 last purchase     SEARCH events USING COVERING INDEX idx_q4 (user_id=? AND event_type=?)   >10x
   Q5 types for a user  SEARCH events USING COVERING INDEX idx_q5 (user_id=?)                    >10x
   ```

   (Hints, one per query in order: composite `(user_id, ts)`; expression index on `date(ts)`; equality column first, then the range column; equality columns first, then the `ORDER BY` column; and a composite that already contains every column the query reads. Other designs can also pass: if your plan differs but says `SEARCH` and the speedup holds, that is a valid answer.)

2. **Offset versus keyset.** Write `page_offset(conn, page, size=20)` and `page_keyset(conn, last_id, size=20)`. Get page 40,000 of size 20 (event ids 799,981 to 800,000) both ways, check the results are equal, print the first and last row, and check that the keyset version is more than 100 times faster. Print both plans. (You promised yourself this on Day 4.)

   ```sh
   True (799981,) (800000,)
   keyset is more than 100x faster: True
   ['SCAN events']
   ['SEARCH events USING INTEGER PRIMARY KEY (rowid>?)']
   ```

3. **Bonus: FTS5.** Build an FTS5 table over the titles of `hn_posts`. Compare the number of posts found by `LIKE '%python%' OR LIKE '%rust%'` and by `MATCH 'python OR rust'` and explain the difference. List the five most relevant titles by `bm25()` (ties by post id) with their scores rounded to 2 decimals, and show the first two hits for `rust` with the word highlighted using square brackets. Finally check that the FTS5 query is faster than the `LIKE` query.

   ```sh
   (20099,)
   LIKE: (265,) FTS5: (207,)
   title                                        score
   -------------------------------------------  -----
   Intellij-Rust Rust Plugin for IntelliJ IDEA  -8.36
   Rust Mutation Testing                        -7.86
   Alternative Rust Compiler                    -7.86
   Ceph Rust Plugin                             -7.86
   See Python, See Python Go, Go Python Go      -7.78
   (5 rows)
   [('Asynchronous IO in [Rust]',), ('Announcing [Rust] 1.3',)]
   FTS5 faster than LIKE: True
   ```

CONGRATULATIONS !

[<< Day 20](../20_Day_Import_clean_export/20_import_clean_export.md) | [Day 22 >>](../22_Day_Views_and_triggers/22_views_and_triggers.md)
