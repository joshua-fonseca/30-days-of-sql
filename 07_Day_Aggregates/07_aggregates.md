<div align="center">
  <h1> 30 Days Of SQL: Day 7 - Aggregates, GROUP BY, HAVING</h1>
</div>

[<< Day 6](../06_Day_Expressions_and_functions/06_expressions_and_functions.md) | [Day 8 >>](../08_Day_Update_delete_transactions/08_update_delete_transactions.md)

- [Day 7](#day-7)
  - [Aggregate Functions](#aggregate-functions)
    - [COUNT](#count)
    - [SUM, AVG, MIN and MAX](#sum-avg-min-and-max)
    - [Aggregates and NULL](#aggregates-and-null)
    - [Aggregates on an Empty Set](#aggregates-on-an-empty-set)
  - [GROUP BY](#group-by)
    - [Grouping by One Column](#grouping-by-one-column)
    - [Several Aggregates at Once](#several-aggregates-at-once)
    - [Grouping by More Than One Column](#grouping-by-more-than-one-column)
    - [Grouping by an Expression](#grouping-by-an-expression)
  - [WHERE vs HAVING](#where-vs-having)
  - [The Order SQL Really Runs In](#the-order-sql-really-runs-in)
  - [The Bare Column Trap](#the-bare-column-trap)
  - [Joining Values Together: string_agg](#joining-values-together-string_agg)
  - [ Exercises: Day 7](#exercises-day-7)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 7

## Aggregate Functions

Yesterday's scalar functions worked on one row at a time. An **aggregate function** reads **many rows** and boils them down to a single value:
how many there are, their total, their average. This is where SQL starts to feel like data analysis.

We use the `students` table again:

```py
import sqlite3
from helpers import show

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

### COUNT

There are three ways to count, and they answer different questions:

| Expression | Counts |
|---|---|
| `COUNT(*)` | every row |
| `COUNT(column)` | the rows where that column is **not NULL** |
| `COUNT(DISTINCT column)` | the different non-NULL values |

```py
show(conn.execute('''
    SELECT COUNT(*) AS students, COUNT(score) AS scores, COUNT(city) AS cities,
           COUNT(DISTINCT city) AS distinct_cities
    FROM students
'''))
```

```sh
students  scores  cities  distinct_cities
--------  ------  ------  ---------------
8         7       7       4
(1 row)
```

There are 8 students, but only 7 have a score (Fay's is missing) and 7 have a city (Hal's is missing). Four different cities appear.
`COUNT(*)` is the safest "how many rows".

### SUM, AVG, MIN and MAX

```py
show(conn.execute('SELECT SUM(score), AVG(score), MIN(score), MAX(score) FROM students'))
```

```sh
SUM(score)  AVG(score)         MIN(score)  MAX(score)
----------  -----------------  ----------  ----------
535         76.42857142857143  59          91
(1 row)
```

Aggregates are used with `SELECT` like any other column, so you can give them aliases and apply `round` to them:

```py
print(conn.execute('SELECT round(AVG(score), 1) AS avg_score FROM students').fetchone())     # (76.4,)
```

`MIN` and `MAX` also work on text (alphabetical order) and dates:

```py
print(conn.execute('SELECT MIN(name), MAX(name), MIN(city) FROM students').fetchone())     # ('Ana', 'Hal', 'London')
```

> **In other databases:** `MIN`/`MAX` with several arguments (yesterday) are SQLite's. Elsewhere use `LEAST()` and `GREATEST()`.
> DuckDB has both.

### Aggregates and NULL

**Aggregates ignore NULLs.** The `AVG(score)` of `76.43` is the sum of the 7 real scores (535) divided by **7**, not by 8:

```py
show(conn.execute('SELECT SUM(score) AS total, COUNT(score) AS n, SUM(score) * 1.0 / COUNT(score) AS manual_avg, AVG(score) AS avg FROM students'))
```

```sh
total  n  manual_avg         avg
-----  -  -----------------  -----------------
535    7  76.42857142857143  76.42857142857143
(1 row)
```

That is usually what you want. Here is what happens if you "fix" the NULL by replacing it with a default, as we warned yesterday:

```py
show(conn.execute('SELECT AVG(coalesce(score, 0)) AS avg_with_zero, AVG(score) AS avg_ignoring_null FROM students'))
```

```sh
avg_with_zero  avg_ignoring_null
-------------  -----------------
66.875         76.42857142857143
(1 row)
```

Treating Fay's missing score as a zero drags the average down by ten points. It is a different question: "the average if absentees score
zero". Choose on purpose.

### Aggregates on an Empty Set

What if no rows match? `COUNT` returns `0`, and the others return `NULL`, because there is nothing to add up or average.

```py
show(conn.execute('SELECT COUNT(*), SUM(score), AVG(score), MAX(score), total(score) FROM students WHERE score > 1000'))
```

```sh
COUNT(*)  SUM(score)  AVG(score)  MAX(score)  total(score)
--------  ----------  ----------  ----------  ------------
0         NULL        NULL        NULL        0.0
(1 row)
```

`total()` is SQLite's variant of `SUM` that returns `0.0` instead of `NULL` for nothing. An aggregate with no `GROUP BY` always returns **exactly one row**, even
when nothing matched.

## GROUP BY

An aggregate on the whole table is useful, but the real power is asking the question **per group**: students per city, sales per month, the
average score per class. `GROUP BY` splits the rows into groups by a column's value, and the aggregates run once for each group.

```sql
-- syntax
SELECT group_column, AGGREGATE(column)
FROM table_name
GROUP BY group_column;
```

### Grouping by One Column

```py
show(conn.execute('SELECT city, COUNT(*) AS students FROM students GROUP BY city'))
```

```sh
city     students
-------  --------
NULL     1
London   2
Oslo     1
Paris    2
Toronto  2
(5 rows)
```

Five groups, one row for each. The students without a city form their own `NULL` group, since `GROUP BY` treats all NULLs as equal.
Think of it as sorting the students into piles by city, then counting each pile.

Add `ORDER BY` and `LIMIT` to rank the groups. You can order by an alias or by the aggregate itself:

```py
show(conn.execute('SELECT city, COUNT(*) AS students FROM students GROUP BY city ORDER BY students DESC, city LIMIT 2'))
```

```sh
city    students
------  --------
London  2
Paris   2
(2 rows)
```

### Several Aggregates at Once

```py
show(conn.execute('''
    SELECT city, COUNT(*) AS students, round(AVG(score), 1) AS avg_score, MAX(score) AS best
    FROM students GROUP BY city ORDER BY students DESC, city
'''))
```

```sh
city     students  avg_score  best
-------  --------  ---------  ----
London   2         70.5       74
Paris    2         81.0       88
Toronto  2         86.5       91
NULL     1         59.0       59
Oslo     1         NULL       NULL
(5 rows)
```

Oslo has one student, Fay, whose score is missing, so her group's average and best are `NULL` while the group still counts 1.

### Grouping by More Than One Column

List several columns and each *combination* becomes a group:

```py
show(conn.execute('SELECT city, age, COUNT(*) AS students FROM students GROUP BY city, age ORDER BY city, age'))
```

Every combination in this tiny table is unique, so you get eight groups of one. On bigger tables, it answers questions like "orders per customer per year".

### Grouping by an Expression

You can group by a calculation too, and you can use the alias from the `SELECT`:

```py
show(conn.execute('SELECT upper(substr(city, 1, 1)) AS initial, COUNT(*) AS students FROM students GROUP BY initial ORDER BY initial'))
```

```sh
initial  students
-------  --------
NULL     1
L        2
O        1
P        2
T        2
(5 rows)
```

## WHERE vs HAVING

Both filter, but at different moments:

- `WHERE` filters **rows**, before they are grouped.
- `HAVING` filters **groups**, after the aggregates have been calculated.

```sql
-- syntax
SELECT group_column, AGGREGATE(column)
FROM table_name
WHERE row_condition
GROUP BY group_column
HAVING group_condition;
```

Which cities have at least two students?

```py
show(conn.execute('SELECT city, COUNT(*) AS students FROM students GROUP BY city HAVING COUNT(*) >= 2 ORDER BY city'))
```

```sh
city     students
-------  --------
London   2
Paris    2
Toronto  2
(3 rows)
```

You cannot use an aggregate in `WHERE`, since the groups do not exist yet when `WHERE` runs:

```py
try:
    conn.execute('SELECT city, COUNT(*) FROM students WHERE COUNT(*) >= 2 GROUP BY city')
except sqlite3.Error as e:
    print(type(e).__name__, e)      # OperationalError misuse of aggregate: COUNT()
```

You can use both together. Here `WHERE` drops the students without a score before grouping, and `HAVING` keeps only the cities where the remaining students
average above 70:

```py
show(conn.execute('''
    SELECT city, round(AVG(score), 1) AS avg_score
    FROM students
    WHERE score IS NOT NULL
    GROUP BY city
    HAVING AVG(score) > 70
    ORDER BY avg_score DESC
'''))
```

```sh
city     avg_score
-------  ---------
Toronto  86.5
Paris    81.0
London   70.5
(3 rows)
```

**Rule of thumb:** if the condition is about a single row's own values, use `WHERE`. If it is about a group's aggregate, use `HAVING`. When both could work, `WHERE` is better, since it
shrinks the data *before* the expensive grouping.

## The Order SQL Really Runs In

You write `SELECT` first, but SQL does not run it first. Understanding the real order explains almost every "why can't I do that?" question:

```
  1. FROM       pick the table (and, from Day 11, join tables)
  2. WHERE      keep only the rows that match
  3. GROUP BY   put the rows into groups
  4. HAVING     keep only the groups that match
  5. SELECT     calculate the columns, aliases and aggregates
  6. DISTINCT   remove duplicate rows
  7. ORDER BY   sort the result
  8. LIMIT      cut off the rows you do not want
```

This tells you why:

- an aggregate cannot be in `WHERE` (the groups come in step 3, after `WHERE` in step 2),
- you can use a `SELECT` alias in `ORDER BY` (step 7 comes after step 5),
- SQLite (unlike most databases) also lets you use an alias in `WHERE`/`GROUP BY` as a convenience, but it is not standard and other databases reject it.

## The Bare Column Trap

When you group by city, what should `name` mean in `SELECT city, name, COUNT(*)`? A city has several students, so there is no single right
name. Most databases reject the query. **SQLite does not**; it quietly picks the name from some row in each group:

```py
show(conn.execute('SELECT city, name, COUNT(*) FROM students GROUP BY city ORDER BY city'))
```

```sh
city     name  COUNT(*)
-------  ----  --------
NULL     Hal   1
London   Ben   2
Oslo     Fay   1
Paris    Di    2
Toronto  Ana   2
(5 rows)
```

It looks fine, but `Ben` is only an arbitrary pick from London's two students. This is called a **bare column**. The rule: every column in the
`SELECT` of a grouped query must be either in the `GROUP BY` or inside an aggregate. SQLite has one special case, which is tempting but fragile: with a single `MIN` or `MAX`, a bare
column comes from the row holding the min or max (`SELECT name, MAX(score) FROM students` gives `Cy`). Don't rely on it. A subquery does it properly, as Day 13 shows.

> **In other databases:** PostgreSQL, SQL Server, Oracle and DuckDB all give an error such as `column "name" must appear in the GROUP BY clause or be used in an aggregate function`.
> That error is protecting you. Write your SQLite queries as if SQLite raised it too.

## Joining Values Together: string_agg

`string_agg(column, separator)` (or `group_concat`, its older name) glues the values of a group into one string. From SQLite 3.44 you can sort the values inside the call with `ORDER BY`.

```py
show(conn.execute("SELECT city, string_agg(name, ', ' ORDER BY name) AS names FROM students GROUP BY city ORDER BY city"))
```

```sh
city     names
-------  --------
NULL     Hal
London   Ben, Eli
Oslo     Fay
Paris    Di, Gus
Toronto  Ana, Cy
(5 rows)
```

Without the inner `ORDER BY`, the order of the glued values is not guaranteed.

Counting, averaging and grouping let you summarise a table of any size in one query. Now do some exercises.

## Exercises: Day 7

### Exercises: Level 1

Use your `00_practice/library.db`.

1. Count the books.
2. Find the total number of pages of all books.
3. Find the average rating, rounded to 2 decimals. (Do the unrated books count?)
4. Show the oldest and newest publication year in one row (as `oldest` and `newest`).
5. In one row, show how many books are rated (`rated`) and how many are not (`unrated`). Use only `COUNT`.
6. Count the books in each genre (as `books`), the biggest genre first, ties by genre.
7. Show only the genres with more than 2 books.
8. Show the average number of pages for each genre, rounded to 1 decimal, ordered by genre.
9. Show the authors who have more than one book, with their book count, ordered by author.
10. Count the distinct authors.
11. Find the total price of all books in dollars (the sum of `price_cents` divided by 100.0).
12. Show the cheapest and the dearest price in cents (as `cheapest` and `dearest`).
13. Find the average number of pages of only the `Sci-Fi` books.
14. For each genre, list its titles in one cell, sorted alphabetically and separated by `, `. Order by genre.

```sh
# expected for exercise 6
genre      books
---------  -----
Sci-Fi     4
Dystopian  2
Fantasy    2
Romance    2
Tech       2
(5 rows)

# expected for exercise 14
genre      titles
---------  -------------------------------------------------
Dystopian  1984, Brave New World
Fantasy    The Hobbit, The Name of the Wind
Romance    Emma, Pride and Prejudice
Sci-Fi     Dune, Neuromancer, Project Hail Mary, The Martian
Tech       Clean Code, The Pragmatic Programmer
(5 rows)
```

### Exercises: Level 2

1. This is a classic statistics exercise, now in SQL. Create a table `ages (age INTEGER)` holding `19, 22, 19, 24, 20, 25, 26, 24, 25, 24`. In one query, find the
   minimum, maximum and average age, the range (max minus min), and the distance of the minimum and the maximum from the average (use `abs` and round to 2 decimals).
   Then work out the **median** age: fetch the middle two ages with `ORDER BY ... LIMIT 2 OFFSET 4` and average them in Python.

   ```sh
   min_age  max_age  avg_age  age_range  min_gap  max_gap
   -------  -------  -------  ---------  -------  -------
   19       26       22.8     7          3.8      3.2
   (1 row)
   median: 24.0
   ```

2. For each author, show the number of books (`books`) and the average page count (`avg_pages`, 1 decimal). Put the authors with the most books first, ties by author.

   ```sh
   author            books  avg_pages
   ----------------  -----  ---------
   Andy Weir         2      422.5
   Jane Austen       2      376.5
   Aldous Huxley     1      311.0
   ...
   William Gibson    1      271.0
   (10 rows)
   ```

3. This query fails. Run it, read the error, explain why it fails, and fix it:

   ```sql
   SELECT genre FROM books WHERE COUNT(*) > 2 GROUP BY genre
   ```

4. Calculate the average rating three ways in one row: `AVG(rating)`, `SUM(rating) / COUNT(*)`, and `AVG(coalesce(rating, 0))`, each rounded to 2 decimals.
   Explain why the first answer differs from the other two and which one answers "what do readers think of the books they rated?".

   ```sh
   avg_ignoring_nulls  sum_over_all_books  avg_nulls_as_zero
   ------------------  ------------------  -----------------
   4.44                3.33                3.33
   (1 row)
   ```

5. Count the books per **decade** (the year divided by 10, times 10) and add up their pages. Order by decade.

   ```sh
   decade  books  pages
   ------  -----  -----
   1810    2      753
   1930    2      621
   ...
   2020    1      476
   (9 rows)
   ```

6. Show the genres whose average rating is above 4.5, with the average rounded to 2 decimals, best first.

   ```sh
   genre      avg_rating
   ---------  ----------
   Dystopian  4.6
   Fantasy    4.55
   (2 rows)
   ```

7. Ask for `COUNT(*)`, `SUM(pages)`, `AVG(pages)` and `total(pages)` for books published after the year 3000. What do you get, and why is a row returned at all?

### Exercises: Level 3

Use `00_practice/datasets.db`.

1. Load `data/weight-height.csv` into a table `people (gender TEXT, height REAL, weight REAL)`. Then show, for each gender, the number of people, the average height and weight
   (2 decimals), and the shortest and tallest height. (Heights are in inches and weights in pounds.)

   ```sh
   gender  n     avg_height  avg_weight  shortest  tallest
   ------  ----  ----------  ----------  --------  -------
   Female  5000  63.71       135.86      54.26     73.39
   Male    5000  69.03       187.02      58.41     79.0
   (2 rows)
   ```

2. Among Hacker News authors with **at least 10 posts**, show the 10 with the highest average points: number of posts, average points and average comments (1 decimal each).
   Break ties by author.

   ```sh
   author       posts  avg_points  avg_comments
   -----------  -----  ----------  ------------
   temp         10     205.0       94.3
   robin_reala  16     189.1       84.1
   ivank        11     165.5       74.1
   rdl          14     161.9       86.9
   tshtf        15     158.9       69.9
   adamnemecek  42     143.0       60.4
   rfreytag     12     141.5       53.3
   antouank     13     127.5       54.5
   sinak        15     127.1       65.9
   samber       11     126.0       39.8
   (10 rows)
   ```

3. Show the 10 currencies used by the most countries, with the number of countries (ties by currency name).

   ```sh
   currency                   countries
   -------------------------  ---------
   Euro                       35
   United States dollar       12
   Australian dollar          9
   East Caribbean dollar      8
   West African CFA franc     8
   Central African CFA franc  6
   British pound              5
   New Zealand dollar         5
   CFP franc                  3
   Danish krone               3
   (10 rows)
   ```

4. In one row, show the number of countries, the total world population, and how many countries have more than 100 million people. (Hint: for the last one, use `COUNT(*) FILTER (WHERE ...)`,
   which counts only the rows matching the condition.)

   ```sh
   countries  world_population  over_100m
   ---------  ----------------  ---------
   250        7349137231        12
   (1 row)
   ```

CONGRATULATIONS !

[<< Day 6](../06_Day_Expressions_and_functions/06_expressions_and_functions.md) | [Day 8 >>](../08_Day_Update_delete_transactions/08_update_delete_transactions.md)
