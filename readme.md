# 30 Days Of SQL

A self-paced SQL course that runs entirely from Python. You write SQL, run it with Python, and learn the same ideas in
two engines: **`sqlite3`** (built into Python) for the first 22 days, then **DuckDB** for analytics.

Each lesson explains one idea at a time, shows a runnable example with its output, then gives you exercises at three levels:
**Level 1** is quick practice, **Level 2** combines ideas, and **Level 3** uses real data and shows what your output should look like.

> **"30 days" is a guide, not a deadline.** A "day" is one lesson. Some take an hour and some take a weekend.
> Go at your own pace, and don't skip the exercises.

You should already know basic Python: functions, loops, comprehensions, files, `json`/`csv`, exceptions and classes.

## Lessons

### Part 1: SQL foundations with `sqlite3`

| # Day | Topics |
|------|:--------------------------------------------------:|
| 01 | [Introduction](./01_Day_Introduction/01_introduction.md) |
| 02 | [Creating Tables & Data Types](./02_Day_Creating_tables/02_creating_tables.md) |
| 03 | [Inserting Data](./03_Day_Inserting_data/03_inserting_data.md) |
| 04 | [SELECT, ORDER BY, LIMIT](./04_Day_Select/04_select.md) |
| 05 | [Filtering with WHERE](./05_Day_Filtering/05_filtering.md) |
| 06 | [Expressions & Scalar Functions](./06_Day_Expressions_and_functions/06_expressions_and_functions.md) |
| 07 | [Aggregates, GROUP BY, HAVING](./07_Day_Aggregates/07_aggregates.md) |
| 08 | [UPDATE, DELETE & Transactions](./08_Day_Update_delete_transactions/08_update_delete_transactions.md) |
| 09 | [Constraints, Keys & Upsert](./09_Day_Constraints_and_upsert/09_constraints_and_upsert.md) |
| 10 | [Database Design & Normalization](./10_Day_Database_design/10_database_design.md) |
| R1 | [Review 1: Foundations](./10R_Review_Foundations/10R_review_foundations.md) |

### Part 2: Combining data

| # Day | Topics |
|------|:--------------------------------------------------:|
| 11 | [INNER JOIN](./11_Day_Inner_join/11_inner_join.md) |
| 12 | [Outer, Self & Cross Joins](./12_Day_Outer_self_cross_joins/12_outer_self_cross_joins.md) |
| 13 | [Subqueries](./13_Day_Subqueries/13_subqueries.md) |
| 14 | [CTEs & Temporary Tables](./14_Day_CTEs_and_temp_tables/14_ctes_and_temp_tables.md) |
| 15 | [Set Operations & Conditional Aggregation](./15_Day_Set_operations/15_set_operations.md) |
| 16 | [Dates & Times](./16_Day_Dates_and_times/16_dates_and_times.md) |
| R2 | [Review 2: Combining Data](./16R_Review_Combining_data/16R_review_combining_data.md) |

### Part 3: Analytical SQL

| # Day | Topics |
|------|:--------------------------------------------------:|
| 17 | [Window Functions I: Ranking](./17_Day_Window_functions_ranking/17_window_functions_ranking.md) |
| 18 | [Window Functions II: Running Totals, LAG/LEAD, Frames](./18_Day_Window_functions_running/18_window_functions_running.md) |
| R3 | [Review 3: Analytical SQL](./18R_Review_Analytical_sql/18R_review_analytical_sql.md) |

### Part 4: Python and SQLite in depth

| # Day | Topics |
|------|:--------------------------------------------------:|
| 19 | [The sqlite3 Module in Depth](./19_Day_Sqlite3_in_depth/19_sqlite3_in_depth.md) |
| 20 | [Importing, Cleaning & Exporting Data](./20_Day_Import_clean_export/20_import_clean_export.md) |
| 21 | [Indexes & Query Performance](./21_Day_Indexes/21_indexes.md) |
| 22 | [Views & Triggers](./22_Day_Views_and_triggers/22_views_and_triggers.md) |
| R4 | [Review 4: Python and SQLite](./22R_Review_Python_and_sqlite/22R_review_python_and_sqlite.md) |

### Part 5: DuckDB

| # Day | Topics |
|------|:--------------------------------------------------:|
| 23 | [Meet DuckDB](./23_Day_Meet_duckdb/23_meet_duckdb.md) |
| 24 | [Querying Files Directly](./24_Day_Querying_files/24_querying_files.md) |
| 25 | [DuckDB's Friendly SQL & Nested Types](./25_Day_Duckdb_friendly_sql/25_duckdb_friendly_sql.md) |
| 26 | [DuckDB with pandas, Polars & SQLite](./26_Day_Duckdb_with_dataframes/26_duckdb_with_dataframes.md) |
| R5 | [Review 5: DuckDB](./26R_Review_Duckdb/26R_review_duckdb.md) |

### Part 6: Craft and projects

| # Day | Topics |
|------|:--------------------------------------------------:|
| 27 | [Security & Best Practices](./27_Day_Security_and_best_practices/27_security_and_best_practices.md) |
| 28 | [Project 1: Library Manager CLI](./28_Day_Project_library_cli/28_project_library_cli.md) |
| 29 | [Project 2: Analytics Report](./29_Day_Project_analytics_report/29_project_analytics_report.md) |
| 30 | [Conclusions](./30_Day_Conclusions/30_conclusions.md) |

## Setup

You need [uv](https://docs.astral.sh/uv/), which installs Python 3.12+ and the packages for you.

```sh
git clone <this repo>
cd sql
uv sync                                   # installs duckdb, pandas, polars, pytest (+ sqlfluff, sqlglot)
uv run python tools/build_shop_db.py      # builds data/shop.db, the practice shop database
uv run python tools/make_big_events.py    # builds data/big_events.csv (only needed from Day 21)
```

Versions this course was written and tested with: Python 3.12, SQLite 3.45, DuckDB 2.0.0.
A newer Python or DuckDB should be fine. An older SQLite may not support everything (Day 1 shows you how to check).

### Without uv

uv is a convenience, not a requirement. You need Python 3.12 or newer (several lessons use 3.12 features) and these packages:

```sh
python3.12 -m venv .venv
source .venv/bin/activate                 # on Windows: .venv\Scripts\activate
pip install duckdb pandas polars pyarrow pytest sqlfluff sqlglot
python tools/build_shop_db.py
python tools/make_big_events.py           # only needed from Day 21
```

After that, wherever the lessons say `uv run python ...`, run `python ...` with the environment activated, and `pytest` instead of `uv run pytest`. A different DuckDB version can change behaviour and error messages, so if something does not match a lesson, check `duckdb.__version__` first.

## How to work through it

- Write your own code in `00_practice/`, one file per day: `day_1.py`, `day_2.py`, and so on. Run it with `uv run python 00_practice/day_1.py`.
- Your own database files (like `library.db`) live in `00_practice/` too. They are ignored by git.
- Datasets are in [`data/`](./data/README.md).
- `solutions/` has a reference answer for every exercise. **Try first, peek later.**
- `tools/check_all.py` runs every reference solution to prove they still work.

<small> HAPPY QUERYING </small>

## Setup & data: what each day needs

Everything you build lives in `00_practice/` (ignored by git). Everything shipped with the course lives in `data/`. Run all commands from the repo root.

| From | You need | How you get it |
|---|---|---|
| Day 1 | Python 3.12+, packages | `uv sync` (run once; this also installs pyarrow for Day 26) |
| Day 3 | `00_practice/library.db` (the 12 books) and `00_practice/datasets.db` (countries + Hacker News) | you build them in the Day 3 exercises |
| Day 8-9 | copies such as `books_copy`; Day 9 rebuilds `books` with constraints | you build them; destructive exercises use copies |
| Day 10 | the library becomes four tables: `authors`, `books`, `members`, `loans`; `countries` gets `languages` and `country_languages` | Day 10 guides the migration. **Back up first**: `00_practice/library_flat.db`, which [Review 1](./10R_Review_Foundations/10R_review_foundations.md) needs |
| Day 11 | `data/shop.db` (customers, products, orders, order_items, employees, newsletter_signups) | `uv run python tools/build_shop_db.py` |
| Day 12 | `00_practice/shop_play.db`, a scratch copy of the shop | a `shutil.copy` in the lesson |
| Day 16 | a fixed "today", `2025-03-14`, so dates in the outputs never drift | defined in the lesson |
| Day 21, 23, 24 | `data/big_events.csv`, one million rows | `uv run python tools/make_big_events.py` |
| Day 23 | `00_practice/shop.duckdb` (reused on Days 25, 26, Review 5) | Day 23 Level 2 builds it |
| Day 24, 29 | internet once, to download DuckDB's `sqlite` extension | automatic on first `ATTACH ... (TYPE sqlite)` |

If a database gets into a bad state, delete it and rebuild: `data/shop.db` and `data/big_events.csv` come from the scripts above, and your own databases come from your day files. The files in `solutions/` (for example `solutions/day_10.py`) show a working version of every step.
