<div align="center">
  <h1> 30 Days Of SQL: Day 29 - Project 2: Analytics Report</h1>
</div>

[<< Day 28](../28_Day_Project_library_cli/28_project_library_cli.md) | [Day 30 >>](../30_Day_Conclusions/30_conclusions.md)

- [Day 29](#day-29)
  - [The Project](#the-project)
  - [Requirements](#requirements)
  - [The Pipeline](#the-pipeline)
  - [Milestones](#milestones)
    - [Milestone 1: Stage the Data as Parquet](#milestone-1-stage-the-data-as-parquet)
    - [Milestone 2: Cross-Check with SQLite](#milestone-2-cross-check-with-sqlite)
    - [Milestone 3: The Ten Questions](#milestone-3-the-ten-questions)
    - [Milestone 4: Write the Report](#milestone-4-write-the-report)
    - [Milestone 5: Make It Repeatable](#milestone-5-make-it-repeatable)
  - [Expected Key Numbers](#expected-key-numbers)
  - [The Finished Report](#the-finished-report)
  - [Stretch Goals](#stretch-goals)
  - [Checking Your Work](#checking-your-work)

# Day 29

The second project is a **business review** of the shop, the kind of report an analyst delivers every month. You will use both engines you know: **DuckDB** for the analysis (it is fast, friendly and reads Parquet directly) and **SQLite** to prove the numbers are right. The result is a Markdown file written from Python.

Again a spec: requirements, milestones, hints, and the numbers you must reproduce. The reference solution is `solutions/day_29.py`; try first, peek later.

> The plan for this course also offered a second option, an analysis of the 47 MB Hacker News file. It is a good *stretch goal* once the shop review is done (see the end of the lesson).

## The Project

Management asks: *How is the business doing? Where does the money come from? Who are our best customers? Do customers come back?* You answer with ten numbered questions, each a SQL query, collected into one readable report.

**You will practise:** `ATTACH ... (TYPE sqlite)` and CTAS/`COPY` (Days 24, 26), joins (Day 11), window functions (Days 17-18), conditional aggregation with `FILTER` (Day 15), dates (Days 16, 23), DuckDB's `GROUP BY ALL`/`QUALIFY` (Day 25) where they help, Parquet (Day 24), and verification of results across two engines (Day 23).

## Requirements

- **Definition of revenue:** the sum of `quantity * unit_price_cents` over the lines of orders whose status is **not** `cancelled`. Use `unit_price_cents` (the price actually charged), not `products.price_cents` (today's price). Keep money in **integer cents** inside queries and format it as dollars only when writing the report.
- **Input:** `data/shop.db` (SQLite), never modified (attach it read-only).
- **Intermediate format:** one denormalized Parquet file, one row per order line.
- **Analysis engine:** DuckDB, reading the Parquet file.
- **Cross-check:** the headline numbers recomputed with `sqlite3` on the original database must be identical.
- **Output:** a Markdown report with one section per question and a Markdown table in each, written from Python with `pathlib`.
- **Deterministic:** every ranking has a tie-breaker; running the program twice gives the identical file.
- **No SQL built from user input** (there is none, but keep the habit): any value that changes is a parameter.

## The Pipeline

```
data/shop.db ──ATTACH (read-only)──► DuckDB ──COPY──► order_lines.parquet
     │                                                       │
     └──sqlite3: independent totals ──┐                      ▼
                                      ├──► assert equal    10 queries ──► report.md
                                      DuckDB totals ◄───────┘
```

Why Parquet in the middle? It makes the analysis independent of the source: the queries only know one flat, typed table, and you can re-run them without the shop database. The file is small, compressed and typed (real `DATE` columns, as on Day 24).

## Milestones

### Milestone 1: Stage the Data as Parquet

In DuckDB, attach `shop.db` read-only and write one Parquet file with **one row per order line** and these columns (use `COALESCE` for products without a category, and real `DATE`s):

| column | meaning |
|---|---|
| `order_id`, `order_date` (DATE), `status` | from `orders` |
| `customer_id`, `customer` (first + last name), `country`, `signup_date` (DATE) | from `customers` |
| `product_id`, `product`, `category` | from `products`/`categories`; `'Uncategorized'` when the category is NULL |
| `quantity`, `unit_price_cents` | from `order_items` |
| `line_cents` | `quantity * unit_price_cents` |

Hints: `ATTACH 'data/shop.db' AS shop (TYPE sqlite, READ_ONLY)` (the sqlite extension downloads on first use, so you need internet once; if you cannot, build the table with the `load_shop` function from Day 23 instead). Use `LEFT JOIN` for the category, since one product has none. `COPY (SELECT ...) TO 'order_lines.parquet' (FORMAT parquet)`. Add an `ORDER BY` so the file is reproducible.

**Acceptance:** reading the file back gives **984 rows** (the shop has 984 order lines; check: `SELECT count(*) FROM read_parquet('order_lines.parquet')`).

### Milestone 2: Cross-Check with SQLite

Before trusting any number, compute the three headline figures twice: from the Parquet file with DuckDB, and from `shop.db` with plain `sqlite3`:

1. number of non-cancelled orders,
2. number of distinct customers who placed one,
3. revenue in cents.

Compare the two tuples with `assert`.

**Acceptance:** both engines print the same tuple:

```sh
duckdb: (375, 54, 4493273)
sqlite: (375, 54, 4493273)
```

If they differ, you have a bug in your staging query (a lost row, a duplicated join, an inner join that dropped the uncategorized product). Find it before moving on. This habit, *reconcile with a second source*, catches more mistakes than anything else in analytics.

### Milestone 3: The Ten Questions

Write one query per question against `read_parquet('order_lines.parquet')`. All except Q7 use only non-cancelled orders. Money columns are cents.

| # | Question | Hint |
|---|---|---|
| Q1 | Headline: orders, buyers, revenue, average order value (cents, rounded) | `count(DISTINCT order_id)` |
| Q2 | Revenue by year, with the growth in % over the previous year | `LAG` over the yearly totals |
| Q3 | Monthly revenue in 2025 with the month-over-month change in % | `strftime(order_date, '%Y-%m')`, `LAG` |
| Q4 | Revenue by category with each category's share of the total in % | `sum(sum(x)) OVER ()`; includes `Uncategorized` |
| Q5 | The 5 best-selling products by revenue (with units sold) | tie-break by product name |
| Q6 | The 5 best customers by revenue, with country and number of orders | group by `customer_id` |
| Q7 | Order status mix, **including cancelled**, with % of all orders | count orders, not lines |
| Q8 | The top 5 countries by revenue, with the number of buyers | |
| Q9 | Repeat customers: buyers, buyers with 2+ orders, their %, average orders per buyer | `count(*) FILTER (WHERE ...)` |
| Q10 | Signup cohorts: for each signup quarter, how many buyers placed their first order within 90 days of signing up | `first_order - signup_date <= 90` on `DATE`s |

Also list the **products that were never ordered**. That one needs the source tables (they are not in the Parquet file, because they have no order lines), so ask `shop.products` / `shop.order_items` through the attached database with `NOT EXISTS`.

A few traps to watch for:

- `count(*)` on order lines counts *lines*; orders need `count(DISTINCT order_id)`.
- A percentage of the total in one query: a window over the grouped result, `sum(sum(line_cents)) OVER ()`.
- Integer vs decimal division: DuckDB's `/` is always a decimal division (Day 23), but multiply by `100.0` anyway to make the intent obvious.
- Q10's cohorts of customers who signed up in 2023 have no first-order-within-90-days at all, because the order history begins on 2024-01-01. That is an honest finding, not a bug: say so in the report.

### Milestone 4: Write the Report

Collect the results as `(title, headers, rows)` and write `report.md` with:

- a title and a one-line definition of revenue,
- one `##` section per question, each with a Markdown table (`| a | b |` header, `|---|---|` separator),
- cents formatted as dollars with thousands separators (`f"${cents / 100:,.2f}"`), columns named without the `_cents` suffix,
- a final section "Products never ordered".

**Acceptance:** the first lines of the file are exactly:

```sh
# Shop business review

Revenue counts every order that was not cancelled. Money is shown in dollars.

## Q1 Headline numbers

| orders | buyers | revenue | avg_order |
|---|---|---|---|
| 375 | 54 | $44,932.73 | $119.82 |

## Q2 Revenue by year

| year | revenue | growth_pct |
|---|---|---|
| 2024 | $18,283.24 |  |
| 2025 | $26,649.49 | 45.8 |
```

The whole file is 108 lines. A NULL (the growth of the first year) is an empty cell.

### Milestone 5: Make It Repeatable

Put the code in functions (`build_parquet()`, `questions()`, `write_report()`), and a `main()` that rebuilds everything from scratch. Re-running must give a byte-identical report, which proves your `ORDER BY`s are complete. Compare with a hash: `hashlib.sha256(path.read_bytes()).hexdigest()` before and after a second run.

## Expected Key Numbers

Check your answers against these. (All from the reference run; money in cents.)

**Q1:** 375 orders, 54 buyers, 4,493,273 cents of revenue (**$44,932.73**), average order 11,982 cents (**$119.82**).

**Q2:**

```sh
year  revenue_cents  growth_pct
2024  1828324        NULL
2025  2664949        45.8
```

**Q3:** the best month of 2025 is December (432,648 cents, +25.4 % over November); the weakest is February (120,411 cents, -33.4 % against January). The big spikes are May (+108.1 %) and then November and December, the seasonal pattern the shop was built with. The full list:

```sh
month    revenue_cents  mom_pct
2025-01  180703         NULL
2025-02  120411         -33.4
2025-03  180877         50.2
2025-04  160987         -11.0
2025-05  335031         108.1
2025-06  174489         -47.9
2025-07  158397         -9.2
2025-08  141552         -10.6
2025-09  192813         36.2
2025-10  242033         25.5
2025-11  345008         42.5
2025-12  432648         25.4
```

**Q4:**

```sh
category        revenue_cents  share_pct
Sports          896318         19.9
Electronics     876543         19.5
Books           786410         17.5
Toys            609294         13.6
Home & Kitchen  495943         11.0
Clothing        422530         9.4
Grocery         369637         8.2
Uncategorized   36598          0.8
```

**Q5:**

```sh
product                      units  revenue_cents
Running Shoes                70     627230
The Pragmatic Programmer     83     414667
Denim Jacket                 40     317560
Bluetooth Speaker            49     291251
Noise-Cancelling Headphones  17     245233
```

Note that *The Pragmatic Programmer* sells more units (83) than any other product in this list, but earns less than *Running Shoes*.

**Q6:**

```sh
customer      country  orders  revenue_cents
Lena Green    France   16      221460
Amara Kim     Germany  19      204568
Ines Martin   Germany  17      204441
Sam Wilson    USA      19      196691
Freya Nguyen  Canada   15      168831
```

**Q7:**

```sh
status     orders  share_pct
delivered  346     86.7
cancelled  24      6.0
pending    15      3.8
shipped    14      3.5
```

**Q8:**

```sh
country  buyers  revenue_cents
USA      15      1271529
Canada   10      976249
France   9       840172
UK       14      798230
Germany  6       607093
```

**Q9:** 54 buyers, 51 of them bought at least twice (**94.4 %**), 6.94 orders per buyer on average.

**Q10:**

```sh
cohort   buyers  ordered_in_90_days
2023-Q2  6       0
2023-Q3  8       0
2023-Q4  5       1
2024-Q1  12      8
2024-Q2  8       6
2024-Q3  4       3
2024-Q4  9       7
2025-Q1  2       2
```

**Never ordered:** `Beanie`, `Camping Hammock`, `Jump Rope`, `Mystery Box`.

Interesting things a report writer would add as commentary: revenue grew 45.8 % in 2025, almost 40 % of the money comes from two categories (Sports and Electronics are 39.4 % together), and almost every buyer comes back, so the business depends on retention more than on acquisition. Four products never sold, and *Camping Hammock* is the second-priciest Sports item: a candidate for a promotion or for removal.

## The Finished Report

Running the reference solution (`uv run python solutions/day_29.py`) prints the four milestones and writes `solutions/_work/d29_report.md`. The first lines of its output (the rest are the question results from Milestone 3):

```sh
# Milestone 1: parquet rows
984
# Milestone 2: cross-check
duckdb: (375, 54, 4493273)
sqlite: (375, 54, 4493273)
```

## Stretch Goals

1. **Hacker News (option b).** Do the same pipeline on `data/HN_posts_year_to_Sep_26_2016.csv`: convert it to Parquet (Day 24), then answer: the best hour of day to post (by average points), the top 10 domains, how many authors posted more than 100 times, and the growth in posts per month. Time the same aggregation in SQLite and in DuckDB (Day 23) and describe what you see in words.
2. **A chart.** Save the monthly revenue as a PNG with a plotting library of your choice and link it from the report (this is the one place where you may need a library beyond what the course installed).
3. **Retention table.** Replace Q10 with a classic cohort grid: first-order month in rows, months-since-first-order in columns, share of the cohort active (`PIVOT`, Day 25).
4. **Customer segments.** Use `NTILE` (Day 17) to split customers into four spend quartiles and report each segment's share of revenue.
5. **Round trip.** Store the final result tables back in a new SQLite file with `ATTACH ... (TYPE sqlite)` and `CREATE TABLE ... AS` (Day 26).
6. **Parameterize the report.** Take the year from the command line with `argparse` (Day 28) and pass it to the queries as a `$year` parameter.

## Checking Your Work

- [ ] The Parquet file has 984 rows and real `DATE` columns.
- [ ] DuckDB and SQLite agree on `(375, 54, 4493273)`, asserted in code.
- [ ] All ten questions match the key numbers above.
- [ ] Money is cents in the queries, dollars only in the Markdown.
- [ ] Every `ORDER BY` has a tie-breaker; two runs give identical files.
- [ ] You can explain why Parquet is a good middle format and why the cross-check is worth five lines of code.

You took raw tables to a finished report with two engines, a file format in between and a safety check at the end. That is what data work looks like in practice.

CONGRATULATIONS !

[<< Day 28](../28_Day_Project_library_cli/28_project_library_cli.md) | [Day 30 >>](../30_Day_Conclusions/30_conclusions.md)
