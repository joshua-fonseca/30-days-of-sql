# Day 4 reference solutions
from helpers import datasets_conn, library_conn, show

lib = library_conn()  # the 12 books exactly as inserted on Day 3
ds = datasets_conn()  # countries + hn_posts exactly as loaded on Day 3

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
print(lib.execute("SELECT * FROM books").fetchall())

print("# Level 1, Q2")
print(lib.execute("SELECT title FROM books").fetchall())

print("# Level 1, Q3")
print(lib.execute("SELECT title, author FROM books").fetchall())

print("# Level 1, Q4")
show(lib.execute("SELECT title AS book, year AS published FROM books"))

print("# Level 1, Q5")
print(lib.execute("SELECT DISTINCT genre FROM books").fetchall())

print("# Level 1, Q6")
show(lib.execute("SELECT title, year FROM books ORDER BY year"))

print("# Level 1, Q7")
show(lib.execute("SELECT title, pages FROM books ORDER BY pages DESC"))

print("# Level 1, Q8")
show(lib.execute("SELECT title, year FROM books ORDER BY year DESC LIMIT 3"))

print("# Level 1, Q9")
show(lib.execute("SELECT title, year FROM books ORDER BY year LIMIT 3"))

print("# Level 1, Q10")
show(lib.execute("SELECT id, title FROM books ORDER BY title LIMIT 4 OFFSET 4"))

print("# Level 1, Q11")
show(lib.execute("SELECT genre, title FROM books ORDER BY genre, title"))

print("# Level 1, Q12")
show(lib.execute("SELECT title, price_cents / 100.0 AS price_dollars FROM books LIMIT 4"))

print("# Level 1, Q13")
show(lib.execute("SELECT id, title, author FROM books"))

print("# Level 1, Q14")
show(lib.execute("SELECT title, price_cents FROM books ORDER BY price_cents, title LIMIT 5"))

print("# Level 1, Q15")
print(len(lib.execute("SELECT author FROM books").fetchall()))  # 12
print(len(lib.execute("SELECT DISTINCT author FROM books").fetchall()))  # 10

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")


def show_aligned(cur):
    """Like show(), but numbers are right-aligned."""
    headers = [col[0] for col in cur.description]
    rows = cur.fetchall()
    is_num = [all(isinstance(r[i], (int, float)) or r[i] is None for r in rows) and any(r[i] is not None for r in rows)
              for i in range(len(headers))]
    cells = [["NULL" if v is None else str(v) for v in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]

    def fmt(values):
        return "  ".join(v.rjust(w) if num else v.ljust(w) for v, w, num in zip(values, widths, is_num)).rstrip()

    print(fmt(headers))
    print("  ".join("-" * w for w in widths))
    for r in cells:
        print(fmt(r))
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")


show_aligned(lib.execute("SELECT title, pages, rating FROM books LIMIT 3"))

print("# Level 2, Q2")


def paginate(conn, page, per_page):
    offset = (page - 1) * per_page
    rows = conn.execute("SELECT title FROM books ORDER BY id LIMIT ? OFFSET ?", (per_page, offset))
    return [title for (title,) in rows]


print(paginate(lib, 1, 5))
print(paginate(lib, 3, 5))
print(paginate(lib, 4, 5))

print("# Level 2, Q3")
show(lib.execute("SELECT title, year, 2025 - year AS age FROM books ORDER BY age DESC, title LIMIT 3"))

print("# Level 2, Q4")
show(lib.execute("SELECT genre, title, pages FROM books ORDER BY genre, pages DESC"))

print("# Level 2, Q5")
show(lib.execute("SELECT title, rating FROM books ORDER BY rating, title"))
show(lib.execute("SELECT title, rating FROM books ORDER BY rating NULLS LAST, title"))
# In SQLite NULL counts as the smallest value, so ascending puts NULLs first and descending puts them last.
# NULLS LAST / NULLS FIRST lets you choose.

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
show(ds.execute("SELECT name, population FROM countries ORDER BY population DESC LIMIT 10"))

print("# Level 3, Q2")
show(ds.execute("SELECT title, num_points, author FROM hn_posts ORDER BY num_points DESC, id LIMIT 5"))

print("# Level 3, Q3")
print(len(ds.execute("SELECT DISTINCT currency FROM countries").fetchall()))

print("# Level 3, Q4")
show(ds.execute("SELECT name FROM countries ORDER BY name LIMIT 10 OFFSET 20"))
