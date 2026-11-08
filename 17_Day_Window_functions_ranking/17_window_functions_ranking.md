<div align="center">
  <h1> 30 Days Of SQL: Day 17 - Window Functions I: Ranking</h1>
</div>

[<< Review 2](../16R_Review_Combining_data/16R_review_combining_data.md) | [Day 18 >>](../18_Day_Window_functions_running/18_window_functions_running.md)

- [Day 17](#day-17)
  - [What Is a Window?](#what-is-a-window)
    - [GROUP BY Collapses, OVER Does Not](#group-by-collapses-over-does-not)
    - [OVER () and PARTITION BY](#over--and-partition-by)
    - [When Do Window Functions Run?](#when-do-window-functions-run)
  - [Numbering and Ranking Rows](#numbering-and-ranking-rows)
    - [ROW_NUMBER](#row_number)
    - [RANK and DENSE_RANK](#rank-and-dense_rank)
    - [Ranking Groups: Windows on Top of GROUP BY](#ranking-groups-windows-on-top-of-group-by)
  - [Top-N per Group](#top-n-per-group)
  - [Buckets and Percentiles](#buckets-and-percentiles)
    - [NTILE](#ntile)
    - [PERCENT_RANK](#percent_rank)
  - [Finding and Removing Duplicates](#finding-and-removing-duplicates)
    - [Detecting Duplicates](#detecting-duplicates)
    - [Choosing the Row to Keep](#choosing-the-row-to-keep)
    - [Deleting the Rest](#deleting-the-rest)
    - [Keeping Them Out for Good](#keeping-them-out-for-good)
  - [ Exercises: Day 17](#exercises-day-17)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 17

## What Is a Window?

Until now every query did one of two things. It looked at **one row at a time** (`SELECT price_cents / 100.0 ...`), or it **collapsed many rows into one** (`GROUP BY` with `SUM`, `COUNT`, ...). A real question often needs both: *"show every product, and next to it how it compares with the rest of its category."*

A **window function** does exactly that. It calculates something over a set of related rows (the **window**) but **keeps every row** in the result. Think of a class photo: a `GROUP BY` is the headcount written on the back, a window function is a caption under every face that says "3rd tallest in the class".

We start with a small table, so you can see everything that happens:

```py
import sqlite3
from helpers import show

conn = sqlite3.connect(':memory:')
conn.execute('CREATE TABLE players (name TEXT, team TEXT, points INTEGER) STRICT')
conn.executemany('INSERT INTO players VALUES (?, ?, ?)', [
    ('Ana', 'Red', 31),  ('Ben', 'Red', 25),  ('Cy', 'Red', 25),
    ('Di', 'Blue', 40),  ('Eli', 'Blue', 22), ('Fay', 'Blue', 22), ('Gus', 'Blue', 18),
    ('Hal', 'Green', 27),
])
show(conn.execute('SELECT * FROM players ORDER BY team, name'))
```

```sh
name  team   points
----  -----  ------
Di    Blue   40
Eli   Blue   22
Fay   Blue   22
Gus   Blue   18
Hal   Green  27
Ana   Red    31
Ben   Red    25
Cy    Red    25
(8 rows)
```

### GROUP BY Collapses, OVER Does Not

Total points per team with `GROUP BY` gives one row per team:

```py
show(conn.execute('''
    SELECT team, SUM(points) AS team_points
    FROM players
    GROUP BY team
    ORDER BY team
'''))
```

```sh
team   team_points
-----  -----------
Blue   102
Green  27
Red    81
(3 rows)
```

Now the same `SUM`, but with `OVER (...)` after it. The eight players are all still there, and each one carries its team's total:

```sql
-- syntax
function_name(...) OVER (
    [PARTITION BY column, ...]
    [ORDER BY column, ...]
    [frame clause]            -- Day 18
)
```

```py
show(conn.execute('''
    SELECT name, team, points,
           SUM(points) OVER (PARTITION BY team) AS team_points
    FROM players
    ORDER BY team, name
'''))
```

```sh
name  team   points  team_points
----  -----  ------  -----------
Di    Blue   40      102
Eli   Blue   22      102
Fay   Blue   22      102
Gus   Blue   18      102
Hal   Green  27      27
Ana   Red    31      81
Ben   Red    25      81
Cy    Red    25      81
(8 rows)
```

`OVER` is what turns an ordinary aggregate into a window function. Everything inside the parentheses describes *which rows form the window for this row*.

### OVER () and PARTITION BY

Empty parentheses mean "the window is the **whole result**". Here is each player's share of all the points scored:

```py
show(conn.execute('''
    SELECT name, points,
           SUM(points) OVER () AS all_points,
           round(100.0 * points / SUM(points) OVER (), 1) AS pct_of_all
    FROM players
    ORDER BY points DESC, name
'''))
```

```sh
name  points  all_points  pct_of_all
----  ------  ----------  ----------
Di    40      210         19.0
Ana   31      210         14.8
Hal   27      210         12.9
Ben   25      210         11.9
Cy    25      210         11.9
Eli   22      210         10.5
Fay   22      210         10.5
Gus   18      210         8.6
(8 rows)
```

`PARTITION BY` cuts the result into separate groups first, and the function is calculated **inside each group**. It is like `GROUP BY`, minus the collapsing. How far is each player from the average of their own team?

```py
show(conn.execute('''
    SELECT name, team, points,
           round(AVG(points) OVER (PARTITION BY team), 1) AS team_avg,
           round(points - AVG(points) OVER (PARTITION BY team), 1) AS vs_team
    FROM players
    ORDER BY team, name
'''))
```

```sh
name  team   points  team_avg  vs_team
----  -----  ------  --------  -------
Di    Blue   40      25.5      14.5
Eli   Blue   22      25.5      -3.5
Fay   Blue   22      25.5      -3.5
Gus   Blue   18      25.5      -7.5
Hal   Green  27      27.0      0.0
Ana   Red    31      27.0      4.0
Ben   Red    25      27.0      -2.0
Cy    Red    25      27.0      -2.0
(8 rows)
```

Window functions were added to SQLite in version 3.25 (2018), so every modern install has them.

> **Older code:** before windows, people faked them with a correlated subquery (Day 13) or a self join. You will still meet code like
> `1 + (SELECT COUNT(*) FROM players p2 WHERE p2.points > p1.points)` to compute a rank. It works, but it is slow on big tables and hard to read. Use window functions.

### When Do Window Functions Run?

Remember the order SQL really runs in (Day 7): `FROM` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `ORDER BY` → `LIMIT`. Window functions are calculated **inside `SELECT`**, after `WHERE`, `GROUP BY` and `HAVING` are done:

```
  FROM / JOIN  →  WHERE  →  GROUP BY  →  HAVING  →  WINDOW FUNCTIONS (in SELECT)  →  ORDER BY  →  LIMIT
```

Two consequences. First, a window only sees the rows that survived `WHERE`. Second, and this is the classic pitfall:

> **Common mistake:** you cannot filter on a window function in `WHERE` (or `HAVING`), because it has not been calculated yet at that point.

```py
try:
    conn.execute('SELECT name FROM players WHERE ROW_NUMBER() OVER (ORDER BY points DESC) <= 3')
except sqlite3.Error as e:
    print(type(e).__name__ + ':', e)
```

```sh
OperationalError: misuse of window function ROW_NUMBER()
```

The fix is to calculate the number in a subquery or a CTE, then filter **outside**. You will do this a lot, starting in a moment.

## Numbering and Ranking Rows

### ROW_NUMBER

`ROW_NUMBER()` gives every row of the window a number: 1, 2, 3, ... in the order given by the window's `ORDER BY`.

```sql
-- syntax
ROW_NUMBER() OVER (PARTITION BY group_col ORDER BY sort_col DESC)
```

```py
show(conn.execute('''
    SELECT name, team, points,
           ROW_NUMBER() OVER (ORDER BY points DESC, name) AS rn,
           ROW_NUMBER() OVER (PARTITION BY team ORDER BY points DESC, name) AS rn_in_team
    FROM players
    ORDER BY rn
'''))
```

```sh
name  team   points  rn  rn_in_team
----  -----  ------  --  ----------
Di    Blue   40      1   1
Ana   Red    31      2   1
Hal   Green  27      3   1
Ben   Red    25      4   2
Cy    Red    25      5   3
Eli   Blue   22      6   2
Fay   Blue   22      7   3
Gus   Blue   18      8   4
(8 rows)
```

Two windows in one `SELECT` is fine. Notice that `Ben` and `Cy` both have 25 points but still get different numbers: `ROW_NUMBER` never ties. That is why we added `name` as a **tie-breaker** in the window's `ORDER BY`. Without it, SQLite would pick an order between equal rows however it likes, and the numbering could change from one run to the next.

### RANK and DENSE_RANK

When two players have the same points, should they get the same position? That is what `RANK` and `DENSE_RANK` do. They differ in what happens **after** a tie:

```py
show(conn.execute('''
    SELECT name, points,
           ROW_NUMBER() OVER (ORDER BY points DESC, name) AS row_number,
           RANK()       OVER (ORDER BY points DESC)       AS rank,
           DENSE_RANK() OVER (ORDER BY points DESC)       AS dense_rank
    FROM players
    ORDER BY points DESC, name
'''))
```

```sh
name  points  row_number  rank  dense_rank
----  ------  ----------  ----  ----------
Di    40      1           1     1
Ana   31      2           2     2
Hal   27      3           3     3
Ben   25      4           4     4
Cy    25      5           4     4
Eli   22      6           6     5
Fay   22      7           6     5
Gus   18      8           8     6
(8 rows)
```

| Function | Ties | After a tie | Like... |
|---|---|---|---|
| `ROW_NUMBER` | never (always unique) | 1, 2, 3, 4 | seat numbers |
| `RANK` | same rank | **skips**: 1, 2, 2, 4 | an Olympic podium: two silvers, no bronze |
| `DENSE_RANK` | same rank | **no gap**: 1, 2, 2, 3 | "how many different scores are better than mine, plus one" |

Look at `Ben` and `Cy` (25 points each): `RANK` gives both a `4` (three players are ahead of them) and then jumps to `6` for `Eli` and `Fay` (five players are ahead). `DENSE_RANK` gives both a `4` and carries on with `5`. Pick by the question you are asked: "who is 4th?" needs a decision about ties.

**In other databases:** all of these exist in PostgreSQL, SQL Server, MySQL 8, Oracle and DuckDB with the same names and syntax. SQL written with them is very portable.

### Ranking Groups: Windows on Top of GROUP BY

Because windows run **after** `GROUP BY`, you can rank the *results of an aggregation*. The aggregate goes inside the window's `ORDER BY`. Let's open `shop.db` (introduced on Day 11) and rank the products by how many units were sold:

```py
shop = sqlite3.connect('data/shop.db')

show(shop.execute('''
    SELECT p.name, SUM(oi.quantity) AS units,
           RANK() OVER (ORDER BY SUM(oi.quantity) DESC) AS units_rank
    FROM order_items AS oi
    JOIN products AS p ON p.product_id = oi.product_id
    GROUP BY p.product_id
    ORDER BY units_rank, p.name
    LIMIT 8
'''))
```

```sh
name                      units  units_rank
------------------------  -----  ----------
Jigsaw Puzzle 1000pc      103    1
Dark Chocolate Bar        102    2
Bamboo Cutting Board      98     3
The Pragmatic Programmer  88     4
Green Tea Box             85     5
Espresso Beans 1kg        80     6
USB-C Cable               80     6
Running Shoes             72     8
(8 rows)
```

The order of events: the join and `GROUP BY` produce one row per product with `SUM(quantity)`; only then is `RANK` computed over those rows. Use an alias in the outer `ORDER BY`, as above.

## Top-N per Group

"The best 3 items of each category" is the most common reason to learn window functions. The recipe has three steps:

1. Number the rows inside each group (`ROW_NUMBER() OVER (PARTITION BY group ORDER BY score DESC)`).
2. Put that query in a CTE (Day 14) or subquery.
3. Filter the number outside: `WHERE rn <= N`.

Top 2 scorers per team from our toy table:

```py
show(conn.execute('''
    WITH numbered AS (
        SELECT name, team, points,
               ROW_NUMBER() OVER (PARTITION BY team ORDER BY points DESC, name) AS rn
        FROM players
    )
    SELECT team, name, points, rn
    FROM numbered
    WHERE rn <= 2
    ORDER BY team, rn
'''))
```

```sh
team   name  points  rn
-----  ----  ------  --
Blue   Di    40      1
Blue   Eli   22      2
Green  Hal   27      1
Red    Ana   31      1
Red    Ben   25      2
(5 rows)
```

Red has two players on 25 points, and `ROW_NUMBER` quietly picked `Ben` as second and dropped `Cy`. If you would rather **keep everybody who ties** for a place, use `RANK` (or `DENSE_RANK`) instead:

```py
show(conn.execute('''
    WITH ranked AS (
        SELECT name, team, points,
               RANK() OVER (PARTITION BY team ORDER BY points DESC) AS rnk
        FROM players
    )
    SELECT team, name, points, rnk
    FROM ranked
    WHERE rnk <= 2
    ORDER BY team, rnk, name
'''))
```

```sh
team   name  points  rnk
-----  ----  ------  ---
Blue   Di    40      1
Blue   Eli   22      2
Blue   Fay   22      2
Green  Hal   27      1
Red    Ana   31      1
Red    Ben   25      2
Red    Cy    25      2
(7 rows)
```

Now Red has three rows, because `Ben` and `Cy` are both 2nd. Neither answer is wrong: they answer different questions ("exactly 2 rows per team" or "everybody who is in the top two"). Decide, then write it down in a comment.

> **Looking ahead:** DuckDB has a `QUALIFY` clause that filters on window functions directly, with no CTE. We use it on Day 25. SQLite doesn't have it, so the CTE recipe above is the portable one.

## Buckets and Percentiles

### NTILE

`NTILE(n)` deals the ordered rows into `n` buckets of (nearly) equal size, numbered 1 to n. It is how you make quartiles (`NTILE(4)`) or "top 10%" (`NTILE(10)`). If the rows don't divide evenly, the first buckets get one extra row.

```py
show(conn.execute('''
    SELECT name, points,
           NTILE(3) OVER (ORDER BY points DESC, name) AS bucket
    FROM players
    ORDER BY points DESC, name
'''))
```

```sh
name  points  bucket
----  ------  ------
Di    40      1
Ana   31      1
Hal   27      1
Ben   25      2
Cy    25      2
Eli   22      2
Fay   22      3
Gus   18      3
(8 rows)
```

Eight players in three buckets: 3 + 3 + 2. Note that `NTILE` splits by *position*, so equal values can land in different buckets (look at `Eli` and `Fay`).

### PERCENT_RANK

`PERCENT_RANK()` says where a row stands on a scale from `0` (the first) to `1` (the last): `(rank - 1) / (rows - 1)`. It uses `RANK`, so ties share a value.

```py
show(conn.execute('''
    SELECT name, points,
           RANK() OVER (ORDER BY points) AS rnk,
           round(PERCENT_RANK() OVER (ORDER BY points), 3) AS pct_rank
    FROM players
    ORDER BY points, name
'''))
```

```sh
name  points  rnk  pct_rank
----  ------  ---  --------
Gus   18      1    0.0
Eli   22      2    0.143
Fay   22      2    0.143
Ben   25      4    0.429
Cy    25      4    0.429
Hal   27      6    0.714
Ana   31      7    0.857
Di    40      8    1.0
(8 rows)
```

With 8 rows, `Gus` (lowest) is `0.0`, `Di` (highest) is `1.0`, and `Ana` with rank 7 is `(7 - 1) / (8 - 1) = 0.857`. Read it as "this row is above 85.7% of the *other* rows".

## Finding and Removing Duplicates

Real tables get duplicates: a form submitted twice, a file imported twice, `Ben@Example.com` typed by someone else than `ben@example.com`. `shop.db` has a table with exactly this problem, `newsletter_signups`, with no constraints on purpose. We work on a **temporary copy** (Day 14) so the original stays untouched:

```py
shop.execute('CREATE TEMP TABLE signups AS SELECT * FROM newsletter_signups')
show(shop.execute('SELECT rowid, email, signed_up_at FROM signups ORDER BY rowid'))
```

```sh
rowid  email               signed_up_at
-----  ------------------  -------------------
1      kira@example.com    2025-01-05 11:46:00
2      ben@example.com     2025-01-13 15:02:00
3      jules@example.com   2025-01-15 11:30:00
4      ana@example.com     2025-02-07 13:50:00
5      elif@example.com    2025-02-15 11:38:00
6      hiro@example.com    2025-02-27 18:47:00
7      gina@example.com    2025-03-18 15:09:00
8      dev@example.com     2025-04-18 16:31:00
9      luca@example.com    2025-06-01 12:17:00
10     farid@example.com   2025-06-01 17:00:00
11     carla@example.com   2025-06-06 18:19:00
12     iris@example.com    2025-07-05 17:07:00
13      iris@example.com   2025-08-05 12:45:00
14     Jules@example.com   2025-08-09 12:45:00
15     Ben@Example.com     2025-09-07 11:30:00
16     dev@example.com     2025-10-09 10:00:00
17     Gina@example.COM    2025-10-12 11:30:00
18     hiro@example.com    2025-10-17 10:00:00
19     ana@example.com     2025-10-26 10:00:00
20     CARLA@example.com   2025-10-26 11:30:00
(20 rows)
```

`rowid` is the hidden number SQLite gives every row of an ordinary table. We use it as the row's identity, because this table has no primary key.

> **In other databases:** `rowid` is an SQLite feature. PostgreSQL has a similar `ctid`, SQL Server and MySQL have nothing built in, so there you use a real primary key or an `id` column in the same recipe.

### Detecting Duplicates

The classic tool is `GROUP BY` + `HAVING COUNT(*) > 1`: "show me the values that appear more than once."

```py
show(shop.execute('''
    SELECT email, COUNT(*) AS times
    FROM signups
    GROUP BY email
    HAVING COUNT(*) > 1
    ORDER BY email
'''))
```

```sh
email             times
----------------  -----
ana@example.com   2
dev@example.com   2
hiro@example.com  2
(3 rows)
```

Three emails are repeated exactly. But look at the data again: `Ben@Example.com` (different case), ` iris@example.com` (a leading space) and `Jules@example.com ` (a trailing space) are **near-duplicates** that this query can't see. Normalise the value you group by with `lower(trim(...))`:

```py
show(shop.execute('''
    SELECT lower(trim(email)) AS clean_email, COUNT(*) AS times
    FROM signups
    GROUP BY lower(trim(email))
    HAVING COUNT(*) > 1
    ORDER BY clean_email
'''))
print(shop.execute('SELECT COUNT(*), COUNT(DISTINCT email), COUNT(DISTINCT lower(trim(email))) FROM signups').fetchone())
```

```sh
clean_email        times
-----------------  -----
ana@example.com    2
ben@example.com    2
carla@example.com  2
dev@example.com    2
gina@example.com   2
hiro@example.com   2
iris@example.com   2
jules@example.com  2
(8 rows)
(20, 17, 12)
```

20 rows, 17 distinct spellings, but only **12 real people**.

### Choosing the Row to Keep

`GROUP BY` tells you *that* there are duplicates but it can't tell you *which row* to keep, because the rows of a group are collapsed. A window can: number the rows inside each group of duplicates, ordered by the rule that picks the survivor. Here we keep the **earliest** signup, so number by `signed_up_at`; `rowid` is the tie-breaker:

```py
show(shop.execute('''
    SELECT rowid, email, signed_up_at,
           ROW_NUMBER() OVER (
               PARTITION BY lower(trim(email))
               ORDER BY signed_up_at, rowid
           ) AS rn
    FROM signups
    ORDER BY lower(trim(email)), rn
'''))
```

```sh
rowid  email               signed_up_at         rn
-----  ------------------  -------------------  --
4      ana@example.com     2025-02-07 13:50:00  1
19     ana@example.com     2025-10-26 10:00:00  2
2      ben@example.com     2025-01-13 15:02:00  1
15     Ben@Example.com     2025-09-07 11:30:00  2
11     carla@example.com   2025-06-06 18:19:00  1
20     CARLA@example.com   2025-10-26 11:30:00  2
8      dev@example.com     2025-04-18 16:31:00  1
16     dev@example.com     2025-10-09 10:00:00  2
5      elif@example.com    2025-02-15 11:38:00  1
10     farid@example.com   2025-06-01 17:00:00  1
7      gina@example.com    2025-03-18 15:09:00  1
17     Gina@example.COM    2025-10-12 11:30:00  2
6      hiro@example.com    2025-02-27 18:47:00  1
18     hiro@example.com    2025-10-17 10:00:00  2
12     iris@example.com    2025-07-05 17:07:00  1
13      iris@example.com   2025-08-05 12:45:00  2
3      jules@example.com   2025-01-15 11:30:00  1
14     Jules@example.com   2025-08-09 12:45:00  2
1      kira@example.com    2025-01-05 11:46:00  1
9      luca@example.com    2025-06-01 12:17:00  1
(20 rows)
```

In every group, the row with `rn = 1` is the survivor; the rows with `rn > 1` are the duplicates to delete. Want to keep the *latest* instead? Change the sort to `signed_up_at DESC`. The rule is yours.

### Deleting the Rest

Put the numbered query in a subquery, keep only the `rowid`s of the duplicates, and delete those rows. As always: write the `SELECT` first, look at what it returns, **then** turn it into a `DELETE`.

```py
cur = shop.execute('''
    DELETE FROM signups
    WHERE rowid IN (
        SELECT rowid
        FROM (
            SELECT rowid,
                   ROW_NUMBER() OVER (
                       PARTITION BY lower(trim(email))
                       ORDER BY signed_up_at, rowid
                   ) AS rn
            FROM signups
        )
        WHERE rn > 1
    )
''')
print('deleted:', cur.rowcount)
print('left:', shop.execute('SELECT COUNT(*) FROM signups').fetchone()[0])
show(shop.execute('SELECT rowid, email, signed_up_at FROM signups ORDER BY lower(trim(email))'))
```

```sh
deleted: 8
left: 12
rowid  email              signed_up_at
-----  -----------------  -------------------
4      ana@example.com    2025-02-07 13:50:00
2      ben@example.com    2025-01-13 15:02:00
11     carla@example.com  2025-06-06 18:19:00
8      dev@example.com    2025-04-18 16:31:00
5      elif@example.com   2025-02-15 11:38:00
10     farid@example.com  2025-06-01 17:00:00
7      gina@example.com   2025-03-18 15:09:00
6      hiro@example.com   2025-02-27 18:47:00
12     iris@example.com   2025-07-05 17:07:00
3      jules@example.com  2025-01-15 11:30:00
1      kira@example.com   2025-01-05 11:46:00
9      luca@example.com   2025-06-01 12:17:00
(12 rows)
```

The 12 survivors are the earliest signup of each person (note that the odd spellings like `Jules@example.com ` only survive if they were first).

> **Older code:** you will see `DELETE FROM t WHERE rowid NOT IN (SELECT MIN(rowid) FROM t GROUP BY email)` in many tutorials. It works when "keep the lowest id" is the rule, but it can't express "keep the earliest date", "keep the longest description" or "keep the most recently updated one". `ROW_NUMBER` can express any of them.

### Keeping Them Out for Good

Cleaning up is only half the job. If nothing stops the next duplicate, you'll be doing this every month. Day 9 gave us `UNIQUE`; here we need a unique **index** (Day 21 explains indexes properly) on the *normalised* email, so that case and spaces don't sneak around it:

```py
shop.execute('CREATE UNIQUE INDEX ux_signups_email ON signups (lower(trim(email)))')
try:
    shop.execute("INSERT INTO signups VALUES ('  BEN@example.com', '2025-12-01 09:00:00')")
except sqlite3.IntegrityError as e:
    print('IntegrityError:', e)
```

```sh
IntegrityError: UNIQUE constraint failed: index 'ux_signups_email'
```

The database now rejects the duplicate for us. (For a brand new table you would simply declare `email TEXT NOT NULL UNIQUE` and store the e-mail already lower-cased.)

You can now number, rank and bucket rows without losing any of them, and clean a table of duplicates in four steps. Tomorrow windows learn to look at their neighbours.

## Exercises: Day 17

### Exercises: Level 1

Use `data/shop.db` (`sqlite3.connect('data/shop.db')`) for 1 to 12 and 16, the normalized `library.db` from Day 10 for 13 to 15, and a tiny inline table for 17. Every ranking needs a **tie-breaker** so that your output is the same as ours.

1. Number all products by price, dearest first, ties broken by `product_id`. Show `product_id`, `name`, `price_cents` and the number as `rn`.

   ```sh
   product_id  name                         price_cents  rn
   ----------  ---------------------------  -----------  --
   4           Noise-Cancelling Headphones  14999        1
   25          Running Shoes                8999         2
   30          Denim Jacket                 7999         3
   13          Chef's Knife                 6999         4
   3           Bluetooth Speaker            5999         5
   ...
   (40 rows)
   ```

2. Show the same products with `RANK` (as `price_rank`) and `DENSE_RANK` (as `price_dense`) next to the row number. Look at the first rows where two products share a price.

   ```sh
   product_id  name                         price_cents  rn  price_rank  price_dense
   ----------  ---------------------------  -----------  --  ----------  -----------
   4           Noise-Cancelling Headphones  14999        1   1           1
   25          Running Shoes                8999         2   2           2
   30          Denim Jacket                 7999         3   3           3
   13          Chef's Knife                 6999         4   4           4
   3           Bluetooth Speaker            5999         5   5           5
   32          Rain Coat                    5999         6   5           5
   5           Webcam                       4999         7   7           6
   9           The Pragmatic Programmer     4999         8   7           6
   8           SQL for Data Analysis        4499         9   9           7
   21          Remote Control Car           4499         10  9           7
   ...
   (40 rows)
   ```

3. Explain in your own words: when do `RANK` and `DENSE_RANK` give different numbers? Which one would you use for "who is on the podium (top 3)?"

4. For every product show its price, the average price of **all** products (`avg_price`, rounded to a whole number of cents) and the difference (`diff`). Use `OVER ()`.

   ```sh
   product_id  name                         price_cents  avg_price  diff
   ----------  ---------------------------  -----------  ---------  -----
   1           Wireless Mouse               2499         3364       -865
   2           USB-C Cable                  999          3364       -2365
   3           Bluetooth Speaker            5999         3364       2635
   4           Noise-Cancelling Headphones  14999        3364       11635
   ...
   (40 rows)
   ```

5. Do the same compared with the average of the product's own **category** (`PARTITION BY category_id`). Show `category_id` too and order by category, then product. What happens to the product with a NULL category?

   ```sh
   category_id  product_id  name                         price_cents  category_avg
   -----------  ----------  ---------------------------  -----------  ------------
   NULL         39          Gift Card Holder             599          599
   1            1           Wireless Mouse               2499         5166
   1            2           USB-C Cable                  999          5166
   1            3           Bluetooth Speaker            5999         5166
   1            4           Noise-Cancelling Headphones  14999        5166
   1            5           Webcam                       4999         5166
   ...
   (40 rows)
   ```

6. Rank the customers by their **number of orders** (all statuses) with `DENSE_RANK`: show `customer_id`, `orders` and `rank_no`, most orders first, ties by `customer_id`. Customers without orders don't appear.

   ```sh
   customer_id  orders  rank_no
   -----------  ------  -------
   7            20      1
   18           19      2
   24           18      3
   43           17      4
   31           16      5
   56           16      5
   15           15      6
   34           13      7
   ...
   (54 rows)
   ```

7. Rank customers by **total spend** in dollars (`spend`, from `order_items`, ignoring `cancelled` orders). Show the top 5 with their full name.

   ```sh
   customer      spend    spend_rank
   ------------  -------  ----------
   Lena Green    2214.6   1
   Amara Kim     2045.68  2
   Ines Martin   2044.41  3
   Sam Wilson    1966.91  4
   Freya Nguyen  1688.31  5
   (5 rows)
   ```

8. Number the orders of each customer in date order (`order_no`, ties by `order_id`). Show `customer_id`, `order_id`, `order_date`, `order_no` for the first 8 rows when sorted by customer and number.

   ```sh
   customer_id  order_id  order_date  order_no
   -----------  --------  ----------  --------
   1            33        2024-04-24  1
   1            54        2024-06-25  2
   1            75        2024-08-12  3
   1            187       2025-01-12  4
   1            272       2025-06-27  5
   1            320       2025-10-09  6
   1            331       2025-10-27  7
   2            24        2024-03-31  1
   (8 rows)
   ```

9. Each product's share of its category's revenue: show `category`, `product`, `revenue` (dollars, from `order_items`) and `share` (percent of the category revenue, 1 decimal). Order by category, then share descending. Compute the revenue per product in a CTE first.

   ```sh
   category        product                      revenue  share
   --------------  ---------------------------  -------  -----
   Books           The Pragmatic Programmer     4396.62  53.6
   Books           SQL for Data Analysis        1151.74  14.0
   Books           Cookbook Basics              998.35   12.2
   Books           Python Crash Course          791.8    9.6
   Books           Mystery Novel                706.78   8.6
   Books           Sci-Fi Anthology             163.71   2.0
   ...
   (35 rows)
   ```

10. Split the products into 4 price quartiles with `NTILE(4)` (cheapest = 1). Then count the products and show the cheapest and dearest price in every quartile.

    ```sh
    quartile  products  cheapest  dearest
    --------  --------  --------  -------
    1         10        399       1499
    2         10        1599      2499
    3         10        2499      3999
    4         10        4499      14999
    (4 rows)
    ```

11. Show every employee's `PERCENT_RANK` by salary (rounded to 2 decimals) next to their name and salary in dollars. Show the 5 best paid.

    ```sh
    name             title                salary  pct_rank
    ---------------  -------------------  ------  --------
    Grace Hopper     CEO                  185000  1.0
    Alan Turing      VP Engineering       140000  0.93
    Ada Lovelace     VP Sales             135000  0.86
    Edsger Dijkstra  VP Operations        130000  0.79
    Barbara Liskov   Engineering Manager  110000  0.71
    (5 rows)
    ```

12. Within each manager's team, rank employees by salary (`RANK() ... PARTITION BY manager_id`). Show `manager_id`, `name`, `salary_cents` and `team_rank`, ordered by manager and rank (first 8 rows).

    ```sh
    manager_id  name               salary_cents  team_rank
    ----------  -----------------  ------------  ---------
    NULL        Grace Hopper       18500000      1
    1           Alan Turing        14000000      1
    1           Ada Lovelace       13500000      2
    1           Edsger Dijkstra    13000000      3
    2           Barbara Liskov     11000000      1
    2           Donald Knuth       10800000      2
    3           Margaret Hamilton  9800000       1
    4           Linus Torvalds     8800000       1
    (8 rows)
    ```

13. Library: number the books inside each genre from longest to shortest (`ROW_NUMBER` over `PARTITION BY genre ORDER BY pages DESC`). Show `genre`, `title`, `pages` and the number.

    ```sh
    genre      title                     pages  longest_first
    ---------  ------------------------  -----  -------------
    Dystopian  1984                      328    1
    Dystopian  Brave New World           311    2
    Fantasy    The Name of the Wind      662    1
    Fantasy    The Hobbit                310    2
    Romance    Emma                      474    1
    Romance    Pride and Prejudice       279    2
    ...
    (12 rows)
    ```

14. Library: rank the **members** by number of loans, including the member who never borrowed (what join do you need to keep them?). Use `DENSE_RANK`.

    ```sh
    name          loans  loan_rank
    ------------  -----  ---------
    Alice Nguyen  3      1
    Bruno Silva   3      1
    Chloe Martin  2      2
    Dev Patel     2      2
    Elena Rossi   0      3
    (5 rows)
    ```

15. Library: for each book show its pages, the pages of the longest book in its genre (`MAX(pages) OVER (PARTITION BY genre)`) and how many pages shorter it is (`shorter_by`). Show the first 6 rows ordered by genre and title.

    ```sh
    genre      title                 pages  longest  shorter_by
    ---------  --------------------  -----  -------  ----------
    Dystopian  1984                  328    328      0
    Dystopian  Brave New World       311    328      17
    Fantasy    The Hobbit            310    662      352
    Fantasy    The Name of the Wind  662    662      0
    Romance    Emma                  474    474      0
    Romance    Pride and Prejudice   279    474      195
    (6 rows)
    ```

16. Try `WHERE` with a window function directly: `SELECT product_id FROM products WHERE ROW_NUMBER() OVER (ORDER BY price_cents DESC) <= 3`. Catch the error and print its message, then write the working version with a CTE.

    ```sh
    OperationalError: misuse of window function ROW_NUMBER()
    product_id  name                         price_cents
    ----------  ---------------------------  -----------
    4           Noise-Cancelling Headphones  14999
    25          Running Shoes                8999
    30          Denim Jacket                 7999
    (3 rows)
    ```

17. **Predict, then run.** The scores `90, 85, 85, 70` are in a table `scores`. Write down the `ROW_NUMBER`, `RANK` and `DENSE_RANK` of each (highest first) before you run the query.

    ```sh
    score  rn  rnk  dense
    -----  --  ---  -----
    90     1   1    1
    85     2   2    2
    85     3   2    2
    70     4   4    3
    (4 rows)
    ```

### Exercises: Level 2

1. **Top 3 products per category** by revenue (dollars). Show `category`, `product`, `revenue` and `pos`. Use `ROW_NUMBER`, ties broken by product name, and order by category, then `pos`. Products without a category don't appear (the inner join drops them).

   ```sh
   category        product                      revenue  pos
   --------------  ---------------------------  -------  ---
   Books           The Pragmatic Programmer     4396.62  1
   Books           SQL for Data Analysis        1151.74  2
   Books           Cookbook Basics              998.35   3
   Clothing        Denim Jacket                 3575.55  1
   Clothing        Rain Coat                    536.91   2
   Clothing        Cotton T-Shirt               440.57   3
   Electronics     Noise-Cancelling Headphones  3202.28  1
   Electronics     Bluetooth Speaker            2972.5   2
   Electronics     Wireless Mouse               1376.95  3
   Grocery         Espresso Beans 1kg           1848.4   1
   Grocery         Green Tea Box                1013.15  2
   Grocery         Mixed Nuts 500g              462.68   3
   Home & Kitchen  Bamboo Cutting Board         1947.02  1
   Home & Kitchen  Cast Iron Pan                1466.08  2
   Home & Kitchen  French Press                 575.81   3
   Sports          Running Shoes                6452.28  1
   Sports          Yoga Mat                     1468.01  2
   Sports          Water Bottle                 1205.33  3
   Toys            Jigsaw Puzzle 1000pc         2052.97  1
   Toys            Building Blocks Set          1766.99  2
   Toys            Board Game Night             1343.66  3
   (21 rows)
   ```

2. The **most recent order of every customer**: show `customer_id`, `order_id`, `order_date` and `status`. Break date ties by the higher `order_id`. Print how many rows you got and the first 6.

   ```sh
   customer_id  order_id  order_date  status
   -----------  --------  ----------  ---------
   1            331       2025-10-27  delivered
   2            383       2025-12-17  pending
   3            219       2025-03-21  delivered
   4            388       2025-12-21  shipped
   6            333       2025-10-29  delivered
   7            395       2025-12-28  pending
   (6 rows)
   54 customers have orders
   ```

3. **Quartiles of customers by spend**: spend per customer in dollars (ignoring cancelled orders), `NTILE(4)` with the biggest spenders in quartile 1. For each quartile show how many customers it holds, and the smallest and largest spend.

   ```sh
   quartile  customers  min_spend  max_spend
   --------  ---------  ---------  ---------
   1         14         1180.61    2214.6
   2         14         770.5      1180.1
   3         13         298.89     662.45
   4         13         29.99      273.41
   (4 rows)
   ```

4. **Deduplicate `newsletter_signups`** on a temp copy: keep the **earliest** signup per person, ignoring case and surrounding spaces. Print how many rows you deleted, then the rows left. Finally add a unique index that makes the same mistake impossible and prove it rejects `'ANA@example.com'`. The expected count after cleaning is 12.

   ```sh
   deleted: 8
   email              signed_up_at
   -----------------  -------------------
   ana@example.com    2025-02-07 13:50:00
   ben@example.com    2025-01-13 15:02:00
   carla@example.com  2025-06-06 18:19:00
   dev@example.com    2025-04-18 16:31:00
   elif@example.com   2025-02-15 11:38:00
   farid@example.com  2025-06-01 17:00:00
   gina@example.com   2025-03-18 15:09:00
   hiro@example.com   2025-02-27 18:47:00
   iris@example.com   2025-07-05 17:07:00
   jules@example.com  2025-01-15 11:30:00
   kira@example.com   2025-01-05 11:46:00
   luca@example.com   2025-06-01 12:17:00
   (12 rows)
   IntegrityError: UNIQUE constraint failed: index 'ux_signups_email'
   ```

5. **The top-spending customer of every country**, with the spend in dollars (ignoring cancelled orders). If two customers tie for first, show both (so `RANK`, not `ROW_NUMBER`). Order by country.

   ```sh
   country  customer      spend
   -------  ------------  -------
   Canada   Freya Nguyen  1688.31
   France   Lena Green    2214.6
   Germany  Amara Kim     2045.68
   UK       Liam Walker   1607.74
   USA      Sam Wilson    1966.91
   (5 rows)
   ```

6. The classic **second-highest** problem: for every category, find the product with the second-highest price. If several products share the highest price, "second" means the next *different* price (so which ranking function?). Show category, product name and price, ordered by category and name.

   ```sh
   category        product                price_cents
   --------------  ---------------------  -----------
   Books           SQL for Data Analysis  4499
   Clothing        Rain Coat              5999
   Electronics     Bluetooth Speaker      5999
   Grocery         Olive Oil 500ml        1499
   Home & Kitchen  Cast Iron Pan          3499
   Sports          Camping Hammock        3999
   Toys            Board Game Night       3999
   (7 rows)
   ```

### Exercises: Level 3

This is the Fortune 1000 list (`data/fortune1000_final.csv`). Work in a new `00_practice/fortune.db`.

1. **Load and clean it.** The file is not UTF-8 (open it with `encoding='latin-1'`). Read it with `csv.DictReader` (the columns you need are `rank`, `title`, `Sector`, `Revenues ($M)` and `Profits ($M)`) and create a table `f1000 (rank INTEGER, company TEXT, sector TEXT, revenue_m INTEGER, profit_m REAL)`. Revenue and profit are strings like `"$500,343 "` and `"$9,862.00 "`: strip the `$`, the commas and the spaces with `replace` + `CAST` **in SQL** (load the raw strings into a staging table first, as you will do properly on Day 20), then print the row count and the biggest revenue. Expected: 1000 rows and Walmart's revenue of 500343.

   ```sh
   (1000, 500343)
   ('Walmart', 500343)
   ```

2. **The top 3 companies by revenue in each sector.** Show `sector`, `company`, `revenue_m` and `pos`, ordered by sector and position. Break revenue ties with the list `rank`. There are 21 sectors, so expect 63 rows.

   ```sh
   sector                          company                   revenue_m  pos
   ------------------------------  ------------------------  ---------  ---
   Aerospace &  Defense            Boeing                    93392      1
   Aerospace &  Defense            United Technologies       59837      2
   Aerospace &  Defense            Lockheed Martin           51048      3
   Apparel                         Nike                      34350      1
   Apparel                         VF                        12400      2
   Apparel                         PVH                       8915       3
   Business Services               ManpowerGroup             21034      1
   Business Services               Visa                      18358      2
   Business Services               Omnicom Group             15274      3
   ...
   (63 rows)
   ```

3. **How dominant is the leader?** For every sector show the number of companies, the sector's total revenue, the name of its biggest company and that company's share of the sector total in percent (1 decimal). Show the 6 sectors with the highest share, most dominant first. *Hint: one window for the number, one for the total, then keep position 1.*

   ```sh
   sector                   companies  sector_total  leader            leader_share
   -----------------------  ---------  ------------  ----------------  ------------
   Motor Vehicles &  Parts  19         433535        General Motors    36.3
   Telecommunications       10         466959        AT&T              34.4
   Apparel                  14         101157        Nike              34.0
   Food &  Drug Stores      12         405468        Kroger            30.3
   Retailing                77         1684353       Walmart           29.7
   Household Products       28         231779        Procter & Gamble  28.6
   (6 rows)
   ```

CONGRATULATIONS !

[<< Review 2](../16R_Review_Combining_data/16R_review_combining_data.md) | [Day 18 >>](../18_Day_Window_functions_running/18_window_functions_running.md)
