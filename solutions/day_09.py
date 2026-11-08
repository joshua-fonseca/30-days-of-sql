# Day 9 reference solutions
import csv
import io
import json
import sqlite3

from helpers import DATA, library_conn, show

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
lib = library_conn()
lib.execute("""
    CREATE TABLE books_new (
        id            INTEGER PRIMARY KEY,
        title         TEXT NOT NULL CHECK (length(title) > 0),
        author        TEXT NOT NULL,
        year          INTEGER CHECK (year BETWEEN 1000 AND 2100),
        pages         INTEGER CHECK (pages > 0),
        genre         TEXT,
        price_cents   INTEGER CHECK (price_cents >= 0),
        rating        REAL CHECK (rating BETWEEN 0 AND 5),
        title_length  INTEGER GENERATED ALWAYS AS (length(title)) VIRTUAL,
        UNIQUE (title, author)
    ) STRICT
""")
lib.execute("""
    INSERT INTO books_new (id, title, author, year, pages, genre, price_cents, rating)
    SELECT id, title, author, year, pages, genre, price_cents, rating FROM books
""")
lib.execute("DROP TABLE books")
lib.execute("ALTER TABLE books_new RENAME TO books")
lib.commit()
print(lib.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM books").fetchone())  # (12, 1, 12)
print(lib.execute("SELECT title, title_length FROM books WHERE id = 1").fetchone())  # ('Dune', 4)

print("# Level 1, Q2")
bad_rows = [
    ("pages = 0", "INSERT INTO books (title, author, pages) VALUES ('Zero', 'A. Writer', 0)"),
    ("rating = 6", "INSERT INTO books (title, author, rating) VALUES ('Six', 'A. Writer', 6)"),
    ("duplicate Dune", "INSERT INTO books (title, author) VALUES ('Dune', 'Frank Herbert')"),
    ("no title", "INSERT INTO books (author) VALUES ('A. Writer')"),
    ("empty title", "INSERT INTO books (title, author) VALUES ('', 'A. Writer')"),
]
for label, sql in bad_rows:
    try:
        lib.execute(sql)
    except sqlite3.IntegrityError as e:
        print(f"{label:15} {e}")
        print(f"{'':15} {e.sqlite_errorname}")  # Q3: the machine-readable name
lib.rollback()

print("# Level 1, Q4")
lib.execute("CREATE TABLE reading_list (title TEXT NOT NULL, author TEXT NOT NULL, rating REAL, UNIQUE (title, author))")
upsert = """
    INSERT INTO reading_list (title, author, rating) VALUES (?, ?, ?)
    ON CONFLICT (title, author) DO UPDATE SET rating = excluded.rating
"""
lib.execute(upsert, ("Foundation", "Isaac Asimov", 4.0))
lib.execute(upsert, ("Foundation", "Isaac Asimov", 4.6))
lib.execute(upsert, ("Dune", "Frank Herbert", 4.5))
show(lib.execute("SELECT * FROM reading_list ORDER BY title"))

print("# Level 1, Q5")
cur = lib.execute("INSERT OR IGNORE INTO books (title, author, pages) VALUES ('Dune', 'Frank Herbert', 1)")
print(cur.rowcount, lib.execute("SELECT pages FROM books WHERE title = 'Dune'").fetchone())  # 0 (612,)
lib.rollback()

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
c = sqlite3.connect(":memory:")
c.execute("CREATE TABLE members (id INTEGER PRIMARY KEY, name TEXT NOT NULL) STRICT")
c.execute("CREATE TABLE loans (id INTEGER PRIMARY KEY, member_id INTEGER NOT NULL REFERENCES members (id), book TEXT NOT NULL) STRICT")
c.execute("INSERT INTO members (name) VALUES ('Ana')")
c.execute("INSERT INTO loans (member_id, book) VALUES (99, 'Dune')")  # no member 99, but nothing stops us
print("without PRAGMA:", c.execute("SELECT * FROM loans").fetchall(), c.execute("PRAGMA foreign_keys").fetchone())
c.rollback()

c2 = sqlite3.connect(":memory:")
c2.execute("PRAGMA foreign_keys = ON")  # right after connecting, before any transaction
c2.execute("CREATE TABLE members (id INTEGER PRIMARY KEY, name TEXT NOT NULL) STRICT")
c2.execute("CREATE TABLE loans (id INTEGER PRIMARY KEY, member_id INTEGER NOT NULL REFERENCES members (id), book TEXT NOT NULL) STRICT")
c2.execute("INSERT INTO members (name) VALUES ('Ana')")
try:
    c2.execute("INSERT INTO loans (member_id, book) VALUES (99, 'Dune')")
except sqlite3.IntegrityError as e:
    print("with PRAGMA:   ", e)

c3 = sqlite3.connect(":memory:")
c3.execute("CREATE TABLE t (x)")
c3.execute("INSERT INTO t VALUES (1)")  # a transaction is now open
c3.execute("PRAGMA foreign_keys = ON")  # ignored inside a transaction!
print("pragma inside a transaction:", c3.execute("PRAGMA foreign_keys").fetchone())  # (0,)

print("# Level 2, Q2")
d = sqlite3.connect(":memory:")
d.execute("PRAGMA foreign_keys = ON")
d.execute("CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT) STRICT")
d.execute("CREATE TABLE players_cascade (id INTEGER PRIMARY KEY, team_id INTEGER REFERENCES teams (id) ON DELETE CASCADE) STRICT")
d.execute("CREATE TABLE players_setnull (id INTEGER PRIMARY KEY, team_id INTEGER REFERENCES teams (id) ON DELETE SET NULL) STRICT")
d.execute("CREATE TABLE players_plain (id INTEGER PRIMARY KEY, team_id INTEGER REFERENCES teams (id)) STRICT")
d.execute("INSERT INTO teams VALUES (1, 'Reds')")
for t in ("players_cascade", "players_setnull", "players_plain"):
    d.executemany(f"INSERT INTO {t} (team_id) VALUES (?)", [(1,), (1,)])
try:
    d.execute("DELETE FROM teams WHERE id = 1")
except sqlite3.IntegrityError as e:
    print("plain FK blocks the delete:", e)
d.execute("DROP TABLE players_plain")
d.execute("DELETE FROM teams WHERE id = 1")
print("cascade:", d.execute("SELECT COUNT(*) FROM players_cascade").fetchone()[0], "rows left")
print("set null:", d.execute("SELECT * FROM players_setnull").fetchall())

print("# Level 2, Q3")


def safe_insert(conn, sql, params=()):
    try:
        conn.execute(sql, params)
        return True
    except sqlite3.IntegrityError:
        return False


e = sqlite3.connect(":memory:")
e.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE) STRICT")
print(safe_insert(e, "INSERT INTO users (email) VALUES (?)", ("a@x.com",)))  # True
print(safe_insert(e, "INSERT INTO users (email) VALUES (?)", ("a@x.com",)))  # False
print(safe_insert(e, "INSERT INTO users (email) VALUES (?)", (None,)))  # False

print("# Level 2, Q4")
e.execute("CREATE TABLE enrollments (student_id INTEGER, course_id INTEGER, PRIMARY KEY (student_id, course_id)) STRICT")
pairs = [(1, 10), (1, 11), (2, 10), (1, 10), (2, 10), (3, 12)]
added = 0
for p in pairs:
    added += e.execute("INSERT OR IGNORE INTO enrollments VALUES (?, ?)", p).rowcount
print(added, "added,", len(pairs) - added, "ignored")  # 4 added, 2 ignored

print("# Level 2, Q5")
e.execute("""
    CREATE TABLE staff (
        id INTEGER PRIMARY KEY,
        email TEXT NOT NULL CHECK (email LIKE '%_@_%._%'),
        hired_on TEXT NOT NULL CHECK (hired_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
        salary_cents INTEGER NOT NULL CHECK (salary_cents > 0)
    ) STRICT
""")
for row in [("ana@example.com", "2025-03-14", 500000), ("not-an-email", "2025-03-14", 500000),
            ("ben@example.com", "14/03/2025", 500000), ("cy@example.com", "2025-03-14", 0)]:
    try:
        e.execute("INSERT INTO staff (email, hired_on, salary_cents) VALUES (?, ?, ?)", row)
        print("ok      ", row)
    except sqlite3.IntegrityError as err:
        print("rejected", row, "->", err)

print("# Level 2, Q6")
e.execute("CREATE TABLE people (email TEXT UNIQUE)")
e.execute("INSERT INTO people VALUES (NULL)")
e.execute("INSERT INTO people VALUES (NULL)")
print(e.execute("SELECT COUNT(*) FROM people").fetchone())  # (2,): UNIQUE allows many NULLs
# PRIMARY KEY: identifies the row, only one per table (can be several columns), never NULL in practice.
# UNIQUE: no repeats, but many allowed per table, and NULLs do not count as repeats.

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
UPDATES = """sku,qty,price_cents
A100,5,250
B200,3,1000
A100,7,250
C300,10,75
B200,4,1200
A100,2,260
"""
UPSERT = """INSERT INTO inventory (sku, qty, price_cents) VALUES (:sku, :qty, :price_cents)
            ON CONFLICT (sku) DO UPDATE SET qty = qty + excluded.qty, price_cents = excluded.price_cents"""
inv = sqlite3.connect(":memory:")
inv.execute("CREATE TABLE inventory (sku TEXT PRIMARY KEY, qty INTEGER NOT NULL CHECK (qty >= 0), price_cents INTEGER NOT NULL) STRICT")
inv.executemany(UPSERT, list(csv.DictReader(io.StringIO(UPDATES))))
show(inv.execute("SELECT * FROM inventory ORDER BY sku"))

print("# Level 3, Q2")
MORE = """sku,qty,price_cents
A100,5,250
D400,-5,100
E500,4,300
A100,3,250
B200,-1,1200
E500,2,320
"""
inv.execute("DELETE FROM inventory")
report = {"inserted": 0, "updated": 0, "rejected": []}
for row in csv.DictReader(io.StringIO(MORE)):
    exists = inv.execute("SELECT 1 FROM inventory WHERE sku = ?", (row["sku"],)).fetchone() is not None
    try:
        inv.execute(UPSERT, row)
        report["updated" if exists else "inserted"] += 1
    except sqlite3.IntegrityError as err:
        report["rejected"].append((row["sku"], row["qty"], str(err)))
print(report["inserted"], "inserted,", report["updated"], "updated,", len(report["rejected"]), "rejected")
for r in report["rejected"]:
    print("rejected:", r)
show(inv.execute("SELECT * FROM inventory ORDER BY sku"))
# Note: B200 was rejected even if it existed with plenty of stock: the proposed row (qty = -1) fails the CHECK
# before SQLite looks for a conflict.

print("# Level 3, Q3")
ds = sqlite3.connect(":memory:")
ds.execute("CREATE TABLE countries_c (name TEXT NOT NULL UNIQUE, capital TEXT, population INTEGER NOT NULL CHECK (population >= 0), currency TEXT) STRICT")
data = json.loads((DATA / "countries_data.json").read_text(encoding="utf-8"))
rows = [(c["name"], c["capital"] or None, c["population"], c["currency"]) for c in data]
ds.executemany("INSERT INTO countries_c VALUES (?, ?, ?, ?)", rows)
print(ds.execute("SELECT COUNT(*) FROM countries_c").fetchone())  # (250,)
ds.executemany("INSERT OR IGNORE INTO countries_c VALUES (?, ?, ?, ?)", rows)
print("after INSERT OR IGNORE reload:", ds.execute("SELECT COUNT(*) FROM countries_c").fetchone()[0], "rows")
before = ds.execute("SELECT population FROM countries_c WHERE name = 'Finland'").fetchone()[0]
bumped = [(n, c, p + 1000, cur_) for n, c, p, cur_ in rows]
ds.executemany(
    """INSERT INTO countries_c VALUES (?, ?, ?, ?)
       ON CONFLICT (name) DO UPDATE SET population = excluded.population""",
    bumped,
)
after = ds.execute("SELECT population FROM countries_c WHERE name = 'Finland'").fetchone()[0]
print("after upsert reload:", ds.execute("SELECT COUNT(*) FROM countries_c").fetchone()[0], "rows; Finland", before, "->", after)
