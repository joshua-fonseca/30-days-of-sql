<div align="center">
  <h1> 30 Days Of SQL: Review 5 - DuckDB (Days 23-26)</h1>
</div>

[<< Day 26](../26_Day_Duckdb_with_dataframes/26_duckdb_with_dataframes.md) | [Day 27 >>](../27_Day_Security_and_best_practices/27_security_and_best_practices.md)

- [Review 5](#review-5)
  - [How to Use This Review](#how-to-use-this-review)
  - [Part A: Write the Query](#part-a-write-the-query)
  - [Part B: Predict the Output](#part-b-predict-the-output)
  - [Part C: Find the Bug](#part-c-find-the-bug)
  - [Part D: Explain](#part-d-explain)
  - [Mini-Project: One Report from Three Sources](#mini-project-one-report-from-three-sources)

# Review 5

No new material today. This is a checkpoint for Days 23 to 26: DuckDB basics, querying files, friendly SQL and nested types, and DuckDB with DataFrames and SQLite. The problems are mixed, and the
earlier SQL of Parts 1 to 4 is fair game too. If something feels shaky, go back to that day before moving on.

## How to Use This Review

- Use the DuckDB shop from Day 23, `00_practice/shop.duckdb`, the files in `data/` and `data/big_events.csv`.
- Try each problem **before** looking at the expected output. For Part B, write your prediction first, then run it.
- Put your work in `00_practice/review_5.py`. Add `ORDER BY` tie-breakers: DuckDB does not promise a row order.

## Part A: Write the Query

1. How many countries in `data/countries_data.json` have more than 50 million people and list `English` among their languages? List them, most populous first.

   ```sh
   [(8,)]
   name                                                  population
   ----------------------------------------------------  ----------
   India                                                 1295210000
   United States of America                              323947000
   Pakistan                                              194125062
   Nigeria                                               186988000
   Philippines                                           103279800
   United Kingdom of Great Britain and Northern Ireland  65110000
   South Africa                                          55653654
   Tanzania, United Republic of                          55155000
   (8 rows)
   ```

2. In the shop, how many customers have never placed an order, split by signup year? (Use `NOT EXISTS`.)

   ```sh
   year  customers
   ----  ---------
   2023  4
   2024  2
   (2 rows)
   ```

3. Straight from `data/big_events.csv`, report per month the number of events and the percentage of them that are purchases (2 decimals). Show the first 3 months.

   ```sh
   month    events  purchase_pct
   -------  ------  ------------
   2025-01  85328   6.87
   2025-02  76371   6.94
   2025-03  85324   6.93
   (3 rows)
   ```

4. Show the number of orders per customer country (rows) and status (columns) with `PIVOT`.

   ```sh
   country  cancelled  delivered  pending  shipped
   -------  ---------  ---------  -------  -------
   Canada   5          76         2        2
   France   8          63         2        1
   Germany  2          51         1        3
   UK       2          73         3        5
   USA      7          83         7        3
   (5 rows)
   ```

5. For each customer country, find the customer who spent the most (cents, cancelled orders included; ties by customer id). Use `QUALIFY`.

   ```sh
   country  customer     spend_cents
   -------  -----------  -----------
   Canada   Priya Brown  215530
   France   Lena Green   223857
   Germany  Ines Martin  218207
   UK       Liam Walker  160774
   USA      Sam Wilson   205487
   (5 rows)
   ```

6. How many different languages are spoken in the countries that use the Euro? Expected: `[(26,)]`.

7. A pandas DataFrame holds sales targets: `USA` 12000, `Canada` 11000, `France` 9000, `UK` 9000, `Germany` 6000 (dollars). Join it to the shop's revenue per customer country (cancelled orders excluded) and show whether each country hit its target.

   ```sh
   country  revenue   target_dollars  hit
   -------  --------  --------------  -----
   Canada   9762.49   11000           False
   France   8401.72   9000            False
   Germany  6070.93   6000            True
   UK       7982.3    9000            False
   USA      12715.29  12000           True
   (5 rows)
   ```

8. (Hard.) A DataFrame `rates` has the euro-dollar rate and the date it came into force: `2024-01-01` 1.08, `2024-07-01` 1.07, `2025-01-01` 1.04, `2025-07-01` 1.17 (make the dates real datetimes with `pd.to_datetime`). With an `ASOF JOIN`, find the rate in force on each order's date and count the orders per rate.

   ```sh
   rate_since           usd_per_eur  orders
   -------------------  -----------  ------
   2024-01-01 00:00:00  1.08         57
   2024-07-01 00:00:00  1.07         124
   2025-01-01 00:00:00  1.04         94
   2025-07-01 00:00:00  1.17         124
   (4 rows)
   ```

## Part B: Predict the Output

Write down what you think each returns, then run it.

1. `SELECT 7 / 2, 7 // 2, CAST(2.5 AS INTEGER), CAST(-2.5 AS INTEGER)`
2. `SELECT [1, 2, 3][2], [1, 2, 3][-1], len([1, 2, 3, 4][2:3]), list_filter([1, 2, 3, 4], lambda x: x % 2 = 0)`
3. With `sales(month, product, units)` holding `('jan','tea',3), ('jan','cake',1), ('feb','tea',4), ('jan','tea',2)`: `PIVOT sales ON product USING SUM(units) GROUP BY month ORDER BY month DESC`
4. `SELECT x FROM (VALUES (2), (NULL), (1)) AS t(x) ORDER BY x DESC`
5. On the same `sales` table: `SELECT product, units, RANK() OVER (ORDER BY units DESC) AS rnk FROM sales QUALIFY rnk <= 2 ORDER BY rnk, product`

```sh
[(3.5, 3, 3, -3)]            # 1   CAST rounds away from zero
[(2, 3, 2, [2, 4])]          # 2   lists start at 1; the slice [2:3] has 2 elements

month  cake  tea             # 3
-----  ----  ---
jan    1     5
feb    NULL  4
(2 rows)

[(2,), (1,), (None,)]        # 4   NULL sorts last in DuckDB, even descending

product  units  rnk         # 5   tea 4 first, then tea 3
-------  -----  ---
tea      4      1
tea      3      2
(2 rows)
```

## Part C: Find the Bug

Each snippet runs but gives the wrong answer (or a surprise). Say what is wrong, then fix it.

1. `read_csv('data/hacker_news.csv', dateformat = '%m/%d/%Y %H:%M')` should give timestamps, but `created_at` shows `2016-08-04` with no time.
2. `SELECT name, city, COUNT(*) AS people FROM df GROUP BY ALL` should count people per city and returns a count of 1 on every row.
3. `SELECT COUNT(*) FROM (VALUES (5), (7)) AS t(price) WHERE price > ALL (SELECT x FROM (VALUES (1)) AS s(x) WHERE x > 100)` returns 2, but "no one is dearer than the nothing" was expected.
4. `CREATE TABLE app.t1 AS SELECT customer_id, SUM(quantity * unit_price_cents) AS spend ...` into an attached SQLite file; later `typeof(spend)` in SQLite says `text`.

```sh
# C1: should be timestampformat, not dateformat (dateformat is for DATE-only columns and drops the time)
created_at
-------------------
2016-08-04 11:52:00
2016-06-23 22:20:00
# C2: name is in the select list, so GROUP BY ALL groups by it; remove name -> Oslo 2, Rome 2
# C3: > ALL over an empty set is true for every row; the MAX version gives [(0,)]
# C4: SUM gives a HUGEINT, which SQLite stores as text: CREATE TABLE t1(customer_id BIGINT, spend VARCHAR);
# use CAST(SUM(...) AS BIGINT) and the column becomes BIGINT (typeof -> integer)
```

## Part D: Explain

Answer in a sentence or two, in your own words.

1. What is the difference between OLTP and OLAP work, and why is a column store faster for `AVG(age)` over millions of rows?
2. You write `SELECT * FROM df` where `df` is a pandas DataFrame. How does DuckDB know what `df` is?
3. Give three reasons why Parquet is a better format than CSV for analysis.
4. When do you query a file directly, when create a view over it, and when `CREATE TABLE AS`?
5. How does `QUALIFY` differ from `WHERE` and `HAVING`?

## Mini-Project: One Report from Three Sources

Build a regional report that combines **three different sources in one query**:

- the shop in `data/shop.db`, attached read-only (customers, orders, order items),
- a pandas DataFrame `segments` mapping `country` to `region`: USA and Canada are `Americas`; France, UK and Germany are `Europe`,
- `data/big_events.csv`, converted once to a Parquet file (pretend that an event's `user_id` is the shop's `customer_id`).

For each region report the number of customers, the number of orders and the revenue in dollars (cancelled orders excluded, 2 decimals), and the number of events and of purchase events of those customers.
Get the result as a Polars DataFrame, write it to CSV and read the CSV back with DuckDB to check it.

```sh
shape: (2, 6)
┌──────────┬───────────┬────────┬──────────┬────────┬───────────┐
│ region   ┆ customers ┆ orders ┆ revenue  ┆ events ┆ purchases │
│ ---      ┆ ---       ┆ ---    ┆ ---      ┆ ---    ┆ ---       │
│ str      ┆ i64       ┆ i64    ┆ f64      ┆ i64    ┆ i64       │
╞══════════╪═══════════╪════════╪══════════╪════════╪═══════════╡
│ Americas ┆ 30        ┆ 173    ┆ 22477.78 ┆ 643    ┆ 34        │
│ Europe   ┆ 30        ┆ 202    ┆ 22454.95 ┆ 582    ┆ 48        │
└──────────┴───────────┴────────┴──────────┴────────┴───────────┘
[('Americas', 30, 173, 22477.78, 643, 34), ('Europe', 30, 202, 22454.95, 582, 48)]
```

Next up is Part 6: craft. Day 27 is about writing SQL that is safe, tidy and tested.

CONGRATULATIONS !

[<< Day 26](../26_Day_Duckdb_with_dataframes/26_duckdb_with_dataframes.md) | [Day 27 >>](../27_Day_Security_and_best_practices/27_security_and_best_practices.md)
