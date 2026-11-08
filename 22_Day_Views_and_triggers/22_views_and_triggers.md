<div align="center">
  <h1> 30 Days Of SQL: Day 22 - Views & Triggers</h1>
</div>

[<< Day 21](../21_Day_Indexes/21_indexes.md) | [Review 4 >>](../22R_Review_Python_and_sqlite/22R_review_python_and_sqlite.md)

- [Day 22](#day-22)
  - [Views](#views)
    - [CREATE VIEW](#create-view)
    - [Views Hide Complexity](#views-hide-complexity)
    - [A View Stores No Data](#a-view-stores-no-data)
    - [Views Cannot Take Parameters](#views-cannot-take-parameters)
    - [Views and Permissions](#views-and-permissions)
    - [TEMP Views](#temp-views)
  - [CTE vs Temp Table vs View vs Table](#cte-vs-temp-table-vs-view-vs-table)
  - [Triggers](#triggers)
    - [Anatomy of a Trigger](#anatomy-of-a-trigger)
    - [NEW and OLD](#new-and-old)
    - [An Audit Log](#an-audit-log)
    - [An updated_at Column](#an-updated_at-column)
    - [Validation with RAISE](#validation-with-raise)
    - [Looking at and Dropping Triggers](#looking-at-and-dropping-triggers)
    - [Hidden Logic](#hidden-logic)
  - [Generated Columns, Views or Triggers?](#generated-columns-views-or-triggers)
  - [Stored Procedures, Revisited](#stored-procedures-revisited)
  - [ Exercises: Day 22](#exercises-day-22)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 22

So far every query has been something you ran. Today we make the database remember two kinds of things for you: **views**, which save a query under a name, and **triggers**, which run SQL automatically when data changes.
Both move a little logic from your Python code into the database. Used with care they remove repetition and protect your data. Used carelessly they hide bugs, so we finish by looking at when *not* to use them.

Examples use the normalized library from Day 10 and `shop.db`. Anything that changes data runs on a copy.

## Views

### CREATE VIEW

A **view** is a `SELECT` with a name. Whenever you query the view, SQLite runs the saved `SELECT` and gives you its rows, as if the view were a table. Think of a saved search in your email program: it stores the *question*, not the messages.

```sql
-- syntax
CREATE VIEW [IF NOT EXISTS] view_name AS
SELECT ...;

DROP VIEW [IF EXISTS] view_name;
```

The library has a three-table join that you keep rewriting: which books are out right now, and who has them?

```py
import sqlite3
from helpers import show

import shutil
shutil.copy('00_practice/library.db', '00_practice/library_day22.db')      # work on a copy of your Day 10 library
lib = sqlite3.connect('00_practice/library_day22.db')
lib.execute('''
    CREATE VIEW current_loans AS
    SELECT loans.id AS loan_id, books.title, members.name AS member, loans.loaned_on, loans.due_on
    FROM loans
    JOIN books   ON books.id = loans.book_id
    JOIN members ON members.id = loans.member_id
    WHERE loans.returned_on IS NULL
''')
show(lib.execute('SELECT * FROM current_loans ORDER BY due_on, loan_id'))
```

```sh
output
loan_id  title                     member        loaned_on   due_on
-------  ------------------------  ------------  ----------  ----------
4        The Pragmatic Programmer  Bruno Silva   2025-02-20  2025-03-06
6        Neuromancer               Chloe Martin  2025-03-01  2025-03-15
7        Pride and Prejudice       Dev Patel     2025-03-05  2025-03-19
8        Dune                      Dev Patel     2025-03-08  2025-03-22
9        Clean Code                Alice Nguyen  2025-03-10  2025-03-24
10       The Hobbit                Bruno Silva   2025-03-12  2025-03-26
(6 rows)
```

The `ORDER BY` goes on the query *using* the view. (You can sort inside a view, but SQLite does not promise to keep that order when the view is used in a bigger query.) The view appears in `sqlite_master` with `type = 'view'`, together with its text.

### Views Hide Complexity

Views can be built on views. `overdue_loans` is just `current_loans` with one more condition. Day 16 gave you the date tools: `julianday()` subtracts two dates into days.

```py
lib.execute('''
    CREATE VIEW overdue_loans AS
    SELECT loan_id, title, member, due_on,
           CAST(julianday('2025-03-14') - julianday(due_on) AS INTEGER) AS days_overdue
    FROM current_loans
    WHERE due_on < '2025-03-14'
''')
show(lib.execute('SELECT * FROM overdue_loans ORDER BY due_on, loan_id'))
```

```sh
output
loan_id  title                     member       due_on      days_overdue
-------  ------------------------  -----------  ----------  ------------
4        The Pragmatic Programmer  Bruno Silva  2025-03-06  8
(1 row)
```

A person (or a Python function) using `overdue_loans` needs to know nothing about three joins or how "overdue" is defined. If the definition changes, you change one view. That is the point of a view: **one definition, many users**, and a stable name that survives changes in the tables underneath.

We hard-coded March 14, 2025 so that your results match this page. A real view would use `date('now')` in place of the literal date. 

### A View Stores No Data

A view has no rows of its own. It runs its query every time, on the data as it is *now*:

```py
print(lib.execute('SELECT COUNT(*) FROM current_loans').fetchone())
lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (4, 5, '2025-03-14', '2025-03-28')")
print(lib.execute('SELECT COUNT(*) FROM current_loans').fetchone())
# (6,)
# (7,)
```

You also cannot write into most views: there is no table behind them to receive the row.

```py
try:
    lib.execute("INSERT INTO current_loans (title) VALUES ('x')")
except sqlite3.OperationalError as e:
    print('OperationalError:', e)
# OperationalError: cannot modify current_loans because it is a view
```

(There is an advanced escape hatch, `INSTEAD OF` triggers, which run your own SQL when someone writes to a view. We mention it below and leave it there.)

Since a view re-runs its query, a view over a big join is as slow as that join. A view does not make anything faster. If you need a *stored* result that is refreshed now and then, keep a real table and refill it
(`DELETE` then `INSERT INTO ... SELECT`, or `CREATE TABLE ... AS SELECT`). Other databases call that a **materialized view**; SQLite does not have one.

### Views Cannot Take Parameters

A view has no `?` placeholders. "Overdue as of a date *I* choose" cannot be a parameter of the view. Two common ways around it: filter *outside* the view (`SELECT * FROM current_loans WHERE due_on < ?`, which is why `current_loans` keeps the `due_on` column), or use `date('now')` inside the view for "as of today".

### Views and Permissions

In server databases (PostgreSQL, MySQL, SQL Server), views are also a **security tool**: you can `GRANT SELECT` on a view that shows only some columns or rows (say, a `members_public` view without email addresses) and give users no access to the table underneath.
SQLite has no users or `GRANT`, so there it is only about convenience. (If you need real restriction, open the database read-only, Day 27, or give a program only the view's output.)

### TEMP Views

`CREATE TEMP VIEW` makes a view that exists only for the current connection and disappears when it closes. You used one on Day 20 for the cleaning step. It is perfect for scaffolding in a script, because it leaves no trace in the database file:

```py
import sqlite3
from contextlib import closing

with closing(sqlite3.connect('00_practice/temp_view_demo.db')) as c:
    c.executescript('CREATE TABLE t (x INTEGER); INSERT INTO t VALUES (1), (2), (3);')
    c.execute('CREATE TEMP VIEW big AS SELECT x FROM t WHERE x >= 2')
    print(c.execute('SELECT COUNT(*) FROM big').fetchone())
with closing(sqlite3.connect('00_practice/temp_view_demo.db')) as c:
    try:
        c.execute('SELECT COUNT(*) FROM big')
    except sqlite3.OperationalError as e:
        print('OperationalError:', e)
# (2,)
# OperationalError: no such table: big
```

## CTE vs Temp Table vs View vs Table

Day 14 gave you CTEs and temp tables. With views and ordinary tables you now have four ways to "keep a query result around". Here is the finished comparison:

| | **CTE** (`WITH`) | **Temp table** | **View** | **Regular table** |
|---|---|---|---|---|
| Holds rows? | no (a named subquery) | yes, a snapshot | no (re-runs the query) | yes |
| Lives | one statement | until the connection closes | until dropped (saved in the file) | until dropped |
| Sees later changes to the source? | yes (it re-runs) | no, until you refill it | yes | no, until you refill it |
| Can have indexes? | no | yes | no (the tables underneath can) | yes |
| Visible to other connections? | no | no | yes | yes |
| Best for | breaking one query into readable steps | an expensive intermediate result you use many times in a script, or a staging step | a named, reusable question (reports, hiding joins) | data you want to keep |

A quick way to choose: *Do I need it again after this query?* No: CTE. *Yes, but only inside this script, and it is slow to compute?* Temp table. *Yes, in many queries, and always current?* View. *It is real data?* Table.

## Triggers

A **trigger** is SQL that the database runs **by itself** when a row is inserted, updated or deleted. You do not call it. Typical jobs: write an audit trail, keep a timestamp fresh, reject changes that break a rule, update a related table.

### Anatomy of a Trigger

```sql
-- syntax
CREATE TRIGGER [IF NOT EXISTS] trigger_name
{BEFORE | AFTER} {INSERT | UPDATE [OF column, ...] | DELETE} ON table_name
[FOR EACH ROW]
[WHEN condition]
BEGIN
    statement;
    statement;
END;

DROP TRIGGER [IF EXISTS] trigger_name;
```

- **When**: `BEFORE` runs before the change (good for checking), `AFTER` runs once it is done (good for logging and copying).
- **Which event**: `INSERT`, `UPDATE` (optionally only when certain columns are named in the `SET`) or `DELETE`.
- **`WHEN`**: an optional condition. The trigger body runs only for rows where it is true.
- **Body**: one or more statements between `BEGIN` and `END`, each ending in `;`. SQLite triggers are always *row-level*: they run once **for each affected row**.

Because the body contains `;` characters, create triggers with `execute` (one statement) or `executescript`, not by splitting text yourself.

### NEW and OLD

Inside the body, two pseudo-rows are available: **`NEW`** is the row as it will be (or now is) after an `INSERT` or `UPDATE`; **`OLD`** is the row as it was before an `UPDATE` or `DELETE`.

| Event | `OLD` | `NEW` |
|---|---|---|
| `INSERT` | not available | the inserted row |
| `UPDATE` | the row before | the row after |
| `DELETE` | the deleted row | not available |

### An Audit Log

An **audit log** answers "who changed what, and what was it before?". Here is a tiny bank with a trigger that records every balance change:

```py
t = sqlite3.connect(':memory:')
t.executescript('''
    CREATE TABLE accounts (id INTEGER PRIMARY KEY, owner TEXT, balance_cents INTEGER NOT NULL) STRICT;
    CREATE TABLE audit (id INTEGER PRIMARY KEY, account_id INTEGER, old_cents INTEGER, new_cents INTEGER) STRICT;

    CREATE TRIGGER trg_accounts_audit
    AFTER UPDATE OF balance_cents ON accounts
    BEGIN
        INSERT INTO audit (account_id, old_cents, new_cents) VALUES (OLD.id, OLD.balance_cents, NEW.balance_cents);
    END;

    INSERT INTO accounts (owner, balance_cents) VALUES ('Ana', 10000), ('Ben', 500);
    UPDATE accounts SET balance_cents = balance_cents - 2500 WHERE owner = 'Ana';
    UPDATE accounts SET balance_cents = balance_cents + 1000;
''')
show(t.execute('SELECT * FROM audit'))
```

```sh
output
id  account_id  old_cents  new_cents
--  ----------  ---------  ---------
1   1           10000      7500
2   1           7500       8500
3   2           500        1500
(3 rows)
```

The second `UPDATE` touched two rows with one statement, and the trigger ran twice, once per row. Your Python code never mentioned `audit`.

For the library, a trigger that logs every new loan, and one that logs returns, looks like this. `logged_at` is filled by a column `DEFAULT (datetime('now'))`:

```py
lib.close()                                                  # release the old file first
shutil.copy('00_practice/library.db', '00_practice/library_day22.db')           # a fresh copy without the Q4 loan above
lib = sqlite3.connect('00_practice/library_day22.db')
lib.executescript('''
    CREATE TABLE loan_log (
        id        INTEGER PRIMARY KEY,
        loan_id   INTEGER NOT NULL,
        action    TEXT NOT NULL,
        logged_at TEXT NOT NULL DEFAULT (datetime('now'))
    ) STRICT;

    CREATE TRIGGER trg_loans_log_insert
    AFTER INSERT ON loans
    BEGIN
        INSERT INTO loan_log (loan_id, action) VALUES (NEW.id, 'loaned');
    END;

    CREATE TRIGGER trg_loans_log_return
    AFTER UPDATE OF returned_on ON loans
    WHEN OLD.returned_on IS NULL AND NEW.returned_on IS NOT NULL
    BEGIN
        INSERT INTO loan_log (loan_id, action) VALUES (NEW.id, 'returned');
    END;
''')
lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (4, 5, '2025-03-14', '2025-03-28')")
lib.execute("UPDATE loans SET returned_on = '2025-03-14' WHERE id = 11")
lib.execute("UPDATE loans SET returned_on = '2025-03-15' WHERE id = 11")
show(lib.execute('SELECT loan_id, action FROM loan_log ORDER BY id'))
```

```sh
output
loan_id  action
-------  --------
11       loaned
11       returned
(2 rows)
```

The third statement changed `returned_on` again, but `WHEN OLD.returned_on IS NULL ...` was false, so nothing was logged. This is why `WHEN` conditions matter: without it, the trigger would claim the book was returned twice. (Remember `IS NULL`, not `= NULL`, from Day 5.)

### An updated_at Column

"When was this row last changed?" is the most common trigger. SQLite cannot add a column with a non-constant default after the fact, so add the column plain and fill it with a trigger:

```py
lib.execute('ALTER TABLE books ADD COLUMN updated_at TEXT')
lib.execute('''
    CREATE TRIGGER trg_books_updated_at
    AFTER UPDATE ON books
    WHEN NEW.updated_at IS OLD.updated_at
    BEGIN
        UPDATE books SET updated_at = datetime('now') WHERE id = NEW.id;
    END
''')
lib.execute('UPDATE books SET rating = 4.9 WHERE id = 1')
show(lib.execute('SELECT id, title, updated_at IS NOT NULL AS touched FROM books WHERE id IN (1, 2) ORDER BY id'))
```

```sh
output
id  title        touched
--  -----------  -------
1   Dune         1
2   Neuromancer  0
(2 rows)
```

(The timestamp itself changes every run, so we only print whether it is set.) A trigger that does an `UPDATE` on its own table could trigger itself forever. SQLite avoids this by default (`PRAGMA recursive_triggers` is off), and the `WHEN` clause
makes the trigger safe even if somebody turns that on: the inner update sets a *new* `updated_at`, so `NEW.updated_at IS OLD.updated_at` is false and it stops.

### Validation with RAISE

The `CHECK` constraints from Day 9 can only look at one row. A trigger can look at **other rows and other tables**, and stop the change with `RAISE`. Rule: *a book that is already out cannot be lent again*.

```sql
-- syntax (only inside a trigger body)
SELECT RAISE(ABORT, 'message');
```

```py
lib.close()                                                  # release the old file first
shutil.copy('00_practice/library.db', '00_practice/library_day22b.db')      # another fresh copy of the Day 10 library
lib = sqlite3.connect('00_practice/library_day22b.db')
lib.execute('''
    CREATE TRIGGER trg_loans_no_double_loan
    BEFORE INSERT ON loans
    WHEN EXISTS (SELECT 1 FROM loans WHERE book_id = NEW.book_id AND returned_on IS NULL)
    BEGIN
        SELECT RAISE(ABORT, 'book is already on loan');
    END
''')
try:
    lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (9, 5, '2025-03-14', '2025-03-28')")
except sqlite3.IntegrityError as e:
    print('IntegrityError:', e)
lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (4, 5, '2025-03-14', '2025-03-28')")
print(lib.execute('SELECT COUNT(*) FROM loans').fetchone())
# IntegrityError: book is already on loan
# (11,)
```

Book 9 is out (loan 4 in the data), so the insert is refused; book 4 is free and goes in. `RAISE` shows up in Python as `sqlite3.IntegrityError` (its `sqlite_errorname` is `SQLITE_CONSTRAINT_TRIGGER`). The options:

| | Effect |
|---|---|
| `RAISE(ABORT, msg)` | stop and undo **this statement** (the most useful; your `with conn:` then rolls back the rest) |
| `RAISE(FAIL, msg)` | stop; keep the changes already made by this statement |
| `RAISE(ROLLBACK, msg)` | stop and roll back the **whole transaction** |
| `RAISE(IGNORE)` | silently skip this row and carry on |

A multi-row statement is all-or-nothing under `ABORT`: if the third of ten rows violates the rule, the first two are undone as well.

Does this make the `LibraryRepository.lend()` check from Day 19 pointless? No. Both together are the usual best practice: the **trigger is the safety net** that nobody can bypass (a script, another program, a person at the `sqlite3` prompt), and the **Python check comes first**
and raises a friendlier `AlreadyLoanedError`. In the solutions, `repo.lend(9, 5, '2025-03-14')` on this database still prints `AlreadyLoanedError: book 9 is already on loan`, because the repository checks before the trigger ever fires.

**In other databases:** triggers exist everywhere but the syntax differs. PostgreSQL triggers call a separate *function* (`CREATE TRIGGER ... EXECUTE FUNCTION f()`), MySQL needs `DELIMITER` tricks in its shell, SQL Server uses `INSERTED` and `DELETED` tables instead of `NEW`/`OLD` and fires once per *statement*, and errors use `SIGNAL` / `RAISERROR` / `THROW` instead of `RAISE`.

### Looking at and Dropping Triggers

```py
print(lib.execute("SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger'").fetchall())
lib.execute('DROP TRIGGER trg_loans_no_double_loan')
# [('trg_loans_no_double_loan', 'loans')]
```

A trigger belongs to its table: `DROP TABLE` removes its triggers too. There is also `CREATE TEMP TRIGGER` (connection-only), and `INSTEAD OF` triggers on views, which turn writes to a view into writes to the tables underneath:

```sql
CREATE TRIGGER trg_return INSTEAD OF DELETE ON current_loans
BEGIN
    UPDATE loans SET returned_on = '2025-03-14' WHERE id = OLD.loan_id;
END;
-- now DELETE FROM current_loans WHERE loan_id = 4 returns that book instead of failing
```

### Hidden Logic

**Common mistake:** putting business logic in triggers because it is clever. Triggers are **invisible** at the place where they matter. Somebody reads `conn.execute('INSERT INTO order_items ...')`, sees nothing about stock, and
wonders why `products.stock` changed. Triggers fire in the order SQLite chooses; they make bulk loads slower (Day 20's import now runs your trigger a million times); they are not in your Python tests unless you create them there; and a trigger that updates another table with its own triggers makes chains that are painful to debug.

Guidelines:

- Use triggers for **invariants that must hold no matter who writes**: an audit trail, `updated_at`, a stock count, a rule that spans tables.
- Keep each trigger **small and single-purpose**, name it `trg_<table>_<what>`, and write the rule in a comment above it.
- Keep the SQL that creates them in a schema file in version control (Day 27: migrations), so people find them.
- If the rule is a *workflow* ("when an order is placed, also send an email, and if that fails ..."), it belongs in Python.

## Generated Columns, Views or Triggers?

Three tools, three jobs. You already know generated columns from Day 2.

```py
gen = sqlite3.connect(':memory:')
gen.execute('''
    CREATE TABLE lines (qty INTEGER, unit_cents INTEGER,
                        total_cents INTEGER GENERATED ALWAYS AS (qty * unit_cents) STORED) STRICT
''')
gen.execute('INSERT INTO lines (qty, unit_cents) VALUES (3, 250)')
print(gen.execute('SELECT * FROM lines').fetchall())
try:
    gen.execute('UPDATE lines SET total_cents = 1')
except sqlite3.OperationalError as e:
    print('OperationalError:', e)
# [(3, 250, 750)]
# OperationalError: cannot UPDATE generated column "total_cents"
```

| Need | Use |
|---|---|
| A value computed from **other columns of the same row** (`qty * unit_cents`, `length(title)`) | generated column (`VIRTUAL` = computed when read, `STORED` = computed on write and indexable) |
| A different **view of existing data**: a join, a filter, a summary | view |
| An effect on **other rows or tables**, or something that needs the **old value** (`updated_at`, audit, stock) | trigger |
| A rule across several rows or steps with a friendly error message | Python (the repository), backed by a trigger if it must never be bypassed |

## Stored Procedures, Revisited

On Day 19 we said SQLite has no stored procedures. Now you can see the full picture of what plays that role: a **view** is the saved *read*, a **trigger** is the saved *reaction*, a **registered Python function** is the saved *calculation*, and a **repository method** (`lend()`, `return_book()`) is the saved *workflow*.
In PostgreSQL you would write one `CREATE PROCEDURE lend_book(...)`; here you write one method, with the benefit that you can test it with pytest (Day 27) and keep it in version control like all your other code.

Views name your questions and triggers guard your answers. Remember the rule of thumb: rules that must hold for everyone go in the database, workflows go in Python.

## Exercises: Day 22

### Exercises: Level 1

Use a **copy** of your normalized library for all questions (back it up first, Day 19). Put your work in `00_practice/day_22.py`.

1. Create the view `current_loans` (`loan_id, title, member, loaned_on, due_on` for loans not yet returned) and print `SELECT * FROM current_loans ORDER BY due_on, loan_id`.

   ```sh
   loan_id  title                     member        loaned_on   due_on
   -------  ------------------------  ------------  ----------  ----------
   4        The Pragmatic Programmer  Bruno Silva   2025-02-20  2025-03-06
   6        Neuromancer               Chloe Martin  2025-03-01  2025-03-15
   7        Pride and Prejudice       Dev Patel     2025-03-05  2025-03-19
   8        Dune                      Dev Patel     2025-03-08  2025-03-22
   9        Clean Code                Alice Nguyen  2025-03-10  2025-03-24
   10       The Hobbit                Bruno Silva   2025-03-12  2025-03-26
   (6 rows)
   ```

2. Find the view in `sqlite_master`. Expected: `[('view', 'current_loans')]`.
3. Create `overdue_loans` on top of `current_loans`: loans due before `2025-03-14`, with a `days_overdue` column (use `julianday`, cast to integer).

   ```sh
   loan_id  title                     member       due_on      days_overdue
   -------  ------------------------  -----------  ----------  ------------
   4        The Pragmatic Programmer  Bruno Silva  2025-03-06  8
   (1 row)
   ```

4. Count the rows of `current_loans`, insert a new loan (book 4, member 5, loaned `2025-03-14`, due `2025-03-28`) and count again. Expected `(6,)` then `(7,)`. What does this show about views?
5. Try to `INSERT` into `current_loans` and catch the error. Expected: `OperationalError: cannot modify current_loans because it is a view`.
6. Drop `overdue_loans` with `DROP VIEW IF EXISTS` (run it twice: no error the second time) and list the remaining views. Expected: `[('current_loans',)]`.
7. On a fresh copy, create a table `loan_log (id INTEGER PRIMARY KEY, loan_id, action, logged_at DEFAULT (datetime('now')))` and a trigger that inserts `(NEW.id, 'loaned')` after every insert on `loans`. Insert the loan from Q4 and show `loan_id, action` from the log.

   ```sh
   loan_id  action
   -------  ------
   11       loaned
   (1 row)
   ```

8. Insert two more loans for member 5 (books 6 and 8) and count the log rows per action. Expected: `loaned  3`.
9. Add a trigger that logs `'returned'` when `returned_on` changes from `NULL` to a date. Return loan 11 and then try returning it again with a different date. Show the log: the second return must not be logged.

   ```sh
   loan_id  action
   -------  --------
   11       loaned
   12       loaned
   13       loaned
   11       returned
   (4 rows)
   ```

10. List the triggers in `sqlite_master`. Expected: `[('trg_loans_log_insert', 'loans'), ('trg_loans_log_return', 'loans')]` (name yours the same way).
11. Drop the return trigger, return loan 12 and show that no new `returned` row appears. Expected: `(1,)` rows with action `returned`.
12. Create a `TEMP VIEW` in a file database, use it, close the connection, reconnect and show that it is gone. Expected: `OperationalError: no such table: big`.
13. In your own words: what is the difference between a view and a table?
14. In your own words: why do people say triggers are "hidden logic"? Name one situation where a trigger is still the right tool.
15. Create a view `book_catalog (id, title, author, year, genre)` that hides the join to `authors`, then list the Sci-Fi books from it, oldest first.

    ```sh
    id  title              author          year  genre
    --  -----------------  --------------  ----  ------
    1   Dune               Frank Herbert   1965  Sci-Fi
    2   Neuromancer        William Gibson  1984  Sci-Fi
    12  The Martian        Andy Weir       2011  Sci-Fi
    11  Project Hail Mary  Andy Weir       2021  Sci-Fi
    (4 rows)
    ```

### Exercises: Level 2

1. **No double loans.** On a fresh copy, add a `BEFORE INSERT` trigger that aborts when the book is already on loan. Try to lend book 9 (it is out) to member 5, catch the error, then lend book 4 successfully. Print the loan count. Finally call your `LibraryRepository.lend(9, 5, '2025-03-14')` from Day 19 on the same database and see which error you get.

   ```sh
   IntegrityError: book is already on loan
   11
   AlreadyLoanedError: book 9 is already on loan
   ```

2. **updated_at.** Add an `updated_at TEXT` column to `books` and a trigger that sets it to `datetime('now')` whenever a book is updated (guard it so that it cannot loop). Show that no book has `updated_at` at first, update the rating of book 1, and show that only book 1 was touched. Print the length of the timestamp (it is `19`: `2025-03-14 09:30:12`).

   ```sh
   0
   id  title        touched
   --  -----------  -------
   1   Dune         1
   2   Neuromancer  0
   (2 rows)
   19
   ```

3. **A shop view used three times.** On a copy of `shop.db`, create the view `order_totals (order_id, customer_id, order_date, status, line_count, total_cents)`. Use it in three different queries: (a) the five biggest orders by total (ties by order id); (b) delivered orders and revenue (in dollars) per year; (c) the top three customers by total spent on non-cancelled orders.

   ```sh
   order_id  customer_id  total_cents
   --------  -----------  -----------
   48        2            62493
   304       60           62393
   245       14           59993
   225       7            51040
   243       47           49591
   (5 rows)
   year  orders  revenue
   ----  ------  --------
   2024  167     18283.24
   2025  179     22553.3
   (2 rows)
   customer     spent
   -----------  -------
   Lena Green   2214.6
   Amara Kim    2045.68
   Ines Martin  2044.41
   (3 rows)
   ```

4. **At most three open loans.** Write a `BEFORE INSERT` trigger that refuses a loan when the member already has three unreturned books. Lend books 4, 6, 8 and 11 to member 5 in turn and print what happens. Then call `repo.lend(11, 5, ...)` and see the Python exception.

   ```sh
   lent 4
   lent 6
   lent 8
   refused 11 - member already has 3 books out
   LoanLimitError: member 5 already has 3 books out
   ```

5. **Price history.** Create `price_history (book_id, old_price_cents, new_price_cents, changed_at)` and a trigger on `UPDATE OF price_cents` that logs a row **only when the price really changes**. Raise the price of all Tech books by 100 cents, then set book 9 to its current price again. Show the history.

   ```sh
   book_id  old_price_cents  new_price_cents
   -------  ---------------  ---------------
   9        4999             5099
   10       3999             4099
   (2 rows)
   ```

6. **Choose the tool.** For each need, say whether you would use a generated column, a view, a trigger or Python, and why: (a) show `price_cents / 100.0` as dollars on every book; (b) keep a log of who deleted a member; (c) a report of the ten latest loans, used by three different scripts; (d) refuse a loan to a member whose membership has expired, with the message shown to a human. Then prove with `UPDATE` that a generated column cannot be written (`cannot UPDATE generated column`).

### Exercises: Level 3

1. **Stock management.** On an in-memory copy of `shop.db` (use `backup()`), create triggers on `order_items` so that:
   - a new row **decrements `products.stock`** by its quantity,
   - a new row is **refused** with `RAISE(ABORT, 'not enough stock')` when the quantity is larger than the stock (the `BEFORE` check must come before the decrement),
   - a deleted row **puts the quantity back**.

   Create orders 400 (customer 1) and 401 (customer 2), both `pending` and dated `2026-01-05`. Print the stock of products 1, 2 and 3 (it starts at 23, 2 and 63). Then run the inserts below, each in its own `with conn:` block, printing `ok` or `refused` with the message, then the stock again. Finally delete `(400, 1)` and print the stock a last time.

   | order | product | quantity | unit price (cents) |
   |---|---|---|---|
   | 400 | 1 | 3 | 2499 |
   | 400 | 2 | 2 | 999 |
   | 401 | 2 | 1 | 999 |
   | 401 | 1 | 10 | 2499 |
   | 401 | 3 | 100 | 5999 |
   | 401 | 3 | 13 | 5999 |

   ```sh
   [(1, 23), (2, 2), (3, 63)]
   ok      (400, 1, 3)
   ok      (400, 2, 2)
   refused (401, 2, 1) - not enough stock
   ok      (401, 1, 10)
   refused (401, 3, 100) - not enough stock
   ok      (401, 3, 13)
   [(1, 10), (2, 0), (3, 50)]
   [(1, 13), (2, 0), (3, 50)]
   (0,)
   ```

   The last line is the number of products with negative stock. Think about why the table's own `CHECK (stock >= 0)` would also have refused the bad inserts, and what the trigger adds. (Hint: a friendlier message, and it fires *before* any change.)

CONGRATULATIONS !

[<< Day 21](../21_Day_Indexes/21_indexes.md) | [Review 4 >>](../22R_Review_Python_and_sqlite/22R_review_python_and_sqlite.md)
