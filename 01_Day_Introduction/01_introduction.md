<div align="center">
  <h1> 30 Days Of SQL: Day 1 - Introduction</h1>
</div>

[Day 2 >>](../02_Day_Creating_tables/02_creating_tables.md)

- [Day 1](#day-1)
  - [Welcome](#welcome)
  - [What is a Database?](#what-is-a-database)
  - [The Relational Model](#the-relational-model)
  - [What is SQL?](#what-is-sql)
  - [SQLite and DuckDB](#sqlite-and-duckdb)
  - [Environment Setup](#environment-setup)
    - [Checking Your SQLite Version](#checking-your-sqlite-version)
  - [Your First Query](#your-first-query)
    - [Connection and Cursor](#connection-and-cursor)
    - [Fetching Results](#fetching-results)
    - [Doing Math in SQL](#doing-math-in-sql)
    - [Strings in SQL](#strings-in-sql)
    - [Several Values at Once](#several-values-at-once)
    - [The Shortcut: conn.execute](#the-shortcut-connexecute)
  - [Databases That Live in Files](#databases-that-live-in-files)
  - [Comments](#comments)
  - [Reading Error Messages](#reading-error-messages)
  - [How This Course Works](#how-this-course-works)
  - [ Exercises: Day 1](#exercises-day-1)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)

# Day 1

## Welcome

Welcome to **30 Days Of SQL**. You will learn how to store, find and analyse data with SQL, and you will do it all from
Python. If you know basic Python (functions, loops, lists, dictionaries and `try`/`except`), you already have everything you need.

The course works the same way as the Python one: short explanations, runnable examples, and exercises at three levels.
"30 days" is a guide, not a deadline. A "day" is one lesson, so go at your own pace.

## What is a Database?

A **database** is an organised collection of data that a program can search and change quickly and safely.

You already store data in Python, in lists and dictionaries, and in files such as CSV and JSON. So why use a database?
Think of a spreadsheet. It works well until:

- the data gets big (a million rows is slow to scan from a CSV file every time),
- two people or programs change it at the same time,
- you need to make sure a column only holds valid values (no text in the "age" column),
- you need rows in one sheet to point at rows in another ("this order belongs to that customer"),
- a change must either fully happen or not happen at all (money leaves one account **and** arrives in another).

A database is built to handle exactly these problems.

## The Relational Model

Most databases you will meet are **relational**. Data lives in **tables**. A table has:

- **columns**, which define what you store (a name, a price, a date), and each column has a type,
- **rows**, where each row is one record.

```sh
students
 id | name  | age | city
----+-------+-----+---------
  1 | Ana   |  21 | Toronto
  2 | Ben   |  23 | London
  3 | Cy    |  22 | Toronto
```

Tables are connected to each other by values they share. An `orders` table might hold a `customer_id`, which points at a row in
the `customers` table. That connection between tables is the "relation" in "relational", and it is the subject of Days 10 to 12.

## What is SQL?

**SQL** (Structured Query Language, often pronounced "sequel" or "S-Q-L") is the language you use to talk to a relational
database. It has been used for about fifty years and is still the most common way to work with data.

SQL is **declarative**: you describe *what* you want, and the database works out *how* to get it. Compare these two ways of
finding the students who scored at least 75:

```py
# Python: imperative, you spell out every step
scores = [('Ana', 82), ('Ben', 67), ('Cy', 91), ('Di', 74)]
passed = []
for name, score in scores:
    if score >= 75:
        passed.append(name)
print(passed)           # ['Ana', 'Cy']
```

```sql
-- SQL: declarative, you describe the result
SELECT name FROM scores WHERE score >= 75;
```

You never write the loop. The database decides how to look through the data, and when the data gets large it can choose a
much faster way than a loop. That is why SQL is so useful.

## SQLite and DuckDB

SQL is a language, and many programs ("database engines") understand it. This course uses two:

- **SQLite** comes built into Python (the `sqlite3` module). The whole database lives in a single file, or in memory, and
  there is no server to install. It is the most widely used database in the world: your phone, your browser and many apps use it
  to store their data. It is designed for **storing and changing** data (OLTP: many small reads and writes). We use it for Days 1 to 22.
- **DuckDB** is a newer engine designed for **analysing** data (OLAP: big queries that scan millions of rows). It can query CSV
  and Parquet files directly and works well with pandas. We use it from Day 23.

Most of the SQL you learn works in both, and in most other databases too. When a feature differs between databases you will see
a ** In other databases** note.

## Environment Setup

Install [uv](https://docs.astral.sh/uv/) and set up the course (the [readme](../readme.md) has the commands). You will run your
code with `uv run`, for example:

```sh
uv run python 00_practice/day_1.py
```

Python also ships with a small interactive SQLite shell. It is handy for trying a query quickly:

```sh
uv run python -m sqlite3
```

```sh
sqlite> SELECT 1 + 1;
(2,)
sqlite> .quit
```

> **Tool tip:** if you prefer a visual tool, the "SQLite Viewer" extension for VS Code lets you open `.db` files and browse their
> tables. You never need it for this course.

### Checking Your SQLite Version

Python bundles its own copy of SQLite, and its version depends on your Python install. Some features need a recent version
(for example `RIGHT JOIN` and `FULL JOIN` need 3.39 or newer). Check yours:

```py
import sqlite3

print(sqlite3.sqlite_version)         # 3.45.1
print(sqlite3.sqlite_version_info)    # (3, 45, 1)
```

If yours is older than 3.39, most of the course still works. Day 12 will tell you which parts need a newer version.

## Your First Query

### Connection and Cursor

To talk to a database from Python you need two objects:

- a **connection**, which is the open line to the database,
- a **cursor**, which sends SQL over that connection and holds the results.

```py
# syntax
conn = sqlite3.connect(database)
cur = conn.cursor()
cur.execute('SQL STATEMENT')
```

`':memory:'` is a special name that gives you a temporary database that lives in RAM and disappears when your program ends. It is
perfect for practice.

```py
import sqlite3

conn = sqlite3.connect(':memory:')
cur = conn.cursor()
cur.execute('SELECT 1 + 1')
```

### Fetching Results

`execute` runs the query, but the answer waits inside the cursor until you ask for it. `fetchone()` gives you the next row, and
`fetchall()` gives you every remaining row.

```py
cur.execute('SELECT 1 + 1')
print(cur.fetchone())      # (2,)
```

Notice that the result is a **tuple**, `(2,)`, even though there is only one value. Every row comes back as a tuple, with one item
per column. You will use tuple indexing and unpacking constantly.

```py
row = cur.execute('SELECT 2 + 3').fetchone()
print(row)        # (5,)
print(row[0])     # 5
```

`execute` returns the cursor itself, so you can chain `.fetchone()` straight onto it, as above.

### Doing Math in SQL

A `SELECT` does not need a table. It can evaluate any expression, which makes it a calculator.

```py
print(cur.execute('SELECT 10 - 4').fetchone())       # (6,)
print(cur.execute('SELECT 2 * 3').fetchone())        # (6,)
print(cur.execute('SELECT 7 % 3').fetchone())        # (1,)  the remainder
```

**Common mistake: integer division.** If both numbers are integers, SQLite gives an integer back and throws the decimals
away. Make one of them a decimal to get a decimal result.

```py
print(cur.execute('SELECT 10 / 3, 10 / 3.0').fetchone())   # (3, 3.3333333333333335)
```

> **In other databases:** PostgreSQL and SQL Server also do integer division for `10 / 3`. MySQL and DuckDB return `3.3333`. Never
> rely on it without checking, and write `10 / 3.0` when you mean decimals.

### Strings in SQL

Text goes in **single quotes**. Double quotes are for column and table names. The `||` operator joins two strings.

```py
print(cur.execute("SELECT 'Hello, SQL'").fetchone())          # ('Hello, SQL',)
print(cur.execute("SELECT 'SQL' || ' is fun'").fetchone())     # ('SQL is fun',)
```

### Several Values at Once

Separate expressions with commas to get several columns in one row. Tuple unpacking then makes the result easy to use.

```py
a, b, c = cur.execute("SELECT 2 * 3, 'a' || 'b', 10 - 4").fetchone()
print(a, b, c)      # 6 ab 6
```

### The Shortcut: conn.execute

The connection has its own `execute` method that creates a cursor for you. For quick one-off queries it saves a line:

```py
print(conn.execute('SELECT 1 + 1').fetchone())      # (2,)
```

We will use `conn.execute(...)` for short queries and an explicit cursor when we loop over results.

## Databases That Live in Files

A database in memory disappears when your program ends. To keep your data, give `connect` a **file name** instead. If the file
does not exist, SQLite creates it.

```py
from pathlib import Path
import sqlite3

db_path = Path('demo.db')
print(db_path.exists())      # False

conn = sqlite3.connect(db_path)
print(db_path.exists())      # True
conn.close()
```

In SQLite a database simply *is* a file. That is why there is no `CREATE DATABASE` statement here: `connect()` creates it, and
deleting the file deletes it. Copying the file copies the whole database, which makes SQLite very easy to back up and share.

> **In other databases:** PostgreSQL, MySQL and SQL Server run as separate servers. There you do write `CREATE DATABASE shop;`
> and `DROP DATABASE shop;`. DuckDB works like SQLite: one file per database.

Always close a connection when you are done with it using `conn.close()`. Later you will see tidier ways to do this.

## Comments

Comments are notes for humans. SQL ignores them.

```sql
-- a single line comment

/* a comment
   that spans several lines */
SELECT 5; -- a comment after code
```

```py
conn = sqlite3.connect(':memory:')       # a fresh connection: the previous one was closed
print(conn.execute("SELECT 5 -- five").fetchone())                     # (5,)
print(conn.execute("SELECT 5 /* a block comment */ + 1").fetchone())   # (6,)
```

SQL keywords are **not case sensitive**: `select`, `Select` and `SELECT` all work. The common style, and the one we use, is
UPPERCASE for keywords and `snake_case` for table and column names. It makes queries easier to read.

## Reading Error Messages

You will write queries that fail. That is normal. Python raises a `sqlite3.Error` (or a subclass) and the message tells you what is wrong.

```py
try:
    conn.execute('SELEC 1')
except sqlite3.Error as e:
    print(type(e).__name__, e)      # OperationalError near "SELEC": syntax error

try:
    conn.execute('SELECT * FROM nope')
except sqlite3.Error as e:
    print(type(e).__name__, e)      # OperationalError no such table: nope
```

Read the message from the start: it names the table or word that confused SQLite. Python's `try`/`except` is how you catch them, and we
will use it a lot.

## How This Course Works

- Put your practice code in `00_practice/day_1.py`, `day_2.py` and so on.
- Read a section, type the examples yourself (don't just read them!) and change them to see what happens.
- Every day ends with exercises. Level 1 is quick practice, Level 2 combines ideas, and from Day 3 on, Level 3 uses real data
  and shows the output your code should produce.
- Several exercises build one project, a small library database, from Day 2 to Day 10. Keep your database file.
- A reference answer for every exercise is in `solutions/`. Try first, peek later.

You have written your first SQL and run it from Python. You are on your way to greatness! Now do some exercises.

## Exercises: Day 1

### Exercises: Level 1

1. Import `sqlite3` and print the SQLite version.
2. Print `True` or `False` for whether your SQLite version is at least 3.39. (Hint: compare `sqlite3.sqlite_version_info` with a tuple.)
3. Connect to an in-memory database and create a cursor.
4. Use the cursor to run `SELECT 2 + 3` and print the result of `fetchone()`.
5. Select the text `Hello, SQL` and print only the string, not the tuple.
6. In a single query select `10 / 3` and `10 / 3.0`. Explain the difference between the two results.
7. Select the remainder of `17 % 5`.
8. Select `6 * 7` and `100 - 58` in one query and unpack the result into two variables, then print them.
9. Join the strings `'SQL'` and `' is fun'` with `||`.
10. Run `SELECT 1 + 1` using the `conn.execute` shortcut instead of a cursor.
11. Run a query that contains both a `--` comment and a `/* */` comment, and check it still returns the right answer.
12. Create a database file named `library.db` inside the `00_practice` folder and use `pathlib` to check that the file exists. Close the connection.
13. Run the misspelled query `SELEKT 1`, catch the error, and print its type and message.
14. Run `uv run python -m sqlite3` in your terminal, run `SELECT 6 * 7;`, then leave with `.quit`.

### Exercises: Level 2

1. In your own words, explain the difference between *declarative* and *imperative* code. Then, for this list, write the
   Python loop and the SQL query that find the students who scored **above 70**:

   ```py
   scores = [('Ana', 82), ('Ben', 67), ('Cy', 91), ('Di', 74), ('Eli', 70)]
   ```

   (To run the SQL you need a table. Use this in-memory setup, we will explain it on Day 2 and Day 3:)

   ```py
   conn.execute('CREATE TABLE scores (name TEXT, score INTEGER)')
   conn.executemany('INSERT INTO scores VALUES (?, ?)', scores)
   ```

   Both approaches should print `['Ana', 'Cy', 'Di']`.

2. Use one `SELECT` with arithmetic only to find: the number of seconds in a week, the hours in a leap year (366 days), and the
   minutes in a day. Print them in a sentence.

   ```sh
   A week has 604800 seconds, a leap year has 8784 hours and a day has 1440 minutes.
   ```

3. Why does `SELECT 10 / 4` return `2`? Write a query that returns `2.5` without typing a decimal point anywhere. (Hint: multiply by `1.0`.)

4. SQL keywords are not case sensitive. Run `select 1+1`, `Select 1 + 1` and `SELECT 1+1` and show that they return the same
   result. Then explain, in one sentence, why most people still write keywords in uppercase.

5. Write a function `scalar(conn, sql)` that runs a query and returns just the first value of the first row (not the tuple).
   Test it with `scalar(conn, 'SELECT 6 * 7')`, which should return `42`.

CONGRATULATIONS !

[Day 2 >>](../02_Day_Creating_tables/02_creating_tables.md)
