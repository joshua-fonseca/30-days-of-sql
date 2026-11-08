<div align="center">
  <h1> 30 Days Of SQL: Review 2 - Combining Data (Days 11-16)</h1>
</div>

[<< Day 16](../16_Day_Dates_and_times/16_dates_and_times.md) | [Day 17 >>](../17_Day_Window_functions_ranking/17_window_functions_ranking.md)

- [Review 2](#review-2)
  - [How to Use This Review](#how-to-use-this-review)
  - [Part A: Write the Query](#part-a-write-the-query)
  - [Part B: Predict the Output](#part-b-predict-the-output)
  - [Part C: Find the Bug](#part-c-find-the-bug)
  - [Part D: Explain](#part-d-explain)
  - [Mini-Project: Customer Health Report](#mini-project-customer-health-report)

# Review 2

No new material today. This is a checkpoint for Days 11 to 16: joins, subqueries, CTEs and temporary tables, set operations, conditional aggregation and dates. The problems are mixed on purpose and do not say which day they come from, and a few lean on
Days 1 to 10 as well (filtering, grouping, `CASE`, `COALESCE`...). If something feels shaky, go back to that day before starting Part 3: window functions use joins and CTEs all the time.

## How to Use This Review

- Use `data/shop.db` for the shop problems and your normalized `00_practice/library.db` for the library ones (`authors`, `books`, `members`, `loans`).
- Where a problem says "today", use the fixed date `TODAY = '2025-03-14'` as a parameter.
- Try each problem **before** looking at the expected output. For Part B, write your prediction first, then run it.
- Money is in integer cents; show dollars with `format('%.2f', cents / 100.0)`.
- Order your results exactly as asked, so they can be compared with the expected output.
- Put your work in `00_practice/review_2.py`.

## Part A: Write the Query

1. List the products of the **Books** category with their price in dollars, most expensive first, ties by name.

   ```sh
   product                   price
   ------------------------  -----
   The Pragmatic Programmer  49.99
   SQL for Data Analysis     44.99
   Python Crash Course       39.99
   Cookbook Basics           24.99
   Sci-Fi Anthology          17.99
   Mystery Novel             14.99
   (6 rows)
   ```

2. List the first 5 orders placed in March 2025 (by date, then order id) with the customer's full name, and say how many orders there were in the month in total.

   ```sh
   order_id  order_date  customer
   --------  ----------  ----------
   214       2025-03-04  Isla Brown
   215       2025-03-05  Sam Wilson
   216       2025-03-05  Sam Khan
   217       2025-03-08  Freya Kim
   218       2025-03-20  Lena Scott
   (5 rows)
   (12,)
   ```

3. For every category, including empty ones, show the number of products, fewest first, ties by category name.

   ```sh
   category        products
   --------------  --------
   Garden          0
   Clothing        5
   Grocery         5
   Toys            5
   Books           6
   Electronics     6
   Home & Kitchen  6
   Sports          6
   (8 rows)
   ```

4. Show the 3 biggest-spending customers among those whose total spend (non-cancelled orders) is **above the average** customer spend. Print how many customers are above average as well.

   ```sh
   customer     spend
   -----------  -------
   Lena Green   2214.60
   Amara Kim    2045.68
   Ines Martin  2044.41
   (3 rows)
   (26,)
   ```

5. List Ada Lovelace and everybody who works under her, directly or not, with their title and how many levels below her they are.

   ```sh
   name               title            depth
   -----------------  ---------------  -----
   Ada Lovelace       VP Sales         0
   Margaret Hamilton  Sales Manager    1
   Hedy Lamarr        Sales Associate  2
   Katherine Johnson  Sales Associate  2
   (4 rows)
   ```

6. For every category (including the empty one) show the revenue in dollars of non-cancelled orders in 2024 and in 2025, side by side, in category order.

   ```sh
   category        y2024    y2025
   --------------  -------  -------
   Books           3567.28  4296.82
   Clothing        2277.55  1947.75
   Electronics     2621.26  6144.17
   Garden          0.00     0.00
   Grocery         1812.52  1883.85
   Home & Kitchen  2268.92  2690.51
   Sports          3020.02  5943.16
   Toys            2503.65  3589.29
   (8 rows)
   ```

7. Library: for each member, the number of loans and the number of books they still have out. Members with no loans must appear. Most loans first, ties by name.

   ```sh
   name          loans  still_out
   ------------  -----  ---------
   Alice Nguyen  3      1
   Bruno Silva   3      2
   Chloe Martin  2      1
   Dev Patel     2      2
   Elena Rossi   0      0
   (5 rows)
   ```

8. Which customers ordered in 2024 but **not** at all in 2025? Use a set operation. Show their full names alphabetically.

   ```sh
   customer
   ------------
   Ethan Nguyen
   Mason Thomas
   Olivia White
   (3 rows)
   ```

9. The 5 customers who have been silent the longest: the customer, the date of their last order and the number of days between that date and today. Longest silence first, ties by name. Only customers who have ordered.

   ```sh
   customer      last_order  days_silent
   ------------  ----------  -----------
   Ethan Nguyen  2024-09-23  172
   Olivia White  2024-11-15  119
   Mason Thomas  2024-11-26  108
   Ethan Martin  2025-02-01  41
   Isla Brown    2025-03-04  10
   (5 rows)
   ```

## Part B: Predict the Output

Create two tiny tables and write down what each query returns, then run it.

```py
t = sqlite3.connect(':memory:')
t.execute('CREATE TABLE a (x INTEGER)')
t.execute('CREATE TABLE b (y INTEGER)')
t.executemany('INSERT INTO a VALUES (?)', [(1,), (2,), (2,), (None,)])
t.executemany('INSERT INTO b VALUES (?)', [(2,), (3,), (None,)])
```

1. `SELECT COUNT(*) FROM a JOIN b ON a.x = b.y`
2. `SELECT COUNT(*), COUNT(b.y) FROM a LEFT JOIN b ON a.x = b.y`
3. `SELECT x FROM a WHERE x NOT IN (SELECT y FROM b)`
4. The number of rows of `SELECT x FROM a UNION SELECT y FROM b`, and of the same with `UNION ALL`.
5. `SELECT date('2025-01-31', '+1 month'), date('2025-03-14', 'start of month', '-1 day'), strftime('%w', '2025-03-14')`
6. `SELECT x, (SELECT COUNT(*) FROM b WHERE b.y >= a.x) FROM a ORDER BY x`

The answers, to check yourself after you have run them (do not peek before you've made your own predictions):

```sh
(2,)                                             # 1  the two 2s in a match the one 2 in b; NULL never matches
(4, 2)                                           # 2  all 4 rows of a are kept, only two found a partner
[]                                               # 3  the NULL in b ruins NOT IN
(4,) (7,)                                        # 4  UNION: 1, 2, 3, NULL (NULLs count as equal)
('2025-03-03', '2025-02-28', '5')                # 5  Feb 31 rolls over to March 3; 5 = Friday
[(None, 0), (1, 2), (2, 2), (2, 2)]              # 6  correlated; NULL compares with nothing, so the count is 0
```

## Part C: Find the Bug

Each snippet runs without an error and gives a wrong answer. Say what is wrong, then fix it.

1. The goal: one row for each of the 60 customers, with the number of their delivered orders from 2025 (zero for most). The result has only 50 rows.

   ```sql
   SELECT c.customer_id, COUNT(o.order_id) AS delivered_2025
   FROM customers AS c
   LEFT JOIN orders AS o ON o.customer_id = c.customer_id
   WHERE o.status = 'delivered' AND o.order_date >= '2025-01-01'
   GROUP BY c.customer_id
   ```

   ```sh
   (50,)
   (60,)
   ```

2. The goal: the average order value in cents. The query prints 4883, but the correct answer is 12044.

   ```sql
   SELECT SUM(i.quantity * i.unit_price_cents) / COUNT(*)
   FROM orders AS o JOIN order_items AS i ON i.order_id = o.order_id
   ```

   ```sh
   (4883,) (12044,)
   (984,) (399,)
   ```

3. The goal: the number of categories that have no products. We expect 1 (Garden), but the query prints 0.

   ```sql
   SELECT COUNT(*) FROM categories WHERE category_id NOT IN (SELECT category_id FROM products)
   ```

   Fix it and print the new answer.
4. The table `events (at TEXT)` holds `'2025-03-13 23:59:59'`, `'2025-03-14 00:00:00'`, `'2025-03-14 18:45:00'` and `'2025-03-15 08:00:00'`. The query below should count the events that happened on 14 March, but returns 0. Why? Fix it in two ways.

   ```sql
   SELECT COUNT(*) FROM events WHERE at BETWEEN '2025-03-14' AND '2025-03-14'
   ```

   ```sh
   (0,)
   (2,)
   (2,)
   ```

## Part D: Explain

Answer in a sentence or two, in your own words.

1. A `LEFT JOIN` with a condition on the right table: what is the difference between putting it in `ON` and in `WHERE`?
2. What makes a subquery *correlated*, and why can it be slow on a big table?
3. When would you choose a temporary table over a CTE, and a CTE over a temporary table?
4. What is the difference between `UNION` and `UNION ALL`? Which one is the safe default, and why?
5. Why should dates be stored as ISO-8601 text in SQLite, and what happens if you store them as `3/14/2025`?
6. What are the two parts of a recursive CTE, and what happens if you forget the stop condition?

## Mini-Project: Customer Health Report

Build a report on the health of the shop's customer base as of today (`2025-03-14`), using a chain of CTEs:

1. `order_totals`: the total of every non-cancelled order.
2. `per_customer`: for **every** customer (including those who never ordered), their name, country, signup date, date of first order, date of last order, number of orders and total spend.
3. `labelled`: add a `status`: `never ordered` (no orders), `active` (last order within 90 days of today) or `dormant`.

Then answer, with a query on `labelled`:

- For each status: how many customers, their total spend in dollars and the average number of days between signup and first order (rounded; `-` if there are none).
- The 3 dormant customers who spent the most, with country, orders, spend and last order date.

With the data in `solutions/review_2.py` you get:

```sh
status         customers  total_spend  avg_days_to_first_order
-------------  ---------  -----------  -----------------------
active         50         44412.38     139
never ordered  6          0.00         -
dormant        4          520.35       281
(3 rows)
customer      country  orders  spend   last_order
------------  -------  ------  ------  ----------
Mason Thomas  USA      3       211.44  2024-11-26
Ethan Nguyen  UK       2       179.96  2024-09-23
Olivia White  USA      1       94.98   2024-11-15
(3 rows)
```

(Hint: pass `today` as a named parameter. One value is used in two places in the CTE. A `LEFT JOIN` keeps the customers who never ordered, and `COALESCE` turns their `NULL` spend into 0.)

Part 3 starts tomorrow: window functions, the most powerful tool in analytic SQL. Everything from today (joins, CTEs, dates) will be in use all the time.

CONGRATULATIONS !

[<< Day 16](../16_Day_Dates_and_times/16_dates_and_times.md) | [Day 17 >>](../17_Day_Window_functions_ranking/17_window_functions_ranking.md)
