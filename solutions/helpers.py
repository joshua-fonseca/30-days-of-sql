"""Helpers shared by the reference solutions (not part of the lessons).

`show` is the helper students build on Day 4. The rest keep the solutions self-contained: every solution
works in solutions/_work/, never in the student's 00_practice/ folder.
"""

import json
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WORK = Path(__file__).resolve().parent / "_work"
WORK.mkdir(exist_ok=True)


def show(cur):
    """Print the rows left in a cursor as an aligned table (the Day 4 helper)."""
    headers = [col[0] for col in cur.description]
    rows = cur.fetchall()
    cells = [["NULL" if v is None else str(v) for v in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip())
    print("  ".join("-" * w for w in widths))
    for r in cells:
        print("  ".join(v.ljust(w) for v, w in zip(r, widths)).rstrip())
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")


BOOKS_SCHEMA = """
CREATE TABLE books (
    id            INTEGER PRIMARY KEY,
    title         TEXT NOT NULL,
    author        TEXT NOT NULL,
    year          INTEGER,
    pages         INTEGER,
    genre         TEXT,
    price_cents   INTEGER,
    rating        REAL,
    title_length  INTEGER GENERATED ALWAYS AS (length(title)) VIRTUAL
) STRICT
"""

# (title, author, year, pages, genre, price_cents, rating) -- the 12 books every student inserts on Day 3
BOOKS = [
    ("Dune", "Frank Herbert", 1965, 612, "Sci-Fi", 1099, 4.5),
    ("Neuromancer", "William Gibson", 1984, 271, "Sci-Fi", 899, 4.0),
    ("The Hobbit", "J.R.R. Tolkien", 1937, 310, "Fantasy", 799, 4.7),
    ("The Name of the Wind", "Patrick Rothfuss", 2007, 662, "Fantasy", 1299, 4.4),
    ("Pride and Prejudice", "Jane Austen", 1813, 279, "Romance", 599, 4.3),
    ("Emma", "Jane Austen", 1815, 474, "Romance", 649, None),
    ("1984", "George Orwell", 1949, 328, "Dystopian", 799, 4.6),
    ("Brave New World", "Aldous Huxley", 1932, 311, "Dystopian", 849, None),
    ("The Pragmatic Programmer", "Andrew Hunt", 1999, 352, "Tech", 4999, 4.8),
    ("Clean Code", "Robert C. Martin", 2008, 464, "Tech", 3999, 4.1),
    ("Project Hail Mary", "Andy Weir", 2021, 476, "Sci-Fi", 1599, None),
    ("The Martian", "Andy Weir", 2011, 369, "Sci-Fi", 1199, 4.6),
]


def library_conn():
    """A fresh in-memory library exactly as it looks at the end of Day 3."""
    conn = sqlite3.connect(":memory:")
    conn.execute(BOOKS_SCHEMA)
    conn.executemany(
        "INSERT INTO books (title, author, year, pages, genre, price_cents, rating) VALUES (?, ?, ?, ?, ?, ?, ?)",
        BOOKS,
    )
    conn.commit()
    return conn


def datasets_conn():
    """A fresh in-memory datasets db with `countries` and `hn_posts` loaded as on Day 3 (L3)."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE countries (name TEXT, capital TEXT, population INTEGER, currency TEXT)"
    )
    conn.execute(
        "CREATE TABLE hn_posts (id INTEGER, title TEXT, url TEXT, num_points INTEGER,"
        " num_comments INTEGER, author TEXT, created_at TEXT)"
    )
    for c in json.loads((DATA / "countries_data.json").read_text(encoding="utf-8")):
        conn.execute(
            "INSERT INTO countries VALUES (?, ?, ?, ?)",
            (c["name"], c["capital"] or None, c["population"], c["currency"]),
        )
    with (DATA / "hacker_news.csv").open(newline="", encoding="utf-8") as f:
        rows = [
            (int(r["id"]), r["title"], r["url"] or None, int(r["num_points"]), int(r["num_comments"]), r["author"], r["created_at"])
            for r in csv.DictReader(f)
        ]
    conn.executemany("INSERT INTO hn_posts VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    return conn


# --------------------------------------------------------------------------------------------------
# The library as it looks after Day 10 (normalized). Later days (11+) and the review lessons use this.
# --------------------------------------------------------------------------------------------------
TODAY = "2025-03-14"  # the fixed "today" used by date exercises (Day 16) so expected output never drifts

MEMBERS = [
    ("Alice Nguyen", "alice@example.com", "2024-01-15"),
    ("Bruno Silva", "bruno@example.com", "2024-02-20"),
    ("Chloe Martin", "chloe@example.com", "2024-03-05"),
    ("Dev Patel", "dev@example.com", "2024-06-18"),
    ("Elena Rossi", "elena@example.com", "2024-09-02"),  # never borrows a book
]

# (book_id, member_id, loaned_on, due_on, returned_on) -- due_on is always loaned_on + 14 days
LOANS = [
    (1, 1, "2025-01-10", "2025-01-24", "2025-01-20"),
    (3, 1, "2025-01-25", "2025-02-08", "2025-02-05"),
    (7, 2, "2025-02-01", "2025-02-15", "2025-02-14"),
    (9, 2, "2025-02-20", "2025-03-06", None),  # overdue on 2025-03-14
    (12, 3, "2025-02-03", "2025-02-17", "2025-02-25"),  # returned late
    (2, 3, "2025-03-01", "2025-03-15", None),  # due tomorrow
    (5, 4, "2025-03-05", "2025-03-19", None),
    (1, 4, "2025-03-08", "2025-03-22", None),
    (10, 1, "2025-03-10", "2025-03-24", None),
    (3, 2, "2025-03-12", "2025-03-26", None),
]

LIBRARY_SCHEMA = """
CREATE TABLE authors (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE
) STRICT;

CREATE TABLE books (
    id            INTEGER PRIMARY KEY,
    title         TEXT NOT NULL CHECK (length(title) > 0),
    author_id     INTEGER NOT NULL REFERENCES authors (id),
    year          INTEGER CHECK (year BETWEEN 1000 AND 2100),
    pages         INTEGER CHECK (pages > 0),
    genre         TEXT,
    price_cents   INTEGER CHECK (price_cents >= 0),
    rating        REAL CHECK (rating BETWEEN 0 AND 5),
    title_length  INTEGER GENERATED ALWAYS AS (length(title)) VIRTUAL,
    UNIQUE (title, author_id)
) STRICT;

CREATE TABLE members (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    joined_on  TEXT NOT NULL
) STRICT;

CREATE TABLE loans (
    id           INTEGER PRIMARY KEY,
    book_id      INTEGER NOT NULL REFERENCES books (id),
    member_id    INTEGER NOT NULL REFERENCES members (id),
    loaned_on    TEXT NOT NULL,
    due_on       TEXT NOT NULL,
    returned_on  TEXT
) STRICT;
"""


def library_full_conn():
    """A fresh in-memory library exactly as it looks at the end of Day 10 (authors, books, members, loans)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(LIBRARY_SCHEMA)
    names = sorted({b[1] for b in BOOKS})
    conn.executemany("INSERT INTO authors (name) VALUES (?)", [(n,) for n in names])
    author_id = {n: i for i, n in enumerate(names, start=1)}
    conn.executemany(
        "INSERT INTO books (title, author_id, year, pages, genre, price_cents, rating) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(t, author_id[a], y, p, g, pc, r) for t, a, y, p, g, pc, r in BOOKS],
    )
    conn.executemany("INSERT INTO members (name, email, joined_on) VALUES (?, ?, ?)", MEMBERS)
    conn.executemany("INSERT INTO loans (book_id, member_id, loaned_on, due_on, returned_on) VALUES (?, ?, ?, ?, ?)", LOANS)
    conn.commit()
    return conn


# --------------------------------------------------------------------------------------------------
# Added for Days 11-16 and Review 2
# --------------------------------------------------------------------------------------------------
def shop_conn():
    """An in-memory COPY of data/shop.db (so destructive exercises never touch the real file)."""
    src = sqlite3.connect(DATA / "shop.db")
    conn = sqlite3.connect(":memory:")
    src.backup(conn)
    src.close()
    return conn


def languages_conn():
    """datasets db after Day 10 (L3): countries(id, ...), languages(id, name), country_languages(country_id, language_id)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE countries (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, capital TEXT,
            population INTEGER NOT NULL CHECK (population >= 0), currency TEXT
        ) STRICT;
        CREATE TABLE languages (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE) STRICT;
        CREATE TABLE country_languages (
            country_id  INTEGER NOT NULL REFERENCES countries (id),
            language_id INTEGER NOT NULL REFERENCES languages (id),
            PRIMARY KEY (country_id, language_id)
        ) STRICT;
        """
    )
    for c in json.loads((DATA / "countries_data.json").read_text(encoding="utf-8")):
        cur = conn.execute(
            "INSERT INTO countries (name, capital, population, currency) VALUES (?, ?, ?, ?)",
            (c["name"], c["capital"] or None, c["population"], c["currency"]),
        )
        for lang in c["languages"]:
            conn.execute("INSERT OR IGNORE INTO languages (name) VALUES (?)", (lang,))
            lid = conn.execute("SELECT id FROM languages WHERE name = ?", (lang,)).fetchone()[0]
            conn.execute("INSERT OR IGNORE INTO country_languages VALUES (?, ?)", (cur.lastrowid, lid))
    conn.commit()
    return conn


# --------------------------------------------------------------------------------------------------
# DuckDB days (23-26). `show` already works on DuckDB results (connection.execute(...) and relations
# both offer .description and .fetchall()), so no separate adapter is needed.
# --------------------------------------------------------------------------------------------------
DUCK_SHOP_DDL = """
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, first_name VARCHAR NOT NULL, last_name VARCHAR NOT NULL,
                        email VARCHAR UNIQUE, city VARCHAR, country VARCHAR NOT NULL, signup_date DATE NOT NULL);
CREATE TABLE categories (category_id INTEGER PRIMARY KEY, name VARCHAR NOT NULL UNIQUE);
CREATE TABLE products (product_id INTEGER PRIMARY KEY, name VARCHAR NOT NULL,
                       category_id INTEGER REFERENCES categories (category_id),
                       price_cents INTEGER NOT NULL, stock INTEGER NOT NULL);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers (customer_id),
                     order_date DATE NOT NULL, status VARCHAR NOT NULL);
CREATE TABLE order_items (order_id INTEGER NOT NULL REFERENCES orders (order_id),
                          product_id INTEGER NOT NULL REFERENCES products (product_id),
                          quantity INTEGER NOT NULL, unit_price_cents INTEGER NOT NULL,
                          PRIMARY KEY (order_id, product_id));
CREATE TABLE employees (employee_id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, title VARCHAR NOT NULL,
                        manager_id INTEGER REFERENCES employees (employee_id), hire_date DATE NOT NULL,
                        salary_cents INTEGER NOT NULL);
CREATE TABLE newsletter_signups (email VARCHAR NOT NULL, signed_up_at TIMESTAMP NOT NULL);
"""
DUCK_SHOP_TABLES = ["customers", "categories", "products", "orders", "order_items", "employees", "newsletter_signups"]


def shop_duck(path=None):
    """A DuckDB connection holding the shop (typed DATE columns, money still in integer cents).

    This is the Day 23 `load_shop` exercise. With `path=None` it is an in-memory copy; otherwise the
    database is written to that file (and rebuilt from scratch each time).
    """
    import duckdb

    if path is not None:
        Path(path).unlink(missing_ok=True)
    con = duckdb.connect(str(path) if path is not None else ":memory:")
    con.execute(DUCK_SHOP_DDL)
    lite = sqlite3.connect(DATA / "shop.db")
    for table in DUCK_SHOP_TABLES:
        rows = lite.execute(f"SELECT * FROM {table}").fetchall()
        marks = ", ".join("?" * len(rows[0]))
        con.executemany(f"INSERT INTO {table} VALUES ({marks})", rows)
    lite.close()
    return con


# --------------------------------------------------------------------------------------------------
# data/big_events.csv loaded into SQLite (Days 21 and 23). Built once, then cached in _work/.
# --------------------------------------------------------------------------------------------------
def events_db_path():
    """Path of a SQLite file holding `events` (1,000,000 rows, no secondary indexes), built on first use."""
    path = WORK / "events.db"
    if path.exists():
        return path
    csv_path = DATA / "big_events.csv"
    if not csv_path.exists():
        import subprocess
        import sys

        subprocess.run([sys.executable, str(ROOT / "tools" / "make_big_events.py")], check=True)
    tmp = WORK / "events.db.tmp"
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    conn.execute(
        """CREATE TABLE events (
            event_id     INTEGER PRIMARY KEY,
            user_id      INTEGER NOT NULL,
            event_type   TEXT NOT NULL,
            ts           TEXT NOT NULL,
            amount_cents INTEGER
        ) STRICT"""
    )
    from itertools import batched

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        rows = ((int(i), int(u), t, ts, round(float(a) * 100) if a else None) for i, u, t, ts, a in reader)
        for chunk in batched(rows, 50_000):
            conn.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?)", chunk)
    conn.commit()
    conn.close()
    tmp.rename(path)
    return path
