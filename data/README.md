# Data

## Source datasets

Copied unchanged from an open-source teaching repository by Asabeneh (<https://github.com/Asabeneh/30-Days-Of-Python>). Credit and thanks to the author.

| File | Rows | Used for |
|---|---|---|
| `countries_data.json` | 250 | Loading JSON, normalization (the `languages` list), joins, DuckDB `unnest` |
| `hacker_news.csv` | 20,099 | `LIKE` filtering, aggregates, dates (non-ISO `8/4/2016 11:52`), window functions |
| `HN_posts_year_to_Sep_26_2016.csv` | ~290,000 | Performance, DuckDB querying files directly |
| `F500.csv` | 500 | Cleaning dirty data: `;` delimiter, `"$485,873"` strings, `"2,300,000"` employee counts |
| `fortune1000_final.csv` | 1,000 | Sectors and states, ranking inside a group, DuckDB |
| `weight-height.csv` | 10,000 | Aggregates by gender |

## Built for this course

### `shop.sql` / `shop.db`

A small online shop. `shop.sql` is the frozen source of truth (generated once by `tools/generate_shop_sql.py`, seed 30).
`shop.db` is built from it by `uv run python tools/build_shop_db.py` and is not committed.

| Table | Rows | Notes |
|---|---|---|
| `customers` | 60 | |
| `categories` | 8 | |
| `products` | 40 | prices in **integer cents** (`price_cents`) |
| `orders` | 399 | 2024-01-02 to 2025-12-31 |
| `order_items` | 984 | `unit_price_cents` is the price paid at the time |
| `employees` | 15 | four levels, `salary_cents` |
| `newsletter_signups` | 20 | no constraints on purpose |

**Deliberate quirks.** Lessons rely on all of these, and `tools/verify_shop.py` checks them:

- 6 customers have **no orders** (anti-joins, Day 12).
- 4 products were **never ordered**. 1 product has a NULL `category_id`. The **Garden** category has no products.
- 3 customers have a NULL `email` and 7 have a NULL `city` (NULL handling, Days 5 and 6).
- Repeated first names ("Sam" appears 5 times) and repeated cities (`DISTINCT`, `GROUP BY`).
- About 1 in 6 `order_items.unit_price_cents` differ from the product's current price (prices change over time).
- The CEO's `manager_id` is NULL (self join, recursive CTE).
- Orders are seasonal, with far more in November and December.
- Customers 3, 12 and 29 order on **consecutive days** (streaks for the gaps-and-islands exercise, Day 18).
- `newsletter_signups` has 20 rows but only 12 distinct people: exact duplicates, case-only differences
  and stray whitespace (the duplicates lesson, Day 17).

### `big_events.csv` (not committed)

1,000,000 seeded rows: `event_id, user_id, event_type, ts, amount`. Create it with
`uv run python tools/make_big_events.py` (about 6 seconds, 41 MB). Used on Days 21, 23 and 24.
