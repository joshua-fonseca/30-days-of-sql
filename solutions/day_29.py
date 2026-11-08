# Day 29 reference solution: Project 2, the shop business review with SQLite + DuckDB
#
# Pipeline:  shop.db --(DuckDB ATTACH)--> order_lines.parquet --(DuckDB queries)--> report.md
#            shop.db --(sqlite3)--> independent cross-check of the headline numbers
import sqlite3
from pathlib import Path

import duckdb

from helpers import DATA, WORK, show

PARQUET = WORK / "d29_order_lines.parquet"
REPORT = WORK / "d29_report.md"
LIVE = "status != 'cancelled'"  # revenue only counts orders that were not cancelled


# ---------------------------------------------------------------- Milestone 1: stage the data
def build_parquet(con: duckdb.DuckDBPyConnection, path: Path = PARQUET) -> int:
    """One row per order line, denormalized, with typed dates. Returns the row count."""
    con.execute(f"ATTACH '{DATA / 'shop.db'}' AS shop (TYPE sqlite, READ_ONLY)")
    con.execute(
        f"""
        COPY (
            SELECT o.order_id,
                   CAST(o.order_date AS DATE)              AS order_date,
                   o.status,
                   c.customer_id,
                   c.first_name || ' ' || c.last_name      AS customer,
                   c.country,
                   CAST(c.signup_date AS DATE)             AS signup_date,
                   p.product_id,
                   p.name                                  AS product,
                   coalesce(cat.name, 'Uncategorized')     AS category,
                   i.quantity,
                   i.unit_price_cents,
                   i.quantity * i.unit_price_cents         AS line_cents
            FROM shop.order_items AS i
            JOIN shop.orders      AS o   ON o.order_id = i.order_id
            JOIN shop.customers   AS c   ON c.customer_id = o.customer_id
            JOIN shop.products    AS p   ON p.product_id = i.product_id
            LEFT JOIN shop.categories AS cat ON cat.category_id = p.category_id
            ORDER BY o.order_id, p.product_id
        ) TO '{path}' (FORMAT parquet)
        """
    )
    return con.execute(f"SELECT count(*) FROM read_parquet('{path}')").fetchone()[0]


def usd(cents) -> str:
    return "-" if cents is None else f"${cents / 100:,.2f}"


# ---------------------------------------------------------------- Milestone 3: the questions
def questions(con: duckdb.DuckDBPyConnection, parquet: Path = PARQUET) -> dict[str, tuple[list[str], list[tuple]]]:
    src = f"read_parquet('{parquet}')"

    def q(sql: str):
        cur = con.execute(sql)
        return [d[0] for d in cur.description], cur.fetchall()

    out = {}
    out["Q1 Headline numbers"] = q(
        f"""
        SELECT count(DISTINCT order_id) AS orders, count(DISTINCT customer_id) AS buyers,
               sum(line_cents) AS revenue_cents,
               round(sum(line_cents) / count(DISTINCT order_id)) AS avg_order_cents
        FROM {src} WHERE {LIVE}
        """
    )
    out["Q2 Revenue by year"] = q(
        f"""
        WITH yearly AS (
            SELECT year(order_date) AS year, sum(line_cents) AS revenue_cents
            FROM {src} WHERE {LIVE} GROUP BY year
        )
        SELECT year, revenue_cents,
               round(100.0 * (revenue_cents - lag(revenue_cents) OVER (ORDER BY year))
                     / lag(revenue_cents) OVER (ORDER BY year), 1) AS growth_pct
        FROM yearly ORDER BY year
        """
    )
    out["Q3 Monthly revenue, 2025"] = q(
        f"""
        WITH monthly AS (
            SELECT strftime(order_date, '%Y-%m') AS month, sum(line_cents) AS revenue_cents
            FROM {src} WHERE {LIVE} AND year(order_date) = 2025 GROUP BY month
        )
        SELECT month, revenue_cents,
               round(100.0 * (revenue_cents - lag(revenue_cents) OVER (ORDER BY month))
                     / lag(revenue_cents) OVER (ORDER BY month), 1) AS mom_pct
        FROM monthly ORDER BY month
        """
    )
    out["Q4 Revenue by category"] = q(
        f"""
        SELECT category, sum(line_cents) AS revenue_cents,
               round(100.0 * sum(line_cents) / sum(sum(line_cents)) OVER (), 1) AS share_pct
        FROM {src} WHERE {LIVE}
        GROUP BY category ORDER BY revenue_cents DESC, category
        """
    )
    out["Q5 Top 5 products"] = q(
        f"""
        SELECT product, sum(quantity) AS units, sum(line_cents) AS revenue_cents
        FROM {src} WHERE {LIVE}
        GROUP BY product ORDER BY revenue_cents DESC, product LIMIT 5
        """
    )
    out["Q6 Top 5 customers"] = q(
        f"""
        SELECT customer, country, count(DISTINCT order_id) AS orders, sum(line_cents) AS revenue_cents
        FROM {src} WHERE {LIVE}
        GROUP BY customer_id, customer, country ORDER BY revenue_cents DESC, customer LIMIT 5
        """
    )
    out["Q7 Order status mix"] = q(
        f"""
        SELECT status, count(DISTINCT order_id) AS orders,
               round(100.0 * count(DISTINCT order_id) / sum(count(DISTINCT order_id)) OVER (), 1) AS share_pct
        FROM {src} GROUP BY status ORDER BY orders DESC, status
        """
    )
    out["Q8 Revenue by country"] = q(
        f"""
        SELECT country, count(DISTINCT customer_id) AS buyers, sum(line_cents) AS revenue_cents
        FROM {src} WHERE {LIVE}
        GROUP BY country ORDER BY revenue_cents DESC, country LIMIT 5
        """
    )
    out["Q9 Repeat customers"] = q(
        f"""
        WITH per_customer AS (
            SELECT customer_id, count(DISTINCT order_id) AS orders,
                   min(order_date) AS first_order, max(order_date) AS last_order
            FROM {src} WHERE {LIVE} GROUP BY customer_id
        )
        SELECT count(*) AS buyers,
               count(*) FILTER (WHERE orders >= 2) AS repeat_buyers,
               round(100.0 * count(*) FILTER (WHERE orders >= 2) / count(*), 1) AS repeat_pct,
               round(avg(orders), 2) AS avg_orders
        FROM per_customer
        """
    )
    out["Q10 Signup cohorts: ordered within 90 days"] = q(
        f"""
        WITH customers AS (
            SELECT customer_id, any_value(signup_date) AS signup_date,
                   min(order_date) AS first_order
            FROM {src} WHERE {LIVE} GROUP BY customer_id
        )
        SELECT strftime(signup_date, '%Y') || '-Q' || quarter(signup_date) AS cohort,
               count(*) AS buyers,
               count(*) FILTER (WHERE first_order - signup_date <= 90) AS ordered_in_90_days
        FROM customers GROUP BY cohort ORDER BY cohort
        """
    )
    return out


def never_ordered(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute(
        """
        SELECT p.name FROM shop.products p
        WHERE NOT EXISTS (SELECT 1 FROM shop.order_items i WHERE i.product_id = p.product_id)
        ORDER BY p.name
        """
    ).fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------------- Milestone 2: cross-check with SQLite
def sqlite_headline() -> tuple:
    with sqlite3.connect(DATA / "shop.db") as lite:
        return lite.execute(
            """
            SELECT count(DISTINCT o.order_id), count(DISTINCT o.customer_id), sum(i.quantity * i.unit_price_cents)
            FROM orders o JOIN order_items i ON i.order_id = o.order_id
            WHERE o.status != 'cancelled'
            """
        ).fetchone()


# ---------------------------------------------------------------- Milestone 4: the Markdown report
MONEY_COLUMNS = {"revenue_cents", "avg_order_cents"}


def markdown_table(headers: list[str], rows: list[tuple]) -> str:
    def cell(h, v):
        if v is None:
            return ""
        if h in MONEY_COLUMNS:
            return usd(v)
        return str(v)

    names = [h.replace("_cents", "") if h in MONEY_COLUMNS else h for h in headers]
    lines = ["| " + " | ".join(names) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(cell(h, v) for h, v in zip(headers, row)) + " |" for row in rows]
    return "\n".join(lines)


def write_report(results, unsold: list[str], path: Path = REPORT) -> None:
    parts = ["# Shop business review", "", "Revenue counts every order that was not cancelled. Money is shown in dollars.", ""]
    for title, (headers, rows) in results.items():
        parts += [f"## {title}", "", markdown_table(headers, rows), ""]
    parts += ["## Products never ordered", "", ", ".join(unsold), ""]
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    PARQUET.unlink(missing_ok=True)
    con = duckdb.connect()
    print("# Milestone 1: parquet rows")
    print(build_parquet(con))
    print("# Milestone 2: cross-check")
    results = questions(con)
    duck = con.execute(
        f"SELECT count(DISTINCT order_id), count(DISTINCT customer_id), sum(line_cents) FROM read_parquet('{PARQUET}') WHERE {LIVE}"
    ).fetchone()
    lite = sqlite_headline()
    print("duckdb:", duck)
    print("sqlite:", lite)
    assert duck == lite
    print("# Milestone 3: the questions")
    for title, (headers, rows) in results.items():
        print(f"## {title}")
        print(headers)
        for r in rows:
            print(r)
    unsold = never_ordered(con)
    print("never ordered:", unsold)
    write_report(results, unsold)
    print("# Milestone 4: report")
    text = REPORT.read_text(encoding="utf-8")
    print(len(text.splitlines()), "lines")
    print("\n".join(text.splitlines()[:16]))


if __name__ == "__main__":
    main()
