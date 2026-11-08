<div align="center">
  <h1> 30 Days Of SQL: Day 9 - Constraints, Keys & Upsert</h1>
</div>

[<< Day 8](../08_Day_Update_delete_transactions/08_update_delete_transactions.md) | [Day 10 >>](../10_Day_Database_design/10_database_design.md)

- [Day 9](#day-9)
  - [Constraints](#constraints)
    - [NOT NULL](#not-null)
    - [PRIMARY KEY](#primary-key)
    - [UNIQUE](#unique)
    - [CHECK](#check)
    - [Naming a Constraint](#naming-a-constraint)
    - [Catching Constraint Errors in Python](#catching-constraint-errors-in-python)
  - [Foreign Keys](#foreign-keys)
    - [Turning Foreign Keys On](#turning-foreign-keys-on)
    - [ON DELETE: What Happens to the Children?](#on-delete-what-happens-to-the-children)
  - [Handling Conflicts](#handling-conflicts)
    - [INSERT OR IGNORE](#insert-or-ignore)
    - [INSERT OR REPLACE](#insert-or-replace)
    - [Upsert: ON CONFLICT DO UPDATE](#upsert-on-conflict-do-update)
  - [Adding Constraints to an Existing Table](#adding-constraints-to-an-existing-table)
  - [ Exercises: Day 9](#exercises-day-9)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 9

## Constraints

A **constraint** is a rule that the table enforces on every insert and update. If a row breaks a rule, the database refuses it with an error. Constraints are the reason a
database can be trusted: no matter how buggy your Python code is, bad data cannot get in.

You have already met some. Here is a table using all of them:

```py
import sqlite3
from helpers import show

conn = sqlite3.connect(':memory:')
conn.execute('''
    CREATE TABLE products (
        id          INTEGER PRIMARY KEY,
        sku         TEXT NOT NULL UNIQUE,
        name        TEXT NOT NULL,
        price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
        stock       INTEGER NOT NULL DEFAULT 0,
        CONSTRAINT stock_not_negative CHECK (stock >= 0)
    ) STRICT
''')
conn.execute("INSERT INTO products (sku, name, price_cents) VALUES ('A1', 'Pen', 150)")
```

### NOT NULL

The column must always have a value.

```py
try:
    conn.execute("INSERT INTO products (sku, price_cents) VALUES ('B1', 100)")      # no name
except sqlite3.IntegrityError as e:
    print(e)        # NOT NULL constraint failed: products.name
```

### PRIMARY KEY

A primary key uniquely identifies a row. Every table should have one. As Day 2 explained, `INTEGER PRIMARY KEY` also numbers rows for you.

```py
try:
    conn.execute("INSERT INTO products (id, sku, name, price_cents) VALUES (1, 'C1', 'Duplicate id', 5)")
except sqlite3.IntegrityError as e:
    print(e)        # UNIQUE constraint failed: products.id
```

A primary key can span **several columns**. This is a **composite key**, common in tables that link two others. Each *combination* must be unique:

```py
conn.execute('''
    CREATE TABLE enrollments (
        student_id INTEGER,
        course_id  INTEGER,
        PRIMARY KEY (student_id, course_id)
    ) STRICT
''')
conn.execute('INSERT INTO enrollments VALUES (1, 10)')
conn.execute('INSERT INTO enrollments VALUES (1, 11)')       # same student, different course: fine
try:
    conn.execute('INSERT INTO enrollments VALUES (1, 10)')   # the same pair again
except sqlite3.IntegrityError as e:
    print(e)        # UNIQUE constraint failed: enrollments.student_id, enrollments.course_id
```

### UNIQUE

`UNIQUE` forbids repeated values in a column (or a combination of columns, written `UNIQUE (a, b)`). A table has one primary key but can have many `UNIQUE` constraints.

```py
try:
    conn.execute("INSERT INTO products (sku, name, price_cents) VALUES ('A1', 'Pencil', 100)")
except sqlite3.IntegrityError as e:
    print(e)        # UNIQUE constraint failed: products.sku
```

**NULL is never equal to another NULL**, so a `UNIQUE` column accepts many `NULL`s (add `NOT NULL` if you do not want that):

```py
conn.execute('CREATE TABLE people (email TEXT UNIQUE)')
conn.execute('INSERT INTO people VALUES (NULL)')
conn.execute('INSERT INTO people VALUES (NULL)')
print(conn.execute('SELECT COUNT(*) FROM people').fetchone())      # (2,)
```

> **In other databases:** this is standard, but SQL Server allows only one NULL in a `UNIQUE` column.

### CHECK

`CHECK (condition)` accepts the row only if the condition is **not false** (so `NULL` passes, the same trap as `WHERE`). Use it for rules about the values themselves:

```py
try:
    conn.execute("INSERT INTO products (sku, name, price_cents) VALUES ('B2', 'Negative', -5)")
except sqlite3.IntegrityError as e:
    print(e)        # CHECK constraint failed: price_cents >= 0
```

A CHECK can use any expression, including the string functions from Day 6. For instance, an email-ish format or an ISO date shape:

```py
conn.execute('''
    CREATE TABLE staff (
        email    TEXT NOT NULL CHECK (email LIKE '%_@_%._%'),
        hired_on TEXT NOT NULL CHECK (hired_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
    ) STRICT
''')
```

(It's a cheap sanity check, not a complete validator: real email validation belongs in your Python code.)

### Naming a Constraint

Give a constraint a name with `CONSTRAINT name`, and the error message becomes self-explanatory:

```py
try:
    conn.execute("INSERT INTO products (sku, name, price_cents, stock) VALUES ('B3', 'Oops', 5, -1)")
except sqlite3.IntegrityError as e:
    print(e)        # CHECK constraint failed: stock_not_negative
```

### Catching Constraint Errors in Python

All of these raise `sqlite3.IntegrityError` (a subclass of `sqlite3.Error`). Use `try`/`except`. Since Python 3.11 the exception also tells you *which* rule broke,
through the attribute `sqlite_errorname`, so your code can react to the kind of violation without parsing the message:

```py
try:
    conn.execute("INSERT INTO products (sku, name, price_cents) VALUES ('A1', 'Pencil', 100)")
except sqlite3.IntegrityError as e:
    print(e.sqlite_errorname)       # SQLITE_CONSTRAINT_UNIQUE
```

Other names include `SQLITE_CONSTRAINT_NOTNULL`, `SQLITE_CONSTRAINT_CHECK`, `SQLITE_CONSTRAINT_PRIMARYKEY` and `SQLITE_CONSTRAINT_FOREIGNKEY`.

## Foreign Keys

A **foreign key** says "this column's value must exist in that other table". It is the rule that stops an order from belonging to a customer who does not exist.

```sql
-- syntax
column_name type REFERENCES other_table (other_column)
```

```py
conn.execute('CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT NOT NULL) STRICT')
conn.execute('''
    CREATE TABLE emp (
        id      INTEGER PRIMARY KEY,
        name    TEXT NOT NULL,
        dept_id INTEGER REFERENCES dept (id)
    ) STRICT
''')
```

Here `emp.dept_id` must be the `id` of a row in `dept` (or `NULL`, meaning "no department"). The table holding the foreign key (`emp`) is the **child**, and the table it points at (`dept`) is the **parent**.

### Turning Foreign Keys On

**SQLite does not enforce foreign keys unless you ask it to.** The rule is written in the table, but by default it is ignored:

```py
conn.execute("INSERT INTO emp (name, dept_id) VALUES ('Ghost', 99)")      # there is no department 99
print(conn.execute('SELECT * FROM emp').fetchall())                       # [(1, 'Ghost', 99)]
```

The ghost employee is in the table. You need to switch enforcement on **for every connection**, with a `PRAGMA`:

```py
conn = sqlite3.connect('shop.db')
conn.execute('PRAGMA foreign_keys = ON')
```

**Do it right after connecting, before anything else.** The pragma is silently ignored while a transaction is open:

```py
c = sqlite3.connect(':memory:')
c.execute('CREATE TABLE t (x)')
c.execute('INSERT INTO t VALUES (1)')               # this opened a transaction
c.execute('PRAGMA foreign_keys = ON')               # no error, but also no effect!
print(c.execute('PRAGMA foreign_keys').fetchone())  # (0,)    still off
```

`PRAGMA foreign_keys` (with no value) tells you whether it is on: `(1,)` or `(0,)`. With enforcement on, the ghost is refused:

```py
fk = sqlite3.connect(':memory:')
fk.execute('PRAGMA foreign_keys = ON')
fk.execute('CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT NOT NULL) STRICT')
fk.execute('CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT NOT NULL, dept_id INTEGER REFERENCES dept (id)) STRICT')
fk.execute("INSERT INTO dept VALUES (1, 'Eng')")

try:
    fk.execute("INSERT INTO emp (name, dept_id) VALUES ('Ghost', 99)")
except sqlite3.IntegrityError as e:
    print(e)        # FOREIGN KEY constraint failed
```

From now on, every database we open in this course for real work begins with this pragma. (`PRAGMA foreign_key_check` lists any rows that already break a rule.)

### ON DELETE: What Happens to the Children?

What should happen when you delete a parent that still has children? You choose, with an `ON DELETE` clause:

| Clause | Effect when the parent row is deleted |
|---|---|
| *(none)* / `RESTRICT` | the delete is **refused** while children exist |
| `CASCADE` | the children are **deleted too** |
| `SET NULL` | the children's foreign key becomes `NULL` |
| `SET DEFAULT` | the children's foreign key becomes its default |

```py
d = sqlite3.connect(':memory:')
d.execute('PRAGMA foreign_keys = ON')
d.execute('CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT) STRICT')
d.execute('CREATE TABLE players_cascade (id INTEGER PRIMARY KEY, team_id INTEGER REFERENCES teams (id) ON DELETE CASCADE) STRICT')
d.execute('CREATE TABLE players_setnull (id INTEGER PRIMARY KEY, team_id INTEGER REFERENCES teams (id) ON DELETE SET NULL) STRICT')
d.execute("INSERT INTO teams VALUES (1, 'Reds')")
for table in ('players_cascade', 'players_setnull'):
    d.executemany(f'INSERT INTO {table} (team_id) VALUES (?)', [(1,), (1,)])

d.execute('DELETE FROM teams WHERE id = 1')
print(d.execute('SELECT COUNT(*) FROM players_cascade').fetchone())        # (0,)   the players went with the team
print(d.execute('SELECT * FROM players_setnull').fetchall())               # [(1, None), (2, None)]   players stay, with no team
```

`CASCADE` fits data that has no meaning without its parent (an order's lines). `SET NULL` fits optional links (an employee whose department closed). With no clause, the safest
default, the database refuses the delete. Choose deliberately. A careless `CASCADE` can wipe a lot of data with one statement.

## Handling Conflicts

What should happen when you insert a row that collides with an existing one (same primary key, same `UNIQUE` value)? By default: an error. Often you want something gentler.

```py
conn.execute('CREATE TABLE inv (sku TEXT PRIMARY KEY, qty INTEGER NOT NULL, note TEXT) STRICT')
conn.execute("INSERT INTO inv VALUES ('A', 5, 'first')")
```

### INSERT OR IGNORE

Silently skips a row that would break a rule:

```py
cur = conn.execute("INSERT OR IGNORE INTO inv VALUES ('A', 3, 'dup')")
print(cur.rowcount)                                                  # 0    nothing was inserted
print(conn.execute("SELECT * FROM inv").fetchall())                  # [('A', 5, 'first')]
```

Good for "add it if it is not there yet". Check `rowcount` if you need to know whether it did.

### INSERT OR REPLACE

On conflict, **deletes the old row and inserts the new one**:

```py
conn.execute("INSERT OR REPLACE INTO inv VALUES ('A', 3, 'replaced')")
print(conn.execute("SELECT * FROM inv").fetchall())                  # [('A', 3, 'replaced')]
```

It replaces the *whole* row. Any column you did not mention is reset to its default or NULL, and a row it replaces counts as a delete, which can trigger `ON DELETE CASCADE`.
It is rarely what you want. The next form is almost always better.

### Upsert: ON CONFLICT DO UPDATE

**Upsert** means "update if it exists, insert if it does not". It is one of the most useful statements in SQL (SQLite 3.24+; also PostgreSQL and DuckDB).

```sql
-- syntax
INSERT INTO table (columns) VALUES (values)
ON CONFLICT (conflict_column) DO UPDATE SET column = expression;
```

Inside `DO UPDATE`, the name of the column alone means the **existing** row's value, and `excluded.column` means the **new** value you tried to insert:

```py
conn.execute("DELETE FROM inv")
conn.execute("INSERT INTO inv VALUES ('A', 5, 'first')")

upsert = '''
    INSERT INTO inv (sku, qty) VALUES (?, ?)
    ON CONFLICT (sku) DO UPDATE SET qty = qty + excluded.qty
'''
conn.execute(upsert, ('A', 4))      # A exists: 5 + 4
conn.execute(upsert, ('B', 4))      # B is new: inserted
print(conn.execute('SELECT * FROM inv ORDER BY sku').fetchall())
# [('A', 9, 'first'), ('B', 4, None)]
```

Notice that A kept its note, since the upsert only touched `qty`. That is the difference from `OR REPLACE`. You can also write `DO NOTHING` instead of `DO UPDATE`, which makes it the targeted cousin of `OR IGNORE`.
And with `executemany` you can fold a whole list of events into the table, including repeated keys:

```py
conn.executemany(upsert, [('C', 1), ('C', 2), ('A', 10)])
print(conn.execute('SELECT * FROM inv ORDER BY sku').fetchall())
# [('A', 19, 'first'), ('B', 4, None), ('C', 3, None)]
```

An optional `WHERE` after `DO UPDATE SET ...` limits when the update runs, for example `WHERE excluded.qty > qty` to only ever raise a value.

**Constraints on the new row are checked first.** If `qty` has `CHECK (qty >= 0)`, an upsert that adds `-1` is rejected *even though* the final total would be fine, because SQLite tests the proposed row
before it looks for a conflict:

```py
c = sqlite3.connect(':memory:')
c.execute('CREATE TABLE stock (sku TEXT PRIMARY KEY, qty INTEGER NOT NULL CHECK (qty >= 0)) STRICT')
c.execute("INSERT INTO stock VALUES ('A', 5)")
try:
    c.execute("INSERT INTO stock VALUES ('A', -1) ON CONFLICT (sku) DO UPDATE SET qty = qty + excluded.qty")
except sqlite3.IntegrityError as e:
    print(e)        # CHECK constraint failed: qty >= 0
```

For subtracting, use a plain `UPDATE stock SET qty = qty - 1 WHERE sku = 'A'`, which works because only the final value is checked.

## Adding Constraints to an Existing Table

Day 2 said `ALTER TABLE` cannot add most constraints to an existing column. The standard SQLite technique is to **rebuild the table**:

1. create a new table with the constraints you want,
2. copy the rows across with `INSERT INTO ... SELECT`,
3. drop the old table,
4. rename the new one.

```sql
-- syntax
INSERT INTO new_table (col1, col2) SELECT col1, col2 FROM old_table;
```

`INSERT INTO ... SELECT` inserts the **result of a query**, as many rows as it returns. Here it is, giving the Day 2 `fruits` idea a rule it lacked:

```py
conn.execute('CREATE TABLE fruits (id INTEGER PRIMARY KEY, name TEXT, price_cents INTEGER) STRICT')
conn.executemany('INSERT INTO fruits (name, price_cents) VALUES (?, ?)', [('kiwi', 50), ('fig', 120)])

conn.execute('''
    CREATE TABLE fruits_new (
        id          INTEGER PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        price_cents INTEGER NOT NULL CHECK (price_cents > 0)
    ) STRICT
''')
conn.execute('INSERT INTO fruits_new (id, name, price_cents) SELECT id, name, price_cents FROM fruits')
conn.execute('DROP TABLE fruits')
conn.execute('ALTER TABLE fruits_new RENAME TO fruits')
print(conn.execute('SELECT * FROM fruits').fetchall())       # [(1, 'kiwi', 50), (2, 'fig', 120)]
```

If the old data breaks one of the new rules, the `INSERT ... SELECT` fails and you find out *before* dropping anything. In the exercises you will do this to your real `books` table.

With constraints, bad data cannot get into your tables, and with upsert you can load data that arrives in messy, repeated batches. Now do some exercises.

## Exercises: Day 9

### Exercises: Level 1

Use your `00_practice/library.db`. Exercise 1 **rebuilds** your real `books` table, so take it carefully. The 12 books must come out unchanged.

1. Rebuild `books` with these rules, using the four-step technique from the end of the lesson (new table, `INSERT INTO ... SELECT`, drop, rename). Keep `STRICT` and all the existing
   columns, including the generated `title_length`; do not copy it, as it is calculated.
   - `title` is required and must not be an empty string,
   - `author` is required,
   - `year`, when given, must be between 1000 and 2100,
   - `pages`, when given, must be greater than 0,
   - `price_cents`, when given, must be 0 or more,
   - `rating`, when given, must be between 0 and 5,
   - the combination of `title` and `author` must be unique.

   Check that you still have 12 books with ids 1 to 12, and that Dune's `title_length` is 4.

   ```sh
   (12, 1, 12)
   ('Dune', 4)
   ```

2. Try to insert a book that breaks each rule in turn (pages `0`; rating `6`; a second copy of `Dune` by `Frank Herbert`; no title; an empty title). Catch each `IntegrityError` and print the message.
   Roll back at the end so nothing is left over.
3. For each error in exercise 2, also print `e.sqlite_errorname`.
4. Create a table `reading_list (title TEXT NOT NULL, author TEXT NOT NULL, rating REAL, UNIQUE (title, author))`. Use an upsert that updates the rating when the book is already
   there to: add Foundation by Isaac Asimov with rating 4.0, then again with 4.6, then add Dune by Frank Herbert with 4.5. Show the table.

   ```sh
   title       author         rating
   ----------  -------------  ------
   Dune        Frank Herbert  4.5
   Foundation  Isaac Asimov   4.6
   (2 rows)
   ```

5. Use `INSERT OR IGNORE` to try adding Dune by Frank Herbert to `books` again with 1 page. Print the `rowcount` and Dune's page count to show that nothing changed, then roll back.

   ```sh
   0 (612,)
   ```

### Exercises: Level 2

1. **Foreign keys are optional.** In an in-memory database create `members (id, name)` and `loans (id, member_id REFERENCES members(id), book)`. Add the member Ana.
   (a) Without the pragma, insert a loan for `member_id = 99` and show that it is accepted. (b) On a connection that runs `PRAGMA foreign_keys = ON` first, show that it is refused. (c) Show that
   setting the pragma *after* an `INSERT` has opened a transaction has no effect, by printing `PRAGMA foreign_keys`.

   ```sh
   without PRAGMA: [(1, 99, 'Dune')] (0,)
   with PRAGMA:    FOREIGN KEY constraint failed
   pragma inside a transaction: (0,)
   ```

2. Create `teams (id, name)` and three child tables of players: one with `ON DELETE CASCADE`, one with `ON DELETE SET NULL`, and one with no clause. Add a team with two players in each. Show what happens when you delete
   the team: the plain table blocks it; then drop that table and delete again, and show the results for the other two.

   ```sh
   plain FK blocks the delete: FOREIGN KEY constraint failed
   cascade: 0 rows left
   set null: [(1, None), (2, None)]
   ```

3. Write `safe_insert(conn, sql, params)` that runs the insert and returns `True` on success or `False` if it raises `sqlite3.IntegrityError`. Test it with a table `users (id, email NOT NULL UNIQUE)`: a new email, the same
   email again, and a `None` email.

   ```sh
   True
   False
   False
   ```

4. Create `enrollments (student_id, course_id, PRIMARY KEY (student_id, course_id))` and try to insert these pairs with `INSERT OR IGNORE`: `(1,10), (1,11), (2,10), (1,10), (2,10), (3,12)`. Use `rowcount` to report how many were added and how many ignored.

   ```sh
   4 added, 2 ignored
   ```

5. Create a table `staff (email, hired_on, salary_cents)` with CHECKs: the email matches `'%_@_%._%'`, `hired_on` looks like `YYYY-MM-DD` (use `GLOB`), and the salary is above 0. Insert these four rows, report which are accepted, and print the error for each rejected one:
   `('ana@example.com', '2025-03-14', 500000)`, `('not-an-email', '2025-03-14', 500000)`, `('ben@example.com', '14/03/2025', 500000)`, `('cy@example.com', '2025-03-14', 0)`.

6. In your own words, explain the difference between `PRIMARY KEY` and `UNIQUE`. Prove with code that a `UNIQUE` column accepts two `NULL`s.

### Exercises: Level 3

1. A warehouse sends you a CSV of stock deliveries. The same SKU can appear many times, and quantities must add up. Create `inventory (sku TEXT PRIMARY KEY, qty INTEGER NOT NULL CHECK (qty >= 0), price_cents INTEGER NOT NULL)`
   and load the deliveries below with **one** `executemany` and an upsert that **adds** the quantity and takes the **latest** price. Parse the text with `csv.DictReader(io.StringIO(text))`.

   ```py
   UPDATES = """sku,qty,price_cents
   A100,5,250
   B200,3,1000
   A100,7,250
   C300,10,75
   B200,4,1200
   A100,2,260
   """
   ```

   ```sh
   sku   qty  price_cents
   ----  ---  -----------
   A100  14   260
   B200  7    1200
   C300  10   75
   (3 rows)
   ```

2. A second file contains some bad rows (negative quantities). Starting from an empty `inventory`, process this file **row by row**, counting how many rows were inserted, updated and rejected, and printing every rejected row with its error.
   Why is `B200` rejected even if it exists with plenty of stock? (Hint: re-read the warning in the upsert section.)

   ```py
   MORE = """sku,qty,price_cents
   A100,5,250
   D400,-5,100
   E500,4,300
   A100,3,250
   B200,-1,1200
   E500,2,320
   """
   ```

   ```sh
   2 inserted, 2 updated, 2 rejected
   rejected: ('D400', '-5', 'CHECK constraint failed: qty >= 0')
   rejected: ('B200', '-1', 'CHECK constraint failed: qty >= 0')
   sku   qty  price_cents
   ----  ---  -----------
   A100  8    250
   E500  6    320
   (2 rows)
   ```

3. Create `countries_c (name TEXT NOT NULL UNIQUE, capital TEXT, population INTEGER NOT NULL CHECK (population >= 0), currency TEXT)` and load `data/countries_data.json` into it (250 rows, empty capitals as `NULL`). Then (a) load the same rows again with `INSERT OR IGNORE`
   and show the row count did not change, and (b) load them a third time using an upsert that sets the population to the new value plus 1000, and show Finland's population before and after.

   ```sh
   (250,)
   after INSERT OR IGNORE reload: 250 rows
   after upsert reload: 250 rows; Finland 5491817 -> 5492817
   ```

CONGRATULATIONS !

[<< Day 8](../08_Day_Update_delete_transactions/08_update_delete_transactions.md) | [Day 10 >>](../10_Day_Database_design/10_database_design.md)
