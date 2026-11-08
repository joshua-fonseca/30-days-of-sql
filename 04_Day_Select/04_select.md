<div align="center">
  <h1> 30 Days Of SQL: Day 4 - SELECT, ORDER BY, LIMIT</h1>
</div>

[<< Day 3](../03_Day_Inserting_data/03_inserting_data.md) | [Day 5 >>](../05_Day_Filtering/05_filtering.md)

- [Day 4](#day-4)
  - [SELECT](#select)
    - [Choosing Columns](#choosing-columns)
    - [SELECT * and Why to Avoid It](#select--and-why-to-avoid-it)
    - [Column Aliases](#column-aliases)
    - [Computed Columns](#computed-columns)
    - [DISTINCT](#distinct)
  - [Getting Results into Python](#getting-results-into-python)
    - [fetchone, fetchall and Looping](#fetchone-fetchall-and-looping)
    - [Building a show() Helper](#building-a-show-helper)
  - [ORDER BY](#order-by)
    - [Sorting Ascending and Descending](#sorting-ascending-and-descending)
    - [Sorting by More Than One Column](#sorting-by-more-than-one-column)
    - [Ties Have No Guaranteed Order](#ties-have-no-guaranteed-order)
    - [Where Do NULLs Go?](#where-do-nulls-go)
  - [LIMIT and OFFSET](#limit-and-offset)
    - [Pagination](#pagination)
  - [ Exercises: Day 4](#exercises-day-4)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 4

## SELECT

`SELECT` is the statement you will write more than any other. It reads data from a table without changing it.

```sql
-- syntax
SELECT column1, column2
FROM table_name;
```

For today's examples we use a small `students` table. Create it by running this once:

```py
import sqlite3

conn = sqlite3.connect(':memory:')
conn.execute('''
    CREATE TABLE students (
        id    INTEGER PRIMARY KEY,
        name  TEXT NOT NULL,
        age   INTEGER,
        city  TEXT,
        score INTEGER
    ) STRICT
''')
conn.executemany('INSERT INTO students (name, age, city, score) VALUES (?, ?, ?, ?)', [
    ('Ana', 21, 'Toronto', 82), ('Ben', 23, 'London', 67), ('Cy', 22, 'Toronto', 91),
    ('Di', 20, 'Paris', 74),    ('Eli', 24, 'London', 74), ('Fay', 22, 'Oslo', None),
    ('Gus', None, 'Paris', 88), ('Hal', 21, None, 59),
])
```

Some values are missing on purpose (`None` becomes `NULL`) so we can see how they behave.

### Choosing Columns

List the columns you want, separated by commas. They come back in the order you list them.

```py
print(conn.execute('SELECT name, city FROM students').fetchall())
# [('Ana', 'Toronto'), ('Ben', 'London'), ('Cy', 'Toronto'), ('Di', 'Paris'),
# ('Eli', 'London'), ('Fay', 'Oslo'), ('Gus', 'Paris'), ('Hal', None)]
```

### SELECT * and Why to Avoid It

`*` means "all columns":

```py
print(conn.execute('SELECT * FROM students').fetchall())
# [(1, 'Ana', 21, 'Toronto', 82), (2, 'Ben', 23, 'London', 67), (3, 'Cy', 22, 'Toronto', 91), ... ]
```

`SELECT *` is great for looking around in a new table. In real code, name the columns. If someone adds a column later, `SELECT *`
changes the shape of your result, and tuple unpacking like `name, age = row` suddenly breaks. It is also wasteful to fetch columns
you never use.

### Column Aliases

`AS` gives a column a new name in the result:

```sql
-- syntax
SELECT column AS new_name FROM table_name;
```

```py
cur = conn.execute('SELECT name AS student, score AS points FROM students LIMIT 3')
print(cur.fetchall())
# [('Ana', 82), ('Ben', 67), ('Cy', 91)]
print([col[0] for col in cur.description])
# ['student', 'points']
```

The alias does not change the table, only the label on the result. (We will explain `cur.description` in a moment.)

### Computed Columns

A column in a `SELECT` can be any expression: arithmetic on columns, constants, functions. Give it an alias so it has a decent name.

```py
cur = conn.execute('SELECT name, score, score + 5 AS curved, score / 100.0 AS fraction FROM students LIMIT 4')
print(cur.fetchall())
# [('Ana', 82, 87, 0.82), ('Ben', 67, 72, 0.67), ('Cy', 91, 96, 0.91), ('Di', 74, 79, 0.74)]
```

The calculation happens for every row, and the stored data does not change.

### DISTINCT

`DISTINCT` removes duplicate rows from the result.

```sql
-- syntax
SELECT DISTINCT column FROM table_name;
```

```py
print(conn.execute('SELECT city FROM students').fetchall())
# [('Toronto',), ('London',), ('Toronto',), ('Paris',), ('London',), ('Oslo',), ('Paris',), (None,)]

print(conn.execute('SELECT DISTINCT city FROM students').fetchall())
# [('Toronto',), ('London',), ('Paris',), ('Oslo',), (None,)]
```

`DISTINCT` looks at the **whole row** you selected. With two columns, only rows where *both* values repeat are removed:

```py
print(conn.execute('SELECT DISTINCT city, age FROM students ORDER BY city, age').fetchall())
# [(None, 21), ('London', 23), ('London', 24), ('Oslo', 22), ('Paris', None),
# ('Paris', 20), ('Toronto', 21), ('Toronto', 22)]
```

Notice that `NULL` counts as a value, and two NULLs are treated as the same by `DISTINCT`.

## Getting Results into Python

### fetchone, fetchall and Looping

You met `fetchone()` and `fetchall()` on Day 1. A cursor remembers where it is. Each `fetchone()` moves forward by one row, and
`fetchall()` returns the rows that are left.

```py
cur = conn.execute('SELECT name, age FROM students ORDER BY id')
print(cur.fetchone())      # ('Ana', 21)
print(cur.fetchone())      # ('Ben', 23)
print(cur.fetchall())      # [('Cy', 22), ('Di', 20), ('Eli', 24), ('Fay', 22), ('Gus', None), ('Hal', 21)]
print(cur.fetchone())      # None  nothing left
```

When the rows run out, `fetchone()` returns `None` and `fetchall()` returns an empty list. A cursor is also **iterable**, so you can
loop over it directly, which is how you handle large results without building a big list:

```py
for name, age in conn.execute('SELECT name, age FROM students LIMIT 2'):
    print(name, age)
# Ana 21
# Ben 23
```

### Building a show() Helper

Lists of tuples are hard to read once there are more than a few rows or columns. Let's write a helper that prints a cursor as a neat
table. We will use it for the rest of the course, so save it in a file called `00_practice/helpers.py`:

```py
# 00_practice/helpers.py
def show(cur):
    """Print the rows left in a cursor as a table."""
    headers = [col[0] for col in cur.description]
    rows = cur.fetchall()
    cells = [['NULL' if v is None else str(v) for v in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    print('  '.join(h.ljust(w) for h, w in zip(headers, widths)).rstrip())
    print('  '.join('-' * w for w in widths))
    for r in cells:
        print('  '.join(v.ljust(w) for v, w in zip(r, widths)).rstrip())
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
```

Here is how it works, line by line:

- `cur.description` is a tuple with one entry per column of the last query. The first item of each entry is the column's **name**
  (the alias, if you used one), so `headers` is the list of column names. This is why `show` works for any query.
- `rows = cur.fetchall()` gets all the rows.
- `cells` converts every value to a string, showing `None` as `NULL`, so everything can be measured and aligned.
- `widths` finds, for each column, the longest text among the header and all its cells.
- The `print` lines pad (`ljust`) each piece to its column width and join them with two spaces. `rstrip()` removes the spaces left at
  the end of each line. The second line is the dashed rule under the headers.
- The last line reports the row count, with the correct singular or plural.

To use it from another file, import it:

```py
from helpers import show

show(conn.execute('SELECT * FROM students'))
```

```sh
id  name  age   city     score
--  ----  ----  -------  -----
1   Ana   21    Toronto  82
2   Ben   23    London   67
3   Cy    22    Toronto  91
4   Di    20    Paris    74
5   Eli   24    London   74
6   Fay   22    Oslo     NULL
7   Gus   NULL  Paris    88
8   Hal   21    NULL     59
(8 rows)
```

If your practice files are in `00_practice/`, `from helpers import show` works when you run them as `uv run python 00_practice/day_4.py`.

## ORDER BY

Without `ORDER BY`, SQL promises **no particular order**. The rows usually come out in the order they were inserted, but you must
never rely on that. If order matters, say so.

### Sorting Ascending and Descending

```sql
-- syntax
SELECT columns FROM table_name ORDER BY column [ASC | DESC];
```

`ASC` (ascending, smallest first) is the default. `DESC` is descending.

```py
show(conn.execute('SELECT name, score FROM students ORDER BY score DESC LIMIT 3'))
```

```sh
name  score
----  -----
Cy    91
Gus   88
Ana   82
(3 rows)
```

Text sorts alphabetically, numbers numerically, and ISO dates (`'2025-03-14'`) chronologically. You can also sort by an expression or by
an alias:

```py
show(conn.execute('SELECT name, score * 2 AS double FROM students ORDER BY double DESC LIMIT 3'))
```

```sh
name  double
----  ------
Cy    182
Gus   176
Ana   164
(3 rows)
```

### Sorting by More Than One Column

Put several columns after `ORDER BY`. The first is the main sort, and the next ones break ties.

```py
show(conn.execute('SELECT name, city, score FROM students ORDER BY city, score DESC'))
```

```sh
name  city     score
----  -------  -----
Hal   NULL     59
Eli   London   74
Ben   London   67
Fay   Oslo     NULL
Gus   Paris    88
Di    Paris    74
Cy    Toronto  91
Ana   Toronto  82
(8 rows)
```

Rows are sorted by city first. Inside each city, the higher score comes first. `ASC`/`DESC` applies to **each column
separately**: `ORDER BY city, score DESC` means city ascending, then score descending.

### Ties Have No Guaranteed Order

Look at Di and Eli, who both scored 74. If you only sort by `score`, SQL may list them in either order, and a different version of
SQLite or a different query plan could change it. When your result must be reproducible (and for exercises with expected output),
add a column that breaks every tie, such as `id` or `name`:

```py
show(conn.execute('SELECT name, score FROM students ORDER BY score DESC, name'))
```

### Where Do NULLs Go?

SQLite treats `NULL` as smaller than every other value. So ascending order puts NULLs **first**, and descending order puts them **last**.

```py
show(conn.execute('SELECT name, score FROM students ORDER BY score'))
```

```sh
name  score
----  -----
Fay   NULL
Hal   59
Ben   67
Di    74
Eli   74
Ana   82
Gus   88
Cy    91
(8 rows)
```

You can choose with `NULLS FIRST` or `NULLS LAST` (SQLite 3.30+):

```py
show(conn.execute('SELECT name, score FROM students ORDER BY score NULLS LAST'))
```

```sh
name  score
----  -----
Hal   59
Ben   67
Di    74
Eli   74
Ana   82
Gus   88
Cy    91
Fay   NULL
(8 rows)
```

> **In other databases:** PostgreSQL and Oracle put NULLs *last* for ascending order, the opposite of SQLite and MySQL. SQL Server
> puts them first, like SQLite. Writing `NULLS FIRST` or `NULLS LAST` makes your query behave the same everywhere (SQL Server lacks the
> keyword, MySQL too).

## LIMIT and OFFSET

`LIMIT n` returns at most `n` rows. `OFFSET m` skips the first `m` rows. Together with `ORDER BY` they answer "top 3" and
"next 3" questions.

```sql
-- syntax
SELECT columns FROM table_name ORDER BY column LIMIT count OFFSET skip;
```

```py
# the 3 highest scores
show(conn.execute('SELECT name, score FROM students ORDER BY score DESC LIMIT 3'))
```

```sh
name  score
----  -----
Cy    91
Gus   88
Ana   82
(3 rows)
```

```py
# skip those 3, then take the next 3
show(conn.execute('SELECT name, score FROM students ORDER BY score DESC LIMIT 3 OFFSET 3'))
```

```sh
name  score
----  -----
Di    74
Eli   74
Ben   67
(3 rows)
```

`LIMIT` without an `ORDER BY` returns *some* rows, not necessarily the first ones, so always sort first when "which rows" matters.

> **In other databases:** SQL Server writes `SELECT TOP 3 name FROM students ORDER BY score DESC`. The SQL standard form,
> supported by PostgreSQL, Oracle and DuckDB, is `... ORDER BY score DESC FETCH FIRST 3 ROWS ONLY`. DuckDB and PostgreSQL also accept `LIMIT`.

### Pagination

Websites show results one page at a time. The pattern is:

```
LIMIT page_size OFFSET (page_number - 1) * page_size
```

With 3 students per page, page 3 skips 6 rows:

```py
show(conn.execute('SELECT id, name FROM students ORDER BY id LIMIT 3 OFFSET 6'))
```

```sh
id  name
--  ----
7   Gus
8   Hal
(2 rows)
```

Page 3 only has two rows because that is all that is left. On very large tables a big `OFFSET` gets slow, since SQLite still has to
walk past the skipped rows. Day 21 (indexes) explains why, and shows a faster technique called keyset pagination.

You can now ask a table for exactly the columns, the order and the amount you want. You are well on your way! Now do some exercises.

## Exercises: Day 4

### Exercises: Level 1

Use your `00_practice/library.db` with the twelve books from Day 3. For output with several columns, use `show()`.

1. Select every column of every book with `SELECT *` and print the rows.
2. Select only the titles.
3. Select the title and the author of every book.
4. Select the title as `book` and the year as `published`.
5. Get the distinct genres.
6. Show the title and year of all books ordered by year, oldest first.
7. Show the title and pages ordered by pages, longest first.
8. Show the 3 newest books (title and year).
9. Show the 3 oldest books (title and year).
10. Show page 2 of the books ordered by `title`, with 4 books per page (show `id` and `title`).
11. Show genre and title, ordered by genre and then by title.
12. Show the title and the price in dollars as a column called `price_dollars` (`price_cents / 100.0`), for the first 4 books.
13. Use `show()` to display `id`, `title` and `author` for all books.
14. Show the 5 cheapest books (title and `price_cents`). When prices tie, put the title that comes first alphabetically first.
15. Count the books and the distinct authors by taking `len()` of the fetched rows. You should get 12 and 10.

```sh
# expected for exercise 10
id  title
--  -------------------
6   Emma
2   Neuromancer
5   Pride and Prejudice
11  Project Hail Mary
(4 rows)

# expected for exercise 14
title                price_cents
-------------------  -----------
Pride and Prejudice  599
Emma                 649
1984                 799
The Hobbit           799
Brave New World      849
(5 rows)
```

### Exercises: Level 2

1. Write `show_aligned(cur)`, a copy of `show()` that **right-aligns columns containing numbers** (ints or floats) and left-aligns the
   rest. (Hint: look at the Python types of the fetched values with `isinstance`.) Test it on `SELECT title, pages, rating FROM books LIMIT 3`.

   ```sh
   title        pages  rating
   -----------  -----  ------
   Dune           612     4.5
   Neuromancer    271     4.0
   The Hobbit     310     4.7
   (3 rows)
   ```

2. Write a function `paginate(conn, page, per_page)` that returns a list of **titles** (ordered by `id`) for the given page. Use
   placeholders for the numbers. With 5 per page:

   ```py
   print(paginate(conn, 1, 5))   # ['Dune', 'Neuromancer', 'The Hobbit', 'The Name of the Wind', 'Pride and Prejudice']
   print(paginate(conn, 3, 5))   # ['Project Hail Mary', 'The Martian']
   print(paginate(conn, 4, 5))   # []
   ```

3. Show each book's age as a computed column: `2025 - year AS age`. List the 3 oldest books (title, year, age), breaking ties by title.

   ```sh
   title                year  age
   -------------------  ----  ---
   Pride and Prejudice  1813  212
   Emma                 1815  210
   Brave New World      1932  93
   (3 rows)
   ```

4. Show `genre`, `title` and `pages`, ordered by genre, and within each genre the longest book first.

   ```sh
   genre      title                     pages
   ---------  ------------------------  -----
   Dystopian  1984                      328
   Dystopian  Brave New World           311
   Fantasy    The Name of the Wind      662
   Fantasy    The Hobbit                310
   ...
   (12 rows)
   ```

5. Three of your books have no rating yet (`NULL`). Order the books by `rating` ascending (then `title`) and look at where the unrated
   ones appear. Then change the query so that the unrated books come **last**. Explain why NULLs came first in the original query.

### Exercises: Level 3

Use `00_practice/datasets.db` from Day 3 (`countries` and `hn_posts`).

1. Find the 10 most populated countries. This is the exercise you solved with Python on Day 10 and Day 19. Now it is one query:

   ```sh
   name                      population
   ------------------------  ----------
   China                     1377422166
   India                     1295210000
   United States of America  323947000
   Indonesia                 258705000
   Brazil                    206135893
   Pakistan                  194125062
   Nigeria                   186988000
   Bangladesh                161006790
   Russian Federation        146599183
   Japan                     126960000
   (10 rows)
   ```

2. Show the 5 Hacker News posts with the most points (title, `num_points`, author). If two posts tie, the one with the smaller `id` comes first.

   ```sh
   title                                  num_points  author
   -------------------------------------  ----------  -------------
   Pardon Snowden                         2553        erlend_sh
   Tell HN: New features and a moderator  2381        dang
   Master Plan, Part Deux                 1851        arturogarrido
   Responsive Pixel Art                   1622        bpierre
   I've Just Liberated My Modules         1573        chejazi
   (5 rows)
   ```

3. How many different currencies are used in the `countries` table? Fetch the distinct currencies and print `len()` of the result. (Day 7
   will show a way to count inside SQL.) The answer is `158`.

4. Countries are shown 10 per page, ordered by name. Show the names on page 3.

   ```sh
   name
   --------------------------------
   Belgium
   Belize
   Benin
   Bermuda
   Bhutan
   Bolivia (Plurinational State of)
   Bonaire, Sint Eustatius and Saba
   Bosnia and Herzegovina
   Botswana
   Bouvet Island
   (10 rows)
   ```

CONGRATULATIONS !

[<< Day 3](../03_Day_Inserting_data/03_inserting_data.md) | [Day 5 >>](../05_Day_Filtering/05_filtering.md)
