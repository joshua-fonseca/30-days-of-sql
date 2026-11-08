<div align="center">
  <h1> 30 Days Of SQL: Day 27 - Security & Best Practices</h1>
</div>

[<< Review 5](../26R_Review_Duckdb/26R_review_duckdb.md) | [Day 28 >>](../28_Day_Project_library_cli/28_project_library_cli.md)

- [Day 27](#day-27)
  - [SQL Injection](#sql-injection)
    - [A Vulnerable Login](#a-vulnerable-login)
    - [Three Attacks](#three-attacks)
    - [Stacked Statements: execute vs executescript](#stacked-statements-execute-vs-executescript)
    - [The Fix: Parameters](#the-fix-parameters)
    - [Identifiers Cannot Be Parameters](#identifiers-cannot-be-parameters)
    - [LIKE Wildcards Are Not Injection, But...](#like-wildcards-are-not-injection-but)
  - [Least Privilege](#least-privilege)
    - [Read-Only Connections](#read-only-connections)
    - [query_only and the Authorizer](#query_only-and-the-authorizer)
  - [Secrets](#secrets)
  - [Backups](#backups)
  - [Migrations with PRAGMA user_version](#migrations-with-pragma-user_version)
  - [Testing SQL with pytest](#testing-sql-with-pytest)
    - [A First Test](#a-first-test)
    - [Fixtures: A Fresh Database per Test](#fixtures-a-fresh-database-per-test)
    - [Testing Errors and Many Cases](#testing-errors-and-many-cases)
  - [Style and Linting](#style-and-linting)
    - [A Small Style Guide](#a-small-style-guide)
    - [SQLFluff](#sqlfluff)
    - [sqlglot](#sqlglot)
  - [Common Pitfalls Checklist](#common-pitfalls-checklist)
  - [ Exercises: Day 27](#exercises-day-27)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 27

You can now write a lot of SQL. Today is about writing SQL that is **safe**, **repeatable** and **checked**: not letting strangers run their own SQL in your database, giving programs only the access they need, keeping copies, changing a schema without losing data, and proving with automated tests that your queries still work after the next change.

Everything runs on a copy or in memory. The reference code is in `solutions/day_27.py`, with the tests in `solutions/test_day_27_lesson.py` and `solutions/test_day_27.py`.

## SQL Injection

**SQL injection** is the oldest and still most common way databases get attacked. It happens when a program builds a SQL statement by pasting user text into a string. If the text contains SQL, the database cannot tell your SQL from the attacker's, so it runs both. Think of a form letter that says "Dear ____": if somebody writes `Dear Sir, please also wire me $1000` in the blank, the letter now contains an instruction you never wrote.

On Day 3 you were warned about f-strings. Today you see exactly what goes wrong.

### A Vulnerable Login

Here is a tiny `users` table and a login function written the **wrong** way:

```py
import sqlite3

conn = sqlite3.connect(':memory:')
conn.executescript("""
    CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, password TEXT NOT NULL);
    INSERT INTO users (name, password) VALUES ('alice', 's3cret'), ('bob', 'hunter2');
    CREATE TABLE api_keys (owner TEXT, secret TEXT);
    INSERT INTO api_keys VALUES ('alice', 'key-ALICE-123'), ('bob', 'key-BOB-456');
""")


def login_vulnerable(conn, name, password):
    """DO NOT WRITE CODE LIKE THIS. SQL is built by pasting the user's text into a string."""
    sql = f"SELECT id, name FROM users WHERE name = '{name}' AND password = '{password}'"
    return conn.execute(sql).fetchone()


print(login_vulnerable(conn, 'alice', 'wrong'))
# None
```

(Real applications never store plain passwords; the [Secrets](#secrets) section shows the right way. The table is a toy.)

With honest input, it works: a wrong password finds no row.

### Three Attacks

**Attack 1: comment out the password check.** In SQL, `--` starts a comment. The name `alice' --` closes the quote and comments out the rest:

```py
print(login_vulnerable(conn, "alice' --", 'anything'))
# (1, 'alice')

name = "alice' --"
print(f"SELECT id, name FROM users WHERE name = '{name}' AND password = 'anything'")
# SELECT id, name FROM users WHERE name = 'alice' --' AND password = 'anything'
```

Everything after `--` is ignored, so the password is never checked. We are logged in as alice without her password.

**Attack 2: make the condition always true.** With password `' OR '1'='1` the `WHERE` becomes `name = 'nobody' AND password = '' OR '1'='1'`. `AND` binds tighter than `OR` (Day 5), so this is "(name and password match) OR 1=1", which is true for every row:

```py
print(login_vulnerable(conn, 'nobody', "' OR '1'='1"))
# (1, 'alice')
```

The user `nobody` does not exist, and we still got a row back (the first user in the table).

**Attack 3: steal data from other tables.** `UNION` (Day 15) glues another query's rows onto ours. The attacker only needs the same number of columns:

```py
print(login_vulnerable(conn, "x' UNION SELECT 0, secret FROM api_keys WHERE owner = 'bob' --", ''))
# (0, 'key-BOB-456')
```

The "name" returned by the login is Bob's API key. One text box has become a window into the whole database.

### Stacked Statements: execute vs executescript

The classic cartoon attack ends with `; DROP TABLE users`, a second statement glued onto the first. Python's `sqlite3` protects you here, but only partly:

```py
try:
    conn.execute("SELECT 1; DROP TABLE users")
except sqlite3.ProgrammingError as err:
    print(type(err).__name__, err)
# ProgrammingError You can only execute one statement at a time.

print(conn.execute("SELECT count(*) FROM users").fetchone())
# (2,)

conn.executescript("SELECT 1; DROP TABLE users")      # executescript runs *every* statement
try:
    conn.execute("SELECT count(*) FROM users")
except sqlite3.OperationalError as err:
    print(type(err).__name__, err)
# OperationalError no such table: users

# put the table back for the next examples
conn.executescript("""
    CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, password TEXT NOT NULL);
    INSERT INTO users (name, password) VALUES ('alice', 's3cret'), ('bob', 'hunter2');
""")
```

`execute` refuses a second statement. `executescript` runs all of them, which is its job (Day 19). So: **never pass anything a user typed, or any text from a file you do not control, to `executescript`**. And do not count on `execute` being the only line of defence: attacks 1 to 3 above are single statements.

> **Common mistake:** "I'll just remove the quote characters from the input." Escaping by hand is a game you lose eventually (different quote styles, Unicode tricks, numbers that need no quotes at all). The fix is not to clean the text; it is to **never put the text in the SQL string**.

### The Fix: Parameters

You have used placeholders since Day 3. This is why. With `?`, the SQL text is sent to SQLite first and compiled into a plan, and the values are handed over **separately**. A value can never become SQL, whatever characters it contains:

```py
def login_safe(conn, name, password):
    sql = "SELECT id, name FROM users WHERE name = ? AND password = ?"
    return conn.execute(sql, (name, password)).fetchone()


print(login_safe(conn, "alice' --", 'anything'))
# None
print(login_safe(conn, 'alice', 's3cret'))
# (1, 'alice')
```

(We ran the attacks above before dropping `users`; rebuild the table from the script to follow along.) The attack text is now just a very strange user name, and no user has it, so there is no match. This is a **parameterized query**, also called a prepared statement, and it is the main defence. Rules to remember:

- Values (numbers, strings, dates, `NULL`) always travel as parameters.
- f-strings are for *printing*, never for building SQL.
- This is true for every database and every language, not only SQLite and Python. DuckDB has the same `?` and `$name` placeholders (Day 23).

**In other databases:** PostgreSQL drivers use `%s` or `$1`, SQL Server drivers `?` or `@name`, MySQL drivers `%s`. The idea is identical.

### Identifiers Cannot Be Parameters

Placeholders stand in for **values**. They cannot stand in for table or column names, because the plan is made before the values arrive and the plan needs to know which table to read. What happens if you try?

```py
from helpers import library_conn          # the Day 3 library: one table, 12 books
lib = library_conn()

print(lib.execute('SELECT title FROM books ORDER BY ? LIMIT 3', ('year',)).fetchall())
# [('Dune',), ('Neuromancer',), ('The Hobbit',)]
print(lib.execute('SELECT title FROM books ORDER BY year LIMIT 3').fetchall())
# [('Pride and Prejudice',), ('Emma',), ('Brave New World',)]
```

No error, and no sorting either: `ORDER BY ?` sorts by the constant text `'year'`, which is the same for every row, so the rows stay in insertion order. A silent wrong answer.

So when a user picks the column (a "sort by" drop-down, a report builder), you must put the name into the SQL text yourself. The safe way is an **allowlist**: a fixed dictionary from what the user may ask for to the SQL text you control.

```py
BOOK_SORT_COLUMNS = {'title': 'title', 'author': 'author', 'year': 'year', 'pages': 'pages', 'price': 'price_cents'}
SORT_DIRECTIONS = {'asc': 'ASC', 'desc': 'DESC'}


def sort_books(conn, column, direction='asc'):
    try:
        col = BOOK_SORT_COLUMNS[column]
        way = SORT_DIRECTIONS[direction.lower()]
    except KeyError:
        raise ValueError(f'cannot sort by {column!r} {direction!r}') from None
    # `id` is the tie-breaker, so equal values always come out in the same order
    return conn.execute(f'SELECT id, title, {col} FROM books ORDER BY {col} {way}, id').fetchall()
```

The f-string here is fine: both `col` and `way` come out of *our* dictionaries, never from the user's text. The user only chooses which entry to take.

```py
print(sort_books(lib, 'year', 'desc')[:3])
# [(11, 'Project Hail Mary', 2021), (12, 'The Martian', 2011), (10, 'Clean Code', 2008)]
print(sort_books(lib, 'price', 'ASC')[:3])
# [(5, 'Pride and Prejudice', 599), (6, 'Emma', 649), (3, 'The Hobbit', 799)]

for bad in [('year; DROP TABLE books', 'asc'), ('year', 'sideways')]:
    try:
        sort_books(lib, *bad)
    except ValueError as err:
        print('ValueError:', err)
# ValueError: cannot sort by 'year; DROP TABLE books' 'asc'
# ValueError: cannot sort by 'year' 'sideways'
```

The same trick works for table names, `LIMIT` (convert with `int()`), and anything else that is not a value. The  alternative is `sqlite_master`/`PRAGMA table_info` to build the allowlist from the real schema, which is handy when the columns change.

>  A header row read from a CSV (Day 20) is also **user input** when the file comes from outside. Do not paste it into SQL either.

### LIKE Wildcards Are Not Injection, But...

A search box that lands in `LIKE '%' || ? || '%'` is safe from injection, but the user's `%` and `_` still act as wildcards (Day 5). Searching for the single character `%` matches everything:

```py
print(lib.execute("SELECT count(*) FROM books WHERE title LIKE '%' || ? || '%'", ('%',)).fetchone())
# (12,)
```

The fix is an `ESCAPE` character. You choose it, put it in front of each wildcard in the user's text, and tell `LIKE` about it:

```py
print(lib.execute("SELECT count(*) FROM books WHERE title LIKE '%' || ? || '%' ESCAPE '\\'", ('\\%',)).fetchone())
# (0,)
```

Level 2 asks you to wrap that in a function.

## Least Privilege

**Least privilege** means every part of a system gets only the access it needs. A report that only reads should not be *able* to delete. Then even a bug (or an injection you missed) cannot do damage.

PostgreSQL or MySQL give you users and `GRANT SELECT ON ...`. SQLite has no users: whoever can open the file can do anything. What it does have is **how you open it**.

### Read-Only Connections

A SQLite connection can be opened with a **URI** (a `file:` address with options). `mode=ro` makes the connection read-only. Pass `uri=True` to `sqlite3.connect`. `Path.as_uri()` builds the correct address from a path (it takes care of spaces and special characters):

```py
from pathlib import Path

path = Path('00_practice/library.db').resolve()          # the Day 10 library in a file
uri = path.as_uri() + '?mode=ro'
print(uri)
# file:///home/you/sql/00_practice/library.db?mode=ro

ro = sqlite3.connect(uri, uri=True)
print(ro.execute('SELECT count(*) FROM books').fetchone())
# (12,)
try:
    ro.execute('DELETE FROM books')
except sqlite3.OperationalError as err:
    print(type(err).__name__, err)
# OperationalError attempt to write a readonly database
```

(The first line of output differs on your machine, since the path is yours.) Reading works; any write fails, no matter what SQL runs. A read-only connection also **does not create the file** if it is missing, which protects you from "I mistyped the path and now have an empty database":

```py
try:
    sqlite3.connect(Path('does_not_exist.db').resolve().as_uri() + '?mode=ro', uri=True)
except sqlite3.OperationalError as err:
    print(type(err).__name__, err)
# OperationalError unable to open database file
```

Use a read-only connection for reports, exports, dashboards and for any code that only needs `SELECT`. In DuckDB the same idea is `duckdb.connect('file.duckdb', read_only=True)`, and `ATTACH '...' (TYPE sqlite, READ_ONLY)` as you did on Day 26.

### query_only and the Authorizer

Two more tools, both on an ordinary connection:

```py
q = sqlite3.connect(path)
q.execute('PRAGMA query_only = ON')       # this connection refuses to change the database
try:
    q.execute('DELETE FROM books')
except sqlite3.OperationalError as err:
    print(type(err).__name__, err)
# OperationalError attempt to write a readonly database
```

`query_only` can be switched off again by the same code, so it protects against mistakes, not against an attacker who can run arbitrary SQL. `mode=ro` is decided when you open the file, so use that when you can.

For finer control, `conn.set_authorizer(callback)` lets Python approve or deny each *kind* of action before it runs:

```py
a = sqlite3.connect(path)

def deny_writes(action, arg1, arg2, db_name, trigger):
    if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE, sqlite3.SQLITE_DROP_TABLE):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK

a.set_authorizer(deny_writes)
print(a.execute('SELECT count(*) FROM books').fetchone())
# (12,)
try:
    a.execute('DELETE FROM books')
except sqlite3.DatabaseError as err:
    print(type(err).__name__, err)
# DatabaseError not authorized
```

You will rarely need the authorizer. It is good to know it exists, for example when you must run SQL written by someone else (an "analyst" box in a tool) and want to allow only `SELECT`.

## Secrets

A **secret** is anything that would hurt if it leaked: passwords, API keys, tokens, connection strings with passwords. SQLite databases usually have none of those in the connection (no password!), but your programs will meet them as soon as they talk to PostgreSQL, MotherDuck or a web API.

- **Never write secrets in code or commit them.** Read them from the environment (or a file outside the repository). `os.environ.get('NAME', default)` also gives you a simple way to make the database path configurable:

  ```py
  import os
  from pathlib import Path

  db_path = Path(os.environ.get('LIBRARY_DB', '00_practice/library.db'))
  print(db_path)
  # 00_practice/library.db
  ```

- **Keep database files out of git** (`*.db` in `.gitignore`, as this course does). A database file is data, and data often contains personal information.
- **Never store passwords as text.** Store a salted, slow hash (`hashlib.scrypt` is in the standard library) and compare in constant time:

  ```py
  import hashlib, hmac, os

  def hash_password(password, salt=None):
      salt = salt or os.urandom(16)
      digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
      return salt.hex() + ':' + digest.hex()

  def check_password(password, stored):
      salt_hex, digest_hex = stored.split(':')
      again = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
      return hmac.compare_digest(again.hex(), digest_hex)

  stored = hash_password('s3cret')
  print(len(stored), stored.count(':'))
  print(check_password('s3cret', stored), check_password('wrong', stored))
  # 161 1
  # True False
  ```

  (In a real application use a maintained library such as `argon2-cffi`, or your web framework's built-in password support. The point is: the database never holds the password itself.)
- **Do not log parameter values** of sensitive queries, and do not print whole rows of personal data in error messages.
- **Protect the file.** SQLite has no login, so file permissions are your access control. On a server, only the account that runs your program should be able to read the database.

## Backups

A database you cannot restore is a database you do not have. You met two ways on Day 19, `conn.backup()` and `iterdump()`. A third one is very convenient: **`VACUUM INTO`** (SQLite 3.27+) writes a compact, consistent copy of the database to a new file, even while it is in use:

```py
src = sqlite3.connect(path)
src.execute('VACUUM INTO ?', ('00_practice/d27_snapshot.db',))     # the file name is a parameter
src.close()

snap = sqlite3.connect('00_practice/d27_snapshot.db')
print(snap.execute('PRAGMA integrity_check').fetchone(), snap.execute('SELECT count(*) FROM loans').fetchone())
# ('ok',) (10,)
```

`PRAGMA integrity_check` returns `('ok',)` when the file is healthy. Always **test a backup** by opening it and checking something, as above. A few habits:

- Name backups with the date (`library-2025-03-14.db`; ISO dates sort in time order) and keep the last few, not only the last one. Level 3 has you write that rotation.
- Store backups on a *different* disk or machine from the database.
- Never copy the `.db` file with `shutil.copy` while a program writes to it (Day 19: WAL mode keeps recent changes in separate files).
- Practise restoring. Restoring is just opening the backup file.

## Migrations with PRAGMA user_version

Your schema will change: a new column, a new table, a new index. On your own laptop you can delete the file and start again. A real database holds data you cannot lose, so you change it **step by step, in a recorded order**. Each step is a **migration**: a small SQL file such as

```
migrations/
    001_create_notes.sql
    002_add_created_on.sql
```

The database must remember which migrations it has already seen, otherwise running them twice would fail (`table already exists`) or damage data. Tools like Alembic or Flyway keep a table for this. SQLite has a built-in shortcut: a free integer stored in the file header, called **`user_version`**, which starts at 0 and which you can read and write with a PRAGMA:

```py
conn = sqlite3.connect(':memory:')
print(conn.execute('PRAGMA user_version').fetchone())
# (0,)
conn.execute('PRAGMA user_version = 5')
print(conn.execute('PRAGMA user_version').fetchone())
# (5,)
```

The rule: **version N means "all migrations up to N are applied".** A runner then does this: read `user_version`, run every file whose number is higher, in order, and set `user_version` after each. Each file and its version bump should happen in **one transaction**, so a failing file leaves the database exactly as it was:

```py
def migrate(conn, folder):
    files = {}
    for path in sorted(folder.glob('[0-9][0-9][0-9]_*.sql')):
        version = int(path.name.split('_', 1)[0])
        if version in files:
            raise ValueError(f'two migrations share version {version}')
        files[version] = path
    (current,) = conn.execute('PRAGMA user_version').fetchone()
    applied = []
    for version in sorted(files):
        if version <= current:
            continue
        script = f"BEGIN;\n{files[version].read_text(encoding='utf-8')}\nPRAGMA user_version = {int(version)};\nCOMMIT;"
        try:
            conn.executescript(script)
        except sqlite3.Error:
            if conn.in_transaction:
                conn.rollback()
            raise
        applied.append(version)
    return applied
```

Two things to notice. `PRAGMA user_version = N` cannot take a `?`, so the number is pasted into the text, but only after `int()` conversion of a number we parsed from the file name, so nothing can sneak in. And `executescript` is fine here: the SQL comes from files **you** wrote and committed, which is exactly what it is for.

Try it with two migration files, a third that is broken, and then a fixed third:

```py
from pathlib import Path
folder = Path('00_practice/d27_migrations')
folder.mkdir(exist_ok=True)
(folder / '001_create_notes.sql').write_text('CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL) STRICT;\n')
(folder / '002_add_created_on.sql').write_text('ALTER TABLE notes ADD COLUMN created_on TEXT;\n')

db = sqlite3.connect(':memory:')
print(migrate(db, folder), db.execute('PRAGMA user_version').fetchone())
# [1, 2] (2,)
print(migrate(db, folder), db.execute('PRAGMA user_version').fetchone())     # nothing new to do
# [] (2,)

(folder / '003_broken.sql').write_text('CREATE TABLE tags (id INTEGER PRIMARY KEY);\nINSERT INTO nope VALUES (1);\n')
try:
    migrate(db, folder)
except sqlite3.OperationalError as err:
    print(type(err).__name__, err)
print(db.execute('PRAGMA user_version').fetchone(), [r[0] for r in db.execute('SELECT name FROM sqlite_master ORDER BY name')])
# OperationalError no such table: nope
# (2,) ['notes']

(folder / '003_broken.sql').write_text('CREATE TABLE tags (id INTEGER PRIMARY KEY, label TEXT);\n')
print(migrate(db, folder), db.execute('PRAGMA user_version').fetchone())
# [3] (3,)
```

The broken migration created `tags` *and then failed*, yet after the rollback there is no `tags` table and the version is still 2. That "all or nothing" is the entire point. Migration rules of thumb: never edit a migration that others have already applied (add a new one), and keep them in version control next to the code that needs them (Day 22 promised this).

> **Older code:** you will also see a `schema_version` table with one row instead of `user_version`. It does the same job and works in every database. `user_version` is just shorter in SQLite.

## Testing SQL with pytest

You have been checking your queries by running them and looking. That works for a day. Next week you change a query, forget what it used to return, and something breaks quietly. **Automated tests** write down "this call must give this result" once, and re-check it in a second, every time.

**pytest** (already installed by `uv sync`) is the standard Python test tool. The recipe: put functions named `test_...` in a file named `test_....py`; use plain `assert`; run `uv run pytest`. Because SQLite can live in memory (`':memory:'`, Day 1), a test can have its own brand-new database each time at almost no cost.

### A First Test

Your Day 19 `LibraryRepository` is perfect to test: it has rules (14-day loans, no double loans, a limit of 3). Create `00_practice/test_library_repo.py`:

```py
# 00_practice/test_library_repo.py
def test_lend_sets_due_date_14_days_later(repo):
    book_id = repo.add_book('Dune', 'Frank Herbert')
    member_id = repo.add_member('Alice', 'alice@example.com', '2025-01-01')
    repo.lend(book_id, member_id, '2025-03-14')
    (loan,) = repo.active_loans()
    assert loan.due_on == '2025-03-28'
```

A test follows **arrange, act, assert**: set up the data, do the one thing under test, check the result. If any `assert` is false, or an exception escapes, the test fails and pytest shows exactly which line and values.

The argument `repo` is not defined in the function, it is a *fixture*:

### Fixtures: A Fresh Database per Test

A **fixture** is a function marked `@pytest.fixture` that builds something a test needs. A test that lists the fixture's name as a parameter receives its value. Code after `yield` runs when the test ends (cleanup):

```py
import sqlite3
import pytest
from library_repo import AlreadyLoanedError, LibraryRepository, NotFoundError

SCHEMA = open('00_practice/library_schema.sql').read()      # your Day 10 CREATE TABLE statements, saved in a file


@pytest.fixture
def repo():
    conn = sqlite3.connect(':memory:')          # a brand new, empty database for every test
    conn.executescript(SCHEMA)
    repo = LibraryRepository(conn)
    yield repo
    repo.close()
```

Every test gets its own empty library, so tests cannot disturb each other, and the order they run in does not matter. (In the reference solution the schema comes from `helpers.LIBRARY_SCHEMA` instead of a file.) If you have no schema file yet, copy your Day 10 `CREATE TABLE` statements into `00_practice/library_schema.sql`.

### Testing Errors and Many Cases

To check that something **raises**, use `pytest.raises` as a context manager. To run one test with many inputs, use `@pytest.mark.parametrize`:

```py
def test_add_book_returns_id_and_book_is_found(repo):
    book_id = repo.add_book('Dune', 'Frank Herbert', year=1965)
    book = repo.get_book(book_id)
    assert book.title == 'Dune'
    assert book.author == 'Frank Herbert'


def test_second_loan_of_same_book_is_rejected(repo):
    book_id = repo.add_book('Dune', 'Frank Herbert')
    alice = repo.add_member('Alice', 'alice@example.com', '2025-01-01')
    bob = repo.add_member('Bob', 'bob@example.com', '2025-01-01')
    repo.lend(book_id, alice, '2025-03-14')
    with pytest.raises(AlreadyLoanedError):
        repo.lend(book_id, bob, '2025-03-15')


@pytest.mark.parametrize('book_id, member_id', [(999, 1), (1, 999)])
def test_unknown_book_or_member(repo, book_id, member_id):
    repo.add_book('Dune', 'Frank Herbert')
    repo.add_member('Alice', 'alice@example.com', '2025-01-01')
    with pytest.raises(NotFoundError):
        repo.lend(book_id, member_id, '2025-03-14')
```

Run them (with `-v` for one line per test, `-q` for a short summary):

```sh
uv run pytest -v 00_practice/test_library_repo.py
```

```sh
output
test_day_27_lesson.py::test_add_book_returns_id_and_book_is_found PASSED [ 20%]
test_day_27_lesson.py::test_lend_sets_due_date_14_days_later PASSED      [ 40%]
test_day_27_lesson.py::test_second_loan_of_same_book_is_rejected PASSED  [ 60%]
test_day_27_lesson.py::test_unknown_book_or_member[999-1] PASSED         [ 80%]
test_day_27_lesson.py::test_unknown_book_or_member[1-999] PASSED         [100%]

============================== 5 passed in 0.03s ===============================
```

(The file name and timing in your output differ; the reference file is `test_day_27_lesson.py`.) Five results from four test functions: the parametrized test ran twice.

When a test fails, pytest shows the line and the values. For example, with `assert 1 + 1 == 3`:

```sh
output
    def test_math():
>       assert 1 + 1 == 3
E       assert (1 + 1) == 3

_work/failing_test.py:2: AssertionError
=========================== short test summary info ============================
FAILED _work/failing_test.py::test_math - assert (1 + 1) == 3
1 failed in 0.04s
```

What makes a good SQL test:

- **One behaviour per test**, with a name that says what (`test_second_loan_of_same_book_is_rejected`).
- **Tiny, explicit data** built inside the test. Do not rely on a big shared file whose contents you have to remember.
- Test the **edges**: the empty result, the exact boundary (due *today* is not overdue, due *yesterday* is), NULLs, duplicates, ties.
- Test the **failure** paths as carefully as the success paths: a rule that is never tested is a rule that quietly stops working.
- Give every query a deterministic `ORDER BY` (with a tie-breaker), or your tests will fail on some days and pass on others.

>  For file-based code, pytest's built-in `tmp_path` fixture gives each test its own empty temporary folder: `def test_x(tmp_path): conn = sqlite3.connect(tmp_path / 'test.db')`. Level 3 uses it.

## Style and Linting

### A Small Style Guide

Code is read many more times than it is written. A shared style makes queries easy to scan. The conventions this course has used since Day 1 are a fine default:

- Keywords in `UPPERCASE`, identifiers in `snake_case`.
- Each major clause (`FROM`, `WHERE`, `GROUP BY`, `ORDER BY`) starts on its own line. One select item per line once there are more than two or three.
- Always write column lists (`INSERT INTO t (a, b)`), and avoid `SELECT *` in application code.
- Qualify columns with a table alias as soon as there are two tables.
- Explicit `JOIN ... ON`, never comma joins. Name CTEs for what they contain (`monthly_revenue`, not `t1`).
- A deterministic `ORDER BY` with a tie-breaker, wherever the order matters.
- Money as integer cents, dates as ISO text (SQLite) or real `DATE`s (DuckDB).

### SQLFluff

Nobody wants to check these rules by eye.  **SQLFluff** is a linter and formatter for SQL, with a dialect for SQLite and for DuckDB. `uv sync` installed it as a dev tool. Here is a messy query in `messy.sql`:

```sql
select * from books where genre='Sci-Fi' order by year
```

```sh
uv run sqlfluff lint messy.sql --dialect sqlite
```

```sh
output
== [messy.sql] FAIL
L:   1 | P:   8 | AM04 | Query produces an unknown number of result columns.
                       | [ambiguous.column_count]
L:   1 | P:  21 | LT14 | The 'where' keyword should always start a new line.
                       | [layout.keyword_newline]
L:   1 | P:  32 | LT01 | Expected single whitespace between naked identifier and
                       | raw comparison operator '='. [layout.spacing]
L:   1 | P:  33 | LT01 | Expected single whitespace between raw comparison
                       | operator '=' and quoted literal. [layout.spacing]
L:   1 | P:  42 | LT14 | The 'order' keyword should always start a new line.
                       | [layout.keyword_newline]
All Finished!
```

Each line says where (`L`ine, `P`osition), a rule **code** and what to change. `AM04` is the `SELECT *` warning. `sqlfluff fix` repairs everything that can be repaired automatically:

```sh
uv run sqlfluff fix messy.sql --dialect sqlite
```

```sql
select * from books
where genre = 'Sci-Fi'
order by year
```

It fixed the layout (four of the violations) and left `SELECT *`, since only you know which columns you need. Use it from Python too, which is handy in tests: `sqlfluff.lint(sql, dialect='sqlite')` returns a list of dictionaries with a `code` and a `description`. A project usually adds a `.sqlfluff` file with the dialect and the rules to ignore, so the command needs no flags, and runs `sqlfluff lint` before every commit.

SQLFluff is opinionated and sometimes fussy (it also complains about line length and table aliases). Treat it as a reviewer: fix what you agree with, and switch off the rules you do not want in `.sqlfluff`, rather than fighting it.

### sqlglot

**sqlglot** (installed too) parses SQL into a tree. Besides translating dialects (Day 30), it formats and it **detects syntax errors** without a database:

```py
import sqlglot

print(sqlglot.transpile("SELECT title,author,year FROM books WHERE year>2000 AND genre = 'Fantasy'ORDER BY year",
                        read='sqlite', write='sqlite', pretty=True)[0])
# SELECT
# title,
# author,
# year
# FROM books
# WHERE
# year > 2000 AND genre = 'Fantasy'
# ORDER BY
# year

try:
    sqlglot.parse_one('SELEC title FROM books WHERE', read='sqlite')
except sqlglot.errors.ParseError as err:
    print(type(err).__name__)
# ParseError
```

## Common Pitfalls Checklist

Print this list. Most database trouble in real projects comes from items on it, and every one is something you have already met:

- [ ] **No SQL built with f-strings or `+`**; every value is a `?` or `:name` parameter. Identifiers come from an allowlist.
- [ ] `executescript` only runs text you wrote yourself.
- [ ] The connection has the **least access** it needs (`mode=ro` for readers).
- [ ] `PRAGMA foreign_keys = ON` for every connection (Day 9); constraints (`NOT NULL`, `CHECK`, `UNIQUE`, `FOREIGN KEY`) say what the data may be, so bad data cannot get in from any program.
- [ ] Writes sit in a **transaction** (`with conn:`); you `commit()`; related changes succeed or fail together (Day 8).
- [ ] No `UPDATE` or `DELETE` without a `WHERE` (and you looked at `rowcount`).
- [ ] NULLs handled: `IS NULL` instead of `= NULL`, no `NOT IN` over a column that can be NULL, `COALESCE` where you need a default (Days 5, 6, 13).
- [ ] Money is **integer cents**; dates are ISO; no floating point equality.
- [ ] Every ordered query has a **tie-breaker**; every pagination uses a stable order (keyset pagination when large).
- [ ] No `SELECT *` in application code; every `GROUP BY` lists all non-aggregated columns.
- [ ] Indexes exist for the columns you filter and join on, checked with `EXPLAIN QUERY PLAN` (Day 21).
- [ ] Schema changes go through **migrations**, in version control.
- [ ] There is a **backup**, and you have restored from it at least once.
- [ ] The important behaviour has **tests**.
- [ ] No secrets or database files in git.

You can now defend a database, change it safely and prove it still works. That is the difference between SQL that runs and SQL you can ship. Two projects remain.

## Exercises: Day 27

For Level 1, create the `users` and `api_keys` tables from [A Vulnerable Login](#a-vulnerable-login) in a fresh in-memory database before each exercise that needs them (the demo dropped `users`).

### Exercises: Level 1

1. Write `login_vulnerable(conn, name, password)` exactly as in the lesson and call it with `'alice'` and `'wrong'`. Expected: `None`.
2. Log in as `bob` **without knowing his password**, using a comment in the name. Expected: `(2, 'bob')`.
3. Log in as someone who does not exist, using the `' OR '1'='1` password. Expected: `(1, 'alice')`. Why does it return alice and not bob?
4. Make the login function return the secret key of **alice** (not bob) in the `name` column of its result, with a `UNION`. Expected: `(0, 'key-ALICE-123')`.
5. Print the SQL string the vulnerable function builds for the attack in exercise 2 (use the same f-string, but print it) and explain in your own words which part of it the database sees as a comment.
6. Write `login_safe` with placeholders and replay the attacks from exercises 2, 3 and 4. Expected: three times `None`, and `(1, 'alice')` for the honest `alice` / `s3cret`.
7. Call `conn.execute('SELECT 1; DROP TABLE users')`, catch the error and print its type and message. Then do the same with `executescript` and show that the table is gone. Which of the two should never see user input?
8. In your own words: why can `?` not be used for a column name? What does `ORDER BY ?` with `'year'` actually sort by? Run it on the library to check.
9. Save your Day 10 library to a file (`conn.backup()`), open it with a read-only URI and print the number of books. Expected: `(12,)`.
10. Try `DELETE FROM books` on the read-only connection and print the exception type and message. Expected: `OperationalError attempt to write a readonly database`.
11. Open a **missing** file with `mode=ro` and show the error. Does a file appear on disk? (Use `Path.exists()`.) Expected: `OperationalError unable to open database file`, and `False`.
12. Make a `VACUUM INTO` copy of the library, open it, and print the `integrity_check` result and the number of loans. Expected: `('ok',) (10,)`.
13. Read `PRAGMA user_version` of a new in-memory database, set it to 5, and read it again. Expected: `(0,)`, then `(5,)`.
14. Write three messy queries of your own (or use the ones below), lint each with `sqlfluff.lint(sql, dialect='sqlite')` and print the sorted set of rule codes for each:
    ```sql
    select * from books where genre='Sci-Fi' order by year
    SELECT title,author,year FROM books WHERE year>2000 AND genre = 'Fantasy'ORDER BY year
    select b.title, a.name from books b join authors a on a.id=b.author_id where a.name like 'J%'
    ```
    Then run `sqlfluff fix` on the first and compare. (The first query has `AM04`, `LT01`, `LT12`, `LT14`.)
15. Explain in your own words: why store a hash of a password instead of the password, and why compare with `hmac.compare_digest`?

### Exercises: Level 2

1. **Safe sorting.** Write `sort_books(conn, column, direction)` for the Day 3 library with an allowlist (title, author, year, pages, price → `price_cents`; asc/desc). Return `(id, title, value)` tuples with `id` as tie-breaker, and raise `ValueError` for anything else. Check with these calls:
   ```py
   print(sort_books(lib, 'year', 'desc')[:3])
   print(sort_books(lib, 'price', 'ASC')[:3])
   sort_books(lib, 'year; DROP TABLE books', 'asc')
   ```
   ```sh
   [(11, 'Project Hail Mary', 2021), (12, 'The Martian', 2011), (10, 'Clean Code', 2008)]
   [(5, 'Pride and Prejudice', 599), (6, 'Emma', 649), (3, 'The Hobbit', 799)]
   ValueError: cannot sort by 'year; DROP TABLE books' 'asc'
   ```
2. **Five tests.** In `00_practice/test_library_repo.py` (reuse the fixture from the lesson) write five new tests for `LibraryRepository`, each in the arrange-act-assert shape:
   1. `return_book` makes the book available again (`is_available` is `False` before, `True` after);
   2. returning a book that is not on loan raises `NotFoundError`;
   3. a member who already has 3 books cannot borrow a fourth (`LoanLimitError`), and the failed `lend` leaves exactly 3 active loans;
   4. a loan lent on `2025-03-01` is due `2025-03-15`: `overdue('2025-03-15')` is empty, and `overdue('2025-03-20')` has one loan with `days_overdue == 5`;
   5. `search_books('BOOK')` is case-insensitive and ordered by title (add four books called `Book 1` to `Book 4`).

   All must pass: `5 passed` (plus the lesson's 5 if you run the whole file).
3. **Literal search.** Write `search_title_literal(conn, text)` that returns the sorted titles containing `text`, where `%` and `_` in `text` mean themselves (use `ESCAPE`; remember to escape the escape character itself). After adding a book called `100% Pure_Python`, check:
   ```py
   print(search_title_literal(lib, '%'), search_title_literal(lib, '_'), search_title_literal(lib, 'the'))
   ```
   ```sh
   ['100% Pure_Python'] ['100% Pure_Python'] ['The Hobbit', 'The Martian', 'The Name of the Wind', 'The Pragmatic Programmer']
   ```
4. **Password helpers.** Write `hash_password` and `check_password` as in the lesson. Show that hashing the same password twice gives two *different* strings, that both verify, and that a wrong password does not. Expected: `False`, `True True`, `False`.

### Exercises: Level 3

1. **A migration runner.** Write `migrate(conn, folder)` as described above: apply `NNN_name.sql` files in order, skipping versions up to `user_version`, each file and its version bump in one transaction, returning the list of versions applied. Then write **pytest tests** (use the `tmp_path` fixture to create the files) proving that:
   1. a fresh database gets `[1, 2]` applied and `user_version == 2`, and a second call applies `[]`;
   2. a file `003_more.sql` added later is applied alone (`[3]`);
   3. a broken `003` (a valid `CREATE TABLE half ...` followed by an `INSERT` into a missing table) raises `sqlite3.OperationalError`, leaves `user_version == 2`, and **no `half` table exists**.

   Expected: `3 passed`. Use the sequence from the lesson's [migration demo](#migrations-with-pragma-user_version) as a manual check first.
2. **Backup rotation.** Write `backup_with_rotation(db_path, folder, today, keep=3)` that creates `folder/library-<today>.db` with `VACUUM INTO`, then deletes the oldest snapshots so only the newest `keep` remain, and returns the remaining file names. Call it for `2025-03-10`, `2025-03-11`, `2025-03-12` and `2025-03-13` in order and print the result of the last call. Expected:
   ```sh
   ['library-2025-03-11.db', 'library-2025-03-12.db', 'library-2025-03-13.db']
   ```
   Then open the newest snapshot read-only and run `PRAGMA integrity_check`.

CONGRATULATIONS !

[<< Review 5](../26R_Review_Duckdb/26R_review_duckdb.md) | [Day 28 >>](../28_Day_Project_library_cli/28_project_library_cli.md)
