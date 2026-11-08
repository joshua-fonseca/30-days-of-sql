# Day 10 reference solutions
import json
import sqlite3

from helpers import BOOKS_SCHEMA, DATA, LIBRARY_SCHEMA, LOANS, MEMBERS, datasets_conn, library_conn, show

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
# The flat table. Anomalies:
#  update anomaly: Ana's city is stored 3 times; change it in two rows and the data contradicts itself.
#  insert anomaly: you cannot record a new product until somebody orders it (order_id is part of the key).
#  delete anomaly: deleting Ben's only order erases everything we know about Ben.
flat = sqlite3.connect(":memory:")
flat.execute("""
    CREATE TABLE orders_flat (order_id INTEGER, customer TEXT, email TEXT, city TEXT, product TEXT, price_cents INTEGER, qty INTEGER)
""")
flat.executemany("INSERT INTO orders_flat VALUES (?, ?, ?, ?, ?, ?, ?)", [
    (1, "Ana", "ana@x.com", "Toronto", "Pen", 150, 2),
    (1, "Ana", "ana@x.com", "Toronto", "Notebook", 400, 1),
    (2, "Ben", "ben@x.com", "London", "Pen", 150, 5),
    (3, "Ana", "ana@x.com", "Toronto", "Stapler", 900, 1),
])
flat.execute("UPDATE orders_flat SET city = 'Ottawa' WHERE order_id IN (1, 3) AND product <> 'Notebook'")  # forgot a row
show(flat.execute("SELECT DISTINCT customer, city FROM orders_flat ORDER BY customer, city"))

print("# Level 1, Q2")
# 1 student - course: many-to-many; 2 person - passport: one-to-one; 3 customer - order: one-to-many;
# 4 author - book (a book has one author in our library): one-to-many; 5 book - member through loans: many-to-many

print("# Level 1, Q3")
# 1NF: every cell holds one value, and there are no repeating columns or lists packed in a cell.

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1-4")
lib = library_conn()  # 12 books as on Day 3, flat books table
# Day 9 rebuild, so we start from the same state as a student who finished Day 9
lib.execute("""
    CREATE TABLE books_new (
        id INTEGER PRIMARY KEY, title TEXT NOT NULL CHECK (length(title) > 0), author TEXT NOT NULL,
        year INTEGER CHECK (year BETWEEN 1000 AND 2100), pages INTEGER CHECK (pages > 0), genre TEXT,
        price_cents INTEGER CHECK (price_cents >= 0), rating REAL CHECK (rating BETWEEN 0 AND 5),
        title_length INTEGER GENERATED ALWAYS AS (length(title)) VIRTUAL, UNIQUE (title, author)
    ) STRICT
""")
lib.execute("INSERT INTO books_new (id, title, author, year, pages, genre, price_cents, rating) "
            "SELECT id, title, author, year, pages, genre, price_cents, rating FROM books")
lib.execute("DROP TABLE books")
lib.execute("ALTER TABLE books_new RENAME TO books")
lib.commit()
lib.execute("PRAGMA foreign_keys = ON")  # (a student would set this right after connecting)

# 1. authors
lib.execute("CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE) STRICT")
lib.execute("INSERT INTO authors (name) SELECT DISTINCT author FROM books ORDER BY author")
# 2. link the books to their authors
lib.execute("ALTER TABLE books ADD COLUMN author_id INTEGER REFERENCES authors (id)")
lib.execute("UPDATE books SET author_id = authors.id FROM authors WHERE authors.name = books.author")
print(lib.execute("SELECT COUNT(*) FROM authors").fetchone(), lib.execute("SELECT COUNT(*) FROM books WHERE author_id IS NULL").fetchone())
# 3. rebuild books without the text author column
lib.execute("""
    CREATE TABLE books_new (
        id INTEGER PRIMARY KEY, title TEXT NOT NULL CHECK (length(title) > 0),
        author_id INTEGER NOT NULL REFERENCES authors (id),
        year INTEGER CHECK (year BETWEEN 1000 AND 2100), pages INTEGER CHECK (pages > 0), genre TEXT,
        price_cents INTEGER CHECK (price_cents >= 0), rating REAL CHECK (rating BETWEEN 0 AND 5),
        title_length INTEGER GENERATED ALWAYS AS (length(title)) VIRTUAL, UNIQUE (title, author_id)
    ) STRICT
""")
lib.execute("""
    INSERT INTO books_new (id, title, author_id, year, pages, genre, price_cents, rating)
    SELECT id, title, author_id, year, pages, genre, price_cents, rating FROM books
""")
lib.execute("DROP TABLE books")
lib.execute("ALTER TABLE books_new RENAME TO books")
# 4. members and loans
lib.execute("""
    CREATE TABLE members (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, joined_on TEXT NOT NULL) STRICT
""")
lib.execute("""
    CREATE TABLE loans (
        id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL REFERENCES books (id),
        member_id INTEGER NOT NULL REFERENCES members (id),
        loaned_on TEXT NOT NULL, due_on TEXT NOT NULL, returned_on TEXT
    ) STRICT
""")
lib.executemany("INSERT INTO members (name, email, joined_on) VALUES (?, ?, ?)", MEMBERS)
lib.executemany("INSERT INTO loans (book_id, member_id, loaned_on, due_on, returned_on) VALUES (?, ?, ?, ?, ?)", LOANS)
lib.commit()
for t in ("authors", "books", "members", "loans"):
    print(t, lib.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
show(lib.execute("SELECT id, title, author_id FROM books ORDER BY id LIMIT 4"))
print(lib.execute("PRAGMA foreign_key_check").fetchall())

print("# Level 2, Q5")
try:
    lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (99, 1, '2025-03-14', '2025-03-28')")
except sqlite3.IntegrityError as e:
    print(e)
lib.rollback()

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1-3")
ds = datasets_conn()
ds.execute("PRAGMA foreign_keys = ON")
ds.execute("""
    CREATE TABLE countries_new (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, capital TEXT,
        population INTEGER NOT NULL CHECK (population >= 0), currency TEXT
    ) STRICT
""")
ds.execute("INSERT INTO countries_new (name, capital, population, currency) SELECT name, capital, population, currency FROM countries")
ds.execute("DROP TABLE countries")
ds.execute("ALTER TABLE countries_new RENAME TO countries")
ds.execute("CREATE TABLE languages (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE) STRICT")
ds.execute("""
    CREATE TABLE country_languages (
        country_id  INTEGER NOT NULL REFERENCES countries (id),
        language_id INTEGER NOT NULL REFERENCES languages (id),
        PRIMARY KEY (country_id, language_id)
    ) STRICT
""")
data = json.loads((DATA / "countries_data.json").read_text(encoding="utf-8"))
for c in data:
    country_id = ds.execute("SELECT id FROM countries WHERE name = ?", (c["name"],)).fetchone()[0]
    for lang in c["languages"]:
        ds.execute("INSERT OR IGNORE INTO languages (name) VALUES (?)", (lang,))
        language_id = ds.execute("SELECT id FROM languages WHERE name = ?", (lang,)).fetchone()[0]
        ds.execute("INSERT OR IGNORE INTO country_languages VALUES (?, ?)", (country_id, language_id))
ds.commit()
for t in ("countries", "languages", "country_languages"):
    print(t, ds.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
print(ds.execute("SELECT COUNT(*) FROM countries WHERE id NOT IN (SELECT country_id FROM country_languages)").fetchone())
print(ds.execute("PRAGMA foreign_key_check").fetchall())
show(ds.execute("SELECT id, name, capital FROM countries ORDER BY id LIMIT 3"))
