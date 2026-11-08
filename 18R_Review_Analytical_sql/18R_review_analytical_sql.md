<div align="center">
  <h1> 30 Days Of SQL: Review 3 - Analytical SQL (Days 11-18)</h1>
</div>

[<< Day 18](../18_Day_Window_functions_running/18_window_functions_running.md) | [Day 19 >>](../19_Day_Sqlite3_in_depth/19_sqlite3_in_depth.md)

- [Review 3](#review-3)
  - [How to Use This Review](#how-to-use-this-review)
  - [Part A: Write the Query](#part-a-write-the-query)
  - [Part B: Predict the Output](#part-b-predict-the-output)
  - [Part C: Find the Bug](#part-c-find-the-bug)
  - [Part D: Explain](#part-d-explain)
  - [Mini-Project: Customer Report](#mini-project-customer-report)

# Review 3

No new material today. This is a checkpoint for **Days 11 to 18**: joins (inner, outer, self, cross), subqueries, CTEs and temporary tables, set operations and conditional aggregation, dates, and window functions. It also leans on everything from Part 1. The problems are mixed and not labelled by day, so **you** have to decide which tool fits: that is the real skill of analytical SQL.

If something feels shaky, go back to that day before moving on. Days 19 to 22 leave pure SQL for a while and look at Python and `sqlite3` in depth.

## How to Use This Review

- Parts A, C and the mini-project use `data/shop.db`. Open it with `sqlite3.connect('data/shop.db')`. Revenue means `quantity * unit_price_cents` of order lines whose order is **not** `cancelled`, in integer cents, unless a question says otherwise.
- Some Part A questions use your normalized `library.db` from Day 10. Where a "today" is needed, use `2025-03-14`.
- Try each problem **before** looking at the expected output. For Part B, write your prediction first, then run it.
- Add tie-breakers to every `ORDER BY` so that your output matches ours. Where only the start of a long result is shown, `...` and the row count tell you how it ends.
- Put your work in `00_practice/review_3.py`.

## Part A: Write the Query

1. Show all 40 products with the name of their category. One product has no category: it must still appear, with the text `uncategorised` instead of `NULL`. Show the first 3 rows by `product_id` and the uncategorised one.

   ```sh
   product_id  name               category
   ----------  -----------------  -------------
   1           Wireless Mouse     Electronics
   2           USB-C Cable        Electronics
   3           Bluetooth Speaker  Electronics
   39          Gift Card Holder   uncategorised
   (4 rows)
   ```

2. List the customers who have **never placed an order**, with first name, last name and signup date, ordered by `customer_id`. Expect 6.

   ```sh
   customer_id  first_name  last_name  signup_date
   -----------  ----------  ---------  -----------
   5            Sam         Patel      2023-08-14
   17           Mia         Thomas     2024-09-26
   23           Sofia       Green      2023-12-07
   36           Diego       Scott      2024-02-26
   44           Tara        Kim        2023-06-03
   58           Isla        Clark      2023-10-25
   (6 rows)
   ```

3. Show every employee with the name of their manager (the CEO has none: show `NULL`). Order by `employee_id`, first 5 rows.

   ```sh
   employee_id  name             title                manager
   -----------  ---------------  -------------------  ------------
   1            Grace Hopper     CEO                  NULL
   2            Alan Turing      VP Engineering       Grace Hopper
   3            Ada Lovelace     VP Sales             Grace Hopper
   4            Edsger Dijkstra  VP Operations        Grace Hopper
   5            Barbara Liskov   Engineering Manager  Alan Turing
   (5 rows)
   ```

4. For each year, count the orders by status in a **single row per year**: columns `year`, `delivered`, `cancelled`, `open` (pending or shipped) and `total`.

   ```sh
   year  delivered  cancelled  open  total
   ----  ---------  ---------  ----  -----
   2024  167        14         0     181
   2025  179        10         29    218
   (2 rows)
   ```

5. Which products have **never been ordered**? Solve it in two different ways (an anti-join and `NOT EXISTS`) and check they agree. Show the names, ordered by `product_id`.

   ```sh
   product_id  name
   ----------  ---------------
   27          Jump Rope
   28          Camping Hammock
   33          Beanie
   40          Mystery Box
   (4 rows)
   (4,)
   ```

6. How many orders were placed on each day of the week? Show the weekday number (0 = Sunday) and the count, ordered by weekday. Which day is busiest?

   ```sh
   weekday  orders
   -------  ------
   0        48
   1        57
   2        51
   3        61
   4        61
   5        54
   6        67
   (7 rows)
   ```

7. Products that cost **more than the average price of their own category**. Show `name`, `price_cents` and the category average rounded to a whole number (`category_avg`), ordered by name. Show the first 6 rows and the total count.

   ```sh
   name                         price_cents  category_avg
   ---------------------------  -----------  ------------
   Bluetooth Speaker            5999         5166
   Board Game Night             3999         3399
   Building Blocks Set          3499         3399
   Camping Hammock              3999         3449
   Cast Iron Pan                3499         3449
   Chef's Knife                 6999         3449
   ...
   (16 rows)
   ```

8. Library: which loans are **overdue** on `2025-03-14` (not returned and past `due_on`)? Show the member, the book title, the due date and the days overdue. *(Day 10's tables: `loans`, `members`, `books`.)*

   ```sh
   member       title                     due_on      days_overdue
   -----------  ------------------------  ----------  ------------
   Bruno Silva  The Pragmatic Programmer  2025-03-06  8
   (1 row)
   ```

9. Sort the customers into spend **tiers** with a CTE: `gold` for 100000 cents or more, `silver` for 30000 or more, otherwise `bronze` (cancelled orders do not count; only customers with orders). Show how many customers fall into each tier and their combined spend, biggest tier first.

   ```sh
   tier    customers  total_cents
   ------  ---------  -----------
   gold    20         2969247
   silver  19         1236931
   bronze  15         287095
   (3 rows)
   ```

10. The two **best-selling products (by units) in each category**, with ties broken by name. Show `category`, `product`, `units` and the position. Expect 14 rows (7 categories have products; the empty category and the uncategorised product do not appear).

    ```sh
    category        product                   units  pos
    --------------  ------------------------  -----  ---
    Books           The Pragmatic Programmer  88     1
    Books           Mystery Novel             47     2
    Clothing        Denim Jacket              45     1
    Clothing        Cotton T-Shirt            23     2
    Electronics     USB-C Cable               80     1
    Electronics     Wireless Mouse            55     2
    ...
    (14 rows)
    ```

11. Show the **org chart** with a recursive CTE: every employee with their `level` (the CEO is level 1) and the `chain` of names from the CEO down, joined by ` > `. Order by chain; the first 6 rows.

    ```sh
    level  chain
    -----  -------------------------------------------------------------------
    1      Grace Hopper
    2      Grace Hopper > Ada Lovelace
    3      Grace Hopper > Ada Lovelace > Margaret Hamilton
    4      Grace Hopper > Ada Lovelace > Margaret Hamilton > Hedy Lamarr
    4      Grace Hopper > Ada Lovelace > Margaret Hamilton > Katherine Johnson
    2      Grace Hopper > Alan Turing
    ...
    (15 rows)
    ```

12. Revenue per category for **each month of the first quarter of 2025, including months with no sales** (zeros, not missing rows). Generate the combinations with `CROSS JOIN` and `LEFT JOIN` the sales on. Columns: `category`, `month`, `cents`. Order by category and month; first 9 rows. (There are 8 categories, so 24 rows in total.)

    ```sh
    category        month    cents
    --------------  -------  -----
    Books           2025-01  32243
    Books           2025-02  14997
    Books           2025-03  16495
    Clothing        2025-01  0
    Clothing        2025-02  6799
    Clothing        2025-03  7999
    Electronics     2025-01  40984
    Electronics     2025-02  14545
    Electronics     2025-03  36396
    ...
    (24 rows)
    ```

13. For 2025, show each month's revenue, the **change from the previous month in percent** and a **3-month moving average** (the month and the two before it, rounded to a whole number of cents). The window must see 2024 so that January has predecessors; show only the months January to June 2025.

    ```sh
    month    cents   change_pct  avg_3m
    -------  ------  ----------  ------
    2025-01  180703  -45.0       286556
    2025-02  120411  -33.4       209934
    2025-03  180877  50.2        160664
    2025-04  160987  -11.0       154092
    2025-05  335031  108.1       225632
    2025-06  174489  -47.9       223502
    (6 rows)
    ```

14. Customers who bought **both** a product from `Books` **and** a product from `Toys`: list their ids with `INTERSECT`, then show how many there are. Then do it again with a different technique (a join plus `HAVING COUNT(DISTINCT ...) = 2`) and make sure the counts match.

    ```sh
    37 [1, 2, 3, 4, 6, 7, 8, 9]
    (37,)
    ```

15. **Streaks.** For each customer, find the longest run of consecutive **order days**, and list the customers whose longest streak is at least 3 days (`customer_id`, `streak_start`, `streak_end`, `days`). Several orders on one day count as one day.

    ```sh
    customer_id  streak_start  streak_end  days
    -----------  ------------  ----------  ----
    3            2024-03-11    2024-03-15  5
    12           2025-02-03    2025-02-06  4
    29           2025-11-20    2025-11-22  3
    (3 rows)
    ```

## Part B: Predict the Output

Two tiny tables. Write down what you think each query returns, then run it. The tables:

```py
import sqlite3
from helpers import show

t = sqlite3.connect(':memory:')
t.executescript('''
    CREATE TABLE a (x INTEGER);
    CREATE TABLE b (x INTEGER);
    INSERT INTO a VALUES (1), (2), (2), (3), (NULL);
    INSERT INTO b VALUES (2), (3), (3), (4);
''')
```

1. `SELECT a.x, b.x FROM a LEFT JOIN b ON a.x = b.x ORDER BY a.x, b.x`
2. `SELECT x FROM b WHERE x NOT IN (SELECT x FROM a)`
3. The row counts of: `a UNION b`, `a UNION ALL b`, `a INTERSECT b`, `a EXCEPT b` (each as `SELECT x FROM ... `), in this order.
4. `SELECT x, SUM(x) OVER (ORDER BY x) AS s, RANK() OVER (ORDER BY x) AS r, LAG(x) OVER (ORDER BY x) AS prev FROM b ORDER BY x`
5. `SELECT date('2025-01-31', '+1 month'), date('2025-03-14', 'start of month', '+1 month', '-1 day'), strftime('%w', '2025-03-14')`

Answers (cover this block while you predict):

```sh
# 1
x     x
----  ----
NULL  NULL
1     NULL
2     2
2     2
3     3
3     3
(6 rows)
# 2
[]    # NULL in the subquery: NOT IN is never true
# 3
[5, 9, 2, 2]
# 4
x  s   r  prev
-  --  -  ----
2  2   1  NULL
3  8   2  2
3  8   2  3
4  12  4  3
(4 rows)
# 5
('2025-03-03', '2025-03-31', '5')
```

Notes on the answers: Question 2 is the classic `NOT IN` trap; question 4 shows that `SUM() OVER (ORDER BY ...)` treats equal values as peers (the default `RANGE` frame); question 5 shows that `+1 month` on January 31 overflows into March (there is no February 31).

## Part C: Find the Bug

Each query runs without an error but gives the wrong answer. Say what is wrong, then fix it. After each buggy query you see the wrong output and what the fixed version should return.

1. "Which customers placed **no order in 2025**?" This returns nothing, but there should be 9.

```py
conn = sqlite3.connect('data/shop.db')

show(conn.execute('''
    SELECT c.customer_id, c.first_name
    FROM customers AS c
    LEFT JOIN orders AS o ON o.customer_id = c.customer_id
    WHERE o.order_date >= '2025-01-01' AND o.order_id IS NULL
'''))
```

```sh
customer_id  first_name
-----------  ----------
(0 rows)
```

   After the fix, the count is `9`:

   ```sh
   (9,)
   ```

2. "Which categories have no products?" Garden has none, but the query returns nothing.

```py
show(conn.execute('''
    SELECT name FROM categories
    WHERE category_id NOT IN (SELECT category_id FROM products)
'''))
```

```sh
name
----
(0 rows)
```

   After the fix you get Garden:

   ```sh
   name
   ------
   Garden
   (1 row)
   ```

3. "How many orders did customer 3 place?" The answer should be 11.

```py
print(conn.execute('''
    SELECT COUNT(*)
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    WHERE o.customer_id = 3
''').fetchone())
```

```sh
(30,)
```

   After the fix:

   ```sh
   (11,)
   ```

4. "Show the running number of orders after each order." On 2024-04-19 two orders were placed, yet they show the same running total.

```py
show(conn.execute('''
    WITH x AS (
        SELECT order_id, order_date,
               COUNT(*) OVER (ORDER BY order_date) AS running_orders
        FROM orders
    )
    SELECT * FROM x WHERE order_date BETWEEN '2024-04-18' AND '2024-04-20' ORDER BY order_id
'''))
```

```sh
order_id  order_date  running_orders
--------  ----------  --------------
29        2024-04-19  30
30        2024-04-19  30
31        2024-04-20  31
(3 rows)
```

   After the fix each order gets its own number:

   ```sh
   order_id  order_date  running_orders
   --------  ----------  --------------
   29        2024-04-19  29
   30        2024-04-19  30
   31        2024-04-20  31
   (3 rows)
   ```

5. "How many orders were placed in March (of any year)?" There are certainly orders in March, so a count of 0 is wrong:

```py
print(conn.execute("SELECT COUNT(*) FROM orders WHERE strftime('%m', order_date) = 3").fetchone())
```

```sh
(0,)
```

   After the fix:

   ```sh
   (27,)
   ```

6. "How many orders were placed in total in 2024 and in 2025?" The answer should be 399... but this says something else.

```py
print(conn.execute('''
    SELECT COUNT(*) FROM (
        SELECT customer_id FROM orders WHERE order_date < '2025-01-01'
        UNION
        SELECT customer_id FROM orders WHERE order_date >= '2025-01-01'
    )
''').fetchone())
```

```sh
(54,)
```

   After the fix:

   ```sh
   (399,)
   ```

## Part D: Explain

Answer in a sentence or two, in your own words.

1. When does an `INNER JOIN` lose rows that a `LEFT JOIN` keeps? Why does `WHERE right_table.column = 5` after a `LEFT JOIN` often turn it into an inner join?
2. A CTE, a subquery in `FROM`, a temporary table: when would you pick each?
3. What is the difference between `GROUP BY customer_id` and `PARTITION BY customer_id`? Name one question that needs each.
4. `ROW_NUMBER`, `RANK` and `DENSE_RANK` on the scores `90, 85, 85, 70`: what does each give, and which one would you use for "top 3 per group" if ties must all be kept?
5. Why does `LAST_VALUE(x) OVER (ORDER BY d)` return the current row's value, and how do you fix it?
6. Explain the "date minus row number" trick for streaks with the dates 1, 2, 3, 5, 6 of a month.
7. A correlated subquery and a window function can both answer "which products cost more than the average of their category?". Which would you choose on a large table, and why?

## Mini-Project: Customer Report

Build a **customer report** for the shop in small steps (the habit of Days 11 and 14). The finished result has one row per customer that has orders (cancelled orders do not count towards spend, but all orders count for the streak), with these columns:

| Column | Meaning |
|---|---|
| `customer_id`, `country` | from `customers` |
| `orders` | number of non-cancelled orders |
| `spend_cents` | total revenue |
| `first_order`, `last_order` | first and last non-cancelled order date |
| `days_idle` | days between `last_order` and `2025-12-31` |
| `country_rank` | rank of the customer's spend inside their country (1 = top, ties share a rank) |
| `tier` | gold / silver / bronze, as in Part A question 9 |
| `best_streak` | the longest run of consecutive order days (all orders, as in Part A question 15) |

Steps:

1. Write one CTE per idea: customer totals, tiers and ranks, streaks. Run each CTE alone before you combine them.
2. Save the result as a temporary table `customer_report` (`CREATE TEMP TABLE ... AS SELECT ...`) so that you can query it many times.
3. Answer three follow-up questions **from the temp table** (no more joins):
   - (a) who is the top customer of every country?
   - (b) how many customers and how much spend per tier?
   - (c) which gold or silver customers had a streak of 3 or more days?

Expected: the report has 54 rows. Here are its 6 biggest spenders:

```sh
customer_id  country  orders  spend_cents  first_order  last_order  days_idle  country_rank  tier  best_streak
-----------  -------  ------  -----------  -----------  ----------  ---------  ------------  ----  -----------
43           France   16      221460       2024-01-02   2025-12-24  7          1             gold  1
18           Germany  19      204568       2024-09-27   2025-12-14  17         1             gold  1
24           Germany  17      204441       2024-06-03   2025-12-26  5          2             gold  1
7            USA      19      196691       2024-12-09   2025-12-28  3          1             gold  1
31           Canada   15      168831       2024-05-08   2025-11-22  39         1             gold  1
53           USA      8       164678       2024-12-24   2025-12-02  29         2             gold  1
(6 rows)
54 rows
```

Follow-ups, from the temp table only:

```sh
# (a) top customer of each country
country  customer_id  spend_cents
-------  -----------  -----------
Canada   31           168831
France   43           221460
Germany  18           204568
UK       34           160774
USA      7            196691
(5 rows)
# (b) tiers
tier    customers  spend_cents
------  ---------  -----------
gold    20         2969247
silver  19         1236931
bronze  15         287095
(3 rows)
# (c) gold or silver with a streak of 3+ days
customer_id  tier    best_streak
-----------  ------  -----------
3            silver  5
12           gold    4
29           silver  3
(3 rows)
```

If your numbers match, you have joined, aggregated, ranked and found streaks in one pipeline: that is what analytical SQL looks like at work. Well done!

CONGRATULATIONS !

[<< Day 18](../18_Day_Window_functions_running/18_window_functions_running.md) | [Day 19 >>](../19_Day_Sqlite3_in_depth/19_sqlite3_in_depth.md)
