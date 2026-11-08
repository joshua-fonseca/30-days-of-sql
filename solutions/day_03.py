# Day 3 reference solutions
import csv
import json
import sqlite3

from helpers import BOOKS_SCHEMA, DATA, WORK

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
db_path = WORK / "day03_library.db"
db_path.unlink(missing_ok=True)
conn = sqlite3.connect(db_path)
conn.execute(BOOKS_SCHEMA)  # the table as it was left at the end of Day 2

COLS = "title, author, year, pages, genre, price_cents, rating"

print("# Level 1, Q2")
cur = conn.execute(
    f"INSERT INTO books ({COLS}) VALUES ('Dune', 'Frank Herbert', 1965, 612, 'Sci-Fi', 1099, 4.5)"
)
conn.commit()
id_dune = cur.lastrowid

print("# Level 1, Q3")
conn.execute(f"""
    INSERT INTO books ({COLS}) VALUES
        ('Neuromancer', 'William Gibson', 1984, 271, 'Sci-Fi', 899, 4.0),
        ('The Hobbit', 'J.R.R. Tolkien', 1937, 310, 'Fantasy', 799, 4.7),
        ('The Name of the Wind', 'Patrick Rothfuss', 2007, 662, 'Fantasy', 1299, 4.4)
""")

print("# Level 1, Q4")
cur = conn.execute(
    f"INSERT INTO books ({COLS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
    ("Pride and Prejudice", "Jane Austen", 1813, 279, "Romance", 599, 4.3),
)
id_pride = cur.lastrowid

print("# Level 1, Q5")
cur = conn.execute(
    "INSERT INTO books (title, author, year, pages, genre, price_cents) "
    "VALUES (:title, :author, :year, :pages, :genre, :price_cents)",
    {"title": "Emma", "author": "Jane Austen", "year": 1815, "pages": 474, "genre": "Romance", "price_cents": 649},
)
id_emma = cur.lastrowid

print("# Level 1, Q6")
rest = [
    ("1984", "George Orwell", 1949, 328, "Dystopian", 799, 4.6),
    ("Brave New World", "Aldous Huxley", 1932, 311, "Dystopian", 849, None),
    ("The Pragmatic Programmer", "Andrew Hunt", 1999, 352, "Tech", 4999, 4.8),
    ("Clean Code", "Robert C. Martin", 2008, 464, "Tech", 3999, 4.1),
    ("Project Hail Mary", "Andy Weir", 2021, 476, "Sci-Fi", 1599, None),
    ("The Martian", "Andy Weir", 2011, 369, "Sci-Fi", 1199, 4.6),
]
cur = conn.executemany(f"INSERT INTO books ({COLS}) VALUES (?, ?, ?, ?, ?, ?, ?)", rest)

print("# Level 1, Q7")
print(id_dune, id_pride, id_emma)  # 1 5 6
print(cur.lastrowid)  # None: lastrowid is not updated by executemany

print("# Level 1, Q8")
conn.commit()
print(conn.execute("SELECT COUNT(*) FROM books").fetchone())  # (12,)

print("# Level 1, Q9")
print(conn.execute("SELECT id, title FROM books").fetchall())

print("# Level 1, Q10")
conn.close()
conn = sqlite3.connect(db_path)
print(conn.execute("SELECT COUNT(*) FROM books").fetchone())  # (12,)

print("# Level 1, Q11")
conn.execute("INSERT INTO books (title, author) VALUES ('Test Book', 'Nobody')")
print(conn.execute("SELECT COUNT(*) FROM books").fetchone())  # (13,) inside this connection
conn.close()  # no commit: the insert is thrown away
conn = sqlite3.connect(db_path)
print(conn.execute("SELECT COUNT(*) FROM books").fetchone())  # (12,)

print("# Level 1, Q12")
print(conn.execute("SELECT id, title, rating, title_length FROM books WHERE id = 6").fetchone())  # (6, 'Emma', None, 4)
conn.close()

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
mem = sqlite3.connect(":memory:")
mem.execute("""
    CREATE TABLE students (
        id   INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age  INTEGER,
        city TEXT DEFAULT 'Unknown'
    ) STRICT
""")
people = [
    {"name": "Ana", "age": 21, "city": "Toronto"},
    {"name": "Ben", "age": 23, "city": "London"},
    {"name": "Cy", "age": 22, "city": "Toronto"},
    {"name": "Di", "age": 20, "city": "Paris"},
]
cur = mem.executemany("INSERT INTO students (name, age, city) VALUES (:name, :age, :city)", people)
mem.commit()
print(cur.rowcount)  # 4
# Extra keys in the dictionary are ignored:
mem.execute("INSERT INTO students (name) VALUES (:name)", {"name": "Eli", "unused": 123})
print(mem.execute("SELECT COUNT(*) FROM students").fetchone())  # (5,)

print("# Level 2, Q2")
test = sqlite3.connect(":memory:")
test.execute("""
    CREATE TABLE books (id INTEGER PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL,
                        year INTEGER, pages INTEGER, genre TEXT, price_cents INTEGER, rating REAL) STRICT
""")


def add_book(conn, title, author, year=None, pages=None, genre=None, price_cents=None, rating=None):
    """Insert a book and return its new id."""
    cur = conn.execute(
        "INSERT INTO books (title, author, year, pages, genre, price_cents, rating) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (title, author, year, pages, genre, price_cents, rating),
    )
    conn.commit()
    return cur.lastrowid


print(add_book(test, "First", "A"))  # 1
print(add_book(test, "Second", "B", year=2020, genre="Tech"))  # 2

print("# Level 2, Q3")
mem.execute("""
    CREATE TABLE tasks (
        id      INTEGER PRIMARY KEY,
        title   TEXT NOT NULL,
        done    INTEGER DEFAULT 0,
        created TEXT DEFAULT CURRENT_TIMESTAMP
    ) STRICT
""")
mem.execute("INSERT INTO tasks (title) VALUES ('Write Day 3 notes')")
row = mem.execute("SELECT * FROM tasks").fetchone()
print(row[:3], "created is set:", bool(row[3]))  # (1, 'Write Day 3 notes', 0) created is set: True

print("# Level 2, Q4")
before = mem.execute("SELECT COUNT(*) FROM students").fetchone()[0]
for label, sql, params in [
    ("a", "INSERT INTO students (name, age) VALUES (?, ?)", ("Zed", 30, "Rome")),
    ("b", "INSERT INTO students (age) VALUES (?)", (3,)),
    ("c", "INSERT INTO students (id, name) VALUES (?, ?), (?, ?)", (100, "P", 100, "Q")),
]:
    try:
        mem.execute(sql, params)
    except sqlite3.Error as e:
        print(label, type(e).__name__, e)
print(mem.execute("SELECT COUNT(*) FROM students").fetchone()[0] == before)  # True: the two-row insert in (c) was all-or-nothing

print("# Level 2, Q5")
# The apostrophe in D'Arcy closes the SQL string early, so the statement is invalid.
# Fix: pass the value through a placeholder.
name = "D'Arcy"
mem.execute("INSERT INTO students (name) VALUES (?)", (name,))
print(mem.execute("SELECT name FROM students WHERE name = ?", (name,)).fetchone())  # ("D'Arcy",)

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1-3")


def load_countries(conn):
    conn.execute("DROP TABLE IF EXISTS countries")
    conn.execute("CREATE TABLE countries (name TEXT, capital TEXT, population INTEGER, currency TEXT)")
    data = json.loads((DATA / "countries_data.json").read_text(encoding="utf-8"))
    rows = [(c["name"], c["capital"] or None, c["population"], c["currency"]) for c in data]
    conn.executemany("INSERT INTO countries VALUES (?, ?, ?, ?)", rows)
    conn.commit()


def load_hn_posts(conn):
    conn.execute("DROP TABLE IF EXISTS hn_posts")
    conn.execute(
        "CREATE TABLE hn_posts (id INTEGER, title TEXT, url TEXT, num_points INTEGER,"
        " num_comments INTEGER, author TEXT, created_at TEXT)"
    )
    with (DATA / "hacker_news.csv").open(newline="", encoding="utf-8") as f:
        rows = [
            (int(r["id"]), r["title"], r["url"] or None, int(r["num_points"]), int(r["num_comments"]), r["author"], r["created_at"])
            for r in csv.DictReader(f)
        ]
    conn.executemany("INSERT INTO hn_posts VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    conn.commit()


ds = sqlite3.connect(WORK / "day03_datasets.db")
for _ in range(2):  # run twice: still exactly the same row counts
    load_countries(ds)
    load_hn_posts(ds)

q = lambda sql: ds.execute(sql).fetchone()
print(q("SELECT COUNT(*) FROM countries"))  # (250,)
print(q("SELECT COUNT(*) FROM countries WHERE capital IS NULL"))  # (5,)
print(q("SELECT COUNT(*) FROM countries WHERE population = 0"))  # (2,)
print(ds.execute("SELECT name, capital FROM countries LIMIT 3").fetchall())
print(q("SELECT COUNT(*) FROM hn_posts"))  # (20099,)
print(q("SELECT COUNT(*) FROM hn_posts WHERE url IS NULL"))  # (2440,)
print(ds.execute("SELECT id, title FROM hn_posts LIMIT 2").fetchall())
