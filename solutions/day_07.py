# Day 7 reference solutions
import csv
import sqlite3

from helpers import DATA, datasets_conn, library_conn, show

lib = library_conn()
ds = datasets_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
print(lib.execute("SELECT COUNT(*) FROM books").fetchone())

print("# Level 1, Q2")
print(lib.execute("SELECT SUM(pages) FROM books").fetchone())

print("# Level 1, Q3")
print(lib.execute("SELECT round(AVG(rating), 2) FROM books").fetchone())

print("# Level 1, Q4")
show(lib.execute("SELECT MIN(year) AS oldest, MAX(year) AS newest FROM books"))

print("# Level 1, Q5")
show(lib.execute("SELECT COUNT(rating) AS rated, COUNT(*) - COUNT(rating) AS unrated FROM books"))

print("# Level 1, Q6")
show(lib.execute("SELECT genre, COUNT(*) AS books FROM books GROUP BY genre ORDER BY books DESC, genre"))

print("# Level 1, Q7")
show(lib.execute("SELECT genre, COUNT(*) AS books FROM books GROUP BY genre HAVING COUNT(*) > 2"))

print("# Level 1, Q8")
show(lib.execute("SELECT genre, round(AVG(pages), 1) AS avg_pages FROM books GROUP BY genre ORDER BY genre"))

print("# Level 1, Q9")
show(lib.execute("SELECT author, COUNT(*) AS books FROM books GROUP BY author HAVING COUNT(*) > 1 ORDER BY author"))

print("# Level 1, Q10")
print(lib.execute("SELECT COUNT(DISTINCT author) FROM books").fetchone())

print("# Level 1, Q11")
print(lib.execute("SELECT SUM(price_cents) / 100.0 AS total_dollars FROM books").fetchone())

print("# Level 1, Q12")
show(lib.execute("SELECT MIN(price_cents) AS cheapest, MAX(price_cents) AS dearest FROM books"))

print("# Level 1, Q13")
print(lib.execute("SELECT round(AVG(pages), 1) FROM books WHERE genre = 'Sci-Fi'").fetchone())

print("# Level 1, Q14")
show(lib.execute("SELECT genre, string_agg(title, ', ' ORDER BY title) AS titles FROM books GROUP BY genre ORDER BY genre"))

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
ages = sqlite3.connect(":memory:")
ages.execute("CREATE TABLE ages (age INTEGER)")
ages.executemany("INSERT INTO ages VALUES (?)", [(a,) for a in [19, 22, 19, 24, 20, 25, 26, 24, 25, 24]])
show(ages.execute("""
    SELECT MIN(age) AS min_age, MAX(age) AS max_age, AVG(age) AS avg_age,
           MAX(age) - MIN(age) AS age_range,
           round(abs(MIN(age) - AVG(age)), 2) AS min_gap, round(abs(MAX(age) - AVG(age)), 2) AS max_gap
    FROM ages
"""))
middle = [a for (a,) in ages.execute("SELECT age FROM ages ORDER BY age LIMIT 2 OFFSET 4")]
print("median:", sum(middle) / 2)

print("# Level 2, Q2")
show(lib.execute("SELECT author, COUNT(*) AS books, round(AVG(pages), 1) AS avg_pages FROM books GROUP BY author ORDER BY books DESC, author"))

print("# Level 2, Q3")
try:
    lib.execute("SELECT genre FROM books WHERE COUNT(*) > 2 GROUP BY genre")
except sqlite3.Error as e:
    print(type(e).__name__, e)
show(lib.execute("SELECT genre FROM books GROUP BY genre HAVING COUNT(*) > 2"))

print("# Level 2, Q4")
show(lib.execute("""
    SELECT round(AVG(rating), 2) AS avg_ignoring_nulls,
           round(SUM(rating) / COUNT(*), 2) AS sum_over_all_books,
           round(AVG(coalesce(rating, 0)), 2) AS avg_nulls_as_zero
    FROM books
"""))

print("# Level 2, Q5")
show(lib.execute("SELECT year / 10 * 10 AS decade, COUNT(*) AS books, SUM(pages) AS pages FROM books GROUP BY decade ORDER BY decade"))

print("# Level 2, Q6")
show(lib.execute("SELECT genre, round(AVG(rating), 2) AS avg_rating FROM books GROUP BY genre HAVING AVG(rating) > 4.5 ORDER BY avg_rating DESC"))

print("# Level 2, Q7")
show(lib.execute("SELECT COUNT(*) AS n, SUM(pages) AS total, AVG(pages) AS average, total(pages) AS total_fn FROM books WHERE year > 3000"))

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
ds.execute("DROP TABLE IF EXISTS people")
ds.execute("CREATE TABLE people (gender TEXT, height REAL, weight REAL)")
with (DATA / "weight-height.csv").open(newline="") as f:
    rows = [(r["Gender"], float(r["Height"]), float(r["Weight"])) for r in csv.DictReader(f)]
ds.executemany("INSERT INTO people VALUES (?, ?, ?)", rows)
ds.commit()
show(ds.execute("""
    SELECT gender, COUNT(*) AS n, round(AVG(height), 2) AS avg_height,
           round(AVG(weight), 2) AS avg_weight, round(MIN(height), 2) AS shortest, round(MAX(height), 2) AS tallest
    FROM people GROUP BY gender ORDER BY gender
"""))

print("# Level 3, Q2")
show(ds.execute("""
    SELECT author, COUNT(*) AS posts, round(AVG(num_points), 1) AS avg_points, round(AVG(num_comments), 1) AS avg_comments
    FROM hn_posts GROUP BY author HAVING COUNT(*) >= 10
    ORDER BY avg_points DESC, author LIMIT 10
"""))

print("# Level 3, Q3")
show(ds.execute("SELECT currency, COUNT(*) AS countries FROM countries GROUP BY currency ORDER BY countries DESC, currency LIMIT 10"))

print("# Level 3, Q4")
show(ds.execute("""
    SELECT COUNT(*) AS countries, SUM(population) AS world_population,
           COUNT(*) FILTER (WHERE population > 100000000) AS over_100m
    FROM countries
"""))
