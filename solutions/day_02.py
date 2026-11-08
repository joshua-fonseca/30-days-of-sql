# Day 2 reference solutions
import sqlite3

from helpers import WORK, BOOKS_SCHEMA

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
db_path = WORK / "day02_library.db"
db_path.unlink(missing_ok=True)
conn = sqlite3.connect(db_path)

print("# Level 1, Q2")
conn.execute("""
    CREATE TABLE books (
        id     INTEGER PRIMARY KEY,
        title  TEXT NOT NULL,
        author TEXT NOT NULL,
        year   INTEGER,
        pages  INTEGER,
        genre  TEXT
    ) STRICT
""")

print("# Level 1, Q3")
for row in conn.execute("PRAGMA table_info(books)"):
    print(row)

print("# Level 1, Q4")
print(conn.execute("SELECT sql FROM sqlite_master WHERE name = 'books'").fetchone()[0])

print("# Level 1, Q5")
conn.execute("ALTER TABLE books ADD COLUMN rating REAL")

print("# Level 1, Q6")
conn.execute("ALTER TABLE books ADD COLUMN notes TEXT")
conn.execute("ALTER TABLE books RENAME COLUMN notes TO comment")
conn.execute("ALTER TABLE books DROP COLUMN comment")

print("# Level 1, Q7")
conn.execute("ALTER TABLE books ADD COLUMN price_cents INTEGER")

print("# Level 1, Q8")
conn.execute("ALTER TABLE books ADD COLUMN title_length INTEGER GENERATED ALWAYS AS (length(title)) VIRTUAL")

print("# Level 1, Q9")
for row in conn.execute("PRAGMA table_xinfo(books)"):
    print(row)
# table_info hides generated columns; table_xinfo shows them (hidden = 2 means virtual generated).

print("# Level 1, Q10")
try:
    conn.execute("CREATE TABLE books (x TEXT)")
except sqlite3.Error as e:
    print(type(e).__name__, e)  # OperationalError table books already exists
conn.execute("CREATE TABLE IF NOT EXISTS books (x TEXT)")  # no error, the existing table is untouched

print("# Level 1, Q11")
conn.execute("DROP TABLE books")
conn.execute(BOOKS_SCHEMA)  # the final schema, see helpers.py
for row in conn.execute("PRAGMA table_xinfo(books)"):
    print(row)

print("# Level 1, Q12")
conn.execute("CREATE TABLE scratch (note TEXT)")
print("scratch" in [r[0] for r in conn.execute("SELECT name FROM sqlite_master")])  # True
conn.execute("DROP TABLE IF EXISTS scratch")
print("scratch" in [r[0] for r in conn.execute("SELECT name FROM sqlite_master")])  # False

print("# Level 1, Q13")
print(conn.execute("SELECT typeof(42), typeof(4.2), typeof('42'), typeof(NULL)").fetchone())
conn.close()

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
conn = sqlite3.connect(":memory:")
conn.execute("""
    CREATE TABLE members (
        member_id          INTEGER PRIMARY KEY,
        first_name         TEXT NOT NULL,
        last_name          TEXT NOT NULL,
        email              TEXT NOT NULL,
        joined_date        TEXT NOT NULL,                -- ISO text: '2025-03-14'
        is_active          INTEGER NOT NULL DEFAULT 1,   -- booleans are 0 / 1 in SQLite
        monthly_fee_cents  INTEGER NOT NULL              -- money as whole cents
    ) STRICT
""")
# Date: SQLite has no date type, ISO text sorts correctly and works with date functions (Day 16).
# Boolean: SQLite has no boolean type, so INTEGER 0/1 is the convention.
# Fee: integer cents, because REAL cannot represent most decimals exactly.

print("# Level 2, Q2")
conn.execute("CREATE TABLE ages (age INTEGER)")
conn.executemany("INSERT INTO ages VALUES (?)", [(25,), ("30",), ("thirty",), (4.5,)])
print("non-strict:", conn.execute("SELECT age, typeof(age) FROM ages").fetchall())
conn.execute("CREATE TABLE strict_ages (age INTEGER) STRICT")
parts = []
for value in [25, "30", "thirty", 4.5]:
    try:
        conn.execute("INSERT INTO strict_ages VALUES (?)", (value,))
        parts.append(f"{value!r} ok")
    except sqlite3.Error:
        parts.append(f"{value!r} failed")
print("strict:", ", ".join(parts).replace("'25'", "25"))

print("# Level 2, Q3")


def list_tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [name for (name,) in rows]


demo = sqlite3.connect(":memory:")
demo.execute("CREATE TABLE members (id INTEGER PRIMARY KEY AUTOINCREMENT)")  # AUTOINCREMENT adds sqlite_sequence
demo.execute("CREATE TABLE books (id INTEGER PRIMARY KEY)")
print(list_tables(demo))  # ['books', 'members']

print("# Level 2, Q4")
prices = [0.10, 0.20, 0.30, 0.10, 0.20, 0.30, 0.10, 0.20, 0.30, 0.10]
total = 0
for price in prices:
    total += price
print("as floats:", total)
total_cents = 0
for price in prices:
    total_cents += round(price * 100)
print(f"as cents:  {total_cents}  ->  {total_cents / 100:.2f}")
# Binary floating point cannot represent 0.1, 0.2, 0.3 exactly, so every addition adds a tiny error.
# Integers are exact.

print("# Level 2, Q5")
conn.execute("""
    CREATE TABLE people (
        name       TEXT,
        height_cm  REAL,
        weight_kg  REAL,
        bmi        REAL GENERATED ALWAYS AS (
            round(weight_kg / ((height_cm / 100.0) * (height_cm / 100.0)), 1)
        ) VIRTUAL
    )
""")
conn.executemany("INSERT INTO people (name, height_cm, weight_kg) VALUES (?, ?, ?)", [("Ana", 170, 65), ("Ben", 182, 90)])
for row in conn.execute("SELECT name, bmi FROM people"):
    print(row)
try:
    conn.execute("INSERT INTO people (name, bmi) VALUES ('Cy', 20)")
except sqlite3.Error as e:
    print(type(e).__name__, e)
