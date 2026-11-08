<div align="center">
  <h1> 30 Days Of SQL: Day 16 - Dates & Times</h1>
</div>

[<< Day 15](../15_Day_Set_operations/15_set_operations.md) | [Review 2 >>](../16R_Review_Combining_data/16R_review_combining_data.md)

- [Day 16](#day-16)
  - [Dates in SQLite](#dates-in-sqlite)
    - [No Date Type: Store ISO-8601 Text](#no-date-type-store-iso-8601-text)
    - [A Fixed "Today"](#a-fixed-today)
  - [The Date and Time Functions](#the-date-and-time-functions)
    - [date, time and datetime](#date-time-and-datetime)
    - [Modifiers](#modifiers)
    - [start of ..., and weekday](#start-of--and-weekday)
    - [strftime: Picking Dates Apart](#strftime-picking-dates-apart)
    - [Differences: julianday, unixepoch and timediff](#differences-julianday-unixepoch-and-timediff)
    - [Bad Dates](#bad-dates)
  - [Grouping by Time](#grouping-by-time)
  - [Python and SQLite Dates](#python-and-sqlite-dates)
  - [ Exercises: Day 16](#exercises-day-16)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 16

## Dates in SQLite

### No Date Type: Store ISO-8601 Text

Most databases have a `DATE` and a `TIMESTAMP` type. **SQLite has neither.** It stores dates as ordinary values of one of three kinds: `TEXT` (like `'2025-03-14 09:30:00'`), `REAL` (Julian day numbers) or `INTEGER` (Unix time: seconds since 1 January 1970). Its date functions understand all three.

The recommended choice is **TEXT in ISO-8601 format**: `YYYY-MM-DD` for a date and `YYYY-MM-DD HH:MM:SS` for a date and time. It's what the shop tables use. Why?

- It is readable by humans.
- It **sorts correctly** as plain text, because the biggest unit comes first: `'2025-03-14' < '2025-12-01'`.
- `BETWEEN`, `<`, `>`, `MIN`, `MAX` and `ORDER BY` all work with no conversion.
- Python's `date.isoformat()` and `datetime.fromisoformat()` speak it.

Compare with a format like `3/14/2025`: as text, `'12/1/2024'` sorts before `'3/14/2025'`, and nobody can tell whether `4/5/2025` is the 4th of May or the 5th of April. The `hacker_news.csv` file has exactly this problem, and you will fix it in the exercises.  **Common mistake:** storing dates in a local format.

### A Fixed "Today"

SQLite can tell you the current date with `date('now')`, but the answer changes every day, so the output in this lesson would drift, and your outputs would never match the ones shown. From now on, whenever the course needs "today", it means a fixed date:

```py
import sqlite3
from helpers import show

TODAY = '2025-03-14'
conn = sqlite3.connect('data/shop.db')
```

(`solutions/helpers.py` has the same `TODAY`.) In your own programs you would use `'now'`. The only difference is passing the date as a **parameter** (`?`) instead of writing `'now'`, which has an extra benefit: your queries become testable, because you can pass any date you like.

## The Date and Time Functions

### date, time and datetime

```sql
-- syntax
SELECT date(time_value);        -- 'YYYY-MM-DD'
SELECT time(time_value);        -- 'HH:MM:SS'
SELECT datetime(time_value);    -- 'YYYY-MM-DD HH:MM:SS'
```

```py
print(conn.execute("SELECT date('2025-03-14 09:30:45'), time('2025-03-14 09:30:45'), datetime('2025-03-14')").fetchone())
# ('2025-03-14', '09:30:45', '2025-03-14 00:00:00')
```

They take a date string and give back a normalised date string. The special value `'now'` means the current moment **in UTC**; add the `'localtime'` modifier to convert to your computer's time zone. `date('now')` returns today's date, but its value changes every day, so we use `TODAY` instead:

```py
print(conn.execute('SELECT date(?)', (TODAY,)).fetchone())
# ('2025-03-14',)
```

### Modifiers

After the time value you can list **modifiers** that shift the date, one after another, from left to right:

```sql
-- syntax
SELECT date(time_value, modifier1, modifier2, ...);
```

```py
print(conn.execute("SELECT date(:t, '+7 days'), date(:t, '-1 month'), date(:t, '+1 year'), datetime(:t, '+90 minutes')", {'t': TODAY}).fetchone())
# ('2025-03-21', '2025-02-14', '2026-03-14', '2025-03-14 01:30:00')
```

The modifiers are `+N days`, `+N hours`, `+N minutes`, `+N seconds`, `+N months`, `+N years` (the number can be negative, and the unit may be singular or plural). Because they apply in order, you can chain them to build any date you want.

### start of ..., and weekday

`'start of month'`, `'start of year'` and `'start of day'` move back to the beginning of that period. Combined with other modifiers they give you month ends, which SQLite has no function for: go to the start of the month, add a month, subtract a day.

```py
print(conn.execute("""
    SELECT date(:t, 'start of month'),
           date(:t, 'start of month', '+1 month', '-1 day'),
           date(:t, 'start of year')
""", {'t': TODAY}).fetchone())
# ('2025-03-01', '2025-03-31', '2025-01-01')
```

`'weekday N'` moves **forward** to the next date that falls on weekday N, where 0 is Sunday, 1 is Monday ... 6 is Saturday. If the date is already that weekday, it stays. 14 March 2025 is a Friday:

```py
print(conn.execute("SELECT date(:t, 'weekday 0'), date(:t, 'weekday 1'), date(:t, '+1 day', 'weekday 5')", {'t': TODAY}).fetchone())
# ('2025-03-16', '2025-03-17', '2025-03-21')
```

The next Sunday is the 16th, the next Monday the 17th. The last value shows how to ask for the next *strictly later* Friday: add a day first.

### strftime: Picking Dates Apart

`strftime(format, time_value)` is the general-purpose function: it formats a date using codes introduced by `%`. This is what you use to extract the year, month or weekday, and to group by them.

```sql
-- syntax
SELECT strftime('%Y-%m', time_value);
```

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| `%Y` | 4-digit year | `%H` | hour 00-23 |
| `%m` | month 01-12 | `%M` | minute 00-59 |
| `%d` | day of month 01-31 | `%S` | second 00-59 |
| `%w` | weekday 0-6 (Sunday = 0) | `%j` | day of the year 001-366 |
| `%W` | week of the year 00-53 | `%s` | seconds since 1970 |

```py
print(conn.execute("SELECT strftime('%Y', :t), strftime('%m', :t), strftime('%d', :t), strftime('%w', :t), strftime('%j', :t)", {'t': TODAY}).fetchone())
# ('2025', '03', '14', '5', '073')
```

Notice that `strftime` returns **text**, even for numbers (`'03'`, not `3`). Use `CAST(strftime('%m', d) AS INTEGER)` when you need a number.

> **In other databases:** you will see `YEAR(d)`, `MONTH(d)`, `DAY(d)` (MySQL, SQL Server), `EXTRACT(YEAR FROM d)` (standard, PostgreSQL, DuckDB), `DATE_TRUNC('month', d)` (PostgreSQL, DuckDB), `DATE_FORMAT` (MySQL) and `FORMAT`/`DATEPART` (SQL Server). SQLite has none of these; `strftime` does all of it. Current time: `NOW()` or `CURRENT_TIMESTAMP` (SQLite also knows `CURRENT_TIMESTAMP`, `CURRENT_DATE`), `GETDATE()` in SQL Server.

### Differences: julianday, unixepoch and timediff

SQLite cannot subtract two dates with `-` (it would convert the texts to numbers first: `'2025-03-14' - '2025-03-01'` gives `0`, since SQLite reads only the leading number, `2025`, of each text). Convert them to numbers first.

`julianday(d)` gives the number of days since a fixed date in the past, as a decimal. The difference of two Julian days is the number of days between them:

```sql
-- syntax
SELECT julianday(later) - julianday(earlier);
```

```py
print(conn.execute("SELECT '2025-03-14' - '2025-03-01'").fetchone())
print(conn.execute("SELECT julianday('2025-03-14') - julianday('2025-03-01')").fetchone())
```

```sh
(0,)
(13.0,)
```

The days come with a decimal part when times are involved (`0.5` is half a day), so `CAST(... AS INTEGER)` or `ROUND` is typical. Two newer functions give other views of the same thing:

- `unixepoch(d)` (SQLite 3.38) returns the number of **seconds** since 1970-01-01 as an integer. Differences of Unix times are seconds, so divide by 60, 3600 or 86400.
- `timediff(a, b)` (SQLite 3.43) returns the difference as a readable text, `+YYYY-MM-DD HH:MM:SS.SSS`.

```py
print(conn.execute("SELECT unixepoch('2025-03-14'), datetime(1741910400, 'unixepoch')").fetchone())
print(conn.execute("SELECT (unixepoch('2025-03-14 12:00:00') - unixepoch('2025-03-13 10:30:00')) / 60").fetchone())
print(conn.execute("SELECT timediff('2025-03-14 12:00:00', '2025-03-13 10:30:00')").fetchone())
```

```sh
(1741910400, '2025-03-14 00:00:00')
(1530,)
('+0000-00-01 01:30:00.000',)
```

That is 1530 minutes, or 1 day, 1 hour and 30 minutes, and `timediff` reads `+0000-00-01 01:30:00.000`: zero years, zero months, one day, then 1:30:00. Use `julianday` when you need days, `unixepoch` when you need minutes or seconds, and `timediff` when a person will read it.

Days since a customer signed up, as of our fixed today:

```py
show(conn.execute('''
    SELECT customer_id, first_name, signup_date,
           CAST(julianday(?) - julianday(signup_date) AS INTEGER) AS days_since_signup
    FROM customers
    ORDER BY customer_id
    LIMIT 4
''', (TODAY,)))
```

```sh
customer_id  first_name  signup_date  days_since_signup
-----------  ----------  -----------  -----------------
1            Chen        2023-07-01   622
2            Diego       2024-02-19   389
3            Liam        2024-01-05   434
4            Noah        2024-11-16   118
(4 rows)
```

### Bad Dates

What does SQLite do with a date that does not exist, or that is not in ISO format?

```py
print(conn.execute("SELECT date('2025-02-30'), date('2025-02-32'), date('2025-13-01'), date('14/03/2025')").fetchone())
# ('2025-03-02', None, None, None)
```

The invalid month, the invalid day-32 and the non-ISO format all give `NULL`: no error, no warning. But `2025-02-30` is **accepted** and silently rolled over to 2 March.  **Common mistake:** assuming SQLite validates dates. If a date function returns `NULL` where you did not expect it, look at the input format first. To really protect a column, add a `CHECK` (Day 9) such as `CHECK (date(day) = day)`, which rejects both the `NULL`s and the rolled-over dates.

## Grouping by Time

Dates become useful when you group by a part of them. `strftime('%Y-%m', date)` gives one text value per month, perfect for `GROUP BY` (Day 7):

```py
show(conn.execute('''
    SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) AS orders
    FROM orders
    WHERE order_date >= '2025-07-01' AND order_date < '2026-01-01'
    GROUP BY month
    ORDER BY month
'''))
```

```sh
month    orders
-------  ------
2025-07  13
2025-08  12
2025-09  13
2025-10  20
2025-11  31
2025-12  35
(6 rows)
```

Note the filter `order_date >= '2025-07-01' AND order_date < '2026-01-01'`. It is the right way to select a range: it is exact and can use an index (Day 21). The alternative `WHERE strftime('%Y', order_date) = '2025'` gives the same rows but calls a function on every row.
The half-open interval (`>=` start, `<` the day after the end) also works for datetimes, where `BETWEEN '2025-12-01' AND '2025-12-31'` would miss everything on the afternoon of the 31st. Let's also see the weekday pattern, with `%w` mapped to names:

```py
show(conn.execute('''
    SELECT CASE strftime('%w', order_date)
               WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue' WHEN '3' THEN 'Wed'
               WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri' ELSE 'Sat' END AS weekday,
           COUNT(*) AS orders
    FROM orders
    GROUP BY strftime('%w', order_date)
    ORDER BY strftime('%w', order_date)
'''))
```

```sh
weekday  orders
-------  ------
Sun      48
Mon      57
Tue      51
Wed      61
Thu      61
Fri      54
Sat      67
(7 rows)
```

## Python and SQLite Dates

Python has `datetime.date` and `datetime.datetime`. Older tutorials let `sqlite3` convert them automatically with "adapters" and "converters". **Those default adapters are deprecated since Python 3.12**: they use a format you didn't choose and will be removed in a future Python. The modern approach is simple, and you
control it: convert to an ISO **string** yourself on the way in and back with `fromisoformat` on the way out.

```py
from datetime import date, datetime

moment = datetime(2025, 3, 14, 18, 45)
print(moment.isoformat(sep=' ', timespec='seconds'))
print(date(2025, 3, 15).isoformat())
print(datetime.fromisoformat('2025-03-14 18:45:00'))
print(date.fromisoformat('2025-03-14') + (date(2025, 3, 15) - date(2025, 3, 14)))
```

```sh
2025-03-14 18:45:00
2025-03-15
2025-03-14 18:45:00
2025-03-15
```

Store the strings, query them with SQL, and convert back when you need Python objects:

```py
toy = sqlite3.connect(':memory:')
toy.execute('CREATE TABLE events (id INTEGER PRIMARY KEY, at TEXT NOT NULL) STRICT')
toy.execute('INSERT INTO events (at) VALUES (?)', (moment.isoformat(sep=' ', timespec='seconds'),))
toy.execute('INSERT INTO events (at) VALUES (?)', (datetime(2025, 3, 15, 8, 0).isoformat(sep=' ', timespec='seconds'),))
rows = toy.execute("SELECT at, datetime(at, '+1 day') FROM events ORDER BY at").fetchall()
print(rows)
print([datetime.fromisoformat(r[0]) for r in rows])
```

```sh
[('2025-03-14 18:45:00', '2025-03-15 18:45:00'), ('2025-03-15 08:00:00', '2025-03-16 08:00:00')]
[datetime.datetime(2025, 3, 14, 18, 45), datetime.datetime(2025, 3, 15, 8, 0)]
```

**Common mistake:** inserting a `datetime` object directly (`conn.execute('INSERT ...', (datetime.now(),))`). On Python 3.12 this still works but raises a `DeprecationWarning`, and the stored text uses a space or a `T` depending on how it was written. `isoformat()` it yourself. Also remember `datetime.now()` gives *local* time while SQLite's `'now'` is *UTC*, a classic source of "off by a few hours" bugs; pick one and stick to it (storing UTC is the usual advice).

Dates are not scary once you store them as ISO text and let `strftime`, `julianday` and the modifiers do the work. Next, do some exercises.

## Exercises: Day 16

Use `TODAY = '2025-03-14'` wherever an exercise says "today", and pass it as a parameter.

### Exercises: Level 1

Questions 9 and 10 use your `00_practice/library.db`. The others use `shop.db`, or no table at all.

1. Select today's date by passing `TODAY` to `date(?)`. Also run `SELECT date('now')` just to see it work (do not compare it with anything: its value changes).

   ```sh
   ('2025-03-14',)
   (1, 19)
   ```

2. What is the date 30 days after today?
3. For the first 5 orders (by id), show the order date and its year and month as integers.

   ```sh
   order_id  order_date  year  month
   --------  ----------  ----  -----
   1         2024-01-02  2024  1
   2         2024-01-10  2024  1
   3         2024-02-08  2024  2
   4         2024-02-14  2024  2
   5         2024-02-17  2024  2
   (5 rows)
   ```

4. For the first 5 customers (by id) show the signup date and the number of days between signup and today.

   ```sh
   customer_id  first_name  signup_date  days_since_signup
   -----------  ----------  -----------  -----------------
   1            Chen        2023-07-01   622
   2            Diego       2024-02-19   389
   3            Liam        2024-01-05   434
   4            Noah        2024-11-16   118
   5            Sam         2023-08-14   578
   (5 rows)
   ```

5. Which day of the week is today? Print the name (`Friday`, ...) using `strftime('%w', ...)` and a `CASE`.
6. For today, print the first day of the month, the last day of the month and the first day of the year, in one row.

   ```sh
   ('2025-03-01', '2025-03-31', '2025-01-01')
   ```

7. What is the date of the next Monday (counting today if it is a Monday), and of the next Monday that is strictly after today?

   ```sh
   ('2025-03-17',) ('2025-03-17',)
   ```

8. Count the orders placed in December 2025 in two ways: with `strftime`, and with a half-open range on the text.

   ```sh
   (35,) (35,)
   ```

9. Library: for the returned loans, show the loan id, the dates loaned and returned and the number of days the book was kept.

   ```sh
   id  loaned_on   returned_on  days_kept
   --  ----------  -----------  ---------
   1   2025-01-10  2025-01-20   10
   2   2025-01-25  2025-02-05   11
   3   2025-02-01  2025-02-14   13
   5   2025-02-03  2025-02-25   22
   (4 rows)
   ```

10. Library: for every member show the name, the date they joined, and how many days they have been a member as of today.

    ```sh
    name          joined_on   days_member
    ------------  ----------  -----------
    Alice Nguyen  2024-01-15  424
    Bruno Silva   2024-02-20  388
    Chloe Martin  2024-03-05  374
    Dev Patel     2024-06-18  269
    Elena Rossi   2024-09-02  193
    (5 rows)
    ```

11. In Python, create `datetime(2025, 3, 14, 9, 30)`, turn it into an ISO string with a space between date and time, ask SQLite for `datetime(that_string, '+90 minutes')`, and turn the answer back into a `datetime` object.

    ```sh
    2025-03-14 09:30:00 ('2025-03-14 11:00:00',)
    datetime.datetime(2025, 3, 14, 11, 0) 2025-03-14
    ```

12. What do `date('2025-02-30')`, `date('2025-02-32')`, `date('2025-13-01')` and `date('14/03/2025')` return? Which one is the dangerous one and why?

    ```sh
    ('2025-03-02', None, None, None)
    ```

13. Ask for the Unix time of today, and convert it back to a date-time text with the `'unixepoch'` modifier.

    ```sh
    (1741910400, '2025-03-14 00:00:00')
    ```

14. How many minutes are there between `2025-03-13 10:30:00` and `2025-03-14 12:00:00`? Get the answer with `unixepoch` and with `timediff` (and read the second one).

    ```sh
    ('+0000-00-01 01:30:00.000',) (1530,)
    ```

15. In your own words: why does ISO-8601 text sort in the right order, and why would `'3/14/2025'` not?

### Exercises: Level 2

1. The number of orders for every month of 2025, in month order (12 rows).

   ```sh
   month    orders
   -------  ------
   2025-01  20
   2025-02  12
   2025-03  12
   2025-04  14
   2025-05  23
   2025-06  13
   2025-07  13
   2025-08  12
   2025-09  13
   2025-10  20
   2025-11  31
   2025-12  35
   (12 rows)
   ```

2. The average number of days between a customer's **signup** and their **first order**, for the customers who ordered. Print how many customers it is based on, and the average rounded to one decimal.

   ```sh
   (54, 140.0)
   ```

3. **Overdue loans.** The library lends books for 14 days (`due_on` is `loaned_on + 14 days`). As of today, which loans are overdue (not returned and due before today)? Show the book, the member, the due date and the number of days overdue. Then show the loans that *were* returned late and by how many days. Finally verify with one query that
   every `due_on` really is 14 days after `loaned_on` (the count of rows where it is not should be 0).

   ```sh
   id  title                     member       due_on      days_overdue
   --  ------------------------  -----------  ----------  ------------
   4   The Pragmatic Programmer  Bruno Silva  2025-03-06  8
   (1 row)
   id  title        due_on      returned_on  days_late
   --  -----------  ----------  -----------  ---------
   5   The Martian  2025-02-17  2025-02-25   8
   (1 row)
   (0,)
   ```

4. The number of orders by weekday (Sunday first), with names.

   ```sh
   weekday  orders
   -------  ------
   Sun      48
   Mon      57
   Tue      51
   Wed      61
   Thu      61
   Fri      54
   Sat      67
   (7 rows)
   ```

5. Which customers signed up in the 90 days before today (including the first of those days)? Show id, name and signup date, oldest first.

   ```sh
   customer_id  first_name  last_name  signup_date
   -----------  ----------  ---------  -----------
   32           Chen        Johnson    2024-12-18
   46           Leo         Anderson   2025-01-08
   22           Emma        Anderson   2025-01-15
   (3 rows)
   2025-03-14
   ```

6. Revenue (non-cancelled orders, in dollars) per quarter of 2025. Compute the quarter number from the month.

   ```sh
   quarter  revenue
   -------  --------
   Q1       4819.91
   Q2       6705.07
   Q3       4927.62
   Q4       10196.89
   (4 rows)
   ```

7. In an in-memory table `events (id INTEGER PRIMARY KEY, at TEXT NOT NULL) STRICT`, store `datetime(2025, 3, 14, 18, 45)` and the 15th of March 2025 at 08:00 as ISO strings (with Python, without the deprecated adapters). Read them back sorted, as strings and as `datetime` objects.

   ```sh
   [('2025-03-14 18:45:00',), ('2025-03-15 08:00:00',)]
   [datetime.datetime(2025, 3, 14, 18, 45), datetime.datetime(2025, 3, 15, 8, 0)]
   ```

### Exercises: Level 3

1. **Hacker News dates.** In `hn_posts`, `created_at` looks like `8/4/2016 11:52`: month/day/year, no leading zeros, and the hour is 0 to 23 without a leading zero either. It is not ISO, so `strftime` returns `NULL` for it. Convert it to `YYYY-MM-DD HH:MM:SS` and
   find the **hour of the day with the highest average number of points**. Do the conversion with SQL string functions (`substr`, `instr`, `printf('%02d', ...)`, a chain of CTEs from Day 14), or in Python while reloading the table with `datetime.strptime(text, '%m/%d/%Y %H:%M')`.
   Show the converted values of the first four posts by id, the top 5 hours (hour, number of posts, average points rounded to two decimals) and the first and last dates.

   ```sh
   id        created_iso
   --------  -------------------
   10176908  2015-09-06 05:56:00
   10176923  2015-09-06 06:03:00
   10177011  2015-09-06 07:25:00
   10177048  2015-09-06 07:50:00
   (4 rows)
   hour  posts  avg_points
   ----  -----  ----------
   13    1102   56.17
   15    1234   55.65
   10    686    54.71
   14    1151   54.44
   19    1144   54.18
   (5 rows)
   ('2015-09-06 05:56:00', '2016-09-26 03:13:00', 20099)
   2016-08-04 11:52:00
   ```

2. With the converted dates, show for each weekday (names) the number of posts and the average points, best average first.

   ```sh
   weekday  posts  avg_points
   -------  -----  ----------
   Wed      3328   52.03
   Sun      2062   51.64
   Thu      3318   51.48
   Mon      3084   50.27
   Tue      3297   50.22
   Sat      2025   48.76
   Fri      2985   47.27
   (7 rows)
   ```

3. **Signup cohorts in the shop.** Group the customers by the month of their signup (`YYYY-MM`). For each cohort show the number of customers, how many of them ever ordered, and how many placed their first order within 90 days after signing up. Show the first 8 cohorts.

   ```sh
   cohort   customers  ordered  within_90_days
   -------  ---------  -------  --------------
   2023-06  7          6        0
   2023-07  1          1        0
   2023-08  2          1        0
   2023-09  6          6        0
   2023-10  3          2        1
   2023-11  2          2        0
   2023-12  2          1        0
   2024-01  5          5        3
   (8 rows)
   (19,)
   ```

That closes Part 2. Before moving on to analytic SQL, test yourself on everything from Days 11 to 16 with Review 2.

CONGRATULATIONS !

[<< Day 15](../15_Day_Set_operations/15_set_operations.md) | [Review 2 >>](../16R_Review_Combining_data/16R_review_combining_data.md)
