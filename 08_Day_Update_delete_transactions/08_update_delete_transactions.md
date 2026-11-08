<div align="center">
  <h1> 30 Days Of SQL: Day 8 - UPDATE, DELETE & Transactions</h1>
</div>

[<< Day 7](../07_Day_Aggregates/07_aggregates.md) | [Day 9 >>](../09_Day_Constraints_and_upsert/09_constraints_and_upsert.md)

- [Day 8](#day-8)
  - [Working Safely on a Copy](#working-safely-on-a-copy)
  - [UPDATE](#update)
    - [Updating Rows](#updating-rows)
    - [The Forgotten WHERE](#the-forgotten-where)
    - [Updating with CASE](#updating-with-case)
    - [Updating from Another Table](#updating-from-another-table)
  - [DELETE](#delete)
  - [RETURNING](#returning)
  - [rowcount](#rowcount)
  - [Transactions](#transactions)
    - [Why Transactions Exist](#why-transactions-exist)
    - [ACID in Plain Words](#acid-in-plain-words)
    - [COMMIT and ROLLBACK](#commit-and-rollback)
    - [Transactions in Python](#transactions-in-python)
    - [with conn: The Safe Pattern](#with-conn-the-safe-pattern)
    - [Modern Transaction Control: autocommit=False](#modern-transaction-control-autocommitfalse)
    - [What Other Connections See](#what-other-connections-see)
  - [ Exercises: Day 8](#exercises-day-8)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 8

## Working Safely on a Copy

Today is the first day we **change** data that already exists, and some of the changes are meant to go wrong. That is risky for the twelve
books you have been building. So for every exercise that changes or deletes data, you will first make a **copy** of the table:

```sql
-- syntax
CREATE TABLE copy_name AS SELECT columns FROM original_table;
```

```py
import sqlite3
from helpers import show

conn = sqlite3.connect('00_practice/library.db')
conn.execute('CREATE TABLE books_copy AS SELECT id, title, author, year, pages, genre, price_cents, rating FROM books')
conn.commit()
print(conn.execute('SELECT COUNT(*) FROM books_copy').fetchone())      # (12,)
```

`CREATE TABLE ... AS SELECT` builds a new table from the result of a query, and fills it with the rows. (It copies the data but not
constraints like `PRIMARY KEY`, so it is perfect for experiments. Day 14 returns to it.) Your real `books` table stays untouched, so the expected
output in later days still matches yours.

For the examples we use a small bank table, which suits this topic well:

```py
bank = sqlite3.connect(':memory:')
bank.execute('''
    CREATE TABLE accounts (
        id            INTEGER PRIMARY KEY,
        owner         TEXT NOT NULL,
        balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0)
    ) STRICT
''')
bank.executemany('INSERT INTO accounts (owner, balance_cents) VALUES (?, ?)', [('Ana', 10000), ('Ben', 5000), ('Cy', 0)])
bank.commit()
```

(`CHECK (balance_cents >= 0)` is a rule that refuses negative balances. Day 9 explains constraints.)

## UPDATE

### Updating Rows

`UPDATE` changes values in rows that already exist.

```sql
-- syntax
UPDATE table_name
SET column1 = value1, column2 = value2
WHERE condition;
```

```py
cur = bank.execute("UPDATE accounts SET balance_cents = balance_cents + 500 WHERE owner = 'Ana'")
print(cur.rowcount)      # 1
print(bank.execute('SELECT owner, balance_cents FROM accounts').fetchall())
# [('Ana', 10500), ('Ben', 5000), ('Cy', 0)]
```

The right-hand side can use the row's current values (`balance_cents + 500`). `SET` can change several columns at once, separated by commas.
Remember Day 3: until you `commit()`, this change lives only in your connection.

### The Forgotten WHERE

`UPDATE` without a `WHERE` changes **every row**.

```py
cur = bank.execute('UPDATE accounts SET balance_cents = 0')       # no WHERE!
print(cur.rowcount)                                                # 3
print(bank.execute('SELECT * FROM accounts').fetchall())
# [(1, 'Ana', 0), (2, 'Ben', 0), (3, 'Cy', 0)]
```

Everyone's money is gone. This is one of the classic database disasters, and it can happen to anyone. Two habits protect you:

1. Write the `WHERE` **first**, or test it as a `SELECT` before turning it into an `UPDATE`.
2. Check `cursor.rowcount` after the statement. If you expected one row and it says 3, stop.

And because the change has not been committed, you can still undo it:

```py
bank.rollback()
print(bank.execute('SELECT * FROM accounts').fetchall())
# [(1, 'Ana', 10000), (2, 'Ben', 5000), (3, 'Cy', 0)]
```

`rollback()` throws away everything since the last commit. Transactions are the second half of today's lesson.

### Updating with CASE

`CASE` (Day 6) lets one `UPDATE` treat different rows differently:

```py
bank.execute('''
    UPDATE accounts
    SET balance_cents = CASE WHEN balance_cents >= 10000 THEN balance_cents + 1000
                             ELSE balance_cents + 100 END
''')
print(bank.execute('SELECT owner, balance_cents FROM accounts').fetchall())
# [('Ana', 11000), ('Ben', 5100), ('Cy', 100)]
bank.rollback()
```

### Updating from Another Table

`UPDATE ... FROM` (SQLite 3.33+) takes new values from a second table, matching rows by a condition:

```py
bank.execute('CREATE TABLE bonus (owner TEXT, amount_cents INTEGER)')
bank.executemany('INSERT INTO bonus VALUES (?, ?)', [('Ana', 100), ('Ben', 250)])

bank.execute('''
    UPDATE accounts
    SET balance_cents = balance_cents + bonus.amount_cents
    FROM bonus
    WHERE accounts.owner = bonus.owner
''')
print(bank.execute('SELECT owner, balance_cents FROM accounts').fetchall())
# [('Ana', 10100), ('Ben', 5250), ('Cy', 0)]
bank.rollback()
```

Only Ana and Ben had a matching bonus row, so Cy was not changed. This is a first taste of combining two tables, which is the topic of Days 11 and 12.

> **In other databases:** PostgreSQL and SQL Server also have `UPDATE ... FROM`, but MySQL writes it as `UPDATE a JOIN b ON ... SET ...`.
> The older portable version uses a subquery (Day 13).

## DELETE

`DELETE` removes rows. It has no column list, since it always removes whole rows.

```sql
-- syntax
DELETE FROM table_name WHERE condition;
```

```py
cur = bank.execute('DELETE FROM accounts WHERE balance_cents = 0')
print(cur.rowcount)      # 1     Cy's account
bank.rollback()
```

And just like `UPDATE`, `DELETE FROM accounts` with no `WHERE` deletes **everything**. The table survives but is empty. (To remove the table itself,
use `DROP TABLE`.)

## RETURNING

Often you want to know exactly which rows an `UPDATE` or `DELETE` touched. Add `RETURNING` (SQLite 3.35+) and the statement hands those rows back, like a `SELECT`:

```py
cur = bank.execute('''
    UPDATE accounts SET balance_cents = balance_cents - 100
    WHERE owner = 'Ben'
    RETURNING id, owner, balance_cents
''')
print(cur.fetchall())        # [(2, 'Ben', 4900)]
```

```py
cur = bank.execute("DELETE FROM accounts WHERE owner = 'Cy' RETURNING *")
print(cur.fetchall())        # [(3, 'Cy', 0)]
```

`RETURNING` works for `INSERT` too, and is a clean way to get a new row's generated `id`:

```py
cur = bank.execute("INSERT INTO accounts (owner, balance_cents) VALUES ('Dee', 1) RETURNING id")
print(cur.fetchone())        # (3,)
bank.rollback()
```

(`RETURNING` is available in PostgreSQL and DuckDB too. MySQL doesn't have it.)

## rowcount

`cursor.rowcount` is the number of rows the last `INSERT`, `UPDATE` or `DELETE` changed. An `UPDATE` whose `WHERE` matches nothing is **not an error**, it simply
changes 0 rows, so the count is the only way to notice:

```py
cur = bank.execute("UPDATE accounts SET owner = 'Zed' WHERE owner = 'Nobody'")
print(cur.rowcount)          # 0
```

## Transactions

### Why Transactions Exist

Moving 25 dollars from Ana to Ben takes **two** updates: subtract from Ana, add to Ben.

```py
bank.execute("UPDATE accounts SET balance_cents = balance_cents - 2500 WHERE owner = 'Ana'")
# ... the program crashes, or the power goes out, right here ...
bank.execute("UPDATE accounts SET balance_cents = balance_cents + 2500 WHERE owner = 'Ben'")
```

If anything fails between the two lines, 25 dollars simply vanish. A **transaction** groups statements so they succeed or fail **together**.

### ACID in Plain Words

Databases promise four things about transactions, abbreviated **ACID**:

- **A**tomic: all of a transaction's changes happen, or none do. There is no half way.
- **C**onsistent: a transaction moves the database from one valid state to another. Rules such as `CHECK` and `FOREIGN KEY` are never left broken.
- **I**solated: other connections do not see your half-finished work.
- **D**urable: once committed, a change survives a crash or power cut.

SQLite gives you all four, even though it is "just a file".

### COMMIT and ROLLBACK

In SQL itself:

```sql
BEGIN;                                   -- start a transaction
UPDATE accounts SET balance_cents = balance_cents - 2500 WHERE owner = 'Ana';
UPDATE accounts SET balance_cents = balance_cents + 2500 WHERE owner = 'Ben';
COMMIT;                                  -- make both permanent   (or: ROLLBACK to undo both)
```

Everything between `BEGIN` and `COMMIT` is one unit. `ROLLBACK` throws all of it away.

### Transactions in Python

You have not written `BEGIN` yet, but you have been using transactions all along. In Python's default mode, the `sqlite3` module silently runs a `BEGIN` just
before the first `INSERT`, `UPDATE` or `DELETE`, which is why you needed `commit()` on Day 3. You can see this with `in_transaction`:

```py
print(bank.in_transaction)                                        # False
bank.execute("UPDATE accounts SET owner = 'X' WHERE id = 1")
print(bank.in_transaction)                                        # True
bank.rollback()
```

`commit()` ends the transaction and saves it. `rollback()` ends it and undoes it. Reading with `SELECT` does not start one.

### with conn: The Safe Pattern

Calling `commit()` and `rollback()` by hand is easy to get wrong, especially with errors. The connection works as a **context manager** (Python's `with` statement) that does the right
thing for you: it commits if the block finishes, and rolls back if an exception escapes.

```py
try:
    with bank:
        bank.execute("UPDATE accounts SET balance_cents = balance_cents - 1000 WHERE owner = 'Ana'")
        bank.execute("UPDATE accounts SET balance_cents = balance_cents + 1000 WHERE owner = 'Ben'")
        raise RuntimeError('boom')          # something goes wrong after both updates
except RuntimeError as e:
    print('error:', e)

print(bank.execute('SELECT owner, balance_cents FROM accounts').fetchall())
# [('Ana', 10000), ('Ben', 5000), ('Cy', 0)]      nothing changed: the whole transaction was rolled back
```

Without the error, the `with` block commits at the end. Here is a transfer function built on this idea. It either moves the money or moves nothing:

```py
def transfer(conn, from_id, to_id, amount_cents):
    with conn:
        taken = conn.execute('UPDATE accounts SET balance_cents = balance_cents - ? WHERE id = ?', (amount_cents, from_id)).rowcount
        given = conn.execute('UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?', (amount_cents, to_id)).rowcount
        if taken != 1 or given != 1:
            raise ValueError('unknown account')       # rolls back both updates

transfer(bank, 1, 2, 2500)
print(bank.execute('SELECT owner, balance_cents FROM accounts').fetchall())
# [('Ana', 7500), ('Ben', 7500), ('Cy', 0)]
```

Two ways it can fail, and both leave the balances untouched: paying more than Ana has trips the `CHECK` (an `IntegrityError`), and sending to an account that does not exist changes
0 rows, so we raise our own error. In both cases the `with` block rolls the first update back.

**Common mistake:** `with conn:` commits or rolls back, but it does **not close** the connection. Call `conn.close()` yourself (or wrap it in `contextlib.closing`, Day 19).

### Modern Transaction Control: autocommit=False

Python's default behaviour of "guess when to `BEGIN`" is a historical quirk. Since Python 3.12 you can ask for clearer behaviour with the `autocommit` argument:

```py
conn = sqlite3.connect('00_practice/library.db', autocommit=False)
```

With `autocommit=False` a transaction is **always open**: it starts as soon as you connect and a new one starts right after each `commit()` or `rollback()`. Nothing is saved
until you commit, and closing without committing discards your changes. That is simple to remember: *you always commit explicitly*. The `with conn:` pattern works the same
way (commit on success, rollback on error).

There is also `autocommit=True`, where every statement is saved immediately and you manage transactions yourself with `BEGIN` / `COMMIT` / `ROLLBACK` in SQL. The default,
`LEGACY_TRANSACTION_CONTROL`, is the "guess" behaviour described above, kept for backwards compatibility.

> **Older code:** most tutorials and existing programs use the default mode and the old `isolation_level` argument. That is why we taught `commit()` the old way first.
> It keeps working, and you will keep meeting it. For new code, prefer `autocommit=False`, because the behaviour no longer depends on which statement you ran.
> The course examples work in either mode.

### What Other Connections See

Isolation in action, with two connections to the same file:

```py
a = sqlite3.connect('demo.db')
a.execute('DROP TABLE IF EXISTS t')          # so you can run this more than once
a.execute('CREATE TABLE t (x INTEGER)')
a.commit()
b = sqlite3.connect('demo.db')

a.execute('INSERT INTO t VALUES (1)')
print('writer sees:', a.execute('SELECT COUNT(*) FROM t').fetchone()[0],
      '| other connection sees:', b.execute('SELECT COUNT(*) FROM t').fetchone()[0])
# writer sees: 1 | other connection sees: 0

a.commit()
print('after commit, other connection sees:', b.execute('SELECT COUNT(*) FROM t').fetchone()[0])
# after commit, other connection sees: 1
```

Nobody sees your half-finished work. While one connection has uncommitted changes, SQLite lets other connections read but makes them wait or fail if they want to write, a story we continue on Day 19.

Changing data safely is the foundation of every real application. Now do some exercises, but remember: **work on the copy**.

## Exercises: Day 8

### Exercises: Level 1

All of these use the copy `books_copy` (see the top of the lesson), so do them in order. Commit after each step unless an exercise says otherwise.

1. Create `books_copy` with `CREATE TABLE ... AS SELECT` from `books` (columns `id, title, author, year, pages, genre, price_cents, rating`), commit, and check that it has 12 rows.
2. Set the rating of `Emma` to `4.2` and print that book's title and rating.
3. Add 1 to the `pages` of **every** book in the copy, and print the total number of pages. (It was 4908 in the original.)
4. Rename the genre `Sci-Fi` to `Science Fiction`. Print how many rows changed, and the number of books per genre.
5. Reduce the price of all `Tech` books by 10%, using integer math: `price_cents * 9 / 10`. Show the title and new price of the Tech books, ordered by title.
6. Delete the book with `id = 12`. Print the `rowcount` and the number of books left.
7. Delete every book published before 1900 with `RETURNING`, and print the `id` and title of what was deleted.
8. **Accident!** Run `DELETE FROM books_copy` without a `WHERE`. Print how many rows it deleted and the count of remaining books, then `rollback()` and print the count again.
9. Use `UPDATE ... RETURNING` to set Dune's rating to `4.9` and print the whole returned row.
10. Use `with conn:` to change the ratings of `Neuromancer` (to `4.0`) and `The Hobbit` (to `4.8`) in one transaction, then show both books.
11. Run an `UPDATE` that matches no book (use a title that does not exist) and print its `rowcount`.
12. Drop the `books_copy` table and commit. Print the table names in the database to check that only your real tables are left.

```sh
# expected for exercise 4 (second part)
genre            books
---------------  -----
Dystopian        2
Fantasy          2
Romance          2
Science Fiction  4
Tech             2
(5 rows)

# expected for exercise 5
title                     price_cents
------------------------  -----------
Clean Code                3599
The Pragmatic Programmer  4499
(2 rows)

# expected for exercise 8
deleted 9 -> (0,)
after rollback (9,)
```

### Exercises: Level 2

1. Create this `accounts` table in an in-memory database (Ana 10,000 cents, Ben 5,000, Cy 0). Write `transfer(conn, from_id, to_id, amount_cents)` that is **all-or-nothing**. It
   must raise an error and leave the balances unchanged when the sender lacks the money (the `CHECK` does that) **and** when either account does not exist. Show the balances
   after a good transfer and after each of the two failing ones.

   ```py
   bank.execute('''
       CREATE TABLE accounts (
           id INTEGER PRIMARY KEY, owner TEXT NOT NULL,
           balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0)
       ) STRICT
   ''')
   ```

   ```sh
   [('Ana', 7500), ('Ben', 7500), ('Cy', 0)]            # after transfer(bank, 1, 2, 2500)
   IntegrityError CHECK constraint failed: balance_cents >= 0
   [('Ana', 7500), ('Ben', 7500), ('Cy', 0)]            # after transfer(bank, 1, 2, 999999)
   ValueError unknown account
   [('Ana', 7500), ('Ben', 7500), ('Cy', 0)]            # after transfer(bank, 1, 99, 100)
   ```

2. Start again with a fresh `accounts` table (Ana 10,000, Ben 5,000, Cy 0). Pay interest in a single `UPDATE` using `CASE`: accounts with at least 10,000 cents get 2%, all others get 1%
   (use integer math: `balance_cents * rate / 100`).

   ```sh
   [('Ana', 10200), ('Ben', 5050), ('Cy', 0)]
   ```

3. **Soft delete.** Instead of really deleting rows, many applications mark them as deleted. Make a table `books_soft` from `books` (`id, title`), add a column
   `is_deleted INTEGER NOT NULL DEFAULT 0`, "delete" the books with ids 1 and 2 by setting `is_deleted = 1`, and count the books that are still active. Then restore book 1 and count again. Name one advantage and one disadvantage of soft deletes.

   ```sh
   (10,)
   (11,)
   ```

4. Create `books_copy (id, title, price_cents)` from `books` and a table `new_prices (title, new_price_cents)` containing `('Dune', 1199)`, `('Emma', 699)` and `('Unknown Book', 100)`. Use
   `UPDATE ... FROM` with `RETURNING` to apply the new prices and print the changed titles and prices. What happens to the `Unknown Book` row?

   ```sh
   [('Dune', 1199), ('Emma', 699)]
   ```

5. In your own words: describe what could go wrong in a money transfer that uses two separate `UPDATE`s *without* a transaction, and explain how a transaction fixes it.

6. Prove isolation. With two connections to the same database file, insert a row in connection A **without** committing and count the rows from both connections. Commit, and count again.

   ```sh
   writer sees: 1 | other connection sees: 0
   after commit, other connection sees: 1
   ```

### Exercises: Level 3

Use `00_practice/datasets.db`. As before, work on copies.

1. Create `countries_copy` from `countries` (`CREATE TABLE countries_copy AS SELECT * FROM countries`). The populations of five countries changed. Update them from this dictionary with
**one** `executemany` call and named placeholders, print the total `rowcount` (it should be `5`), and show the five rows.

   ```py
   new_pops = {'Canada': 38000000, 'Finland': 5500000, 'Japan': 125000000, 'Brazil': 212000000, 'Norway': 5400000}
   ```

   ```sh
   5
   name     population
   -------  ----------
   Brazil   212000000
   Canada   38000000
   Finland  5500000
   Japan    125000000
   Norway   5400000
   (5 rows)
   ```

2. Delete the countries with a population of 0 from the copy using `RETURNING`, and print how many there were and their names. How many countries remain?

   ```sh
   2 ['Bouvet Island', 'Heard Island and McDonald Islands']
   (248,)
   ```

3. Create `hn_copy` from `hn_posts`. Without committing the changes below, (a) lower-case every author name that is not already lower case, and print how many rows changed, (b) delete the posts
   with fewer than 3 points and print how many were removed and how many remain, then (c) `rollback()` and prove the table is back to 20,099 rows.

   ```sh
   authors changed: 2333
   posts removed: 4654
   posts left: 15445
   after rollback: 20099
   ```

CONGRATULATIONS !

[<< Day 7](../07_Day_Aggregates/07_aggregates.md) | [Day 9 >>](../09_Day_Constraints_and_upsert/09_constraints_and_upsert.md)
