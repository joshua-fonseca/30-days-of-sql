<div align="center">
  <h1> 30 Days Of SQL: Day 5 - Filtering with WHERE</h1>
</div>

[<< Day 4](../04_Day_Select/04_select.md) | [Day 6 >>](../06_Day_Expressions_and_functions/06_expressions_and_functions.md)

- [Day 5](#day-5)
  - [WHERE](#where)
    - [Comparison Operators](#comparison-operators)
    - [AND, OR and NOT](#and-or-and-not)
    - [Parentheses](#parentheses)
    - [BETWEEN](#between)
    - [IN](#in)
  - [Pattern Matching](#pattern-matching)
    - [LIKE](#like)
    - [Matching a Literal % or _](#matching-a-literal--or-_)
    - [GLOB](#glob)
    - [Upper and Lower Case](#upper-and-lower-case)
  - [NULL: The Missing Value](#null-the-missing-value)
    - [IS NULL and IS NOT NULL](#is-null-and-is-not-null)
    - [Three-Valued Logic](#three-valued-logic)
    - [NULL Traps](#null-traps)
  - [WHERE with Python Values](#where-with-python-values)
  - [ Exercises: Day 5](#exercises-day-5)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 5

## WHERE

`SELECT` chooses columns. `WHERE` chooses **rows**: only the rows for which the condition is true are kept.

```sql
-- syntax
SELECT columns FROM table_name WHERE condition;
```

We use the `students` table from Day 4. If you need it again, here it is:

```py
import sqlite3
from helpers import show      # the helper you saved on Day 4

conn = sqlite3.connect(':memory:')
conn.execute('''
    CREATE TABLE students (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER, city TEXT, score INTEGER
    ) STRICT
''')
conn.executemany('INSERT INTO students (name, age, city, score) VALUES (?, ?, ?, ?)', [
    ('Ana', 21, 'Toronto', 82), ('Ben', 23, 'London', 67), ('Cy', 22, 'Toronto', 91),
    ('Di', 20, 'Paris', 74),    ('Eli', 24, 'London', 74), ('Fay', 22, 'Oslo', None),
    ('Gus', None, 'Paris', 88), ('Hal', 21, None, 59),
])
```

### Comparison Operators

| Operator | Meaning |
|---|---|
| `=` | equal (a **single** `=`, unlike Python's `==`) |
| `<>` or `!=` | not equal |
| `<`, `<=` | less than, less than or equal |
| `>`, `>=` | greater than, greater than or equal |

```py
show(conn.execute('SELECT name, score FROM students WHERE score > 80'))
```

```sh
name  score
----  -----
Ana   82
Cy    91
Gus   88
(3 rows)
```

Text is compared with quotes, exactly:

```py
show(conn.execute("SELECT name FROM students WHERE city = 'Toronto'"))
```

```sh
name
----
Ana
Cy
(2 rows)
```

### AND, OR and NOT

Combine conditions with `AND` (both must be true), `OR` (at least one) and `NOT` (reverse it).

```py
show(conn.execute("SELECT name, score FROM students WHERE score >= 74 AND city = 'London'"))
```

```sh
name  score
----  -----
Eli   74
(1 row)
```

```py
show(conn.execute("SELECT name, city FROM students WHERE city = 'Paris' OR city = 'Oslo'"))
```

```sh
name  city
----  -----
Di    Paris
Fay   Oslo
Gus   Paris
(3 rows)
```

### Parentheses

`AND` is applied before `OR`, exactly as multiplication comes before addition in maths. When you mix them, **use parentheses** so the
meaning is clear to the database and to the next reader.

```py
# means: age 22  OR  (age 21 AND score > 80)
show(conn.execute('SELECT name, age, score FROM students WHERE age = 22 OR age = 21 AND score > 80'))
```

```sh
name  age  score
----  ---  -----
Ana   21   82
Cy    22   91
Fay   22   NULL
(3 rows)
```

```py
# means: (age 22 OR age 21)  AND  score > 80
show(conn.execute('SELECT name, age, score FROM students WHERE (age = 22 OR age = 21) AND score > 80'))
```

```sh
name  age  score
----  ---  -----
Ana   21   82
Cy    22   91
(2 rows)
```

Fay appears in the first result only. She is 22, which satisfies the left side of the `OR`, and her missing score does not matter.

### BETWEEN

`x BETWEEN low AND high` is a short way to write `x >= low AND x <= high`. **Both ends are included.**

```py
show(conn.execute('SELECT name, age FROM students WHERE age BETWEEN 21 AND 23'))
```

```sh
name  age
----  ---
Ana   21
Ben   23
Cy    22
Fay   22
Hal   21
(5 rows)
```

### IN

`IN` checks whether a value is in a list. It replaces a chain of `OR`s.

```py
show(conn.execute("SELECT name, city FROM students WHERE city IN ('Paris', 'Oslo')"))
```

```sh
name  city
----  -----
Di    Paris
Fay   Oslo
Gus   Paris
(3 rows)
```

`NOT IN` does the opposite:

```py
show(conn.execute("SELECT name, city FROM students WHERE city NOT IN ('Paris', 'Oslo')"))
```

```sh
name  city
----  -------
Ana   Toronto
Ben   London
Cy    Toronto
Eli   London
(4 rows)
```

Hal, whose city is `NULL`, is in neither result. We'll see why shortly.

## Pattern Matching

### LIKE

`LIKE` matches text against a **pattern** with two special characters:

- `%` stands for any number of characters (including none),
- `_` stands for exactly one character.

```py
show(conn.execute("SELECT name FROM students WHERE name LIKE 'A%'"))       # starts with A:  Ana
show(conn.execute("SELECT name FROM students WHERE name LIKE '%a%'"))      # contains a:     Ana, Fay, Hal
show(conn.execute("SELECT name FROM students WHERE name LIKE '_a%'"))      # 2nd letter a:   Fay, Hal
show(conn.execute("SELECT name FROM students WHERE name LIKE '___'"))      # exactly 3 chars: Ana, Ben, Eli, Fay, Gus, Hal
```

In SQLite, `LIKE` ignores upper and lower case for ordinary English letters. So `'a%'` matches `Ana`:

```py
show(conn.execute("SELECT name FROM students WHERE name LIKE 'a%'"))
```

```sh
name
----
Ana
(1 row)
```

`NOT LIKE` is the opposite. A leading `%` (as in `'%word'`) makes matching slower on big tables, a topic for Day 21.

> **In other databases:** `LIKE` is case-**sensitive** in PostgreSQL (use `ILIKE` for case-insensitive) and Oracle, and case-insensitive in
> MySQL and SQL Server by default. DuckDB is case-sensitive too, and has `ILIKE`.

### Matching a Literal % or _

What if you want to find a real `%` in the data? Pick an escape character with `ESCAPE` and put it before the special character:

```py
conn.execute('CREATE TABLE codes (code TEXT)')
conn.executemany('INSERT INTO codes VALUES (?)', [('5%',), ('50',), ('5x',), ('15%',)])

print(conn.execute("SELECT code FROM codes WHERE code LIKE '5%'").fetchall())
# [('5%',), ('50',), ('5x',)]       % acts as a wildcard

print(conn.execute(r"SELECT code FROM codes WHERE code LIKE '5\%' ESCAPE '\'").fetchall())
# [('5%',)]                         \% means a real percent sign
```

### GLOB

`GLOB` is SQLite's other pattern operator. It is **case-sensitive** and uses Unix-style wildcards:

- `*` any number of characters,
- `?` exactly one character,
- `[abc]` or `[a-z]` one character from a set or range.

```py
print(conn.execute("SELECT name FROM students WHERE name GLOB 'a*'").fetchall())       # []     lowercase a: no match
print(conn.execute("SELECT name FROM students WHERE name GLOB 'A*'").fetchall())       # [('Ana',)]
print(conn.execute("SELECT name FROM students WHERE name GLOB '[AB]*'").fetchall())    # [('Ana',), ('Ben',)]
```

Use `GLOB` when case matters and you want character sets, and `LIKE` for quick, case-insensitive searching. `GLOB` is specific to SQLite,
so it will not work in other databases.

### Upper and Lower Case

A plain `=` comparison on text **is** case-sensitive in SQLite. Add `COLLATE NOCASE` to ignore case:

```py
print(conn.execute("SELECT 'Ana' = 'ana', 'Ana' = 'ana' COLLATE NOCASE, 'Ana' LIKE 'ana', 'Ana' GLOB 'ana'").fetchone())
# (0, 1, 1, 0)
```

SQLite has no `TRUE` or `FALSE` result type. A comparison returns `1` for true and `0` for false.

## NULL: The Missing Value

`NULL` is not zero, not an empty string, not `False`. It means "unknown" or "no value". That one idea has some unexpected
consequences, and it causes more SQL bugs than anything else, so take your time with this section.

### IS NULL and IS NOT NULL

You cannot test for `NULL` with `=`:

```py
show(conn.execute('SELECT name, score FROM students WHERE score = NULL'))
```

```sh
name  score
----  -----
(0 rows)
```

No rows! Fay's score is missing, but the comparison "is Fay's score equal to NULL?" has the answer *unknown*, not *true*, and
`WHERE` only keeps rows where the condition is **true**. To test for NULL, use `IS NULL`:

```py
show(conn.execute('SELECT name, score FROM students WHERE score IS NULL'))
```

```sh
name  score
----  -----
Fay   NULL
(1 row)
```

And `IS NOT NULL` for the opposite:

```py
show(conn.execute('SELECT name, score FROM students WHERE score IS NOT NULL ORDER BY score DESC LIMIT 2'))
```

```sh
name  score
----  -----
Cy    91
Gus   88
(2 rows)
```

### Three-Valued Logic

In Python a condition is `True` or `False`. In SQL it can be **true, false or unknown (NULL)**. Any comparison with `NULL`, even
`NULL = NULL`, is unknown. Ask SQLite yourself:

```py
show(conn.execute('SELECT NULL = NULL AS eq, NULL IS NULL AS is_null, 1 = NULL AS one_eq'))
```

```sh
eq    is_null  one_eq
----  -------  ------
NULL  1        NULL
(1 row)
```

Here is how `AND`, `OR` and `NOT` treat unknown. The rule of thumb: *unknown AND false* is false (it can never be true), and
*unknown OR true* is true (it already is), but anything else involving unknown stays unknown.

| `a` | `b` | `a AND b` | `a OR b` |
|---|---|---|---|
| true | true | true | true |
| true | false | false | true |
| true | NULL | **NULL** | true |
| false | false | false | false |
| false | NULL | false | **NULL** |
| NULL | NULL | **NULL** | **NULL** |

and `NOT NULL` is `NULL`. You can check any row yourself:

```py
print(conn.execute('SELECT NULL AND 1, NULL AND 0, NULL OR 1, NULL OR 0, NOT NULL').fetchone())
# (None, 0, 1, None, None)
```

`WHERE` keeps a row only when the condition is **true**. Both *false* and *unknown* rows are dropped. That is the key to everything below.

SQLite also has a null-safe comparison, `IS`, which treats two NULLs as equal: `NULL IS NULL` is true, and `1 IS NULL` is false.
`IS NOT` is its opposite.

### NULL Traps

Because unknown rows disappear, "the opposite" query is **not** always the complement. Be careful with these:

```py
show(conn.execute("SELECT name, city FROM students WHERE city <> 'Toronto'"))
```

```sh
name  city
----  ------
Ben   London
Di    Paris
Eli   London
Fay   Oslo
Gus   Paris
(5 rows)
```

There are 8 students, 2 of them live in Toronto, so you might expect 6 rows. Hal (city `NULL`) is missing because `NULL <> 'Toronto'` is
unknown. If you want him too, say so:

```py
show(conn.execute("SELECT name, city FROM students WHERE city <> 'Toronto' OR city IS NULL"))
```

The same thing happens with `NOT`. `NOT (score > 74)` does not include Fay, because `NOT unknown` is unknown:

```py
show(conn.execute('SELECT name, score FROM students WHERE NOT (score > 74)'))
```

```sh
name  score
----  -----
Ben   67
Di    74
Eli   74
Hal   59
(4 rows)
```

And `NOT IN` is the worst of all: if the list contains a `NULL`, **no row can match**.

```py
show(conn.execute("SELECT name, city FROM students WHERE city NOT IN ('Paris', NULL)"))
```

```sh
name  city
----  ----
(0 rows)
```

Why? For Ana, `'Toronto' NOT IN ('Paris', NULL)` means `'Toronto' <> 'Paris' AND 'Toronto' <> NULL`, which is *true AND unknown* = unknown, so
she is dropped. We will meet this trap again with subqueries on Day 13.

**Rules to remember:** test for missing values with `IS NULL`, never `= NULL`. Whenever a column can be NULL, ask "what should happen to
the rows where it is?" and write that down in the query.

## WHERE with Python Values

Values from Python go in as placeholders, as on Day 3:

```py
min_score, city = 75, 'Paris'
show(conn.execute('SELECT name, score FROM students WHERE score > ? AND city = ?', (min_score, city)))
```

```sh
name  score
----  -----
Gus   88
(1 row)
```

For `IN`, you need one `?` per value:

```py
show(conn.execute('SELECT name FROM students WHERE city IN (?, ?)', ('Oslo', 'Paris')))
```

For `LIKE`, the `%` wildcards are part of the **value**, so add them in Python, not in the SQL text:

```py
keyword = 'a'
show(conn.execute('SELECT name FROM students WHERE name LIKE ?', (f'%{keyword}%',)))
```

```sh
name
----
Ana
Fay
Hal
(3 rows)
```

(Using an f-string here is fine: it builds the *value*, which is then passed safely through the placeholder.)

Filtering is the heart of querying, and you now understand its trickiest part, NULL. Now do some exercises.

## Exercises: Day 5

### Exercises: Level 1

Use your `00_practice/library.db` with the twelve books. Use `show()` to display results, ordered the way each exercise says.

1. Show the title and year of books published after 2000, oldest first.
2. Show the titles of all books by `Jane Austen`, in alphabetical order.
3. Show the title and genre of books whose genre is `Sci-Fi` or `Fantasy`, using `IN`. Order by title.
4. Show the titles that contain the word `the` (in any case), in alphabetical order.
5. Show the title and pages of books with between 300 and 400 pages (inclusive), shortest first.
6. Show the titles of books that have no rating yet, in alphabetical order.
7. Show the title and rating of the 3 best-rated books. Don't include unrated books, and break rating ties by title.
8. Show the title and genre of all books that are **not** `Sci-Fi`, ordered by title.
9. Use `GLOB` to show the titles that start with the capital-letter word `The`.
10. Show the title and author of books whose author's name ends with `Weir`.
11. Use `_` to show the titles that have exactly 4 characters, in alphabetical order.
12. Show the title and year of books published before 1900 **or** after 2010, oldest first.
13. Show the title, `price_cents` and rating of books that cost less than 800 cents **and** have a rating of 4.5 or more, ordered by title.
14. Print how many books were published after 2000, by taking `len()` of the fetched rows. It should be `4`.

```sh
# expected for exercise 4
title
------------------------
The Hobbit
The Martian
The Name of the Wind
The Pragmatic Programmer
(4 rows)

# expected for exercise 13
title       price_cents  rating
----------  -----------  ------
1984        799          4.6
The Hobbit  799          4.7
(2 rows)
```

### Exercises: Level 2

1. Write a function `search_books(conn, keyword)` that returns a sorted list of titles where the keyword appears in the **title or the
   author** (any case). Use a placeholder, and build the `%` wildcards in Python.

   ```py
   print(search_books(conn, 'jane'))   # ['Emma', 'Pride and Prejudice']
   print(search_books(conn, 'the'))    # ['The Hobbit', 'The Martian', 'The Name of the Wind', 'The Pragmatic Programmer']
   print(search_books(conn, 'zzz'))    # []
   ```

2. **Predict, then verify.** For each query, first write down how many rows you think it returns, then run it and print
   the real number. For every one that surprised you, explain why.

   ```sql
   a. SELECT title FROM books WHERE rating = NULL
   b. SELECT title FROM books WHERE rating <> 4.5
   c. SELECT title FROM books WHERE NOT (rating > 4.5)
   d. SELECT title FROM books WHERE rating > 4.5 OR rating IS NULL
   ```

   ```sh
   a 0
   b 8
   c 5
   d 7
   ```

3. Run both queries, and explain in words why the results differ. Then add parentheses to the first query so that it returns the second
   query's rows.

   ```sql
   SELECT title, genre, pages FROM books WHERE genre = 'Sci-Fi' OR genre = 'Tech' AND pages > 400 ORDER BY title
   SELECT title, genre, pages FROM books WHERE (genre = 'Sci-Fi' OR genre = 'Tech') AND pages > 400 ORDER BY title
   ```

   ```sh
   # first query                              # second query
   Clean Code         Tech    464             Clean Code         Tech    464
   Dune               Sci-Fi  612             Dune               Sci-Fi  612
   Neuromancer        Sci-Fi  271             Project Hail Mary  Sci-Fi  476
   Project Hail Mary  Sci-Fi  476
   The Martian        Sci-Fi  369
   ```

4. The query `SELECT title FROM books WHERE author = 'jane austen'` returns nothing. Fix it in **two different ways** so that it returns `Emma`
   and `Pride and Prejudice`.

5. Create a table `codes` holding the values `'5%'`, `'50'`, `'5x'` and `'15%'`. Write one query that finds the codes that *start with a
   5* (it matches three) and another that finds exactly the code `5%` using `ESCAPE`.

### Exercises: Level 3

Use `00_practice/datasets.db`.

1. Show the names of the countries that contain `land` (any case), in alphabetical order.
   (The first and last rows should be `Bouvet Island` and `Åland Islands`; the output has 29 rows.)

   ```sh
   name
   ----------------------------------------------------
   Bouvet Island
   Cayman Islands
   Christmas Island
   ...
   Virgin Islands (U.S.)
   Åland Islands
   (29 rows)
   ```

2. Count the Hacker News posts whose **title** contains python, in four ways, and explain why the numbers differ:
   `LIKE '%python%'`, `GLOB '*python*'`, `GLOB '*Python*'` and `GLOB '*[Pp]ython*'`. A search for the lines containing
   `python` or `Python` is a common task: which of the four matches that question?

   ```sh
   LIKE '%python%'        160
   GLOB '*python*'        12
   GLOB '*Python*'        149
   GLOB '*[Pp]ython*'     160
   ```

3. Show the countries that use the `Euro` and have a population between 1,000,000 and 5,000,000, biggest first.

   ```sh
   name                population
   ------------------  ----------
   Lithuania           2872294
   Slovenia            2064188
   Latvia              1961600
   Republic of Kosovo  1733842
   Estonia             1315944
   (5 rows)
   ```

4. Many Hacker News posts such as "Ask HN" and "Tell HN" have no `url`. Show the 5 posts without a url (`url IS NULL`) that have more than
   100 points, most points first (break ties by `id`), and print how many such posts there are in total.

   ```sh
   id        title                                                                      num_points
   --------  -------------------------------------------------------------------------  ----------
   12073675  Tell HN: New features and a moderator                                      2381
   11312984  Ask HN: How much do you make at Amazon? Here is how much I make at Amazon  1213
   11326011  Tell HN: AngelList told my employer that I'd updated my profile            958
   12496558  Ask HN: What's your favorite HN post?                                      691
   11647165  Tell HN: Apply HN apology and revision                                     653
   (5 rows)
   58
   ```

CONGRATULATIONS !

[<< Day 4](../04_Day_Select/04_select.md) | [Day 6 >>](../06_Day_Expressions_and_functions/06_expressions_and_functions.md)
