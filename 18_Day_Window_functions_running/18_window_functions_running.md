<div align="center">
  <h1> 30 Days Of SQL: Day 18 - Window Functions II: Running Totals, LAG/LEAD, Frames</h1>
</div>

[<< Day 17](../17_Day_Window_functions_ranking/17_window_functions_ranking.md) | [Review 3 >>](../18R_Review_Analytical_sql/18R_review_analytical_sql.md)

- [Day 18](#day-18)
  - [Running Totals](#running-totals)
    - [SUM() OVER (ORDER BY ...)](#sum-over-order-by-)
    - [Running Totals on Real Data](#running-totals-on-real-data)
    - [Restarting for Every Group](#restarting-for-every-group)
  - [Looking at Neighbours: LAG and LEAD](#looking-at-neighbours-lag-and-lead)
    - [LAG and LEAD](#lag-and-lead)
    - [Month-over-Month Change](#month-over-month-change)
  - [Frames: Choosing the Rows Around You](#frames-choosing-the-rows-around-you)
    - [ROWS BETWEEN](#rows-between)
    - [Moving Averages](#moving-averages)
    - [ROWS vs RANGE](#rows-vs-range)
    - [Calendar Windows: RANGE with Numbers](#calendar-windows-range-with-numbers)
  - [FIRST_VALUE, LAST_VALUE and the Default Frame Trap](#first_value-last_value-and-the-default-frame-trap)
  - [Named Windows](#named-windows)
  - [Gaps and Islands: Finding Streaks](#gaps-and-islands-finding-streaks)
    - [The Trick](#the-trick)
    - [Streaks in the Shop](#streaks-in-the-shop)
  - [Putting It Together: Windows and CTEs](#putting-it-together-windows-and-ctes)
  - [ Exercises: Day 18](#exercises-day-18)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 18

## Running Totals

Yesterday windows ranked rows. Today they learn to look at **other rows**: the one before, the next one, the last seven, everything so far. This is where SQL starts doing jobs that you would otherwise write a Python `for` loop with a variable `total += x` for.

We use a week of shop takings in a small table (amounts in cents):

```py
import sqlite3
from helpers import show

conn = sqlite3.connect(':memory:')
conn.execute('CREATE TABLE daily_sales (day TEXT, cents INTEGER) STRICT')
conn.executemany('INSERT INTO daily_sales VALUES (?, ?)', [
    ('2025-03-01', 12000), ('2025-03-02', 8000),  ('2025-03-03', 15000), ('2025-03-04', 9000),
    ('2025-03-05', 20000), ('2025-03-06', 6000),  ('2025-03-07', 11000),
])
show(conn.execute('SELECT * FROM daily_sales ORDER BY day'))
```

```sh
day         cents
----------  -----
2025-03-01  12000
2025-03-02  8000
2025-03-03  15000
2025-03-04  9000
2025-03-05  20000
2025-03-06  6000
2025-03-07  11000
(7 rows)
```

### SUM() OVER (ORDER BY ...)

Last time `SUM(x) OVER (PARTITION BY team)` put the same group total on every row. Add an `ORDER BY` inside the window and the meaning changes: each row's window now grows from the first row **up to the current row**. That is a **running total** (also called a cumulative sum).

```sql
-- syntax
SUM(column) OVER (ORDER BY sort_column)
```

```py
show(conn.execute('''
    SELECT day, cents,
           SUM(cents) OVER (ORDER BY day) AS running_cents
    FROM daily_sales
    ORDER BY day
'''))
```

```sh
day         cents  running_cents
----------  -----  -------------
2025-03-01  12000  12000
2025-03-02  8000   20000
2025-03-03  15000  35000
2025-03-04  9000   44000
2025-03-05  20000  64000
2025-03-06  6000   70000
2025-03-07  11000  81000
(7 rows)
```

Row 3 shows `12000 + 8000 + 15000 = 35000`. Every row adds its own amount to the total of the rows above it. The same idea works for other aggregates: `COUNT(*) OVER (ORDER BY day)` is a running count, `MAX(cents) OVER (ORDER BY day)` is "the best day so far".

What are "the rows so far" exactly? That is decided by a **frame**, which has its own section below. For now remember the rule of thumb:

| Window has... | Rows the function sees |
|---|---|
| no `ORDER BY` (`OVER ()` or only `PARTITION BY`) | the whole partition |
| an `ORDER BY` | from the start of the partition up to the current row (plus any ties) |

### Running Totals on Real Data

Let's open `shop.db` and build the running revenue of the shop. Two steps: first a CTE that turns the order lines into one row per day, then the window on top of it. We skip cancelled orders and keep money in integer cents.

```py
shop = sqlite3.connect('data/shop.db')

show(shop.execute('''
    WITH daily AS (
        SELECT o.order_date AS day, SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY o.order_date
    )
    SELECT day, cents,
           SUM(cents) OVER (ORDER BY day) AS running_cents
    FROM daily
    ORDER BY day
    LIMIT 6
'''))
```

```sh
day         cents  running_cents
----------  -----  -------------
2024-01-02  1198   1198
2024-01-10  7196   8394
2024-02-08  6997   15391
2024-02-14  12796  28187
2024-02-17  5277   33464
2024-02-19  19422  52886
(6 rows)
```

You will write "aggregate in a CTE, then window over it" over and over. Each step stays small: the CTE does the grouping, the outer query does the windowing.

### Restarting for Every Group

Add `PARTITION BY` and the running total restarts for each group. Here is the running spend of customer 3 and customer 7 after each of their orders (the first five rows of each):

```py
show(shop.execute('''
    WITH order_totals AS (
        SELECT o.customer_id, o.order_id, o.order_date,
               SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled' AND o.customer_id IN (3, 7)
        GROUP BY o.order_id
    ), running AS (
        SELECT customer_id, order_id, order_date, cents,
               SUM(cents) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS running_cents,
               ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS n
        FROM order_totals
    )
    SELECT customer_id, order_id, order_date, cents, running_cents
    FROM running
    WHERE n <= 5
    ORDER BY customer_id, n
'''))
```

```sh
customer_id  order_id  order_date  cents  running_cents
-----------  --------  ----------  -----  -------------
3            13        2024-03-11  8797   8797
3            14        2024-03-12  2868   11665
3            15        2024-03-13  599    12264
3            16        2024-03-14  10994  23258
3            17        2024-03-15  10245  33503
7            152       2024-12-09  6998   6998
7            167       2024-12-22  1499   8497
7            177       2024-12-28  4999   13496
7            192       2025-01-20  8386   21882
7            215       2025-03-05  5399   27281
(10 rows)
```

Notice the order of ideas: running total and row number are both computed first, in the CTE, and `WHERE n <= 5` is applied outside (yesterday's rule: no window functions in `WHERE`).

## Looking at Neighbours: LAG and LEAD

### LAG and LEAD

`LAG(column)` returns the value from the **previous row** of the window; `LEAD(column)` from the **next row**. Both take an optional offset (how many rows to jump) and a default (what to return when there is no such row).

```sql
-- syntax
LAG(column [, offset [, default]])  OVER (PARTITION BY ... ORDER BY ...)
LEAD(column [, offset [, default]]) OVER (PARTITION BY ... ORDER BY ...)
```

```py
show(conn.execute('''
    SELECT day, cents,
           LAG(cents)     OVER (ORDER BY day) AS prev_day,
           LEAD(cents)    OVER (ORDER BY day) AS next_day,
           LAG(cents, 2)  OVER (ORDER BY day) AS two_days_ago,
           LEAD(cents, 1, 0) OVER (ORDER BY day) AS next_or_zero
    FROM daily_sales
    ORDER BY day
'''))
```

```sh
day         cents  prev_day  next_day  two_days_ago  next_or_zero
----------  -----  --------  --------  ------------  ------------
2025-03-01  12000  NULL      8000      NULL          8000
2025-03-02  8000   12000     15000     NULL          15000
2025-03-03  15000  8000      9000      12000         9000
2025-03-04  9000   15000     20000     8000          20000
2025-03-05  20000  9000      6000      15000         6000
2025-03-06  6000   20000     11000     9000          11000
2025-03-07  11000  6000      NULL      20000         0
(7 rows)
```

The first row has no previous row, so `LAG` gives `NULL`; the last row has no next row, so `LEAD` gives `NULL`, unless you supply a default (the last column). `LAG`/`LEAD` always need an `ORDER BY` in the window: "previous" means nothing without an order.

> **Common mistake:** forgetting that the first row gets `NULL` and then doing arithmetic on it. `cents - LAG(cents) OVER (...)` is `NULL` for the first row. That is usually correct (there is no change to report), but if you give a default like `0`, the first row will report a fake change of the whole amount.

> **Older code:** before `LAG`, "compare with the previous row" needed a self join on `id = id - 1`, which breaks the moment an id is missing. `LAG` follows the *sort order*, not the id numbers.

On real data: for every order of customer 3, when was the customer's previous order, and how many days passed? `julianday()` (Day 16) turns a date into a number, so the subtraction gives days:

```py
show(shop.execute('''
    SELECT order_id, order_date,
           LAG(order_date) OVER (ORDER BY order_date, order_id) AS prev_order,
           CAST(julianday(order_date) - julianday(LAG(order_date) OVER (ORDER BY order_date, order_id)) AS INTEGER) AS days_since
    FROM orders
    WHERE customer_id = 3
    ORDER BY order_date, order_id
'''))
```

```sh
order_id  order_date  prev_order  days_since
--------  ----------  ----------  ----------
13        2024-03-11  NULL        NULL
14        2024-03-12  2024-03-11  1
15        2024-03-13  2024-03-12  1
16        2024-03-14  2024-03-13  1
17        2024-03-15  2024-03-14  1
19        2024-03-20  2024-03-15  5
20        2024-03-21  2024-03-20  1
59        2024-07-08  2024-03-21  109
126       2024-11-19  2024-07-08  134
168       2024-12-23  2024-11-19  34
219       2025-03-21  2024-12-23  88
(11 rows)
```

Here `WHERE customer_id = 3` filters the rows *before* the window runs, so the window only contains customer 3's orders. For all customers at once you would write `PARTITION BY customer_id`, as in the next exercises.

### Month-over-Month Change

Business reports love "compared with last month". Group by month in a CTE, then use `LAG`:

```py
show(shop.execute('''
    WITH monthly AS (
        SELECT strftime('%Y-%m', o.order_date) AS month,
               SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY month
    )
    SELECT month, cents,
           LAG(cents) OVER (ORDER BY month) AS prev_cents,
           cents - LAG(cents) OVER (ORDER BY month) AS change_cents,
           round(100.0 * (cents - LAG(cents) OVER (ORDER BY month)) / LAG(cents) OVER (ORDER BY month), 1) AS change_pct
    FROM monthly
    ORDER BY month
    LIMIT 6
'''))
```

```sh
month    cents   prev_cents  change_cents  change_pct
-------  ------  ----------  ------------  ----------
2024-01  8394    NULL        NULL          NULL
2024-02  69184   8394        60790         724.2
2024-03  155551  69184       86367         124.8
2024-04  104364  155551      -51187        -32.9
2024-05  83397   104364      -20967        -20.1
2024-06  144410  83397       61013         73.2
(6 rows)
```

January 2024 has no predecessor, so its change is `NULL`. The huge `+724%` for February simply says January was a tiny month. If the previous value could be `0`, divide by `NULLIF(LAG(...), 0)` (Day 6) to avoid a division error. Repeating `LAG(cents) OVER (ORDER BY month)` four times is noisy: the section on named windows shows a tidier way.

## Frames: Choosing the Rows Around You

### ROWS BETWEEN

So far the window was "all rows so far" or "the whole group". A **frame clause** lets you pick a sliding range of rows around the current one:

```sql
-- syntax
function(...) OVER (
    ORDER BY sort_column
    ROWS BETWEEN <start> AND <end>
)
```

where `<start>` and `<end>` are each one of:

| Boundary | Meaning |
|---|---|
| `UNBOUNDED PRECEDING` | the first row of the partition |
| `n PRECEDING` | n rows before the current row |
| `CURRENT ROW` | the current row |
| `n FOLLOWING` | n rows after the current row |
| `UNBOUNDED FOLLOWING` | the last row of the partition |

A few frames and what they compute:

| Frame | Meaning |
|---|---|
| `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` | running total (what `ORDER BY` alone gives you, almost: see `ROWS vs RANGE`) |
| `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` | this row and the two before it (3-row moving window) |
| `ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING` | one neighbour on each side (a centred window) |
| `ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING` | this row and everything after it |

### Moving Averages

A **moving average** smooths noisy numbers by averaging the last few values. Average each day with the two days before it:

```py
show(conn.execute('''
    SELECT day, cents,
           CAST(round(AVG(cents) OVER (
               ORDER BY day
               ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
           )) AS INTEGER) AS moving_avg_3,
           COUNT(*) OVER (
               ORDER BY day
               ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
           ) AS rows_in_window
    FROM daily_sales
    ORDER BY day
'''))
```

```sh
day         cents  moving_avg_3  rows_in_window
----------  -----  ------------  --------------
2025-03-01  12000  12000         1
2025-03-02  8000   10000         2
2025-03-03  15000  11667         3
2025-03-04  9000   10667         3
2025-03-05  20000  14667         3
2025-03-06  6000   11667         3
2025-03-07  11000  12333         3
(7 rows)
```

Check day 3: `(12000 + 8000 + 15000) / 3 = 11667`. The first two days don't have two predecessors yet, so their window is smaller (see `rows_in_window`) and the average is computed from the rows that exist. Whether to show those partial averages or hide them (e.g. with `CASE WHEN rows_in_window = 3 THEN ... END`) is your call; just be aware of it.

A centred window, with a neighbour on each side:

```py
show(conn.execute('''
    SELECT day, cents,
           SUM(cents) OVER (ORDER BY day ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) AS three_day_sum
    FROM daily_sales
    ORDER BY day
'''))
```

```sh
day         cents  three_day_sum
----------  -----  -------------
2025-03-01  12000  20000
2025-03-02  8000   35000
2025-03-03  15000  32000
2025-03-04  9000   44000
2025-03-05  20000  35000
2025-03-06  6000   37000
2025-03-07  11000  17000
(7 rows)
```

### ROWS vs RANGE

There are two ways to count boundaries. `ROWS` counts **physical rows**. `RANGE` works on the **values** of the `ORDER BY` column, so rows with an equal value ("peers") are treated as one and move together. The difference only shows when the sort column has ties:

```py
conn.execute('CREATE TABLE scores (name TEXT, score INTEGER) STRICT')
conn.executemany('INSERT INTO scores VALUES (?, ?)', [('Ana', 10), ('Ben', 20), ('Cy', 20), ('Di', 30)])

show(conn.execute('''
    SELECT name, score,
           SUM(score) OVER (ORDER BY score ROWS  BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS rows_total,
           SUM(score) OVER (ORDER BY score RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS range_total
    FROM scores
    ORDER BY score, name
'''))
```

```sh
name  score  rows_total  range_total
----  -----  ----------  -----------
Ana   10     10          10
Ben   20     30          50
Cy    20     50          50
Di    30     80          80
(4 rows)
```

`Ben` and `Cy` both have 20. With `ROWS`, the running total moves one row at a time (30, then 50). With `RANGE`, they are peers: each includes **both** of them, so both show 50.

> **Common mistake:** **`RANGE` is the default** whenever you write an `ORDER BY` but no frame. So `SUM(x) OVER (ORDER BY day)` quietly treats days with equal values as one group. If the `ORDER BY` column is unique (a date with one row per day) there are no ties and you won't notice; if it has ties, the running total jumps by the whole group at once. When you want a strict row-by-row running total, write `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` or add a tie-breaker column to the `ORDER BY`.

(SQLite also has a third unit, `GROUPS`, which counts groups of peers instead of rows. You will rarely need it.)

### Calendar Windows: RANGE with Numbers

"The last 7 **days**" is not "the last 7 **rows**" when some days have no sales: seven rows could span two weeks. `RANGE` can fix that, because with a number in the `ORDER BY` it measures the distance in values. SQLite requires a numeric sort column, so we sort by `julianday(day)` (days as a number):

```py
conn.executemany('INSERT INTO daily_sales VALUES (?, ?)', [('2025-03-12', 7000), ('2025-03-13', 5000)])   # note: Mar 8 to 11 are missing

show(conn.execute('''
    SELECT day, cents,
           SUM(cents) OVER (ORDER BY day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS last_3_rows,
           SUM(cents) OVER (ORDER BY julianday(day) RANGE BETWEEN 2 PRECEDING AND CURRENT ROW) AS last_3_days
    FROM daily_sales
    ORDER BY day
'''))
```

```sh
day         cents  last_3_rows  last_3_days
----------  -----  -----------  -----------
2025-03-01  12000  12000        12000
2025-03-02  8000   20000        20000
2025-03-03  15000  35000        35000
2025-03-04  9000   32000        32000
2025-03-05  20000  44000        44000
2025-03-06  6000   35000        35000
2025-03-07  11000  37000        37000
2025-03-12  7000   24000        7000
2025-03-13  5000   23000        12000
(9 rows)
```

On 2025-03-12 the 3-row window reaches back to March 6 and 7, but the 3-day calendar window only sees March 12 itself (March 10 and 11 had no sales). For time series with gaps, `RANGE` over `julianday()` is the honest answer.

> **In other databases:** PostgreSQL and DuckDB can write the calendar window directly on a date column: `RANGE BETWEEN INTERVAL 2 DAY PRECEDING AND CURRENT ROW`. SQLite has no intervals, which is why we sort by `julianday()`.

## FIRST_VALUE, LAST_VALUE and the Default Frame Trap

`FIRST_VALUE(col)` returns `col` from the first row of the frame, `LAST_VALUE(col)` from the last row, and `NTH_VALUE(col, n)` from the n-th. Use them to compare every row with "the beginning" or "the end" of its group:

```py
conn.execute("DELETE FROM daily_sales WHERE day >= '2025-03-08'")   # back to the original week

show(conn.execute('''
    SELECT day, cents,
           FIRST_VALUE(cents) OVER (ORDER BY day) AS first_day,
           LAST_VALUE(cents)  OVER (ORDER BY day) AS last_day
    FROM daily_sales
    ORDER BY day
'''))
```

```sh
day         cents  first_day  last_day
----------  -----  ---------  --------
2025-03-01  12000  12000      12000
2025-03-02  8000   12000      8000
2025-03-03  15000  12000      15000
2025-03-04  9000   12000      9000
2025-03-05  20000  12000      20000
2025-03-06  6000   12000      6000
2025-03-07  11000  12000      11000
(7 rows)
```

`FIRST_VALUE` is right, but `LAST_VALUE` is **wrong**: it just echoes each row's own amount instead of the last day's 11000.

> **Common mistake: the default-frame trap.** With an `ORDER BY` and no frame, the default frame stops at the **current row** (`... AND CURRENT ROW`). So the "last row of the frame" is always the current row. The cure is to say you want the whole partition:

```py
show(conn.execute('''
    SELECT day, cents,
           FIRST_VALUE(cents) OVER w AS first_day,
           LAST_VALUE(cents)  OVER w AS last_day,
           NTH_VALUE(cents, 3) OVER w AS third_day
    FROM daily_sales
    WINDOW w AS (ORDER BY day ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
    ORDER BY day
'''))
```

```sh
day         cents  first_day  last_day  third_day
----------  -----  ---------  --------  ---------
2025-03-01  12000  12000      11000     15000
2025-03-02  8000   12000      11000     15000
2025-03-03  15000  12000      11000     15000
2025-03-04  9000   12000      11000     15000
2025-03-05  20000  12000      11000     15000
2025-03-06  6000   12000      11000     15000
2025-03-07  11000  12000      11000     15000
(7 rows)
```

(That `WINDOW w AS (...)` is a named window. The next section explains it.) Another cure for `LAST_VALUE` is to flip the order and use `FIRST_VALUE` with `ORDER BY day DESC`.

## Named Windows

When several functions share the same window, write it once. Define it with `WINDOW name AS (...)` after `HAVING` and before `ORDER BY`, and use `OVER name`:

```sql
-- syntax
SELECT function1() OVER w, function2() OVER w
FROM table_name
WINDOW w AS (PARTITION BY ... ORDER BY ...)
```

Here is the month-over-month query from earlier, without the repetition:

```py
show(shop.execute('''
    WITH monthly AS (
        SELECT strftime('%Y-%m', o.order_date) AS month,
               SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY month
    )
    SELECT month, cents,
           LAG(cents) OVER w AS prev_cents,
           round(100.0 * (cents - LAG(cents) OVER w) / LAG(cents) OVER w, 1) AS change_pct,
           SUM(cents) OVER (w ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_cents
    FROM monthly
    WINDOW w AS (ORDER BY month)
    ORDER BY month
    LIMIT 4
'''))
```

```sh
month    cents   prev_cents  change_pct  running_cents
-------  ------  ----------  ----------  -------------
2024-01  8394    NULL        NULL        8394
2024-02  69184   8394        724.2       77578
2024-03  155551  69184       124.8       233129
2024-04  104364  155551      -32.9       337493
(4 rows)
```

A named window can also be extended: `OVER (w ROWS BETWEEN ...)` reuses `w`'s `PARTITION BY` and `ORDER BY` and adds a frame, as the last column does.

## Gaps and Islands: Finding Streaks

A classic analytics question: *"what is the longest streak of consecutive days on which something happened?"* Consecutive login days, consecutive days with an order, an unbroken run of sales. The rows that belong together form an **island**; the holes between them are **gaps**. SQL has no "next day" loop, but a window function gives a neat trick.

### The Trick

Take these login days. There are three streaks: March 1-3, March 5-6 and March 9 alone.

```py
conn.execute('CREATE TABLE logins (day TEXT PRIMARY KEY) STRICT')
conn.executemany('INSERT INTO logins VALUES (?)', [('2025-03-01',), ('2025-03-02',), ('2025-03-03',), ('2025-03-05',), ('2025-03-06',), ('2025-03-09',)])

show(conn.execute('''
    SELECT day,
           ROW_NUMBER() OVER (ORDER BY day) AS rn,
           date(day, '-' || ROW_NUMBER() OVER (ORDER BY day) || ' days') AS grp
    FROM logins
    ORDER BY day
'''))
```

```sh
day         rn  grp
----------  --  ----------
2025-03-01  1   2025-02-28
2025-03-02  2   2025-02-28
2025-03-03  3   2025-02-28
2025-03-05  4   2025-03-01
2025-03-06  5   2025-03-01
2025-03-09  6   2025-03-03
(6 rows)
```

Let's slow down. The day number goes up by one on each row, **and** inside a streak the date also goes up by one per row. So if you **subtract** the row number (as a number of days) from the date, the result stays constant inside a streak, and jumps whenever a day is missing:

```
 day          rn   day minus rn days     what happened
 2025-03-01    1   2025-02-28  ┐
 2025-03-02    2   2025-02-28  ├ same value: one island
 2025-03-03    3   2025-02-28  ┘
 2025-03-05    4   2025-03-01  ┐ a gap (March 4) made the value jump
 2025-03-06    5   2025-03-01  ┘ same value: the next island
 2025-03-09    6   2025-03-03    another gap, a new island
```

That "constant per streak" value is a perfectly good group key, even though it is not a real date for anything. Group by it and each group is one streak:

```py
show(conn.execute('''
    WITH numbered AS (
        SELECT day,
               date(day, '-' || ROW_NUMBER() OVER (ORDER BY day) || ' days') AS grp
        FROM logins
    )
    SELECT MIN(day) AS streak_start, MAX(day) AS streak_end, COUNT(*) AS days
    FROM numbered
    GROUP BY grp
    ORDER BY streak_start
'''))
```

```sh
streak_start  streak_end  days
------------  ----------  ----
2025-03-01    2025-03-03  3
2025-03-05    2025-03-06  2
2025-03-09    2025-03-09  1
(3 rows)
```

The recipe, in four steps:

1. One row per day (use `SELECT DISTINCT` if a day can appear twice, or the row numbers will drift).
2. `ROW_NUMBER()` in date order (per customer, if you track several: `PARTITION BY`).
3. Date minus row number gives the island key.
4. `GROUP BY` the key (and the customer); `MIN`, `MAX` and `COUNT(*)` describe each streak.

> **In other databases:** the subtraction is written `day - rn` (PostgreSQL, `date - integer`), `DATEADD(day, -rn, day)` (SQL Server) or `day - INTERVAL rn DAY` (DuckDB). SQLite does it with the `date(day, '-N days')` modifier, built here with `'-' || N || ' days'`.

### Streaks in the Shop

`shop.db` was built so that some customers order on consecutive days. Let's look at customer 3 first. A customer can order twice in one day, so step 1 (`DISTINCT`) matters:

```py
show(shop.execute('''
    WITH days AS (
        SELECT DISTINCT order_date FROM orders WHERE customer_id = 3
    )
    SELECT order_date,
           ROW_NUMBER() OVER (ORDER BY order_date) AS rn,
           date(order_date, '-' || ROW_NUMBER() OVER (ORDER BY order_date) || ' days') AS grp
    FROM days
    ORDER BY order_date
'''))
```

```sh
order_date  rn  grp
----------  --  ----------
2024-03-11  1   2024-03-10
2024-03-12  2   2024-03-10
2024-03-13  3   2024-03-10
2024-03-14  4   2024-03-10
2024-03-15  5   2024-03-10
2024-03-20  6   2024-03-14
2024-03-21  7   2024-03-14
2024-07-08  8   2024-06-30
2024-11-19  9   2024-11-10
2024-12-23  10  2024-12-13
2025-03-21  11  2025-03-10
(11 rows)
```

The first five rows share the key `2024-03-10`: five days in a row, from March 11 to 15. Now for **all** customers: partition the row numbers by customer, group by customer and key, and list the longest streaks.

```py
show(shop.execute('''
    WITH days AS (
        SELECT DISTINCT customer_id, order_date FROM orders
    ), keyed AS (
        SELECT customer_id, order_date,
               date(order_date, '-' || ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) || ' days') AS grp
        FROM days
    )
    SELECT customer_id, MIN(order_date) AS streak_start, MAX(order_date) AS streak_end, COUNT(*) AS days
    FROM keyed
    GROUP BY customer_id, grp
    ORDER BY days DESC, customer_id, streak_start
    LIMIT 5
'''))
```

```sh
customer_id  streak_start  streak_end  days
-----------  ------------  ----------  ----
3            2024-03-11    2024-03-15  5
12           2025-02-03    2025-02-06  4
29           2025-11-20    2025-11-22  3
3            2024-03-20    2024-03-21  2
9            2024-05-30    2024-05-31  2
(5 rows)
```

Customer 3 holds the record with 5 days in a row, then customers 12 and 29. The same trick finds "months in a row above target", "consecutive failed logins" or "uninterrupted subscription periods". For gaps (the holes themselves) compare each day with `LAG(day)` and keep the rows where the difference is more than 1.

## Putting It Together: Windows and CTEs

Real analytical queries stack these pieces: a CTE to aggregate, a window to compare, maybe another CTE to filter on the window. Which was the best month of each year, and how far ahead of the second best? Three steps, each one a CTE:

```py
show(shop.execute('''
    WITH monthly AS (
        SELECT strftime('%Y', o.order_date) AS year, strftime('%m', o.order_date) AS month,
               SUM(oi.quantity * oi.unit_price_cents) AS cents
        FROM orders AS o
        JOIN order_items AS oi ON oi.order_id = o.order_id
        WHERE o.status <> 'cancelled'
        GROUP BY year, month
    ), ranked AS (
        SELECT year, month, cents,
               RANK() OVER (PARTITION BY year ORDER BY cents DESC) AS rnk,
               cents - LEAD(cents) OVER (PARTITION BY year ORDER BY cents DESC) AS lead_over_next
        FROM monthly
    )
    SELECT year, month, cents, lead_over_next
    FROM ranked
    WHERE rnk = 1
    ORDER BY year
'''))
```

```sh
year  month  cents   lead_over_next
----  -----  ------  --------------
2024  11     350277  21590
2025  12     432648  87640
(2 rows)
```

Read it like a recipe: *aggregate by month → rank and look at the next month inside each year → keep the winners*. Whenever a window query gets hard, write each step as its own CTE and run them one at a time, the same habit as with joins on Day 11.

> **Looking ahead:** DuckDB (Day 25) can filter on a window directly with `QUALIFY rnk = 1`, so the last CTE disappears.

Running totals, neighbours, frames and streaks: the tools of every analyst. Ready for the exercises?

## Exercises: Day 18

### Exercises: Level 1

Use `data/shop.db` for 1 to 11, the normalized `library.db` for 12 to 14 and small inline tables for 15 to 17. As before: **revenue** means `quantity * unit_price_cents` of order lines whose order is not `cancelled`, in integer cents. Add tie-breakers so your output matches ours.

1. Running revenue by day: show `day`, `cents` and `running_cents`, in date order. First 5 rows.

   ```sh
   day         cents  running_cents
   ----------  -----  -------------
   2024-01-02  1198   1198
   2024-01-10  7196   8394
   2024-02-08  6997   15391
   2024-02-14  12796  28187
   2024-02-17  5277   33464
   (5 rows)
   ```

2. How many orders were placed each month, and the running number of orders (`running_orders`) since January 2024? First 5 months.

   ```sh
   month    orders  running_orders
   -------  ------  --------------
   2024-01  2       2
   2024-02  7       9
   2024-03  15      24
   2024-04  9       33
   2024-05  11      44
   (5 rows)
   ```

3. For the orders of customer 7, show `order_id`, `order_date` and the customer's previous order date (`prev_order`). Use `LAG` with `PARTITION BY customer_id` on all orders, then keep customer 7 in an outer query. First 6 rows.

   ```sh
   order_id  order_date  prev_order
   --------  ----------  ----------
   152       2024-12-09  NULL
   157       2024-12-12  2024-12-09
   167       2024-12-22  2024-12-12
   177       2024-12-28  2024-12-22
   192       2025-01-20  2024-12-28
   215       2025-03-05  2025-01-20
   (6 rows)
   ```

4. Same customer, but with `LEAD`: the date of the next order, with the text `'none'` as default for the last order. Show the last 3 orders.

   ```sh
   order_id  order_date  next_order
   --------  ----------  ----------
   395       2025-12-28  none
   393       2025-12-25  2025-12-28
   389       2025-12-21  2025-12-25
   (3 rows)
   ```

5. Monthly revenue with the difference from the previous month (`change_cents`). Show the first 5 months, where the first change is `NULL`.

   ```sh
   month    cents   change_cents
   -------  ------  ------------
   2024-01  8394    NULL
   2024-02  69184   60790
   2024-03  155551  86367
   2024-04  104364  -51187
   2024-05  83397   -20967
   (5 rows)
   ```

6. The value of each order and the customer's running spend (`running_cents`). Write it for all customers with `PARTITION BY customer_id`, then show only customer 3's rows.

   ```sh
   order_id  order_date  cents  running_cents
   --------  ----------  -----  -------------
   13        2024-03-11  8797   8797
   14        2024-03-12  2868   11665
   15        2024-03-13  599    12264
   16        2024-03-14  10994  23258
   17        2024-03-15  10245  33503
   19        2024-03-20  6196   39699
   20        2024-03-21  5297   44996
   59        2024-07-08  11797  56793
   126       2024-11-19  19496  76289
   168       2024-12-23  14633  90922
   219       2025-03-21  8096   99018
   (11 rows)
   ```

7. Use `MAX(...) OVER (ORDER BY ...)` to show, for customer 3, the value of their biggest order *so far* (`best_so_far`) next to every order.

   ```sh
   order_id  order_date  cents  best_so_far
   --------  ----------  -----  -----------
   13        2024-03-11  8797   8797
   14        2024-03-12  2868   8797
   15        2024-03-13  599    8797
   16        2024-03-14  10994  10994
   17        2024-03-15  10245  10994
   19        2024-03-20  6196   10994
   20        2024-03-21  5297   10994
   59        2024-07-08  11797  11797
   126       2024-11-19  19496  19496
   168       2024-12-23  14633  19496
   219       2025-03-21  8096   19496
   (11 rows)
   ```

8. For every order of customer 3 show the date of their first order (`FIRST_VALUE`) and the number of days since then (`days_since_first`).

   ```sh
   order_id  order_date  first_order  days_since_first
   --------  ----------  -----------  ----------------
   13        2024-03-11  2024-03-11   0
   14        2024-03-12  2024-03-11   1
   15        2024-03-13  2024-03-11   2
   16        2024-03-14  2024-03-11   3
   17        2024-03-15  2024-03-11   4
   19        2024-03-20  2024-03-11   9
   20        2024-03-21  2024-03-11   10
   59        2024-07-08  2024-03-11   119
   126       2024-11-19  2024-03-11   253
   168       2024-12-23  2024-03-11   287
   219       2025-03-21  2024-03-11   375
   (11 rows)
   ```

9. Show `LAST_VALUE(order_date)` for customer 3's orders the wrong way (default frame) and the right way (full frame) in two columns: `wrong` and `right`. Look at the first 3 rows and say why they differ.

   ```sh
   order_id  order_date  wrong       right
   --------  ----------  ----------  ----------
   13        2024-03-11  2024-03-11  2025-03-21
   14        2024-03-12  2024-03-12  2025-03-21
   15        2024-03-13  2024-03-13  2025-03-21
   (3 rows)
   ```

10. Rewrite exercise 5 with a `WINDOW` clause and also show the running total (`running_cents`). First 3 months.

    ```sh
    month    cents   change_cents  running_cents
    -------  ------  ------------  -------------
    2024-01  8394    NULL          8394
    2024-02  69184   60790         77578
    2024-03  155551  86367         233129
    (3 rows)
    ```

11. Employees: list them in hiring order with their salary in dollars, the previous hire's salary (`prev_salary`) and the difference (`diff`). Show the first 6.

    ```sh
    name             hire_date   salary  prev_salary  diff
    ---------------  ----------  ------  -----------  ------
    Grace Hopper     2019-01-07  185000  NULL         NULL
    Alan Turing      2019-03-18  140000  185000       -45000
    Ada Lovelace     2019-05-06  135000  140000       -5000
    Edsger Dijkstra  2020-02-10  130000  135000       -5000
    Barbara Liskov   2020-06-01  110000  130000       -20000
    Donald Knuth     2020-09-14  108000  110000       -2000
    (6 rows)
    ```

12. Library: for every loan show the member's name, the loan date and the date of the same member's previous loan (`prev_loan`). Order by member and date.

    ```sh
    name          loaned_on   prev_loan
    ------------  ----------  ----------
    Alice Nguyen  2025-01-10  NULL
    Alice Nguyen  2025-01-25  2025-01-10
    Alice Nguyen  2025-03-10  2025-01-25
    Bruno Silva   2025-02-01  NULL
    Bruno Silva   2025-02-20  2025-02-01
    Bruno Silva   2025-03-12  2025-02-20
    Chloe Martin  2025-02-03  NULL
    Chloe Martin  2025-03-01  2025-02-03
    Dev Patel     2025-03-05  NULL
    Dev Patel     2025-03-08  2025-03-05
    (10 rows)
    ```

13. Library: order the books by publication year (ties by title) and show a running total of pages (`pages_so_far`). First 5 books.

    ```sh
    title                year  pages  pages_so_far
    -------------------  ----  -----  ------------
    Pride and Prejudice  1813  279    279
    Emma                 1815  474    753
    Brave New World      1932  311    1064
    The Hobbit           1937  310    1374
    1984                 1949  328    1702
    (5 rows)
    ```

14. Library: for every book in publication order, show the title of the **next** published book (`next_title`) with `LEAD`. Last 3 rows.

    ```sh
    title              year  next_title
    -----------------  ----  -----------------
    Project Hail Mary  2021  NULL
    The Martian        2011  Project Hail Mary
    Clean Code         2008  The Martian
    (3 rows)
    ```

15. **Predict, then run.** A table has the values `5, 10, 20, 40` in an order column `n = 1..4`. Write down the running sum, `LAG` and `LEAD` of `v` for each row, then check.

    ```sh
    n  v   running  prev  next
    -  --  -------  ----  ----
    1  5   5        NULL  10
    2  10  15       5     20
    3  20  35       10    40
    4  40  75       20    NULL
    (4 rows)
    ```

16. With the same table, a 3-row moving sum (the row and the two before it) and a centred sum of the row and both neighbours. Predict the row with `n = 3` first.

    ```sh
    n  v   moving3  centred
    -  --  -------  -------
    1  5   5        15
    2  10  15       35
    3  20  35       70
    4  40  70       60
    (4 rows)
    ```

17. Explain in your own words: what is the difference between `ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` and `RANGE BETWEEN 2 PRECEDING AND CURRENT ROW`? When would you choose each?

### Exercises: Level 2

1. **7-day moving average of daily revenue** (calendar days, not rows): for each day with sales show `day`, `cents` and `avg_7d`: the average daily revenue over the current day and the 6 calendar days before it (only days that have sales count), rounded to a whole number of cents. Order the window by `julianday(day)` and use `RANGE`. Show the rows of March 2025 as a sample.

   ```sh
   day         cents  avg_7d
   ----------  -----  ------
   2025-03-04  23470  13734
   2025-03-05  7198   15334
   2025-03-08  4498   11722
   2025-03-20  3598   3598
   2025-03-21  8096   5847
   2025-03-22  16895  9530
   2025-03-28  37995  27445
   2025-03-29  28087  33041
   2025-03-31  51040  39041
   (9 rows)
   ```

2. **Days between consecutive orders** of each customer. First show the rows for customers 1 and 2 (`customer_id`, `order_date`, `prev_order`, `gap_days`), then list the five customers with at least 5 orders and the **smallest average gap** (`avg_gap`, 1 decimal), ties by customer.

   ```sh
   customer_id  order_date  prev_order  gap_days
   -----------  ----------  ----------  --------
   1            2024-04-24  NULL        NULL
   1            2024-06-25  2024-04-24  62
   1            2024-08-12  2024-06-25  48
   1            2025-01-12  2024-08-12  153
   1            2025-06-27  2025-01-12  166
   1            2025-10-09  2025-06-27  104
   1            2025-10-27  2025-10-09  18
   2            2024-03-31  NULL        NULL
   (8 rows)
   customer_id  orders  avg_gap
   -----------  ------  -------
   7            20      20.2
   18           19      24.6
   24           18      33.6
   3            11      37.5
   31           16      37.5
   (5 rows)
   ```

3. **Month-over-month growth in percent for 2025**: `month`, `cents`, `prev_cents`, `growth_pct` (1 decimal). The window must see December 2024 so that January 2025 has a predecessor: filter to 2025 only in the *outer* query.

   ```sh
   month    cents   prev_cents  growth_pct
   -------  ------  ----------  ----------
   2025-01  180703  328687      -45.0
   2025-02  120411  180703      -33.4
   2025-03  180877  120411      50.2
   2025-04  160987  180877      -11.0
   2025-05  335031  160987      108.1
   2025-06  174489  335031      -47.9
   2025-07  158397  174489      -9.2
   2025-08  141552  158397      -10.6
   2025-09  192813  141552      36.2
   2025-10  242033  192813      25.5
   2025-11  345008  242033      42.5
   2025-12  432648  345008      25.4
   (12 rows)
   ```

4. **Customer lifetime**: for customers 1 to 5 show one row each with `first_order`, `last_order` (use `FIRST_VALUE` and `LAST_VALUE` with the right frame, then `SELECT DISTINCT`) and `span_days`, the days between them. Customer 5 has no orders, so expect 4 rows.

   ```sh
   customer_id  first_order  last_order  span_days
   -----------  -----------  ----------  ---------
   1            2024-04-24   2025-10-27  551
   2            2024-03-31   2025-12-17  626
   3            2024-03-11   2025-03-21  375
   4            2024-11-22   2025-12-21  394
   (4 rows)
   ```

5. **Library**: for every loan, the days since the same member's previous loan (`days_since_prev`), and a flag `returned_late` (1 if `returned_on` is after `due_on`, otherwise 0; unreturned loans are 0). Order by member and date.

   ```sh
   name          loaned_on   days_since_prev  returned_late
   ------------  ----------  ---------------  -------------
   Alice Nguyen  2025-01-10  NULL             0
   Alice Nguyen  2025-01-25  15               0
   Alice Nguyen  2025-03-10  44               0
   Bruno Silva   2025-02-01  NULL             0
   Bruno Silva   2025-02-20  19               0
   Bruno Silva   2025-03-12  20               0
   Chloe Martin  2025-02-03  NULL             1
   Chloe Martin  2025-03-01  26               0
   Dev Patel     2025-03-05  NULL             0
   Dev Patel     2025-03-08  3                0
   (10 rows)
   ```

6. **Running revenue per category in 2025**: for each category and month of 2025 show the month's revenue (`cents`) and the running total inside the category (`category_running`). Use a CTE that groups by category and month, then a window with `PARTITION BY`. Order by category and month; the first 6 rows.

   ```sh
   category  month    cents  category_running
   --------  -------  -----  ----------------
   Books     2025-01  32243  32243
   Books     2025-02  14997  47240
   Books     2025-03  16495  63735
   Books     2025-04  31991  95726
   Books     2025-05  36390  132116
   Books     2025-06  54784  186900
   (6 rows)
   ```

### Exercises: Level 3

1. **Hacker News: the busiest week.** Use `hn_posts` from Day 3 (`datasets.db`). `created_at` is not ISO (`8/4/2016 11:52`), so first add a `created_day` column with the ISO date, converting in Python with `datetime.strptime(created_at, '%m/%d/%Y %H:%M')` and an `executemany` update (match rows by `rowid`, as on Day 17: it is much faster than by `id` on a table without an index) (if your Day 16 solution already has an ISO column, use that).
   Then (a) count the posts per day and show the cumulative number of posts, first 5 days; (b) find the **busiest 7-day window**: the 7 calendar days (the day and the 6 before it) with the most posts in total. Show the best 3 windows with their last day and total.
   Expected: the best window ends on 2016-01-16 with 445 posts.

   ```sh
   day         posts  cumulative_posts
   ----------  -----  ----------------
   2015-09-06  32     32
   2015-09-07  41     73
   2015-09-08  42     115
   2015-09-09  54     169
   2015-09-10  47     216
   (5 rows)
   window_end  window_start  posts_7d
   ----------  ------------  --------
   2016-01-16  2016-01-10    445
   2016-01-19  2016-01-13    442
   2016-01-17  2016-01-11    439
   (3 rows)
   ```

2. **Hacker News: how far ahead is an author's best post?** For every author with at least 10 posts, find their best post (most `num_points`, ties by lowest `id`), the points of their second best post, and the gap. Show the 5 authors with the biggest gap (`author`, `posts`, `best`, `second`, `gap`).

   ```sh
   author         posts  best  second  gap
   -------------  -----  ----  ------  ----
   bpierre        32     1622  480     1142
   runesoerensen  27     1020  220     800
   joeyespo       19     841   121     720
   sohkamyung     16     1005  344     661
   dnetesn        98     910   278     632
   (5 rows)
   ```

3. **The longest streak of consecutive order days per customer** in `shop.db` (all orders, several orders on one day count as one day). Show the three customers with the longest streaks: `customer_id`, `streak_start`, `streak_end`, `days`. (Customer 3's five days in March 2024 should be on top.) If a customer has two streaks of the same length, keep the earlier one.

   ```sh
   customer_id  streak_start  streak_end  days
   -----------  ------------  ----------  ----
   3            2024-03-11    2024-03-15  5
   12           2025-02-03    2025-02-06  4
   29           2025-11-20    2025-11-22  3
   (3 rows)
   ```

CONGRATULATIONS !

[<< Day 17](../17_Day_Window_functions_ranking/17_window_functions_ranking.md) | [Review 3 >>](../18R_Review_Analytical_sql/18R_review_analytical_sql.md)
