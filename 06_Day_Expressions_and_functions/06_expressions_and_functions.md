<div align="center">
  <h1> 30 Days Of SQL: Day 6 - Expressions & Scalar Functions</h1>
</div>

[<< Day 5](../05_Day_Filtering/05_filtering.md) | [Day 7 >>](../07_Day_Aggregates/07_aggregates.md)

- [Day 6](#day-6)
  - [Expressions and Functions](#expressions-and-functions)
  - [String Functions](#string-functions)
    - [upper, lower and length](#upper-lower-and-length)
    - [substr](#substr)
    - [instr](#instr)
    - [replace and trim](#replace-and-trim)
    - [Joining Strings: || and concat](#joining-strings--and-concat)
    - [format](#format)
  - [Numeric Functions](#numeric-functions)
    - [round and abs](#round-and-abs)
    - [min and max with Several Values](#min-and-max-with-several-values)
    - [Math Functions](#math-functions)
    - [Integer vs Decimal Division](#integer-vs-decimal-division)
  - [Converting Types](#converting-types)
    - [CAST](#cast)
    - [Implicit Conversion](#implicit-conversion)
  - [CASE](#case)
    - [Searched CASE](#searched-case)
    - [Simple CASE](#simple-case)
    - [iif](#iif)
  - [Handling NULL](#handling-null)
    - [COALESCE and IFNULL](#coalesce-and-ifnull)
    - [NULLIF](#nullif)
  - [More Operators](#more-operators)
  - [ Exercises: Day 6](#exercises-day-6)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 6

## Expressions and Functions

So far you have selected columns as they are. SQL can also **transform** values while it reads them: change the case of text, cut pieces
out of it, round numbers, or pick a value depending on a condition. A **function** takes some inputs in brackets and returns one value.
Functions that work on one row at a time, like all of today's, are called **scalar functions**. (The ones that combine many rows into
one value, like `COUNT`, are tomorrow's topic.)

You can use a function anywhere you can use a value: in the `SELECT` list, in `WHERE`, or in `ORDER BY`. Because a `SELECT` needs no table, we can
try each function on its own first.

```py
import sqlite3
from helpers import show

conn = sqlite3.connect(':memory:')
show(conn.execute("SELECT upper('sql') AS shout"))
```

```sh
shout
-----
SQL
(1 row)
```

## String Functions

### upper, lower and length

```py
print(conn.execute("SELECT upper('sql'), lower('SQL'), length('hello'), length('')").fetchone())
# ('SQL', 'sql', 5, 0)
```

`length` counts **characters** in text. Two things to know:

- `length(NULL)` is `NULL`, since a function given an unknown returns unknown.
- `upper` and `lower` only change plain English (ASCII) letters: `upper('é')` stays `é`. For accented text, handle the case in Python.

### substr

`substr(text, start, length)` cuts a piece out of a string. **Positions start at 1**, not 0 like Python.

```sql
-- syntax
substr(text, start)            -- from start to the end
substr(text, start, length)    -- length characters starting at start
```

```py
print(conn.execute("SELECT substr('database', 1, 4), substr('database', 5), substr('database', -4), substr('database', -4, 2)").fetchone())
# ('data', 'base', 'base', 'ba')
```

A negative start counts from the end (`-4` is the fourth character from the end). Be careful with `0`: `substr('abc', 0, 2)` returns just
`'a'`, because position 0 is "before the first character" and still uses up one of the two characters. Always start at 1 or higher.

> **In other databases:** most call it `SUBSTRING(text FROM 2 FOR 3)` or `SUBSTRING(text, 2, 3)`. SQLite also accepts the name `substring`.

### instr

`instr(text, search)` returns the position where `search` first appears in `text`, or `0` if it does not.

```py
print(conn.execute("SELECT instr('hello world', 'o'), instr('hello', 'z')").fetchone())
# (5, 0)
```

From here on the examples that read the `books` table use your library database. Open it with `lib = sqlite3.connect('00_practice/library.db')`.

`substr` and `instr` together can cut a string at a known character. Here is the first word of each title (we add a space on the end so a one-word title still has a space to find):

```py
from helpers import show
show(lib.execute("SELECT title, substr(title, 1, instr(title || ' ', ' ') - 1) AS first_word FROM books LIMIT 5"))
```

```sh
title                 first_word
--------------------  -----------
Dune                  Dune
Neuromancer           Neuromancer
The Hobbit            The
The Name of the Wind  The
Pride and Prejudice   Pride
(5 rows)
```

Read it from the inside out: `instr` finds the first space, `- 1` steps back one character,
and `substr` takes everything from the start up to there.

### replace and trim

`replace(text, find, substitute)` replaces **every** occurrence of `find`. The `trim` family removes characters from the ends:

```py
print(conn.execute("SELECT replace('a-b-c', '-', '+'), trim('  hi  '), ltrim('  hi  '), rtrim('  hi  '), trim('xxhixx', 'x')").fetchone())
# ('a+b+c', 'hi', 'hi  ', '  hi', 'hi')
```

`trim` removes spaces from both ends by default, `ltrim` only the left and `rtrim` only the right. A second argument lists the characters to
remove instead of spaces. `trim` is a great first step when cleaning messy text from files.

### Joining Strings: || and concat

You met `||` on Day 1. If **either side is `NULL`, the whole result is `NULL`**:

```py
print(conn.execute("SELECT 'a' || 'b' || 1, 'a' || NULL").fetchone())     # ('ab1', None)
```

SQLite 3.44 added `concat()` and `concat_ws()`, which treat `NULL` as an empty string instead and are therefore safer when a value might be missing:

```py
print(conn.execute("SELECT concat('a', NULL, 'b', 1), concat_ws('-', 'a', NULL, 'b')").fetchone())
# ('ab1', 'a-b')
```

`concat_ws(separator, ...)` ("with separator") puts a separator between the values and skips the `NULL`s. It is handy for building a full address from
parts that may be missing.

> **In other databases:** `||` is the standard, but MySQL uses `CONCAT()` (and `||` means OR there!), and SQL Server uses `+` or `CONCAT()`.

### format

`format(pattern, values...)` (also called `printf`) builds a string from a pattern. It works like Python's `%` formatting. The most useful
codes are `%d` for whole numbers, `%f` for decimals (`%.2f` means 2 decimal places), `%s` for text, and `%05d` for zero-padded numbers.

```py
print(conn.execute("SELECT format('%.2f', 3.14159), format('%s has %d items', 'cart', 3), format('%05d', 42)").fetchone())
# ('3.14', 'cart has 3 items', '00042')
```

This is how you turn the integer cents from Day 2 into a price to display:

```py
show(lib.execute("SELECT title, format('$%.2f', price_cents / 100.0) AS price FROM books LIMIT 3"))
```

```sh
title        price
-----------  ------
Dune         $10.99
Neuromancer  $8.99
The Hobbit   $7.99
(3 rows)
```

## Numeric Functions

### round and abs

`round(number, digits)` rounds to that many decimal places (0 if left out). `abs` removes the minus sign.

```py
print(conn.execute("SELECT round(3.14159, 2), round(2.5), round(3.5), round(-2.5), round(1234.5678, -2), abs(-7), abs(-2.5)").fetchone())
# (3.14, 3.0, 4.0, -3.0, 1235.0, 7, 2.5)
```

Two details: halves round **away from zero** (2.5 becomes 3, -2.5 becomes -3), and `round` always returns a decimal (`3.0`, not `3`), even with 0 digits.
SQLite treats a negative number of digits as 0, so `round(1234.5678, -2)` is `1235.0`, not `1200.0`. To round to hundreds, use `round(x / 100) * 100`.

### min and max with Several Values

`max` and `min` can take **several values** and return the biggest or smallest of them. (With one column they become an aggregate, which is tomorrow's story.)

```py
print(conn.execute("SELECT max(3, 9, 5), min(3, 9, 5), max(3, NULL)").fetchone())
# (9, 3, None)
```

If any argument is `NULL`, the result is `NULL`.

### Math Functions

SQLite 3.35 and newer include the usual maths:

```py
print(conn.execute("SELECT sqrt(16), pow(2, 10), floor(2.7), ceil(2.1), floor(-2.1), mod(10, 3), pi()").fetchone())
# (4.0, 1024.0, 2.0, 3.0, -3.0, 1.0, 3.141592653589793)
```

You also have `ln`, `log10`, `exp`, `sin`, `cos` and more. `floor` rounds down and `ceil` rounds up, which is different from `round`.

### Integer vs Decimal Division

Day 1 introduced the trap: dividing two integers drops the decimals. It is useful once you know about it. To group years into decades,
divide and multiply back:

```py
show(lib.execute("SELECT title, year, year / 10 * 10 AS decade FROM books ORDER BY year LIMIT 3"))
```

```sh
title                year  decade
-------------------  ----  ------
Pride and Prejudice  1813  1810
Emma                 1815  1810
Brave New World      1932  1930
(3 rows)
```

For a real division, make one side a decimal: `pages / 100.0` (or `CAST(pages AS REAL) / 100`).

**Dividing by zero** does not crash SQLite. It quietly returns `NULL`:

```py
print(conn.execute('SELECT 100 / 0, 100.0 / 0, 100 % 0').fetchone())     # (None, None, None)
```

> **In other databases:** PostgreSQL, SQL Server, MySQL (in strict mode) and DuckDB raise an *error* for division by zero. Don't rely on SQLite's
> leniency in code you might move elsewhere. We will use `NULLIF` below to avoid dividing by zero in the first place.

## Converting Types

### CAST

`CAST(value AS type)` converts a value to another type.

```py
print(conn.execute("SELECT CAST(7.9 AS INTEGER), CAST(-7.9 AS INTEGER), CAST('42' AS INTEGER), CAST(42 AS TEXT) || '!', CAST(7 AS REAL) / 2").fetchone())
# (7, -7, 42, '42!', 3.5)
```

Casting a decimal to an integer **cuts off** the decimals (it does not round). Casting text takes as many leading digits as it can
read, and `0` if there are none:

```py
print(conn.execute("SELECT CAST('42abc' AS INTEGER), CAST('abc' AS INTEGER)").fetchone())      # (42, 0)
```

That silent `0` is dangerous. A cast never tells you the text was not a number.

### Implicit Conversion

SQLite also converts values on its own when you mix types in arithmetic, which is more flexible than most databases:

```py
print(conn.execute("SELECT '5' + 1, '5' || 1, typeof('5' + 1)").fetchone())      # (6, '51', 'integer')
```

`+` makes the text `'5'` into a number, and `||` makes the number into text. Avoid depending on it, because the other databases would raise an
error for `'5' + 1`. When types matter, `CAST` them yourself.

## CASE

`CASE` is SQL's `if / elif / else`. It returns a value that depends on conditions, so you can use it anywhere a value fits.

### Searched CASE

```sql
-- syntax
CASE
    WHEN condition1 THEN result1
    WHEN condition2 THEN result2
    ELSE default_result
END
```

SQL checks the `WHEN`s **from top to bottom** and uses the first that is true, just like `elif`.

```py
conn.execute('CREATE TABLE students (name TEXT, score INTEGER)')
conn.executemany('INSERT INTO students VALUES (?, ?)',
                 [('Ana', 82), ('Ben', 67), ('Cy', 91), ('Di', 74), ('Eli', 74), ('Fay', None), ('Gus', 88), ('Hal', 59)])

show(conn.execute('''
    SELECT name, score,
           CASE WHEN score >= 90 THEN 'A'
                WHEN score >= 80 THEN 'B'
                WHEN score >= 70 THEN 'C'
                ELSE 'F'
           END AS grade
    FROM students
'''))
```

```sh
name  score  grade
----  -----  -----
Ana   82     B
Ben   67     F
Cy    91     A
Di    74     C
Eli   74     C
Fay   NULL   F
Gus   88     B
Hal   59     F
(8 rows)
```

Fay's missing score ended up as an `F`. Her `NULL >= 90` is unknown, so every `WHEN` was skipped and `ELSE` caught her. If a missing value needs its
own answer, **test for it first**:

```py
show(conn.execute('''
    SELECT name,
           CASE WHEN score IS NULL THEN 'absent'
                WHEN score >= 70 THEN 'pass'
                ELSE 'fail'
           END AS result
    FROM students
'''))
```

Without an `ELSE`, a row that matches no `WHEN` gets `NULL`.

### Simple CASE

When you compare one column with several exact values, the shorter form works:

```sql
-- syntax
CASE column WHEN value1 THEN result1 WHEN value2 THEN result2 ELSE other END
```

```py
show(conn.execute("SELECT name, CASE name WHEN 'Ana' THEN 'first' WHEN 'Hal' THEN 'last' END AS pos FROM students LIMIT 3"))
```

```sh
name  pos
----  -----
Ana   first
Ben   NULL
Cy    NULL
(3 rows)
```

`CASE` also works in `ORDER BY` and `WHERE`. This one puts the missing scores at the end without using `NULLS LAST`:

```py
show(conn.execute('SELECT name, score FROM students ORDER BY CASE WHEN score IS NULL THEN 1 ELSE 0 END, score DESC LIMIT 3'))
```

### iif

For a simple two-way choice there is a shortcut, `iif(condition, if_true, if_false)` (SQLite 3.32+):

```py
show(conn.execute("SELECT name, iif(score >= 70, 'pass', 'fail') AS result FROM students LIMIT 3"))
```

`iif` is just a short `CASE`. Like `CASE`, it takes the false branch when the condition is `NULL`.

## Handling NULL

### COALESCE and IFNULL

`coalesce(a, b, c, ...)` returns the **first value that is not NULL**. It is the standard way to supply a default.

```py
print(conn.execute("SELECT coalesce(NULL, NULL, 'x'), coalesce(NULL, 0), ifnull(NULL, 'dflt'), ifnull(5, 'dflt')").fetchone())
# ('x', 0, 'dflt', 5)
```

`ifnull(a, b)` is the two-argument version (`coalesce(a, b)`), and is SQLite and MySQL's name for it.

```py
show(lib.execute("SELECT title, coalesce(rating, 'unrated') AS rating FROM books WHERE rating IS NULL"))
```

```sh
title              rating
-----------------  -------
Emma               unrated
Brave New World    unrated
Project Hail Mary  unrated
(3 rows)
```

**Common mistake:** a default is a *claim*. Replacing a missing score with `0` says "this student scored zero", which is different from
"we don't know". Tomorrow you will see how aggregates like `AVG` quietly skip NULLs, and how `coalesce(score, 0)` would change the average.
Only replace NULL with a default when the default is really true for your question.

> **In other databases:** `COALESCE` works everywhere. SQL Server has `ISNULL(a, b)` and Oracle has `NVL(a, b)` for the two-argument case.

### NULLIF

`nullif(a, b)` does the reverse: it returns `NULL` **if the two are equal**, otherwise `a`. Its best use is protecting a division from zero, and turning
placeholder values like `''` back into `NULL`.

```py
print(conn.execute("SELECT nullif(5, 5), nullif(5, 6), nullif('', ''), 100 / nullif(0, 0)").fetchone())
# (None, 5, None, None)
```

For example, a hit rate where some players have no attempts:

```py
conn.execute('CREATE TABLE stats (player TEXT, hits INTEGER, attempts INTEGER)')
conn.executemany('INSERT INTO stats VALUES (?, ?, ?)', [('Ana', 30, 40), ('Ben', 5, 20), ('Cy', 0, 0), ('Di', 18, 24)])

show(conn.execute('''
    SELECT player, hits, attempts,
           round(100.0 * hits / nullif(attempts, 0), 1) AS pct
    FROM stats
'''))
```

```sh
player  hits  attempts  pct
------  ----  --------  ----
Ana     30    40        75.0
Ben     5     20        25.0
Cy      0     0         NULL
Di      18    24        75.0
(4 rows)
```

Cy's `attempts` became `NULL`, so the division returns `NULL` instead of an error (in other databases) or a misleading `0`.

## More Operators

| Operator | Meaning |
|---|---|
| `+ - * /` | arithmetic |
| `%` | remainder: `7 % 3` is `1`. Careful, `-7 % 3` is `-1` |
| `<>` and `!=` | both mean "not equal". `<>` is the SQL standard |
| `=` and `==` | both mean "equal" |
| `&`, `\|`, `<<`, `>>`, `~` | bitwise AND, OR, shifts, NOT, used for flags |
| `IS`, `IS NOT` | equal / not equal that treats `NULL` as a normal value |

```py
print(conn.execute('SELECT 7 % 3, -7 % 3, 5 <> 3, 5 != 5, 6 & 3, 6 | 3, 1 << 4').fetchone())
# (1, -1, 1, 0, 2, 7, 16)
```

You can now reshape values as you read them, which is half of cleaning data. Now do some exercises.

## Exercises: Day 6

### Exercises: Level 1

Use your `00_practice/library.db`. Unless stated, order by `id` so your output matches.

1. Show the first 5 titles in upper case.
2. Show each title with its length (as `letters`). List the 5 longest titles, breaking ties by title.
3. Show the first 4 books as a single `label` column in the form `Dune by Frank Herbert`.
4. Show the title and the first 3 letters of it (as `start`) for the first 5 books.
5. Show the title with every space replaced by an underscore (as `slug`) for the first 5 books.
6. Show every title and its rating, but replace missing ratings with the text `unrated`. Order by title.
7. Show the title and price formatted like `$39.99` for the books costing at least 2000 cents, cheapest first.
8. Show the title, rating and the rating rounded to a whole number (as `rounded`) for the first 5 **rated** books.
9. Use one `SELECT` to show `trim`, `ltrim` and `rtrim` of the text `'   Dune  '`, and print the tuple. Make the spaces visible in your output.
10. Show the title, year and decade (as `decade`, like `1810`) for the 6 oldest books, using integer division.
11. Show the title, pages, `pages / 100` and `pages / 100.0` (as `hundreds_int` and `hundreds`) for the first 3 books, and explain the difference.
12. Use `iif` to show the title, pages and a `size` of `'long'` for more than 400 pages and `'short'` otherwise, for the first 6 books.
13. Show which 3 books are closest to 300 pages: show title, pages and `abs(pages - 300)` as `distance`. Order by distance, then title.
14. In one query show `typeof('5' + 1)`, the value of `'5' + 1`, the value of `'5' || 1`, and `typeof(CAST('5' AS INTEGER))`.
15. Show the title in upper case and the author in lower case for the first 2 books.

```sh
# expected for exercise 6
title                     rating
------------------------  -------
1984                      4.6
Brave New World           unrated
Clean Code                4.1
Dune                      4.5
Emma                      unrated
Neuromancer               4.0
Pride and Prejudice       4.3
Project Hail Mary         unrated
The Hobbit                4.7
The Martian               4.6
The Name of the Wind      4.4
The Pragmatic Programmer  4.8
(12 rows)

# expected for exercise 10
title                year  decade
-------------------  ----  ------
Pride and Prejudice  1813  1810
Emma                 1815  1810
Brave New World      1932  1930
The Hobbit           1937  1930
1984                 1949  1940
Dune                 1965  1960
(6 rows)
```

### Exercises: Level 2

1. Classify every book by length with `CASE`: under 300 pages is `'short'`, under 450 is `'medium'`, otherwise `'long'`. Show title, pages and `length_class`, shortest first.

   ```sh
   title                     pages  length_class
   ------------------------  -----  ------------
   Neuromancer               271    short
   Pride and Prejudice       279    short
   The Hobbit                310    medium
   ...
   The Name of the Wind      662    long
   (12 rows)
   ```

2. Build the **initials** of each author from the first letter of the first name and the first letter after the first space, like `FH` for Frank Herbert. Show `author` and `initials`.
   One author's result will look wrong. Which one, and why?

   ```sh
   author            initials
   ----------------  --------
   Frank Herbert     FH
   William Gibson    WG
   J.R.R. Tolkien    JT
   ...
   Robert C. Martin  RC
   ```

3. Create this table and calculate each player's hit percentage `100.0 * hits / attempts`, rounded to 1 decimal, without ever dividing by zero. Show a second column
   that turns a missing percentage into `0.0`.

   ```py
   conn.execute('CREATE TABLE stats (player TEXT, hits INTEGER, attempts INTEGER)')
   conn.executemany('INSERT INTO stats VALUES (?, ?, ?)', [('Ana', 30, 40), ('Ben', 5, 20), ('Cy', 0, 0), ('Di', 18, 24)])
   ```

   ```sh
   player  hits  attempts  pct   pct_or_zero
   ------  ----  --------  ----  -----------
   Ana     30    40        75.0  75.0
   Ben     5     20        25.0  25.0
   Cy      0     0         NULL  0.0
   Di      18    24        75.0  75.0
   (4 rows)
   ```

4. **Predict, then verify.** Write down the result of each expression, then run `SELECT <expression>` and compare. Explain any you got wrong.

   ```sh
   7 / 2                  -> 3
   7 / 2.0                -> 3.5
   '5' + 1                -> 6
   '5' || 1               -> '51'
   'a' || NULL            -> None
   substr('hello', -3)    -> 'llo'
   10 % 4                 -> 2
   length('')             -> 0
   100 / 0                -> None
   ```

   (The right-hand values above are the answers; cover them while you predict.)

5. Add a `verdict` column using `CASE`: `'unrated'` if the rating is missing, `'excellent'` for 4.6 or more, `'good'` for 4.3 or more, otherwise `'okay'`. Show title, rating and verdict, ordered by `id`.
   Which `WHEN` must come first, and why?

6. Give each book a library code like `BK-0001`, zero-padded to 4 digits, using `format`. Show `code` and `title` for the first 4 books.

   ```sh
   code     title
   -------  --------------------
   BK-0001  Dune
   BK-0002  Neuromancer
   BK-0003  The Hobbit
   BK-0004  The Name of the Wind
   (4 rows)
   ```

### Exercises: Level 3

Use `00_practice/datasets.db`.

1. **Domains.** The Hacker News `url` column holds web addresses like `http://www.wired.com/2016/story`. Show the `id` and the **domain** (the part
   between `//` and the next `/`) for the first 8 posts, in `id` order, that have a url. Remove the `http://` or `https://` first with `replace`, then cut at the first `/`.
   Hint: `instr(x || '/', '/')` always finds a `/`, even when the address has none.

   ```sh
   id        domain
   --------  --------------------
   10176908  dangerousminds.net
   10176923  utcc.utoronto.ca
   10177011  www.wired.com
   10177048  www.getrevue.co
   10177077  www.atlasobscura.com
   10177103  www.theguardian.com
   10177144  dmitryfrank.com
   10177201  github.com
   (8 rows)
   ```

2. Label each country as `small` (under 1 million people), `medium` (under 10 million), `large` (under 100 million) or `huge`, using `CASE`. Show name, population and the label
   for the first 10 countries alphabetically.

   ```sh
   name                 population  size
   -------------------  ----------  ------
   Afghanistan          27657145    large
   Albania              2886026     medium
   Algeria              40400000    large
   American Samoa       57100       small
   Andorra              78014       small
   Angola               25868000    large
   Anguilla             13452       small
   Antarctica           1000        small
   Antigua and Barbuda  86295       small
   Argentina            43590400    large
   (10 rows)
   ```

3. Show the `id`, the length of the title (as `letters`) and a `preview` made of the first 40 characters of the title followed by `...`, for the 5 longest titles. Break ties by `id`.

   ```sh
   id        letters  preview
   --------  -------  -------------------------------------------
   10499454  86       The Geography of Radionavigation and the...
   11842386  86       A two-neuron system for adaptive goal-di...
   11930078  86       Kerberos Golden Ticket Protection Mitiga...
   12030097  86       African American Vernacular English Is N...
   12042527  86       Are fluoride levels in drinking water as...
   (5 rows)
   ```

CONGRATULATIONS !

[<< Day 5](../05_Day_Filtering/05_filtering.md) | [Day 7 >>](../07_Day_Aggregates/07_aggregates.md)
