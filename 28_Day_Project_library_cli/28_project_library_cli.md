<div align="center">
  <h1> 30 Days Of SQL: Day 28 - Project 1: Library Manager CLI</h1>
</div>

[<< Day 27](../27_Day_Security_and_best_practices/27_security_and_best_practices.md) | [Day 29 >>](../29_Day_Project_analytics_report/29_project_analytics_report.md)

- [Day 28](#day-28)
  - [The Project](#the-project)
  - [Requirements](#requirements)
  - [How the Pieces Fit](#how-the-pieces-fit)
  - [argparse in Five Minutes](#argparse-in-five-minutes)
  - [Milestones](#milestones)
    - [Milestone 0: Setup](#milestone-0-setup)
    - [Milestone 1: init](#milestone-1-init)
    - [Milestone 2: Books](#milestone-2-books)
    - [Milestone 3: Members and Loans](#milestone-3-members-and-loans)
    - [Milestone 4: Reports](#milestone-4-reports)
    - [Milestone 5: Stats](#milestone-5-stats)
    - [Milestone 6: Tests and Polish](#milestone-6-tests-and-polish)
  - [A Complete Example Session](#a-complete-example-session)
  - [Stretch Goals](#stretch-goals)
  - [Checking Your Work](#checking-your-work)

# Day 28

Time to build something. Today there are no Level 1/2/3 exercises. Instead you write a small but real program: a **command line application** that manages a library. You have already written its heart, the `LibraryRepository` of Day 19, and the tests of Day 27. Today you put a friendly front on it with `argparse`.

This is a spec, not a walkthrough. You get requirements, milestones with *acceptance checks* (commands and the output they must give) and hints. Try it yourself first; a complete reference is in `solutions/day_28/` ("try first, peek later"). Take as long as you need.

## The Project

A librarian types commands such as:

```sh
python library_cli.py lend 4 5
python library_cli.py overdue
```

and the program reads and updates a SQLite database. Each command is one run of the program: it opens the database, does one thing, prints the result and exits.

**You will practise:** schema design (your Day 10 tables), the repository pattern (Day 19), transactions and business rules, parameterized queries (Day 27), JOINs and GROUP BY for reports (Days 11, 7), `argparse`, exit codes, and pytest.

## Requirements

**Commands**

| Command | What it does |
|---|---|
| `init [--demo]` | create the tables in a new database file (`--demo` also adds 8 books and 3 members) |
| `add-book TITLE AUTHOR [--year N] [--pages N] [--genre G] [--price 12.99]` | add a book (and its author if new); the price is given in dollars and **stored as integer cents** |
| `search --title TEXT` / `search --author TEXT` | list books whose title (or author) contains the text, case-insensitively |
| `add-member NAME EMAIL` | register a member, joined today |
| `lend BOOK_ID MEMBER_ID` | lend a book, due in 14 days |
| `return BOOK_ID` | take a book back |
| `loans [--member ID]` | list books currently out (all, or one member's) |
| `overdue` | list late loans with the number of days late |
| `stats` | counts, the 3 most borrowed books, books per genre |

**Global options:** `--db FILE` (default `library.db`) and `--today YYYY-MM-DD` (default: the real date). The `--today` option exists so that tests and examples never depend on the clock. The repository already works this way: dates are passed in.

**Business rules** (these already live in `LibraryRepository.lend`/`return_book`, do not re-implement them):

1. A book can only be lent if it is not already out.
2. A member can have at most 3 books out.
3. Unknown book or member ids are an error.
4. You can only return a book that is out.

**Behaviour**

- Exit code **0** on success, **1** on any error the user can fix (a broken rule, a missing database, a duplicate email), **2** on a bad command line (argparse does this for you).
- Errors go to **stderr** as one line starting with `error:`; normal output goes to stdout. No Python tracebacks for ordinary mistakes.
- Lists print as aligned tables (like your `show()` helper); an empty result prints a short sentence such as `no books found`.
- Prices print as dollars (`$12.99`) but are stored as cents. A missing price prints `-`.
- Every query uses parameters. Searching for `'; DROP TABLE books; --` must be harmless.
- Every list has a deterministic `ORDER BY` with a tie-breaker.

## How the Pieces Fit

```
00_practice/
    library_repo.py        # your Day 19 LibraryRepository (or copy solutions/library_repo.py)
    library_cli.py         # NEW today: argparse + printing, no SQL for the business rules
    test_library_cli.py    # NEW today: pytest, using a temporary database
```

```
  command line ──► argparse ──► library_cli.run() ──► LibraryRepository ──► SQLite file
                                      │                     (rules, SQL)
                                      └──► prints a table, returns an exit code
```

Keep the layers apart: `argparse` turns text into Python values, the repository does the database work, and the CLI only prints. The only SQL in the CLI is for the two reports that the repository does not offer (`loans` with names, and `stats`). That keeps everything easy to test: `main(argv)` returns the exit code, so a test can call `main(['--db', path, 'lend', '1', '1'])` without starting a process.

## argparse in Five Minutes

`argparse` is in the standard library. You describe the command line, and it parses `sys.argv`, creates `--help` and prints errors for you. **Subcommands** (like `git commit`, `git push`) use `add_subparsers`:

```py
import argparse

parser = argparse.ArgumentParser(prog='greet.py', description='Say hello.')
parser.add_argument('--shout', action='store_true')            # a flag: present or not
sub = parser.add_subparsers(dest='command', required=True)
hi = sub.add_parser('hello')                                   # python greet.py hello Ada --times 2
hi.add_argument('name')                                        # positional (required)
hi.add_argument('--times', type=int, default=1)                # option with a type and a default

args = parser.parse_args(['--shout', 'hello', 'Ada', '--times', '2'])
print(args)
print(parser.parse_args(['hello', 'Bob']))
# Namespace(shout=True, command='hello', name='Ada', times=2)
# Namespace(shout=False, command='hello', name='Bob', times=1)
```

`parse_args()` without a list reads the real command line; passing a list (as above) is how you test. `type=int` converts for you and rejects `one`. `add_mutually_exclusive_group(required=True)` allows exactly one of several options, which is what `search --title / --author` needs. In your CLI, put a `main(argv=None)` function that calls `parser.parse_args(argv)`, and end the file with `if __name__ == '__main__': sys.exit(main())`.

## Milestones

Work through them in order. After each milestone the program does something useful and you can run its acceptance checks.

### Milestone 0: Setup

Copy (or write) `library_repo.py` into `00_practice/`. Create `library_cli.py` with a parser that knows all subcommands from the table, and a `main()` that just prints the parsed arguments for now. Add `--help` output to your checks.

**Acceptance:** `python library_cli.py --help` lists the nine subcommands, and a wrong argument is refused with exit code 2:

```sh
$ python library_cli.py --help
usage: library_cli.py [-h] [--db DB] [--today TODAY]
                      {init,add-book,search,add-member,lend,return,loans,overdue,stats}
                      ...

Manage a small library.

positional arguments:
  {init,add-book,search,add-member,lend,return,loans,overdue,stats}
    init                create the tables
    add-book            add a book
    search              find books by title or author
    add-member          register a member
    lend                lend a book to a member
    return              return a book
    loans               list books currently on loan
    overdue             list overdue loans
    stats               a few numbers about the library

options:
  -h, --help            show this help message and exit
  --db DB               database file (default: library.db)
  --today TODAY         ISO date to use instead of the real date (for tests
                        and demos)

$ python library_cli.py lend one two
usage: library_cli.py lend [-h] book_id member_id
library_cli.py lend: error: argument book_id: invalid int value: 'one'
(exit code 2)
```

### Milestone 1: init

Implement `init`. It runs your Day 10 schema (`CREATE TABLE authors, books, members, loans`, `STRICT`, with the `CHECK`, `UNIQUE` and foreign-key constraints) using `executescript`. That is allowed here because the SQL is your own constant. With `--demo` it also adds books and members **through the repository** (`add_book`, `add_member`), not with hand-written INSERTs. Refuse to overwrite an existing database.

**Acceptance:**

```sh
$ python library_cli.py --db library.db init --demo
created library.db with demo data
```

Running it a second time prints `error: library.db already exists` on stderr and exits with 1. Running any other command on a missing file prints `error: nope.db not found; run 'init' first` and exits with 1.

*Hint:* `LibraryRepository.open(path)` would create an empty database for a mistyped path, so check `args.db.exists()` yourself first.

### Milestone 2: Books

Implement `add-book` and `search`. Convert `--price 12.99` to cents with `round(price * 100)` (not `int()`: `int(19.99 * 100)` is `1998`!). Print search results as a table with the columns `id title author year genre price`.

**Acceptance:**

```sh
$ python library_cli.py --db library.db --today 2025-03-14 search --author austen
id  title                author       year  genre    price
--  -------------------  -----------  ----  -------  -----
4   Pride and Prejudice  Jane Austen  1813  Romance  $5.99
5   Emma                 Jane Austen  1815  Romance  $6.49

$ python library_cli.py --db library.db --today 2025-03-14 add-book Hyperion "Dan Simmons" --year 1989 --genre Sci-Fi --price 12.99
added book 9: Hyperion
```

(Quote arguments that contain spaces. The ids you see depend on the order books were added.) `search --title zzz` prints `no books found`. The price in the database is `1299`.

### Milestone 3: Members and Loans

Implement `add-member`, `lend` and `return`. Catch `LibraryError` (the base class from Day 19) once, in `main`, and turn it into `error: <message>` plus exit code 1. Also catch `sqlite3.IntegrityError`, which is what a duplicate email raises. Print the due date after a successful `lend`.

**Acceptance** (the rules, one by one):

```sh
$ python library_cli.py --db library.db --today 2025-03-01 lend 1 1
loan 1: book 1 to member 1, due 2025-03-15
$ python library_cli.py --db library.db --today 2025-03-01 lend 3 1
loan 2: book 3 to member 1, due 2025-03-15
$ python library_cli.py --db library.db --today 2025-03-02 lend 1 2        (exit 1)
error: book 1 is already on loan
$ python library_cli.py --db library.db --today 2025-03-03 lend 6 1
loan 3: book 6 to member 1, due 2025-03-17
$ python library_cli.py --db library.db --today 2025-03-04 lend 7 1        (exit 1)
error: member 1 already has 3 books out
$ python library_cli.py --db library.db --today 2025-03-04 lend 99 1       (exit 1)
error: no book with id 99
```

### Milestone 4: Reports

Implement `loans` and `overdue`. For `loans`, write the JOIN yourself (loans, books, members; `returned_on IS NULL`; ordered by `due_on` then loan id) and support the optional `--member`. For `overdue`, call `repo.overdue(today)`.

*Hint:* an optional filter in one query: `WHERE returned_on IS NULL AND (:member IS NULL OR loans.member_id = :member)`, with `{'member': None}` when the option is missing. No string-building needed.

**Acceptance** (continuing the session; "today" is the 14th and then the 16th):

```sh
$ python library_cli.py --db library.db --today 2025-03-14 loans
loan  title       member        loaned_on   due_on
----  ----------  ------------  ----------  ----------
1     Dune        Alice Nguyen  2025-03-01  2025-03-15
2     The Hobbit  Alice Nguyen  2025-03-01  2025-03-15
3     1984        Alice Nguyen  2025-03-03  2025-03-17

$ python library_cli.py --db library.db --today 2025-03-14 overdue
nothing is overdue

$ python library_cli.py --db library.db --today 2025-03-16 overdue
loan  title       member        due_on      days_late
----  ----------  ------------  ----------  ---------
1     Dune        Alice Nguyen  2025-03-15  1
2     The Hobbit  Alice Nguyen  2025-03-15  1
```

A book due on the 15th is **not** overdue on the 15th. Returning a book makes it disappear from both lists:

```sh
$ python library_cli.py --db library.db --today 2025-03-16 return 1
book 1 returned
$ python library_cli.py --db library.db --today 2025-03-16 return 1        (exit 1)
error: book 1 is not on loan
```

### Milestone 5: Stats

Implement `stats`: a first line with the number of books, members, books on loan and overdue loans, then a "most borrowed" table (top 3 by number of loans, **ties broken by title**), then "books per genre" (count descending, ties by genre).

**Acceptance** (after the commands above):

```sh
$ python library_cli.py --db library.db --today 2025-03-16 stats
books: 9  members: 3  on loan: 2  overdue: 1

most borrowed
title       times
----------  -----
1984        1
Dune        1
The Hobbit  1

books per genre
genre      books
---------  -----
Sci-Fi     4
Romance    2
Dystopian  1
Fantasy    1
Tech       1
```

All three books have one loan, so the title decides the order. Without a tie-breaker, your output could change between runs or databases.

### Milestone 6: Tests and Polish

Write `test_library_cli.py` (pytest) that calls `main([...])` against a database in `tmp_path` and checks exit codes and output with the `capsys` fixture. Aim for at least these:

1. `init` refuses to overwrite; any command on a missing database exits 1.
2. `add-book --price 12.99` stores `1299`.
3. `search --title the` finds `The Hobbit` and `The Martian` but not `Dune`; an empty search says `no books found`.
4. **Injection:** `search --title "'; DROP TABLE books; --"` finds nothing and the books table still has 8 rows.
5. A lend/return cycle: lend (due +14 days), double-lend refused, return, return again refused.
6. The loan limit: the fourth book is refused and the member still has exactly 3 loans.
7. Unknown book id and unknown member id both produce a helpful message.
8. A duplicate member email exits 1 (`UNIQUE` in the message).
9. `overdue` on the due date is empty, five days later shows `5`.
10. A bad argument (`lend one two`) makes `main` raise `SystemExit` with code 2 (`pytest.raises(SystemExit)`).

The reference suite has 12 tests and runs in about a second:

```sh
$ uv run pytest solutions/day_28 -q
12 passed
```

*Polish:* run `sqlfluff lint` on the SQL strings you wrote, check `python library_cli.py --help` reads well, and check that no command can raise a traceback for an ordinary typo.

## A Complete Example Session

Everything below was produced by running the reference solution (`uv run python solutions/day_28.py` plays the whole session). Compare it with yours; ids, order and wording should match if you followed the milestones.

```sh
$ python library_cli.py --db library.db init --demo
created library.db with demo data
$ python library_cli.py --db library.db --today 2025-03-14 search --author austen
id  title                author       year  genre    price
--  -------------------  -----------  ----  -------  -----
4   Pride and Prejudice  Jane Austen  1813  Romance  $5.99
5   Emma                 Jane Austen  1815  Romance  $6.49
$ python library_cli.py --db library.db --today 2025-03-14 add-book Hyperion "Dan Simmons" --year 1989 --genre Sci-Fi --price 12.99
added book 9: Hyperion
$ python library_cli.py --db library.db --today 2025-03-01 lend 1 1
loan 1: book 1 to member 1, due 2025-03-15
$ python library_cli.py --db library.db --today 2025-03-01 lend 3 1
loan 2: book 3 to member 1, due 2025-03-15
$ python library_cli.py --db library.db --today 2025-03-02 lend 1 2
error: book 1 is already on loan
$ python library_cli.py --db library.db --today 2025-03-03 lend 6 1
loan 3: book 6 to member 1, due 2025-03-17
$ python library_cli.py --db library.db --today 2025-03-04 lend 7 1
error: member 1 already has 3 books out
$ python library_cli.py --db library.db --today 2025-03-04 lend 99 1
error: no book with id 99
$ python library_cli.py --db library.db --today 2025-03-16 overdue
loan  title       member        due_on      days_late
----  ----------  ------------  ----------  ---------
1     Dune        Alice Nguyen  2025-03-15  1
2     The Hobbit  Alice Nguyen  2025-03-15  1
$ python library_cli.py --db library.db --today 2025-03-16 return 1
book 1 returned
$ python library_cli.py --db library.db --today 2025-03-16 return 1
error: book 1 is not on loan
$ python library_cli.py --db library.db --today 2025-03-16 add-member Imposter alice@example.com
error: UNIQUE constraint failed: members.email
```

(The dates in a session are made up on purpose: `--today` lets us "travel" in time. In real use you leave the option out.)

## Stretch Goals

Only after the milestones are green. Each uses only what you know:

1. `--json` for `search`/`loans`/`overdue`: print the rows as JSON instead of a table (`json.dumps` of a list of dicts; the repository's dataclasses convert with `dataclasses.asdict`).
2. A `renew LOAN_ID` command that moves the due date 14 days later, at most twice per loan (add a `renewals` column through a **migration**, Day 27, and a rule in the repository).
3. A `history BOOK_ID` command: every loan of one book, with member names and `returned_on`, newest first.
4. A `fines` report: 25 cents per day late for returned books too (`returned_on > due_on`), stored as integer cents and printed in dollars, summed per member.
5. A read-only mode: use `mode=ro` (Day 27) for every command that only reads, so a bug in a report can never change data.
6. A `backup` command using `VACUUM INTO` and a date-stamped file name.
7. `export` that writes the books to CSV with `csv.DictWriter` (Day 20).

## Checking Your Work

- [ ] Every milestone's acceptance commands print exactly the output shown (apart from ids you chose differently).
- [ ] `uv run pytest 00_practice -q` is green.
- [ ] No f-string builds SQL; the only string-formatted SQL (if any) uses allowlisted constants.
- [ ] Rule failures exit with 1 and a one-line `error:`, argparse failures exit with 2, success is 0.
- [ ] Money is stored as integer cents everywhere.
- [ ] The business rules are only in the repository, and the CLI has no duplicate of them.
- [ ] You can explain, in a sentence each, why `lend` runs in a single transaction and why `--today` exists.

You turned a database design into a program that other people can use. That is a real piece of software, and it is yours.

CONGRATULATIONS !

[<< Day 27](../27_Day_Security_and_best_practices/27_security_and_best_practices.md) | [Day 29 >>](../29_Day_Project_analytics_report/29_project_analytics_report.md)
