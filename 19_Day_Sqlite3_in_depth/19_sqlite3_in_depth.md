<div align="center">
  <h1> 30 Days Of SQL: Day 19 - The sqlite3 Module in Depth</h1>
</div>

[<< Review 3](../18R_Review_Analytical_sql/18R_review_analytical_sql.md) | [Day 20 >>](../20_Day_Import_clean_export/20_import_clean_export.md)

- [Day 19](#day-19)
  - [Connection and Cursor](#connection-and-cursor)
    - [Fetching in Pieces](#fetching-in-pieces)
    - [rowcount and lastrowid](#rowcount-and-lastrowid)
  - [Rows by Name](#rows-by-name)
    - [sqlite3.Row](#sqlite3row)
    - [A Dictionary Row Factory](#a-dictionary-row-factory)
    - [Dataclass Records](#dataclass-records)
  - [Errors](#errors)
  - [Connections as Context Managers](#connections-as-context-managers)
  - [Running Many Statements: executescript](#running-many-statements-executescript)
  - [Your Own SQL Functions](#your-own-sql-functions)
    - [Scalar Functions with create_function](#scalar-functions-with-create_function)
    - [The REGEXP Operator](#the-regexp-operator)
    - [Aggregate Functions with create_aggregate](#aggregate-functions-with-create_aggregate)
  - [Adapters and Converters](#adapters-and-converters)
  - [Copies, Dumps and Several Databases](#copies-dumps-and-several-databases)
    - [backup](#backup)
    - [iterdump](#iterdump)
    - [ATTACH DATABASE](#attach-database)
  - [Stored Procedures: The Missing Feature](#stored-procedures-the-missing-feature)
  - [The LibraryRepository Contract](#the-libraryrepository-contract)
  - [Concurrency: Many Readers, One Writer](#concurrency-many-readers-one-writer)
    - [database is locked](#database-is-locked)
    - [The Busy Timeout](#the-busy-timeout)
    - [WAL Mode](#wal-mode)
    - [Threads](#threads)
  - [ Browsing Your Database](#browsing-your-database)
  - [ Exercises: Day 19](#exercises-day-19)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 19

You have used `sqlite3` for eighteen days, but mostly through `connect`, `execute` and `fetchall`. This is the module's second half: getting rows back in a friendlier shape, handling errors properly,
teaching SQLite new tricks with your own Python functions, copying databases, and sharing a database between several connections or threads. At the end we pin down a small class, the
`LibraryRepository`, that wraps the library from Day 10. Days 22, 27 and 28 build on it, so take the contract section seriously.

The examples use the normalized library from Day 10 (12 books, 5 members, 10 loans). When an example changes data, work on a **copy** (you will see how to make one in a moment).

## Connection and Cursor

A **connection** is the open database: it owns the file, the transaction and the settings. A **cursor** is one "reader head" moving through the result of one statement. `conn.execute(...)` is a shortcut
that creates a cursor for you, runs the statement and returns the cursor, which is why `conn.execute(...).fetchall()` works.

You only need explicit cursors when you want several statements in flight at once, for example reading one result while running another query for every row.

### Fetching in Pieces

```py
# syntax
cur.fetchone()       # the next row, or None when the rows run out
cur.fetchmany(n)     # up to n rows (a list; empty when there is nothing left)
cur.fetchall()       # every remaining row
for row in cur: ...  # one row at a time, no big list in memory
```

A cursor remembers its position. Each fetch continues where the previous one stopped:

```py
import sqlite3
from helpers import show

conn = sqlite3.connect('00_practice/library.db')
cur = conn.execute('SELECT id, title FROM books ORDER BY id')
print(cur.fetchmany(3))
print(cur.fetchone())
for row in cur:
    print(row)
    break
print(cur.description[0])
# [(1, 'Dune'), (2, 'Neuromancer'), (3, 'The Hobbit')]
# (4, 'The Name of the Wind')
# (5, 'Pride and Prejudice')
# ('id', None, None, None, None, None, None)
```

`cur.description` has one 7-tuple per column. Only the first item, the name, is filled in; that is exactly what your `show()` helper reads.

For a result with a million rows, `fetchall()` builds a million-item list. Iterating the cursor or calling `fetchmany(1000)` in a loop keeps memory flat:

```py
cur = conn.execute('SELECT id FROM books ORDER BY id')
while batch := cur.fetchmany(5):        # the walrus operator: assign and test at once
    print(len(batch), end=' ')
# 5 5 2
```

### rowcount and lastrowid

After `INSERT`, `UPDATE` and `DELETE`, `cur.rowcount` tells you how many rows were changed, and after an `INSERT`, `cur.lastrowid` is the new row's id (you met both on Day 3).

```py
cur = conn.execute('UPDATE books SET rating = 4.0 WHERE rating IS NULL')
print(cur.rowcount)     # 3
conn.rollback()         # undo it, this was only a demonstration
```

`rowcount` is how `return_book` will know whether there was a loan to close. After a `SELECT`, `rowcount` is `-1` (SQLite does not know in advance how many rows a query will give).

## Rows by Name

By default every row is a plain tuple, and `row[2]` means "whatever the third column was". That is fragile: reorder the `SELECT` list and the code silently reads the wrong value. A **row factory**
turns each row into something you can address by name.

### sqlite3.Row

```py
# syntax
conn.row_factory = sqlite3.Row
```

```py
conn.row_factory = sqlite3.Row
row = conn.execute('SELECT id, title, year FROM books WHERE id = 1').fetchone()
print(row['title'], row[2])
print(row.keys())
print(dict(row))
print(tuple(row))
print(type(row))
# Dune 1965
# ['id', 'title', 'year']
# {'id': 1, 'title': 'Dune', 'year': 1965}
# (1, 'Dune', 1965)
# <class 'sqlite3.Row'>
```

A `sqlite3.Row` works with names *and* with indexes, converts to a `dict` or a tuple, and is cheap. Column names match case-insensitively, and an alias (`AS`) changes the name, so
`SELECT price_cents / 100.0 AS price` gives you `row['price']`.

>  `sqlite3.Row` is what most Python code uses. Set it once right after `connect()`. Your `show()` helper keeps working because it only uses `cur.description` and `fetchall()`, and a `Row` unpacks like a tuple.

### A Dictionary Row Factory

A row factory is any function `(cursor, row) -> anything`. If you want real dictionaries, for example to hand to `json.dumps`, write one:

```py
def dict_factory(cursor, row):
    return {col[0]: value for col, value in zip(cursor.description, row)}

conn.row_factory = dict_factory
print(conn.execute('SELECT id, title FROM books WHERE id = 2').fetchone())
# {'id': 2, 'title': 'Neuromancer'}
```

### Dataclass Records

A dictionary has no fixed shape, and a typo in a key is only found at run time. For data that has a stable shape, use a `@dataclass`. Python 3.12 lets you unpack a `Row` straight into it with `**`:

```py
from dataclasses import dataclass

@dataclass
class Member:
    id: int
    name: str
    email: str
    joined_on: str

conn.row_factory = sqlite3.Row
members = [Member(**row) for row in conn.execute('SELECT * FROM members ORDER BY id')]
print(members[0])
# Member(id=1, name='Alice Nguyen', email='alice@example.com', joined_on='2024-01-15')
```

(`SELECT *` is acceptable here because the dataclass names exactly the columns we expect and `Member(**row)` fails loudly if the table gains or loses a column.) Add `frozen=True` to make
records immutable, which is the right default for rows you read from a database. The repository below does that.

**In other databases:** every Python driver has its own version of this. `psycopg` has `row_factory=dict_row`, `pymysql` has `DictCursor`, and `sqlalchemy` rows are named tuples. The idea is the same.

## Errors

All errors from the module inherit from `sqlite3.Error`. The ones you will meet:

```
Exception
└── sqlite3.Error
    ├── sqlite3.InterfaceError
    └── sqlite3.DatabaseError
        ├── sqlite3.OperationalError     (syntax errors, no such table/column, database is locked)
        ├── sqlite3.IntegrityError       (NOT NULL, UNIQUE, CHECK, FOREIGN KEY violations)
        ├── sqlite3.ProgrammingError     (wrong number of parameters, using a closed connection)
        ├── sqlite3.DataError
        ├── sqlite3.InternalError
        └── sqlite3.NotSupportedError
```

Catch the **narrowest** one you can handle, and let the rest crash loudly:

```py
for sql in ('SELEC 1',
            'SELECT * FROM bookz',
            'SELECT ?',
            "INSERT INTO members (name, email, joined_on) VALUES ('x', 'alice@example.com', '2025-01-01')"):
    try:
        conn.execute(sql)
    except sqlite3.Error as e:
        print(type(e).__name__, '-', e)
# OperationalError - near "SELEC": syntax error
# OperationalError - no such table: bookz
# ProgrammingError - Incorrect number of bindings supplied. The current statement uses 1, and there are 0 supplied.
# IntegrityError - UNIQUE constraint failed: members.email
```

Since Python 3.11 the exception also carries `e.sqlite_errorcode` and `e.sqlite_errorname` (for example `'SQLITE_CONSTRAINT_UNIQUE'`) when SQLite supplied them, which is handy for telling a duplicate email from a failed `CHECK`
without parsing the message text.

**Common mistake:** `except Exception: pass` around database code. If the insert fails and you hide it, your program carries on believing the row exists.

## Connections as Context Managers

You met `with conn:` on Day 8: the block is one transaction, committed if it finishes and rolled back if it raises. Here is the surprise that catches nearly everybody:

```py
try:
    with conn:
        conn.execute("INSERT INTO authors (name) VALUES ('Temp')")
        raise ValueError('boom')
except ValueError:
    pass
print(conn.execute('SELECT COUNT(*) FROM authors').fetchone()[0])   # 10: the insert was rolled back

with conn:
    conn.execute('SELECT 1')
conn.execute('SELECT 1')
print('still open')                                                  # still open
```

**`with conn:` does not close the connection.** It only ends the transaction. A connection often outlives many transactions, so closing it would be the wrong default. To close it as well, wrap it in
`contextlib.closing`:

```py
from contextlib import closing

with closing(sqlite3.connect(':memory:')) as c2:
    print(c2.execute('SELECT 42').fetchone()[0])
try:
    c2.execute('SELECT 1')
except sqlite3.ProgrammingError as e:
    print(e)
# 42
# Cannot operate on a closed database.
```

The usual pattern for a script that opens, uses and closes a database combines both:

```py
with closing(sqlite3.connect('00_practice/library.db')) as conn:
    with conn:                      # one transaction
        conn.execute('...')
```

(Python 3.12 with `autocommit=False` behaves the same way for `with conn:`: commit on success, rollback on error, no close.)

## Running Many Statements: executescript

`execute` runs exactly one statement. `executescript` runs a whole script of statements separated by `;`, which is perfect for **schema files** and migrations:

```py
c3 = sqlite3.connect(':memory:')
c3.executescript('''
    CREATE TABLE a (x INTEGER);
    INSERT INTO a VALUES (1), (2);
    CREATE TABLE b (y TEXT);
''')
print(c3.execute('SELECT name FROM sqlite_master ORDER BY name').fetchall())
# [('a',), ('b',)]
```

Things to know:

- It takes **no parameters**. You cannot use `?` in it.
- It first issues a `COMMIT` for any pending transaction, so it is not part of your transaction. (Put `BEGIN; ... COMMIT;` inside the script if you want one.)
- It is meant for text you wrote or a file you ship with your program.  Never pass user input to it: the single-statement `execute` refuses to run `a; DROP TABLE b`, but `executescript` happily runs both (Day 27 shows the attack).

A typical use is loading a `.sql` file: `conn.executescript(Path('schema.sql').read_text(encoding='utf-8'))`. That is exactly what `tools/build_shop_db.py` does with `data/shop.sql`.

## Your Own SQL Functions

SQLite has no `slugify` or regular expressions out of the box, but you can lend it your Python functions. After you register one, it is usable in any query on that connection.

### Scalar Functions with create_function

```py
# syntax
conn.create_function(name, num_args, python_callable, deterministic=True)
```

```py
import re

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

conn.create_function('slugify', 1, slugify, deterministic=True)
show(conn.execute('SELECT title, slugify(title) AS slug FROM books ORDER BY id LIMIT 4'))
```

```sh
output
title                 slug
--------------------  --------------------
Dune                  dune
Neuromancer           neuromancer
The Hobbit            the-hobbit
The Name of the Wind  the-name-of-the-wind
(4 rows)
```

`deterministic=True` promises "same input, same output, no side effects", which lets SQLite use the function in indexes and cache calls. Leave it off for anything that reads a clock or random numbers.
Notes: a function that returns `None` gives SQL `NULL`; a `NULL` argument arrives as `None`, so handle it; the function exists only on **this connection**, so register it every time you connect.

### The REGEXP Operator

SQLite parses `x REGEXP y` but ships no implementation. It simply calls a user function named `regexp(pattern, text)`. Define it and the operator works (note the argument order: pattern first):

```py
conn.create_function('regexp', 2,
                     lambda pattern, text: text is not None and re.search(pattern, text) is not None,
                     deterministic=True)
print(conn.execute("SELECT title FROM books WHERE title REGEXP '^The ' ORDER BY title").fetchall())
# [('The Hobbit',), ('The Martian',), ('The Name of the Wind',), ('The Pragmatic Programmer',)]
```

**In other databases:** PostgreSQL uses `~` (`title ~ '^The '`), MySQL has `REGEXP` / `RLIKE`, and DuckDB has `regexp_matches()`. Regular expressions are an extension in SQLite, so portable SQL avoids them.

### Aggregate Functions with create_aggregate

An aggregate is a class with a `step(value)` method called once per row and a `finalize()` method that returns the result. SQLite has no `MEDIAN`, so build one:

```py
class Median:
    def __init__(self):
        self.values = []

    def step(self, value):
        if value is not None:
            self.values.append(value)

    def finalize(self):
        if not self.values:
            return None
        s = sorted(self.values)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2

conn.create_aggregate('median', 1, Median)
show(conn.execute('SELECT genre, median(pages) AS median_pages, COUNT(*) AS n FROM books GROUP BY genre ORDER BY genre'))
```

```sh
output
genre      median_pages  n
---------  ------------  -
Dystopian  319.5         2
Fantasy    486.0         2
Romance    376.5         2
Sci-Fi     422.5         4
Tech       408.0         2
(5 rows)
```

(Window-function versions come with `create_window_function`, which also needs `value` and `inverse` methods. You will rarely need it.)

## Adapters and Converters

Python types that SQLite does not know (`date`, `datetime`, your own classes) must be converted to one of the five storage classes. The module has two hooks for this: **adapters** (Python to SQLite) and
**converters** (SQLite to Python, enabled with `detect_types`).

Python used to register adapters for `date` and `datetime` automatically. **Since Python 3.12 those default adapters and converters are deprecated** and emit a `DeprecationWarning`:

```py
import datetime, warnings

c4 = sqlite3.connect(':memory:')
c4.execute('CREATE TABLE t (d TEXT)')
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    c4.execute('INSERT INTO t VALUES (?)', (datetime.date(2025, 3, 14),))
    print(caught[0].category.__name__ + ':', caught[0].message)
# DeprecationWarning: The default date adapter is deprecated as of Python 3.12; see the sqlite3 documentation for suggested replacement recipes
```

The course's rule (since Day 2) is the cleanest fix: **convert explicitly, at the edges.** Store ISO text, and turn it back into a `date` yourself:

```py
c4.execute('DELETE FROM t')
c4.execute('INSERT INTO t VALUES (?)', (datetime.date(2025, 3, 14).isoformat(),))
d = datetime.date.fromisoformat(c4.execute('SELECT d FROM t').fetchone()[0])
print(d, type(d).__name__)
# 2025-03-14 date
```

If you do want automatic conversion for a type of your own, register an adapter. This one lets you pass a `Money` object as a parameter and stores it as integer cents:

```py
class Money:
    def __init__(self, cents):
        self.cents = cents

sqlite3.register_adapter(Money, lambda m: m.cents)
print(c4.execute('SELECT ?', (Money(1099),)).fetchone())
# (1099,)
```

Registering adapters is global to your program, and implicit conversions hide what is stored. That is why most code, including ours, prefers explicit `.isoformat()` and `fromisoformat()`.

> **Older code:** you will see `sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)` with columns declared `TIMESTAMP` or `DATE`. It still works but is deprecated in 3.12 and does not work with `STRICT` tables
> (which only allow the five real types). Prefer ISO text plus explicit conversion.

## Copies, Dumps and Several Databases

### backup

`conn.backup(target)` copies a whole database into another connection, **safely, even while other connections are using it**. It is the right way to snapshot a database. (Copying the file with `shutil.copy`
while someone writes to it can give you a corrupt copy.) It also works from or to `:memory:`:

```py
# syntax
source_conn.backup(target_conn)
```

```py
dest = sqlite3.connect('00_practice/library_copy.db')
conn.backup(dest)
print(dest.execute('SELECT COUNT(*) FROM books').fetchone())
dest.close()
# (12,)
```

Use this to make the "work on a copy" step in exercises: back up first, then experiment on the copy.

### iterdump

`conn.iterdump()` yields the SQL text that would rebuild the database: `CREATE TABLE` and `INSERT` statements. It is how you get a plain-text, version-control-friendly backup:

```py
dump = list(conn.iterdump())
print(len(dump), dump[0])
# 43 BEGIN TRANSACTION;

from pathlib import Path
Path('00_practice/library_dump.sql').write_text('\n'.join(dump), encoding='utf-8')
```

(`data/shop.sql` is this idea in reverse: a dump you load with `executescript`.)

### ATTACH DATABASE

One connection can have **several database files open at once**. `ATTACH` adds one under a schema name, and you refer to its tables as `schema.table`. The original is called `main`.

```sql
-- syntax
ATTACH DATABASE 'path/to/file.db' AS alias;
SELECT ... FROM alias.table_name;
DETACH DATABASE alias;
```

```py
conn.execute('ATTACH DATABASE ? AS archive', ('00_practice/library_copy.db',))   # the path can be a ? parameter
print(conn.execute('SELECT (SELECT COUNT(*) FROM main.books), (SELECT COUNT(*) FROM archive.books)').fetchone()[:])
print([r[1] for r in conn.execute('PRAGMA database_list')])
# (12, 12)
# ['main', 'archive']
```

You can join across them, copy rows with `INSERT INTO archive.books SELECT ...`, and compare old and new versions with an anti-join (Exercise L2 Q4). Everything in one transaction, even across files.

## Stored Procedures: The Missing Feature

In PostgreSQL, MySQL, SQL Server and Oracle you can store a named block of SQL *inside the database*: a **stored procedure** (`CREATE PROCEDURE lend_book(...)`, called with `CALL lend_book(...)`) or a stored function. It has parameters, can run
several statements, use variables and loops, and everyone who connects, in any language, can call it.

**SQLite has no stored procedures.** There is no server process to run them: the database is a file and your program is already running next to it. The role is played by **your Python code**: a function that takes
parameters, runs several statements inside one `with conn:` transaction, and returns a result. That is exactly what `LibraryRepository.lend()` is, as you are about to see. When you want logic that
runs *inside* SQL (in queries, or automatically when data changes), SQLite offers three things: functions you register from Python (above), **triggers** and **views** (Day 22).

**In other databases:** `CREATE PROCEDURE` / `CALL` (MySQL, PostgreSQL 11+), `EXEC` (SQL Server), PL/pgSQL, T-SQL and PL/SQL are the languages those procedures are written in. The trade-off: logic in the
database is shared by every client and runs next to the data, but is harder to test, version and debug than Python.

## The LibraryRepository Contract

A **repository** is a class that hides the SQL for one area of your application. The rest of the program says `repo.lend(book_id, member_id, '2025-03-14')` and never sees a `SELECT`. This separation pays off
three times in this course: on Day 22 we add triggers *under* it without changing callers, on Day 27 you test it with pytest, and on Day 28 the command line app is built on it.

Because later days depend on it, here is the exact **contract**. Your class must match it. All dates are ISO text (`'YYYY-MM-DD'`) passed in by the caller; the repository never reads the clock, which
keeps it testable. Money is integer cents.

```py
# 00_practice/library_repo.py  (the contract: you write the bodies)
import sqlite3
from dataclasses import dataclass
from pathlib import Path


class LibraryError(Exception): ...                    # base class for all business-rule errors
class NotFoundError(LibraryError): ...                # unknown book/member, or a return of a book that is not out
class AlreadyLoanedError(LibraryError): ...           # lend() of a book that is currently out
class LoanLimitError(LibraryError): ...               # lend() to a member who already has MAX_LOANS books out


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str                  # the author's name (joined from authors)
    year: int | None
    pages: int | None
    genre: str | None
    price_cents: int | None
    rating: float | None


@dataclass(frozen=True)
class Loan:
    id: int
    book_id: int
    member_id: int
    loaned_on: str
    due_on: str
    returned_on: str | None


@dataclass(frozen=True)
class OverdueLoan:
    loan_id: int
    title: str
    member: str                  # the member's name
    due_on: str
    days_overdue: int


class LibraryRepository:
    MAX_LOANS = 3                # a member may have at most 3 unreturned books
    LOAN_DAYS = 14               # due_on = loaned_on + 14 days

    def __init__(self, conn: sqlite3.Connection) -> None: ...
    #   stores conn, sets conn.row_factory = sqlite3.Row and runs PRAGMA foreign_keys = ON

    @classmethod
    def open(cls, path: str | Path) -> "LibraryRepository": ...      # sqlite3.connect(path) wrapped in a repository

    def close(self) -> None: ...

    # --- books and authors
    def add_author(self, name: str) -> int: ...
    #   id of the author; creates the row if the name is new, otherwise returns the existing id
    def add_book(self, title: str, author: str, *, year: int | None = None, pages: int | None = None,
                 genre: str | None = None, price_cents: int | None = None, rating: float | None = None) -> int: ...
    #   creates the author if needed, inserts the book, returns the new book id. Constraint violations raise sqlite3.IntegrityError
    def get_book(self, book_id: int) -> Book | None: ...
    def find_by_author(self, fragment: str) -> list[Book]: ...
    #   books whose author name contains fragment (case-insensitive), ordered by year, then title
    def search_books(self, keyword: str) -> list[Book]: ...
    #   books whose title contains keyword (case-insensitive), ordered by title

    # --- members
    def add_member(self, name: str, email: str, joined_on: str) -> int: ...
    #   returns the new member id; a duplicate email raises sqlite3.IntegrityError

    # --- loans
    def is_available(self, book_id: int) -> bool: ...                # True if no unreturned loan exists for the book
    def lend(self, book_id: int, member_id: int, on: str) -> int: ...
    #   returns the new loan id, due_on = on + LOAN_DAYS. Checks, in this order, in ONE transaction:
    #   NotFoundError (book or member missing), AlreadyLoanedError, LoanLimitError
    def return_book(self, book_id: int, on: str) -> None: ...
    #   sets returned_on = on on the book's open loan; NotFoundError if the book is not currently on loan
    def active_loans(self, member_id: int | None = None) -> list[Loan]: ...
    #   unreturned loans (all, or one member's), ordered by due_on, then loan id
    def overdue(self, today: str) -> list[OverdueLoan]: ...
    #   unreturned loans with due_on < today, ordered by due_on, then loan id;
    #   days_overdue = whole days between due_on and today
```

Design choices worth noticing:

- **Business rules live in `lend()`**: it checks the rules and does the insert in one transaction, so a rule failure leaves nothing behind. Rule errors are our own exception classes, so callers can
  catch `LibraryError` without knowing about `sqlite3`.
- **Constraint errors stay `sqlite3.IntegrityError`.** The database already enforces them; wrapping them again would add nothing.
- Methods return **dataclasses**, not rows, so no caller ever depends on column order.
- Every statement uses placeholders. The only text pasted into SQL is the fixed `WHERE` fragment inside `active_loans`.

Here is a short session against the contract (this is also your Level 2 test):

```py
from library_repo import LibraryRepository, LibraryError

repo = LibraryRepository.open('00_practice/library_copy.db')
book_id = repo.add_book('Hyperion', 'Dan Simmons', year=1989, pages=482, genre='Sci-Fi')
member_id = repo.add_member('Farid Haddad', 'farid@example.com', '2025-03-01')
print(book_id, member_id)
print(repo.get_book(book_id))
print(repo.lend(book_id, member_id, '2025-03-14'))
print(repo.active_loans(member_id))
# 13 6
# Book(id=13, title='Hyperion', author='Dan Simmons', year=1989, pages=482, genre='Sci-Fi', price_cents=None, rating=None)
# 11
# [Loan(id=11, book_id=13, member_id=6, loaned_on='2025-03-14', due_on='2025-03-28', returned_on=None)]
```

A reference implementation is in `solutions/library_repo.py`. Write your own first (that is Level 2, Q1), and compare afterwards.

## Concurrency: Many Readers, One Writer

SQLite lets **many connections read at the same time, but only one can write at a time**. A writer takes a lock on the whole database file for the duration of its transaction. That is plenty for most applications
(a write usually takes microseconds), but you must know what happens when two writers collide.

### database is locked

Two connections to the same file. The first starts a write transaction and has not finished; the second tries to write and gives up straight away (we set `timeout=0` to see it immediately):

```py
writer = sqlite3.connect('00_practice/lock_demo.db', autocommit=True)
other = sqlite3.connect('00_practice/lock_demo.db', timeout=0, autocommit=True)
writer.execute('CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT) STRICT')

writer.execute('BEGIN IMMEDIATE')                       # take the write lock now
writer.execute("INSERT INTO notes (body) VALUES ('first')")
try:
    other.execute("INSERT INTO notes (body) VALUES ('second')")
except sqlite3.OperationalError as e:
    print('OperationalError:', e)
writer.execute('COMMIT')                                # lock released
other.execute("INSERT INTO notes (body) VALUES ('second')")   # now it works
print(other.execute('SELECT COUNT(*) FROM notes').fetchone()[0])
# OperationalError: database is locked
# 2
```

(`autocommit=True` is the mode where *you* write `BEGIN`/`COMMIT`; it makes the lock visible in the example. `BEGIN IMMEDIATE` takes the write lock at the start instead of at the first write.)

### The Busy Timeout

Instead of failing at once, a connection can **wait** for the lock to be released. The wait is the **busy timeout**. Python's `sqlite3.connect()` already has `timeout=5.0` seconds by default; I used `0` above only
to show the error. Raise it if your writers can be slow, but also keep your transactions short: do your reading, thinking and web requests *outside* the `with conn:` block.

```py
conn = sqlite3.connect('00_practice/library.db', timeout=30)        # wait up to 30 seconds for a lock
print(conn.execute('PRAGMA busy_timeout').fetchone())               # (30000,) in milliseconds
```

### WAL Mode

By default SQLite uses a rollback journal: a writer blocks readers while it commits. **Write-Ahead Logging** changes how changes are recorded: writes go to a separate `-wal` file, and readers keep
reading the old data until the writer commits. The effect: **readers never block the writer, and the writer never blocks readers**. Writers still wait for each other.

```py
# syntax
PRAGMA journal_mode = WAL;
```

```py
w1 = sqlite3.connect('00_practice/wal_demo.db')
print(w1.execute('PRAGMA journal_mode').fetchone())
print(w1.execute('PRAGMA journal_mode = WAL').fetchone())
# ('delete',)
# ('wal',)
```

The setting is **stored in the file**, so you run it once and every later connection uses WAL. Rereading the demo above after `PRAGMA journal_mode = WAL`: while `writer` holds its transaction, `other` can still
`SELECT` (and sees only committed data), but another write still fails with `database is locked`.

When to turn it on: almost always for an application with several readers or a mix of readers and a writer, such as a web app. Caveats: it creates two extra files next to the database (`-wal` and `-shm`),
so copy databases with `backup()` rather than copying one file, and it needs a local disk (not a network share).

Other pragmas worth knowing, all per connection unless stated: `PRAGMA foreign_keys = ON` (you know this one), `PRAGMA synchronous = NORMAL` (a common companion to WAL: faster commits, still safe from application
crashes), and `PRAGMA busy_timeout = 5000`.

### Threads

A `sqlite3` connection can, by default, only be used by the thread that created it (`check_same_thread=True`), and Python raises a `ProgrammingError` otherwise. The simple, robust rule: **one connection per thread**.
Open the connection inside the thread function. Do not share one connection among threads, and do not turn `check_same_thread` off unless you add your own locking.

```py
import threading

def worker(path, worker_id):
    conn = sqlite3.connect(path, timeout=30)       # this thread's own connection
    for n in range(1000):
        with conn:
            conn.execute('INSERT INTO inserts (worker, n) VALUES (?, ?)', (worker_id, n))
    conn.close()

threads = [threading.Thread(target=worker, args=(path, i)) for i in range(4)]
```

You will run exactly this in Level 3.

## Browsing Your Database

Two optional tools are worth knowing about; no exercise depends on them.

- **Datasette** (`uv tool install datasette`, then `datasette 00_practice/library.db`) opens a local web page where you can click through tables, filter, sort and run SQL, and it can export CSV and JSON.
- **sqlite-utils** (`uv tool install sqlite-utils`) is a command line and Python library for chores such as `sqlite-utils insert`, `sqlite-utils tables --counts` and `sqlite-utils schema` on a database file.

And `python -m sqlite3 00_practice/library.db` (Day 1) is always there.

You can now make SQLite speak your Python and the other way round. A repository around your library is the first piece of a real application. You are halfway through the course, keep going!

## Exercises: Day 19

### Exercises: Level 1

Use a **copy** of your `library.db` (the Day 10 normalized version) in all of these. Put your work in `00_practice/day_19.py`.

1. Make a copy of your library with `conn.backup()`: open `00_practice/library.db` as the source and `00_practice/library_day19.db` as the target, then use the copy from now on. Print the number of books (expected `(12,)`).
2. Set `conn.row_factory = sqlite3.Row`. Select the first book (by `id`) with `id, title, year` and print its title and year *by column name*. Expected: `Dune 1965`.
3. Select the three newest books (`id, title, year`, newest first, ties by title) and print each row as a `dict`.

   ```sh
   {'id': 11, 'title': 'Project Hail Mary', 'year': 2021}
   {'id': 12, 'title': 'The Martian', 'year': 2011}
   {'id': 10, 'title': 'Clean Code', 'year': 2008}
   ```

4. Print the column names of the row from Q2 using one `Row` method. Expected: `['id', 'title', 'year']`.
5. Read all book ids with `fetchmany(5)` in a loop and print the size of each batch. Expected: `[5, 5, 2]`.
6. Run `SELECT titel FROM books` (a typo). Catch the right exception class and print its message. Expected: `OperationalError: no such column: titel`.
7. Try to insert a member with the email `alice@example.com`. Catch the exception and print it. Expected: `IntegrityError: UNIQUE constraint failed: members.email`.
8. Inside `with conn:`, delete every loan and then `raise RuntimeError`. After catching it, print the number of loans (expected `10`). Then open a *new* connection to the copy with `contextlib.closing`, print the member count (expected `5`), and show that the connection is closed after the block by catching the `ProgrammingError` from using it.
9. Write a schema file `00_practice/reading.sql` with two tables (`reading_lists(id, name UNIQUE)` and a junction table `reading_list_items(list_id, book_id)` with a composite primary key) and an `INSERT` of two lists, `Summer` and `Classics`. Run it with `executescript` by reading the file with `pathlib`. Print the list names, sorted. Expected: `[('Classics',), ('Summer',)]`.
10. Print the current `journal_mode` of the copy (expected `delete`), switch it to WAL, close the connection, reopen it and print the mode again. What do you notice? (Expected: `wal` both times; the setting lives in the file.)
11. Define a `Member` dataclass and build a list of them from `SELECT * FROM members ORDER BY id`. Print the last one.

    ```sh
    Member(id=5, name='Elena Rossi', email='elena@example.com', joined_on='2024-09-02')
    ```

12. `ATTACH` the copy to itself under the name `backup_db` and print the number of books in `backup_db.books` (expected `12`), then print the names of all attached databases with `PRAGMA database_list` (expected `['main', 'backup_db']`).
13. Use `iterdump()` to get the SQL of the database as a list. Print whether it has more than 40 lines, and print the first line.
14. Register a function `shout(text)` that returns the text in upper case plus `!`. Use it to print `shout(title)` for book 1. Expected: `DUNE!`.
15. In your own words: (a) what does `with conn:` do and not do? (b) Why does SQLite have no stored procedures, and what plays that role in your program?

### Exercises: Level 2

1. **Implement the `LibraryRepository`** from the contract above in `00_practice/library_repo.py`. Test it on a fresh copy of the library with this sequence, and compare your output to the expected lines:

   ```py
   repo = LibraryRepository.open('00_practice/library_day19.db')   # a fresh copy where nothing has been changed
   new_book = repo.add_book('Hyperion', 'Dan Simmons', year=1989, pages=482, genre='Sci-Fi')
   new_member = repo.add_member('Farid Haddad', 'farid@example.com', '2025-03-01')
   print(new_book, new_member)
   print(repo.get_book(new_book))
   loan_id = repo.lend(new_book, new_member, '2025-03-14')
   print(loan_id, repo.active_loans(new_member))
   # lend the same book to member 1 and a book that does not exist (id 999) to member 1: catch LibraryError and print type name and message
   # lend books 4 and 6 to the new member, then try book 8: catch LoanLimitError and print it
   repo.return_book(new_book, '2025-03-20')
   print(repo.lend(8, new_member, '2025-03-21'))
   print([b.title for b in repo.find_by_author('weir')])
   print(repo.overdue('2025-03-14'))
   ```

   ```sh
   13 6
   Book(id=13, title='Hyperion', author='Dan Simmons', year=1989, pages=482, genre='Sci-Fi', price_cents=None, rating=None)
   11 [Loan(id=11, book_id=13, member_id=6, loaned_on='2025-03-14', due_on='2025-03-28', returned_on=None)]
   AlreadyLoanedError: book 13 is already on loan
   NotFoundError: no book with id 999
   LoanLimitError: member 6 already has 3 books out
   14
   ['The Martian', 'Project Hail Mary']
   [OverdueLoan(loan_id=4, title='The Pragmatic Programmer', member='Bruno Silva', due_on='2025-03-06', days_overdue=8)]
   ```

   (Your messages may be worded differently; the exception class names, ids and returned objects must match.)

2. Register a Python function `word_count(text)` and use it to list the titles with three or more words, most words first, ties by title.

   ```sh
   title                     words
   ------------------------  -----
   The Name of the Wind      5
   Brave New World           3
   Pride and Prejudice       3
   Project Hail Mary         3
   The Pragmatic Programmer  3
   (5 rows)
   ```

3. Register the `Median` aggregate and show the median page count and the number of books per genre (alphabetically by genre).

   ```sh
   genre      median_pages  n
   ---------  ------------  -
   Dystopian  319.5         2
   Fantasy    486.0         2
   Romance    376.5         2
   Sci-Fi     422.5         4
   Tech       408.0         2
   (5 rows)
   ```

4. Back up a copy of the library to `old.db`. In the live copy, delete the loan(s) of book 12 and then book 12 itself. Now `ATTACH` `old.db` as `old` and use an anti-join (Day 12) to list the books that are in `old.books` but no longer in `main.books`.

   ```sh
   id  title
   --  -----------
   12  The Martian
   (1 row)
   ```

5. Reproduce `database is locked` with two connections to the same file (`timeout=0`) as in the lesson, then show that the second write works after the first connection commits. Expected:

   ```sh
   OperationalError: database is locked
   2
   ```

### Exercises: Level 3

1. **Regular expressions on Hacker News.** Using `datasets.db` from Day 3 (table `hn_posts`), register a `regexp` function and count, in one query, the titles that: start with `Ask HN`, start with `Show HN`, end with a `?` (ignore trailing spaces), and are an Ask/Show post that also ends in `?`. (In SQLite a true condition is `1`, so `SUM(condition)` counts.) Then list the three highest-scoring titles that start with `Ask HN` and end with `?`.

   ```sh
   ask_hn  show_hn  ends_with_question  both
   ------  -------  ------------------  ----
   1742    1161     2439                1432
   (1 row)
   title                                                          num_points
   -------------------------------------------------------------  ----------
   Ask HN: What's your favorite HN post?                          691
   Ask HN: Just got an innocent man out of prison. What now?      510
   Ask HN: What are the must-read books about economics/finance?  442
   (3 rows)
   ```

   (This is like Python's `re` module, but the loop is inside the query.)

2. **Back up `shop.db`** to a new file with `backup()`, then verify with code that every table has the same number of rows in both files. Get the table names from `sqlite_master`. Print one line per table and finally `all equal: True`.

   ```sh
   categories               8     8 ok
   customers               60    60 ok
   employees               15    15 ok
   newsletter_signups      20    20 ok
   order_items            984   984 ok
   orders                 399   399 ok
   products                40    40 ok
   all equal: True
   ```

3. **Four writers.** Create a table `inserts (id INTEGER PRIMARY KEY, worker INTEGER NOT NULL, n INTEGER NOT NULL)` in a new file. Start 4 threads; each opens its **own** connection with `timeout=0` and inserts 1,000 rows, one `with conn:` transaction per row, counting the `OperationalError`s it catches.
   First run it with the default journal mode: some inserts should fail with `database is locked`. Then recreate the database in WAL mode, run again with `timeout=30`, and confirm that all 4,000 rows arrived with no errors. (The exact number of failures in the first run differs each time, so print only whether there were any, and that `saved + failed` is 4,000.)

   ```sh
   default journal, timeout=0: some inserts failed: True | saved + failed = 4000
   WAL + timeout=30: saved 4000 failed 0
   ```

CONGRATULATIONS !

[<< Review 3](../18R_Review_Analytical_sql/18R_review_analytical_sql.md) | [Day 20 >>](../20_Day_Import_clean_export/20_import_clean_export.md)
