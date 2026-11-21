<div align="center">
  <h1> 30 Days Of SQL: Day 2 - Creating Tables & Data Types</h1>
</div>

[<< Day 1](../01_Day_Introduction/01_introduction.md) | [Day 3 >>](../03_Day_Inserting_data/03_inserting_data.md)

- [Day 2](#day-2)
  - [Creating Tables](#creating-tables)
    - [CREATE TABLE](#create-table)
    - [Data Types in SQLite](#data-types-in-sqlite)
    - [Type Affinity: SQLite Is Flexible](#type-affinity-sqlite-is-flexible)
    - [STRICT Tables](#strict-tables)
    - [NOT NULL and DEFAULT](#not-null-and-default)
    - [Primary Keys](#primary-keys)
    - [AUTOINCREMENT](#autoincrement)
    - [IF NOT EXISTS and DROP TABLE](#if-not-exists-and-drop-table)
  - [Changing a Table](#changing-a-table)
    - [Adding, Renaming and Dropping Columns](#adding-renaming-and-dropping-columns)
    - [Generated Columns](#generated-columns)
  - [Looking at a Table's Structure](#looking-at-a-tables-structure)
    - [sqlite_master](#sqlite_master)
    - [PRAGMA table_info](#pragma-table_info)
  - [Money and Decimal Precision](#money-and-decimal-precision)
  - [ Exercises: Day 2](#exercises-day-2)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)

# Day 2

## Creating Tables

A table is where data lives, so before you can store anything you must describe the table: its name, and the name and
type of each column. That description is called the **schema**.

### CREATE TABLE

```sql
-- syntax
CREATE TABLE table_name (
    column1 type,
    column2 type,
    ...
);
```

```py
import sqlite3

conn = sqlite3.connect(':memory:')
conn.execute('''
    CREATE TABLE fruits (
        id       INTEGER PRIMARY KEY,
        name     TEXT NOT NULL,
        price    REAL,
        in_stock INTEGER DEFAULT 1
    )
''')
```

Triple-quoted strings let you spread SQL over several lines, which is how we write anything longer than a few words.
A `CREATE TABLE` statement returns no rows. It just changes the database.

<br>

### Data Types in SQLite

SQLite stores every value as one of five **storage classes**:

| Storage class | What it holds | Python equivalent |
|---|---|---|
| `NULL` | no value / unknown | `None` |
| `INTEGER` | whole numbers | `int` |
| `REAL` | decimal numbers (floating point) | `float` |
| `TEXT` | strings | `str` |
| `BLOB` | raw bytes, stored exactly as given | `bytes` |

The function `typeof()` tells you which class a value has:

```py
print(conn.execute("SELECT typeof(1), typeof(1.5), typeof('a'), typeof(NULL), typeof(x'FF')").fetchone())
# ('integer', 'real', 'text', 'null', 'blob')
```
SQLite has no real `BOOLEAN` or `DATE` type. Use `INTEGER` with `0` and `1` for booleans. For dates, use `TEXT` in the
format `'2025-03-14'` (Day 16 explains why).

<br>

You may still see `DATE`, `TIME`, `DATETIME`, `TIMESTAMP`, `BOOLEAN` or `VARCHAR(10)` in a `CREATE TABLE`, and SQLite
accepts them in a normal table. But they are only **labels**: the column keeps the name you typed, SQLite stores
whatever you insert as text, integer or real, and it checks nothing.

A quick word on `INSERT`, since the examples from here on use it and Day 3 explains it properly.
`INSERT INTO table VALUES (a, b, c)` adds one **row** to a table, with the values in the same order as the table's
columns. `conn.execute(...)` is how Python sends the statement to SQLite. Later examples also use `executemany` with `?`
placeholders, which adds many rows in one call. For now, read each `INSERT` as "add this row".

```py
conn.execute('CREATE TABLE labels (d DATE, name VARCHAR(10), done BOOLEAN)')
conn.execute("INSERT INTO labels VALUES ('not a date at all', 'a name much longer than ten characters', 'maybe')")
print(conn.execute('SELECT d, typeof(d), length(name), typeof(done) FROM labels').fetchone())
# ('not a date at all', 'text', 38, 'text')
```

<br>

The nonsense date went in, and the `10` in `VARCHAR(10)` did nothing. So is `DATE` just a readable comment? Almost, but
not quite: a label like `DATE`, `TIME`, `DATETIME` or `TIMESTAMP` gives the column **numeric** affinity (explained
next), which means text that *looks like a number* is converted:

```py
conn.execute('CREATE TABLE stamps (d DATE, t TIME, plain TEXT)')
conn.execute("INSERT INTO stamps VALUES ('2025-03-14', '12:30', '2025-03-14')")
conn.execute("INSERT INTO stamps VALUES ('20250314', '07', '20250314')")
print(conn.execute('SELECT d, typeof(d), t, typeof(t), plain, typeof(plain) FROM stamps').fetchall())
# [('2025-03-14', 'text', '12:30', 'text', '2025-03-14', 'text'), (20250314, 'integer', 7, 'integer', '20250314', 'text')]
```

<br>

A properly formatted ISO date stays text, but `'20250314'` became the integer `20250314` and the time `'07'` lost its
leading zero. A plain `TEXT` column kept both values exactly as typed. That is why this course uses `TEXT` for dates and
times. If you want the reader to see the intent, say it in a comment or in the column name (`due_on`, `created_at`), and
let `STRICT` plus a `CHECK` do the checking.

The next section explains why, and `STRICT` (below) refuses these labels altogether.

<br>

### Type Affinity: SQLite Is Flexible

Here is something that surprises people coming from other databases. In SQLite, the type you write for a column is only
a *preference*, called an **affinity**. SQLite will try to convert a value to that type, and if it cannot, **it stores
the value as it is**.

```py
conn.execute('CREATE TABLE loose (n INTEGER)')
conn.executemany('INSERT INTO loose VALUES (?)', [(5,), ('7',), ('abc',), (2.5,), (3.0,)])
print(conn.execute('SELECT n, typeof(n) FROM loose').fetchall())
# [(5, 'integer'), (7, 'integer'), ('abc', 'text'), (2.5, 'real'), (3, 'integer')]
```

The text `'abc'` went straight into an `INTEGER` column without a complaint. The text `'7'` was converted to the integer
`7`, and `3.0` became `3`. This flexibility is a feature of SQLite, but it also lets bad data in quietly.

<br>

### STRICT Tables

Add the keyword `STRICT` after the closing bracket and SQLite enforces the types:

```py
conn.execute('CREATE TABLE tight (n INTEGER) STRICT')

try:
    conn.execute("INSERT INTO tight VALUES ('abc')")
except sqlite3.Error as e:
    print(type(e).__name__, e)      # IntegrityError cannot store TEXT value in INTEGER column tight.n
```

<br>

A strict table still converts values when it can do so without losing anything (`'7'` becomes `7`), but it rejects the
rest.

```py
conn.execute("INSERT INTO tight VALUES ('7')")
print(conn.execute('SELECT n, typeof(n) FROM tight').fetchall())      # [(7, 'integer')]
```

<br>

STRICT tables only allow the types `INTEGER`, `REAL`, `TEXT`, `BLOB` (and `ANY`). Anything else is an error:

```py
try:
    conn.execute('CREATE TABLE bad (x DATE) STRICT')
except sqlite3.Error as e:
    print(type(e).__name__, e)      # OperationalError unknown datatype for bad.x: "DATE"
```

<br>

**We use `STRICT` for the tables we design from now on.** It catches mistakes early, and it makes SQLite behave more
like the other databases you will meet. `STRICT` needs SQLite 3.37 or newer.

> **In other databases:** PostgreSQL, MySQL and SQL Server always enforce types, and they have many more of them
> (`VARCHAR(50)`, `DATE`, `BOOLEAN`, `DECIMAL(10, 2)` and so on). DuckDB too. SQLite is the odd one out, which is why
> `STRICT` exists.
>
> The same type name can mean different things. `TEXT` is the right string type in SQLite, and in PostgreSQL (where it
> has no length limit). In DuckDB `TEXT` is just another name for `VARCHAR`. In MySQL, `TEXT` is a separate large-object
> type, so short strings usually use `VARCHAR(n)`. In SQL Server the old `text` and `ntext` types are deprecated, and
> you use `varchar(max)` or `nvarchar(max)` for long strings. Day 30 has a translation table.

<br>

### NOT NULL and DEFAULT

Recall how our `fruits` table was constructed:

```py
conn.execute('''
    CREATE TABLE fruits (
        id       INTEGER PRIMARY KEY,
        name     TEXT NOT NULL,
        price    REAL,
        in_stock INTEGER DEFAULT 1
    )
''')
```

Now imagine a fruit is inserted into it:

```py
conn.execute("INSERT INTO fruits (name) VALUES ('kiwi')")
print(conn.execute('SELECT * FROM fruits').fetchall())
# [(1, 'kiwi', None, 1)]      price was not given, so it is NULL; in_stock took its DEFAULT of 1
```

That row came from how our `fruits` table (created at the top of this day) sets each column:

- `name` is `NOT NULL` and has no default, so every insert must give a name. We gave `'kiwi'`.
- `in_stock` has `DEFAULT 1`. We did not mention it, so it took the default `1`.
- `price` has **neither** rule. We did not mention it, so it is `NULL`.
- `id` is the primary key, which SQLite numbers for you (see Primary Keys below), so it became `1`.

<br>

By default any column may hold `NULL`, meaning "no value". Two column rules control that:

- `NOT NULL`: the column must always have a value.
- `DEFAULT value`: the value to use when an insert does not mention the column.

<br>

An example of an insert that fails:

```py
try:
    conn.execute('INSERT INTO fruits (price) VALUES (1.0)')
except sqlite3.Error as e:
    print(type(e).__name__, e)      # IntegrityError NOT NULL constraint failed: fruits.name
```

This insert gave only a `price`, so `name` would have been `NULL`, and `NOT NULL` refused the whole row. The table still
holds just the kiwi.

<br>

### Primary Keys

A **primary key** is a column (or set of columns) whose value uniquely identifies each row, like a student number. It
can never be NULL and never repeat.

A column declared exactly as `INTEGER PRIMARY KEY` gets special treatment in SQLite: it becomes an alias for the row's
internal row id, and when you do not give it a value, SQLite automatically fills in the next number. That makes it an
**auto-incrementing id**.

```py
conn.execute("INSERT INTO fruits (name) VALUES ('fig')")
print(conn.execute('SELECT id, name FROM fruits').fetchall())      # [(1, 'kiwi'), (2, 'fig')]
```

How does SQLite choose the number? It takes the current **largest id plus 1**, or `1` if the table is empty. That is why
the first fruit got `1` and the second got `2`, even though we never wrote `AUTOINCREMENT` (the next section says what
that keyword adds).

This only works for the exact form `INTEGER PRIMARY KEY`. A primary key of any other type, such as `INT` or `TEXT`, does
**not** number itself, and in a normal table it is simply left as `NULL`:

```py
conn.execute('CREATE TABLE b (id INT PRIMARY KEY, v TEXT)')
conn.execute("INSERT INTO b (v) VALUES ('x')")
print(conn.execute('SELECT id, v FROM b').fetchall())      # [(None, 'x')]   INT is not INTEGER: no numbering, and the key is NULL
```

> **In other databases:** a plain `PRIMARY KEY` does **not** number itself there. You have to state it explicitly:
>
> - **MySQL:** `id INT AUTO_INCREMENT PRIMARY KEY`
> - **SQL Server:** `id INT IDENTITY(1,1) PRIMARY KEY`
> - **PostgreSQL:** `id INTEGER GENERATED ALWAYS AS IDENTITY`
> - **DuckDB:** `id INTEGER PRIMARY KEY DEFAULT nextval('seq')`, using a sequence. Without it, an insert that leaves out
>   the id fails with `NOT NULL constraint failed`.
> - **SQLite** is the odd one out: the plain `INTEGER PRIMARY KEY` already numbers itself.

<br>

### AUTOINCREMENT

If you delete the row with the highest id, plain `INTEGER PRIMARY KEY` may hand that number out again. Add
`AUTOINCREMENT` if an id must **never** be reused:

(`DELETE FROM table WHERE ...` removes rows. Day 8 teaches it properly; for now just read it as "delete the row with id
2".)

```py
conn.execute('DELETE FROM fruits WHERE id = 2')
conn.execute("INSERT INTO fruits (name) VALUES ('lime')")
print(conn.execute('SELECT id, name FROM fruits').fetchall())      # [(1, 'kiwi'), (2, 'lime')]   id 2 was reused

conn.execute('CREATE TABLE a (id INTEGER PRIMARY KEY AUTOINCREMENT, v TEXT)')
conn.execute("INSERT INTO a (v) VALUES ('x')")
conn.execute("INSERT INTO a (v) VALUES ('y')")
conn.execute('DELETE FROM a WHERE id = 2')
conn.execute("INSERT INTO a (v) VALUES ('z')")
print(conn.execute('SELECT * FROM a').fetchall())                  # [(1, 'x'), (3, 'z')]   id 2 was never reused
```
Most of the time plain `INTEGER PRIMARY KEY` is enough. Use `AUTOINCREMENT` when old ids may be saved somewhere else (in
logs, in other systems, in a URL) and must not point at a new row. SQLite keeps the counter in a hidden table called
`sqlite_sequence`.

<br>

### IF NOT EXISTS and DROP TABLE

Creating a table that already exists is an error. Adding `IF NOT EXISTS` makes it a harmless "do nothing".

```py
try:
    conn.execute('CREATE TABLE fruits (x)')
except sqlite3.Error as e:
    print(type(e).__name__, e)      # OperationalError table fruits already exists

conn.execute('CREATE TABLE IF NOT EXISTS fruits (x)')      # no error, and the old fruits table is untouched
```

<br>

`DROP TABLE` deletes a table **and all its data**. There is no undo, so be careful.

```py
conn.execute('DROP TABLE a')

try:
    conn.execute('DROP TABLE a')
except sqlite3.Error as e:
    print(type(e).__name__, e)      # OperationalError no such table: a

conn.execute('DROP TABLE IF EXISTS a')      # safe, even though it is already gone
```

Why does this matter? You often run the same script more than once, for example after fixing a typo lower down and
running the whole file again. Here is a script that creates a table, run twice. Without `IF NOT EXISTS`, the second run
stops with an error. With it, both runs work:

```py
for run in (1, 2):
    try:
        conn.execute('CREATE TABLE notes (body TEXT)')
        print('run', run, ': table created')
    except sqlite3.Error as e:
        print('run', run, ':', type(e).__name__, e)
# run 1 : table created
# run 2 : OperationalError table notes already exists

for run in (1, 2):
    conn.execute('CREATE TABLE IF NOT EXISTS memos (body TEXT)')
    print('run', run, ': no error')
# run 1 : no error
# run 2 : no error
```

`IF NOT EXISTS` and `IF EXISTS` make a step safe to repeat: doing it once or ten times leaves the database in the same
state. Programmers call that being **idempotent**.

## Changing a Table

### Adding, Renaming and Dropping Columns

`ALTER TABLE` changes an existing table without losing its data.

```sql
-- syntax
ALTER TABLE table_name ADD COLUMN column_name type;
ALTER TABLE table_name RENAME COLUMN old_name TO new_name;
ALTER TABLE table_name DROP COLUMN column_name;
ALTER TABLE old_table_name RENAME TO new_table_name;
```

<br>

```py
conn.execute('ALTER TABLE fruits ADD COLUMN color TEXT')
conn.execute('ALTER TABLE fruits RENAME COLUMN color TO colour')
conn.execute('ALTER TABLE fruits DROP COLUMN colour')
conn.execute('ALTER TABLE fruits RENAME TO produce')
print([r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")])
# ['produce', 'loose', 'tight', 'sqlite_sequence']
```
`DROP COLUMN` needs SQLite 3.35 or newer, and it refuses to drop a primary key column or a column that other things
depend on. Changing a column's *type* or adding constraints to an existing column is not possible with `ALTER TABLE` in
SQLite. On Day 9 you will see the standard workaround: create a new table and copy the data over.

<br>

### Generated Columns

A **generated column** is calculated from other columns of the same row. You never insert into it. It is always up to
date.

```sql
-- syntax
column_name type GENERATED ALWAYS AS (expression) VIRTUAL
```

```py
conn.execute('''
    CREATE TABLE people (
        name TEXT,
        h_m  REAL,
        w_kg REAL,
        bmi  REAL GENERATED ALWAYS AS (round(w_kg / (h_m * h_m), 1)) VIRTUAL
    )
''')
conn.execute("INSERT INTO people (name, h_m, w_kg) VALUES ('Ana', 1.70, 65)")
print(conn.execute('SELECT * FROM people').fetchall())      # [('Ana', 1.7, 65.0, 22.5)]

try:
    conn.execute("INSERT INTO people (name, bmi) VALUES ('x', 1)")
except sqlite3.Error as e:
    print(type(e).__name__, e)      # OperationalError cannot INSERT into generated column "bmi"
```

There are two kinds of generated column. You choose one at the end of the definition:

- **`VIRTUAL`** (the default if you write neither): calculated **each time you read it**. It takes no space on disk, but
  the calculation is repeated on every read.
- **`STORED`**: calculated **once, when the row is inserted or updated**, and then saved. Reading it is faster, but it
  takes space on disk.

Use `VIRTUAL` for cheap calculations like the BMI above, and `STORED` when the calculation is expensive and you read the
column often. Both kinds are generated columns, and neither can be written to. One SQLite limitation: you can add a
`VIRTUAL` column to an existing table with `ALTER TABLE ... ADD COLUMN`, but adding a `STORED` one fails with
`cannot add a STORED column`.

<br>

You can also add a virtual generated column to a table that exists already:

```py
conn.execute("ALTER TABLE produce ADD COLUMN shout TEXT GENERATED ALWAYS AS (upper(name)) VIRTUAL")
print(conn.execute('SELECT * FROM produce').fetchall())
# [(1, 'kiwi', None, 1, 'KIWI'), (2, 'lime', None, 1, 'LIME')]
```
Note: Generated columns need SQLite 3.31 or newer.

## Looking at a Table's Structure

### sqlite_master

Every SQLite database has a built-in table named `sqlite_master` that lists everything in it: tables, indexes, views and
triggers. You can query it like any other table.

```py
for row in conn.execute('SELECT type, name FROM sqlite_master'):
    print(row)
# ('table', 'produce')
# ('table', 'loose')
# ('table', 'tight')
# ('table', 'sqlite_sequence')
# ('table', 'people')
```

<br>

The `sql` column even stores the original `CREATE TABLE` text:

```py
print(conn.execute("SELECT sql FROM sqlite_master WHERE name = 'people'").fetchone()[0])
# CREATE TABLE people (
# name TEXT,
# ...
```

<br>

### PRAGMA table_info

A `PRAGMA` is a special SQLite command for inspecting and configuring the database. `PRAGMA table_info(table)` returns
one row per column:

```py
for row in conn.execute('PRAGMA table_info(produce)'):     # produce is our renamed fruits table
    print(row)
# (0, 'id', 'INTEGER', 0, None, 1)
# (1, 'name', 'TEXT', 1, None, 0)
# (2, 'price', 'REAL', 0, None, 0)
# (3, 'in_stock', 'INTEGER', 0, '1', 0)
```
Each row is `(cid, name, type, notnull, default_value, pk)`. `notnull` is `1` when the column is `NOT NULL`, and `pk` is
`1` for a primary key column.

<br>

Notice what is missing: the generated column `shout` we added a moment ago. `table_info` does **not** list generated
columns. Use `PRAGMA table_xinfo(table)` to see every column, including those. Its last field, `hidden`, is `2` for a
virtual generated column:

```py
print(conn.execute('PRAGMA table_xinfo(people)').fetchall()[-1])
# (3, 'bmi', 'REAL', 0, None, 0, 2)
```

<br>

## Money and Decimal Precision

Computers store `REAL` numbers in binary, and many decimal fractions cannot be written exactly in binary, just like 1/3
cannot be written exactly in decimal. The tiny errors are usually invisible, until they are not:

```py
print(conn.execute('SELECT 0.1 + 0.2, 0.1 + 0.2 = 0.3').fetchone())      # (0.30000000000000004, 0)
print(conn.execute('SELECT 1.1 * 3, 1.1 * 3 = 3.3').fetchone())          # (3.3000000000000003, 0)
```

<br>

SQL says `0.1 + 0.2` does **not** equal `0.3`, and the same is true in Python. For a measurement like a height this does
not matter. For **money** it does: totals drift by a cent, and equality checks quietly fail.

The standard solution is to store money as a **whole number of the smallest unit**, which is cents:

```py
# $19.99 is stored as 1999
print(conn.execute('SELECT 1999 + 2501 + 99').fetchone())                   # (4599,)
print(conn.execute('SELECT (1999 + 2501 + 99) / 100.0').fetchone())         # (45.99,)  divide only to display
```

<br>

Integers are exact, so adding them never drifts. Divide by 100 only at the moment you show the value. A column for money
is therefore called `price_cents` and has the type `INTEGER`. This course does exactly that.

> **In other databases:** PostgreSQL, MySQL, SQL Server and DuckDB have an exact `DECIMAL(10, 2)` (a.k.a. `NUMERIC`)
> type for money. SQLite does not, which is why we use integer cents. We use `DECIMAL` on the DuckDB days.

You can now design tables. A database is only useful with data in it, so tomorrow we put some in. Now do some exercises.

## Exercises: Day 2

### Exercises: Level 1

From today on, a small **library database** grows alongside the lessons. Do the Level 1 exercises in order, and keep
going in the same file (`00_practice/library.db`), because later days build on it.

1. Connect to `00_practice/library.db`. (If the file already exists from Day 1, delete it and start fresh.)
2. Create a table `books` with the columns `id` (integer primary key), `title` (text, required), `author` (text,
   required), `year` (integer), `pages` (integer) and `genre` (text). Make it a `STRICT` table.
3. Use `PRAGMA table_info(books)` to print the columns.
4. Print the `CREATE TABLE` statement SQLite saved for `books`, using `sqlite_master`.
5. Add a `rating` column of type `REAL` to `books`.
6. Add a column named `notes` (text), rename it to `comment`, then drop it.
7. Add a column `price_cents` of type `INTEGER`.
8. Add a generated column `title_length` (type `INTEGER`) that holds the length of the title, using `length(title)`.
9. Print the table structure again with `PRAGMA table_xinfo(books)`. Why do you see `title_length` here but not in
   `table_info`?
10. Try to create `books` again and catch the error. Then do it with `IF NOT EXISTS` so there is no error.
11. Drop `books` and recreate it in **one** `CREATE TABLE` statement that contains all the final columns:
    `id`, `title`, `author`, `year`, `pages`, `genre`, `price_cents`, `rating`, `title_length`.
    Use `STRICT` again, and print `PRAGMA table_xinfo(books)` to check it.
12. Create a table `scratch` with one text column, check it exists in `sqlite_master`, drop it with
    `DROP TABLE IF EXISTS`, and check that it is gone.
13. Run `SELECT typeof(42), typeof(4.2), typeof('42'), typeof(NULL)` and print the result.

### Exercises: Level 2

1. A gym wants to store its members: a member id, first name, last name, email (every member must have one), date joined
   (like `'2025-03-14'`), whether the membership is active (yes or no), and a monthly fee in dollars and cents. Write a
   `CREATE TABLE members` statement for it. Choose a sensible type for each column and a `DEFAULT` of active for
   `is_active`. Explain your choice for the date, the boolean and the fee.

2. Show SQLite's type flexibility, then prevent it:
   - Create a normal (non-strict) table `ages (age INTEGER)` and insert the values `25`, `'30'`, `'thirty'` and `4.5`.
     Print each value together with its `typeof`.
   - Create `strict_ages (age INTEGER) STRICT`, try the same four inserts one at a time, and print which ones succeed
     and which raise an error.

   ```sh
   non-strict: [(25, 'integer'), (30, 'integer'), ('thirty', 'text'), (4.5, 'real')]
   strict: 25 ok, '30' ok, 'thirty' failed, 4.5 failed
   ```

3. Write a Python function `list_tables(conn)` that returns a sorted list of the names of the user tables in a database.
   It must not include SQLite's internal tables, whose names start with `sqlite_`. (Hint: in `sqlite_master`,
   `WHERE type = 'table' AND name NOT LIKE 'sqlite_%'`.) Test it on a database where you created `members` and `books`;
   it should return `['books', 'members']`.

4. Add up these ten prices once as `REAL` numbers and once as integer cents, and print both totals. Explain why they can
   differ.

   ```py
   prices = [0.10, 0.20, 0.30, 0.10, 0.20, 0.30, 0.10, 0.20, 0.30, 0.10]
   ```

   Use a Python `for` loop with `total += price` (not `sum()`). Convert each price to cents with `round(price * 100)`.

   ```sh
   as floats: 1.9000000000000004
   as cents:  190  ->  1.90
   ```

5. Create a table `people` with `name`, `height_cm`, `weight_kg` and a generated column `bmi` that computes
   `weight_kg / ((height_cm / 100.0) * (height_cm / 100.0))` rounded to one decimal place. Insert two people and print
   their names and BMI. Then try to insert a value into `bmi` yourself and show the error you get.

CONGRATULATIONS !

[<< Day 1](../01_Day_Introduction/01_introduction.md) | [Day 3 >>](../03_Day_Inserting_data/03_inserting_data.md)
