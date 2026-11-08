# Day 6 reference solutions
import sqlite3

from helpers import datasets_conn, library_conn, show

lib = library_conn()
ds = datasets_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
show(lib.execute("SELECT upper(title) AS title FROM books ORDER BY id LIMIT 5"))

print("# Level 1, Q2")
show(lib.execute("SELECT title, length(title) AS letters FROM books ORDER BY letters DESC, title LIMIT 5"))

print("# Level 1, Q3")
show(lib.execute("SELECT title || ' by ' || author AS label FROM books ORDER BY id LIMIT 4"))

print("# Level 1, Q4")
show(lib.execute("SELECT title, substr(title, 1, 3) AS start FROM books ORDER BY id LIMIT 5"))

print("# Level 1, Q5")
show(lib.execute("SELECT replace(title, ' ', '_') AS slug FROM books ORDER BY id LIMIT 5"))

print("# Level 1, Q6")
show(lib.execute("SELECT title, coalesce(rating, 'unrated') AS rating FROM books ORDER BY title"))

print("# Level 1, Q7")
show(lib.execute("SELECT title, format('$%.2f', price_cents / 100.0) AS price FROM books WHERE price_cents >= 2000 ORDER BY price_cents"))

print("# Level 1, Q8")
show(lib.execute("SELECT title, rating, round(rating) AS rounded FROM books WHERE rating IS NOT NULL ORDER BY id LIMIT 5"))

print("# Level 1, Q9")
print(lib.execute("SELECT trim('   Dune  '), ltrim('   Dune  '), rtrim('   Dune  ')").fetchone())

print("# Level 1, Q10")
show(lib.execute("SELECT title, year, year / 10 * 10 AS decade FROM books ORDER BY year LIMIT 6"))

print("# Level 1, Q11")
show(lib.execute("SELECT title, pages, pages / 100 AS hundreds_int, pages / 100.0 AS hundreds FROM books ORDER BY id LIMIT 3"))

print("# Level 1, Q12")
show(lib.execute("SELECT title, pages, iif(pages > 400, 'long', 'short') AS size FROM books ORDER BY id LIMIT 6"))

print("# Level 1, Q13")
show(lib.execute("SELECT title, pages, abs(pages - 300) AS distance FROM books ORDER BY distance, title LIMIT 3"))

print("# Level 1, Q14")
show(lib.execute("SELECT typeof('5' + 1) AS t1, '5' + 1 AS v1, '5' || 1 AS v2, typeof(CAST('5' AS INTEGER)) AS t2"))

print("# Level 1, Q15")
show(lib.execute("SELECT upper(title) AS shout, lower(author) AS quiet FROM books ORDER BY id LIMIT 2"))

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
show(lib.execute("""
    SELECT title, pages,
           CASE WHEN pages < 300 THEN 'short'
                WHEN pages < 450 THEN 'medium'
                ELSE 'long' END AS length_class
    FROM books ORDER BY pages
"""))

print("# Level 2, Q2")
show(lib.execute("""
    SELECT author,
           substr(author, 1, 1) || substr(author, instr(author, ' ') + 1, 1) AS initials
    FROM books ORDER BY id
"""))
# 'J.R.R. Tolkien' -> JT works because the first space precedes 'Tolkien'; 'Robert C. Martin' -> RC (wrong: 3 parts).

print("# Level 2, Q3")
stats = sqlite3.connect(":memory:")
stats.execute("CREATE TABLE stats (player TEXT, hits INTEGER, attempts INTEGER)")
stats.executemany("INSERT INTO stats VALUES (?, ?, ?)", [("Ana", 30, 40), ("Ben", 5, 20), ("Cy", 0, 0), ("Di", 18, 24)])
show(stats.execute("""
    SELECT player, hits, attempts,
           round(100.0 * hits / nullif(attempts, 0), 1) AS pct,
           coalesce(round(100.0 * hits / nullif(attempts, 0), 1), 0.0) AS pct_or_zero
    FROM stats
"""))

print("# Level 2, Q4")
expressions = ["7 / 2", "7 / 2.0", "'5' + 1", "'5' || 1", "'a' || NULL", "substr('hello', -3)", "10 % 4", "length('')", "100 / 0"]
for e in expressions:
    print(f"{e:22} -> {stats.execute('SELECT ' + e).fetchone()[0]!r}")

print("# Level 2, Q5")
show(lib.execute("""
    SELECT title, rating,
           CASE WHEN rating IS NULL THEN 'unrated'
                WHEN rating >= 4.6 THEN 'excellent'
                WHEN rating >= 4.3 THEN 'good'
                ELSE 'okay' END AS verdict
    FROM books ORDER BY id
"""))

print("# Level 2, Q6")
show(lib.execute("SELECT format('BK-%04d', id) AS code, title FROM books ORDER BY id LIMIT 4"))

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
show(ds.execute("""
    SELECT id,
           substr(replace(replace(url, 'https://', ''), 'http://', ''),
                  1,
                  instr(replace(replace(url, 'https://', ''), 'http://', '') || '/', '/') - 1) AS domain
    FROM hn_posts WHERE url IS NOT NULL ORDER BY id LIMIT 8
"""))

print("# Level 3, Q2")
show(ds.execute("""
    SELECT name, population,
           CASE WHEN population < 1000000 THEN 'small'
                WHEN population < 10000000 THEN 'medium'
                WHEN population < 100000000 THEN 'large'
                ELSE 'huge' END AS size
    FROM countries ORDER BY name LIMIT 10
"""))

print("# Level 3, Q3")
show(ds.execute("""
    SELECT id, length(title) AS letters, substr(title, 1, 40) || '...' AS preview
    FROM hn_posts ORDER BY letters DESC, id LIMIT 5
"""))
