# Day 5 reference solutions
import sqlite3

from helpers import datasets_conn, library_conn, show

lib = library_conn()
ds = datasets_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
show(lib.execute("SELECT title, year FROM books WHERE year > 2000 ORDER BY year"))

print("# Level 1, Q2")
show(lib.execute("SELECT title FROM books WHERE author = 'Jane Austen' ORDER BY title"))

print("# Level 1, Q3")
show(lib.execute("SELECT title, genre FROM books WHERE genre IN ('Sci-Fi', 'Fantasy') ORDER BY title"))

print("# Level 1, Q4")
show(lib.execute("SELECT title FROM books WHERE title LIKE '%the%' ORDER BY title"))

print("# Level 1, Q5")
show(lib.execute("SELECT title, pages FROM books WHERE pages BETWEEN 300 AND 400 ORDER BY pages"))

print("# Level 1, Q6")
show(lib.execute("SELECT title FROM books WHERE rating IS NULL ORDER BY title"))

print("# Level 1, Q7")
show(lib.execute("SELECT title, rating FROM books WHERE rating IS NOT NULL ORDER BY rating DESC, title LIMIT 3"))

print("# Level 1, Q8")
show(lib.execute("SELECT title, genre FROM books WHERE genre <> 'Sci-Fi' ORDER BY title"))

print("# Level 1, Q9")
show(lib.execute("SELECT title FROM books WHERE title GLOB 'The*' ORDER BY title"))

print("# Level 1, Q10")
show(lib.execute("SELECT title, author FROM books WHERE author LIKE '%Weir' ORDER BY title"))

print("# Level 1, Q11")
show(lib.execute("SELECT title FROM books WHERE title LIKE '____' ORDER BY title"))

print("# Level 1, Q12")
show(lib.execute("SELECT title, year FROM books WHERE year < 1900 OR year > 2010 ORDER BY year"))

print("# Level 1, Q13")
show(lib.execute("SELECT title, price_cents, rating FROM books WHERE price_cents < 800 AND rating >= 4.5 ORDER BY title"))

print("# Level 1, Q14")
print(len(lib.execute("SELECT title FROM books WHERE year > 2000").fetchall()))  # 4

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")


def search_books(conn, keyword):
    pattern = f"%{keyword}%"
    rows = conn.execute(
        "SELECT title FROM books WHERE title LIKE ? OR author LIKE ? ORDER BY title", (pattern, pattern)
    )
    return [title for (title,) in rows]


print(search_books(lib, "jane"))
print(search_books(lib, "the"))
print(search_books(lib, "zzz"))

print("# Level 2, Q2")
for label, where in [
    ("a", "rating = NULL"),
    ("b", "rating <> 4.5"),
    ("c", "NOT (rating > 4.5)"),
    ("d", "rating > 4.5 OR rating IS NULL"),
]:
    print(label, len(lib.execute(f"SELECT title FROM books WHERE {where}").fetchall()))

print("# Level 2, Q3")
show(lib.execute("SELECT title, genre, pages FROM books WHERE genre = 'Sci-Fi' OR genre = 'Tech' AND pages > 400 ORDER BY title"))
show(lib.execute("SELECT title, genre, pages FROM books WHERE (genre = 'Sci-Fi' OR genre = 'Tech') AND pages > 400 ORDER BY title"))
# AND binds tighter than OR. The first query means: Sci-Fi (any length) OR (Tech AND long).

print("# Level 2, Q4")
print(lib.execute("SELECT title FROM books WHERE author = 'jane austen'").fetchall())  # []
print(lib.execute("SELECT title FROM books WHERE author = 'jane austen' COLLATE NOCASE ORDER BY title").fetchall())
print(lib.execute("SELECT title FROM books WHERE author LIKE 'jane austen' ORDER BY title").fetchall())

print("# Level 2, Q5")
lib.execute("CREATE TABLE codes (code TEXT)")
lib.executemany("INSERT INTO codes VALUES (?)", [("5%",), ("50",), ("5x",), ("15%",)])
print(lib.execute("SELECT code FROM codes WHERE code LIKE '5%'").fetchall())
print(lib.execute(r"SELECT code FROM codes WHERE code LIKE '5\%' ESCAPE '\'").fetchall())

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
show(ds.execute("SELECT name FROM countries WHERE name LIKE '%land%' ORDER BY name"))

print("# Level 3, Q2")
q = lambda sql: ds.execute(sql).fetchone()[0]
print("LIKE '%python%'      ", len(ds.execute("SELECT id FROM hn_posts WHERE title LIKE '%python%'").fetchall()))
print("GLOB '*python*'      ", len(ds.execute("SELECT id FROM hn_posts WHERE title GLOB '*python*'").fetchall()))
print("GLOB '*Python*'      ", len(ds.execute("SELECT id FROM hn_posts WHERE title GLOB '*Python*'").fetchall()))
print("GLOB '*[Pp]ython*'   ", len(ds.execute("SELECT id FROM hn_posts WHERE title GLOB '*[Pp]ython*'").fetchall()))

print("# Level 3, Q3")
show(ds.execute(
    "SELECT name, population FROM countries WHERE population BETWEEN 1000000 AND 5000000 AND currency = 'Euro' ORDER BY population DESC"
))

print("# Level 3, Q4")
show(ds.execute("SELECT id, title, num_points FROM hn_posts WHERE url IS NULL AND num_points > 100 ORDER BY num_points DESC, id LIMIT 5"))
print(len(ds.execute("SELECT id FROM hn_posts WHERE url IS NULL AND num_points > 100").fetchall()))
