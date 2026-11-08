# Review 1 reference solutions (Days 1-10)
import sqlite3

from helpers import library_conn, library_full_conn, show

lib = library_conn()
full = library_full_conn()

print("# R1 Q1 write: Sci-Fi titles, newest first")
show(lib.execute("SELECT title, year FROM books WHERE genre = 'Sci-Fi' ORDER BY year DESC"))

print("# R1 Q2 write: books with rating, rating >= 4.5, by rating desc then title")
show(lib.execute("SELECT title, rating FROM books WHERE rating >= 4.5 ORDER BY rating DESC, title"))

print("# R1 Q3 write: books with no rating")
show(lib.execute("SELECT title FROM books WHERE rating IS NULL ORDER BY title"))

print("# R1 Q4 write: price in dollars, 2 decimals, for books between $10 and $20 inclusive")
show(lib.execute("SELECT title, printf('%.2f', price_cents / 100.0) AS price FROM books WHERE price_cents BETWEEN 1000 AND 2000 ORDER BY price_cents, title"))

print("# R1 Q5 write: books per genre, with average pages rounded to 0 dp, most books first")
show(lib.execute("SELECT genre, COUNT(*) AS books, CAST(round(AVG(pages)) AS INTEGER) AS avg_pages FROM books GROUP BY genre ORDER BY books DESC, genre"))

print("# R1 Q6 write: genres with total value over 2500 cents (HAVING)")
show(lib.execute("SELECT genre, SUM(price_cents) AS total_cents FROM books GROUP BY genre HAVING SUM(price_cents) > 2500 ORDER BY genre"))

print("# R1 Q7 write: title length category")
show(lib.execute("SELECT title, CASE WHEN pages < 300 THEN 'short' WHEN pages <= 500 THEN 'medium' ELSE 'long' END AS size FROM books ORDER BY pages, title"))

print("# R1 Q8 write: authors with more than one book")
show(lib.execute("SELECT author, COUNT(*) AS books FROM books GROUP BY author HAVING COUNT(*) > 1 ORDER BY author"))

print("# R1 Predict P1")
print(lib.execute("SELECT COUNT(*), COUNT(rating), ROUND(AVG(rating), 2) FROM books").fetchone())
print("# R1 Predict P2")
print(lib.execute("SELECT COUNT(*) FROM books WHERE genre NOT IN ('Sci-Fi', 'Fantasy', NULL)").fetchone())
print("# R1 Predict P3")
print(lib.execute("SELECT 7 / 2, 7 / 2.0, 7 % 2, 10 / 0, NULL + 1, 'a' || NULL").fetchone())
print("# R1 Predict P4")
print(lib.execute("SELECT MAX(year) - MIN(year) FROM books").fetchone())

print("# R1 Bug B1: WHERE with aggregate")
try:
    lib.execute("SELECT genre, COUNT(*) FROM books WHERE COUNT(*) > 1 GROUP BY genre")
except sqlite3.Error as e:
    print(type(e).__name__, e)
print("# R1 Bug B2: = NULL")
print(lib.execute("SELECT COUNT(*) FROM books WHERE rating = NULL").fetchone())
print("# R1 Bug B3: forgotten commit")
import os, tempfile
path = os.path.join(tempfile.mkdtemp(), "t.db")
a = sqlite3.connect(path); a.execute("CREATE TABLE t (x INTEGER)"); a.commit()
a.execute("INSERT INTO t VALUES (1)"); a.close()
print(sqlite3.connect(path).execute("SELECT COUNT(*) FROM t").fetchone())
print("# R1 Bug B4: string formatting / quotes")
try:
    lib.execute("SELECT * FROM books WHERE title = 'The Hobbit' OR 1=1 --'")
    print("injection returns", len(lib.execute("SELECT * FROM books WHERE title = '' OR 1=1 --'").fetchall()), "rows")
except sqlite3.Error as e:
    print(e)

print("# R1 Q9 normalized: books with author name")
show(full.execute("SELECT books.title, authors.name FROM books, authors WHERE books.author_id = authors.id AND authors.name = 'Andy Weir' ORDER BY books.title"))
print("# R1 Q10 normalized: counts")
print([full.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("authors", "books", "members", "loans")])
print("# R1 Q11: loans not returned")
print(full.execute("SELECT COUNT(*) FROM loans WHERE returned_on IS NULL").fetchone())
print("# R1 Q12: transaction")
t = sqlite3.connect(":memory:")
t.execute("CREATE TABLE acc (id INTEGER PRIMARY KEY, bal INTEGER NOT NULL CHECK (bal >= 0)) STRICT")
t.executemany("INSERT INTO acc (bal) VALUES (?)", [(100,), (50,)]); t.commit()
try:
    with t:
        t.execute("UPDATE acc SET bal = bal + 150 WHERE id = 2")
        t.execute("UPDATE acc SET bal = bal - 150 WHERE id = 1")  # fails
except sqlite3.IntegrityError as e:
    print(e)
print(t.execute("SELECT id, bal FROM acc").fetchall())

print("# Mini-project: reading journal")
j = sqlite3.connect(":memory:")
j.execute("PRAGMA foreign_keys = ON")
j.executescript("""
CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE) STRICT;
CREATE TABLE entries (id INTEGER PRIMARY KEY, title TEXT NOT NULL, written_on TEXT NOT NULL, minutes INTEGER NOT NULL CHECK (minutes > 0)) STRICT;
CREATE TABLE entry_tags (entry_id INTEGER NOT NULL REFERENCES entries (id) ON DELETE CASCADE, tag_id INTEGER NOT NULL REFERENCES tags (id), PRIMARY KEY (entry_id, tag_id)) STRICT;
""")

j.executemany("INSERT INTO entries (title, written_on, minutes) VALUES (?, ?, ?)", [
    ("SELECT basics", "2025-03-01", 30), ("Joins are hard", "2025-03-02", 45),
    ("Normalization", "2025-03-02", 60), ("Window ideas", "2025-03-05", 20)])
j.executemany("INSERT INTO tags (name) VALUES (?)", [("basics",), ("hard",), ("design",)])
j.executemany("INSERT INTO entry_tags VALUES (?, ?)", [(1, 1), (2, 2), (3, 2), (3, 3), (4, 2)])
show(j.execute("""SELECT tags.name AS tag, COUNT(*) AS entries, SUM(entries.minutes) AS minutes
    FROM entry_tags, tags, entries WHERE entry_tags.tag_id = tags.id AND entry_tags.entry_id = entries.id
    GROUP BY tags.name ORDER BY entries DESC, tag"""))
j.execute("DELETE FROM entries WHERE id = 3")
print(j.execute("SELECT COUNT(*) FROM entry_tags").fetchone())
