# Review 4 reference solutions: Python and SQLite (Days 19-22)
import csv
import io
import json
import sqlite3
import threading
from contextlib import closing

from helpers import TODAY, WORK, library_full_conn, show
from library_repo import LibraryRepository

# ================================================================ Part A: write the query
print("# A1: sqlite3.Row")
conn = library_full_conn()
conn.row_factory = sqlite3.Row
for row in conn.execute("SELECT name, joined_on FROM members ORDER BY joined_on DESC LIMIT 2"):
    print(row["name"], row["joined_on"])

print("# A2: fetchmany")
cur = library_full_conn().execute("SELECT id FROM loans ORDER BY id")
sizes = []
while batch := cur.fetchmany(4):
    sizes.append(len(batch))
print(sizes)

print("# A3: initials()")
conn = library_full_conn()
conn.create_function("initials", 1, lambda name: "".join(w[0].upper() for w in name.split()), deterministic=True)
show(conn.execute("SELECT name, initials(name) AS initials FROM members ORDER BY id"))

print("# A4: a messy CSV into cents")
text = '''item;price;qty
"Pen";"$1.50";"10"
"Notebook";"$4.00";"3"
"Stapler";"n/a";"1"
"Glue";"$2,250.00";"2"
'''
d = sqlite3.connect(":memory:")
d.execute("CREATE TEMP TABLE raw (item TEXT, price TEXT, qty TEXT)")
reader = csv.reader(io.StringIO(text), delimiter=";")
next(reader)
d.executemany("INSERT INTO raw VALUES (?, ?, ?)", reader)
d.execute("""
    CREATE TEMP VIEW stripped AS
    SELECT item, replace(replace(trim(price), '$', ''), ',', '') AS price, trim(qty) AS qty FROM raw
""")
print(d.execute("""
    SELECT SUM(CAST(ROUND(CAST(price AS REAL) * 100) AS INTEGER) * CAST(qty AS INTEGER)) AS total_cents,
           (SELECT COUNT(*) FROM stripped WHERE NOT (price GLOB '*[0-9]*' AND price NOT GLOB '*[^0-9.]*')) AS rejected
    FROM stripped
    WHERE price GLOB '*[0-9]*' AND price NOT GLOB '*[^0-9.]*'
""").fetchone())

print("# A5: JSON totals per customer")
doc = json.dumps([
    {"customer": "Ana", "items": [{"sku": "PEN", "cents": 150, "qty": 2}, {"sku": "NOTE", "cents": 400, "qty": 1}]},
    {"customer": "Ben", "items": [{"sku": "PEN", "cents": 150, "qty": 5}]},
    {"customer": "Ana", "items": [{"sku": "BAG", "cents": 2500, "qty": 1}]},
])
show(sqlite3.connect(":memory:").execute("""
    SELECT o.value ->> 'customer' AS customer, SUM((i.value ->> 'cents') * (i.value ->> 'qty')) AS spent_cents
    FROM json_each(:doc) AS o
    JOIN json_each(o.value, '$.items') AS i
    GROUP BY customer ORDER BY spent_cents DESC, customer
""", {"doc": doc}))

print("# A6: an index on a 200,000-row table")
t = sqlite3.connect(":memory:")
t.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, grp INTEGER NOT NULL, val INTEGER NOT NULL) STRICT")
t.executemany("INSERT INTO t VALUES (?, ?, ?)", ((i, i % 1000, i % 7) for i in range(1, 200_001)))
Q = "SELECT COUNT(*), SUM(val) FROM t WHERE grp = 17"
print([r[3] for r in t.execute("EXPLAIN QUERY PLAN " + Q)])
t.execute("CREATE INDEX idx_t_grp ON t (grp)")
print([r[3] for r in t.execute("EXPLAIN QUERY PLAN " + Q)])
print(t.execute(Q).fetchone())

print("# A7: a view of loan counts")
conn = library_full_conn()
conn.execute("""
    CREATE VIEW member_loan_counts AS
    SELECT members.name AS member,
           COUNT(loans.id) AS total_loans,
           COUNT(loans.id) FILTER (WHERE loans.returned_on IS NULL) AS open_loans
    FROM members
    LEFT JOIN loans ON loans.member_id = members.id
    GROUP BY members.id
""")
show(conn.execute("SELECT * FROM member_loan_counts ORDER BY total_loans DESC, member"))

print("# A8: a trigger that keeps deleted members")
conn.executescript("""
    CREATE TABLE deleted_members (name TEXT NOT NULL, email TEXT NOT NULL) STRICT;
    CREATE TRIGGER trg_members_deleted AFTER DELETE ON members
    BEGIN
        INSERT INTO deleted_members (name, email) VALUES (OLD.name, OLD.email);
    END;
""")
conn.execute("DELETE FROM members WHERE name = 'Elena Rossi'")
print(conn.execute("SELECT name, email FROM deleted_members").fetchall())

# ================================================================ Part B: predict the output
print("# B1")
conn = library_full_conn()
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT id AS book_id, title FROM books WHERE id = 3").fetchone()
print(row["book_id"], row[1], len(row), row.keys(), row["BOOK_ID"])
try:
    row["id"]
except IndexError as e:
    print("IndexError:", e)

print("# B2")
c = sqlite3.connect(":memory:")
c.execute("CREATE TABLE t (x INTEGER PRIMARY KEY CHECK (x > 0)) STRICT")
try:
    with c:
        c.execute("INSERT INTO t VALUES (1)")
        c.execute("INSERT INTO t VALUES (2)")
        c.execute("INSERT INTO t VALUES (-3)")
except sqlite3.IntegrityError:
    print("error")
with c:
    c.execute("INSERT INTO t VALUES (4)")
print(c.execute("SELECT x FROM t").fetchall())
print(c.execute("SELECT 1").fetchone())

print("# B3")
print(sqlite3.connect(":memory:").execute("""
    SELECT CAST('abc' AS INTEGER), CAST('12abc' AS INTEGER), CAST('3.9' AS INTEGER), NULLIF('', '') IS NULL,
           '5' + '5', json_valid('{"a": 1'), '{"a": [1, 2]}' ->> '$.a', '{"a": [1, 2]}' ->> '$.a[1]'
""").fetchone())

print("# B4")
s = sqlite3.connect(":memory:")
s.executescript("""
    CREATE TABLE stock (sku TEXT PRIMARY KEY, qty INTEGER NOT NULL) STRICT;
    CREATE TABLE orders (sku TEXT NOT NULL, qty INTEGER NOT NULL) STRICT;
    INSERT INTO stock VALUES ('A', 10);
    CREATE TRIGGER trg_orders_check BEFORE INSERT ON orders
    WHEN NEW.qty > (SELECT qty FROM stock WHERE sku = NEW.sku)
    BEGIN SELECT RAISE(ABORT, 'too many'); END;
    CREATE TRIGGER trg_orders_take AFTER INSERT ON orders
    BEGIN UPDATE stock SET qty = qty - NEW.qty WHERE sku = NEW.sku; END;
""")
for qty in (4, 7, 6, 1):
    try:
        with s:
            s.execute("INSERT INTO orders VALUES ('A', ?)", (qty,))
        print("ok", qty)
    except sqlite3.IntegrityError as e:
        print("refused", qty, e)
print(s.execute("SELECT qty FROM stock").fetchone(), s.execute("SELECT COUNT(*) FROM orders").fetchone())

print("# B5")
p = sqlite3.connect(":memory:")
p.execute("CREATE TABLE t (a INTEGER, b INTEGER, c INTEGER)")
p.execute("CREATE INDEX idx_ab ON t (a, b)")
for where in ["a = 1", "b = 1", "a = 1 AND b > 5", "a > 1 AND b = 1", "a = 1 ORDER BY b"]:
    print(f"WHERE {where:20}", [r[3] for r in p.execute("EXPLAIN QUERY PLAN SELECT a, b FROM t WHERE " + where)])
print("SELECT c ... WHERE a = 1:", [r[3] for r in p.execute("EXPLAIN QUERY PLAN SELECT c FROM t WHERE a = 1")])

# ================================================================ Part C: find the bug
print("# C1: CAST turns a dash into 0")
m = sqlite3.connect(":memory:")
m.execute("CREATE TABLE firms (name TEXT, market_value TEXT)")
m.executemany("INSERT INTO firms VALUES (?, ?)", [("A", "100"), ("B", "-"), ("C", "300")])
print(m.execute("SELECT AVG(CAST(market_value AS INTEGER)) FROM firms").fetchone())   # bug: 133.33
print(m.execute("""
    SELECT AVG(CAST(market_value AS INTEGER)) FROM firms
    WHERE market_value GLOB '*[0-9]*' AND market_value NOT GLOB '*[^0-9.]*'
""").fetchone())
print(m.execute("""
    SELECT AVG(CASE WHEN market_value GLOB '*[0-9]*' AND market_value NOT GLOB '*[^0-9.]*' THEN CAST(market_value AS INTEGER) END) FROM firms
""").fetchone())

print("# C2: an index that is never used")
u = sqlite3.connect(":memory:")
u.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL) STRICT")
u.execute("CREATE INDEX idx_users_email ON users (email)")
Q = "SELECT id FROM users WHERE lower(email) = 'ana@example.com'"
print([r[3] for r in u.execute("EXPLAIN QUERY PLAN " + Q)])
u.execute("CREATE INDEX idx_users_email_lower ON users (lower(email))")
print([r[3] for r in u.execute("EXPLAIN QUERY PLAN " + Q)])

print("# C3: one connection, two threads")
shared = sqlite3.connect(":memory:")
errors = []
def use_it():
    try:
        shared.execute("SELECT 1")
    except sqlite3.ProgrammingError as e:
        errors.append(str(e))
th = threading.Thread(target=use_it)
th.start()
th.join()
print(errors[0].split(". ")[0])
def use_own():
    own = sqlite3.connect(":memory:")
    errors.append(own.execute("SELECT 42").fetchone()[0])
    own.close()
th = threading.Thread(target=use_own)
th.start()
th.join()
print(errors[1])

print("# C4: keyset paging on a column with duplicates")
k = sqlite3.connect(":memory:")
k.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, created TEXT NOT NULL) STRICT")
k.executemany("INSERT INTO posts VALUES (?, ?)", [(1, "a"), (2, "a"), (3, "a"), (4, "b"), (5, "c")])
page1 = k.execute("SELECT id, created FROM posts ORDER BY created LIMIT 2").fetchall()
page2 = k.execute("SELECT id, created FROM posts WHERE created > ? ORDER BY created LIMIT 2", (page1[-1][1],)).fetchall()
print(page1, page2)   # bug: id 3 is never shown
page1 = k.execute("SELECT id, created FROM posts ORDER BY created, id LIMIT 2").fetchall()
page2 = k.execute("SELECT id, created FROM posts WHERE (created, id) > (?, ?) ORDER BY created, id LIMIT 2", (page1[-1][1], page1[-1][0])).fetchall()
print(page1, page2)

# ================================================================ Part D: explain
print("# D1-D4")
# D1: `with conn:` ends a transaction (commit or rollback). It never closes the connection; contextlib.closing does.
# D2: WAL writes changes to a separate log file, so readers keep reading the old data while a writer works:
#     readers do not block the writer and the writer does not block readers. Writers still queue one at a time.
# D3: when the query matches a large share of the table, when the column is wrapped in a function, with a leading
#     wildcard LIKE, and on tables with many writes (each index must be updated on every insert).
# D4: generated column = value from the same row; view = a saved query over existing data; trigger = automatic
#     reaction to a change, possibly touching other tables.

# ================================================================ Part E: mini-project
print("# E: new acquisitions")
text = '''title;author;year;pages;price
"Hyperion";"Dan Simmons";"1989";"482";"$7.99"
"The Left Hand of Darkness";"Ursula K. Le Guin";"1969";"304";"$8.50"
"Broken row";"Nobody"
"Dune";"Frank Herbert";"1965";"612";"$10.99"
"Ancillary Justice";"Ann Leckie";"two thousand";"386";"$9.99"
"Piranesi";"Susanna Clarke";"2020";"272";"$11.25"
'''
conn = library_full_conn()
conn.executescript("""
    CREATE TABLE book_log (id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL, title TEXT NOT NULL) STRICT;
    CREATE TRIGGER trg_books_log AFTER INSERT ON books
    BEGIN
        INSERT INTO book_log (book_id, title) VALUES (NEW.id, NEW.title);
    END;
    CREATE VIEW books_per_author AS
    SELECT authors.name AS author, COUNT(*) AS books, SUM(books.pages) AS pages
    FROM authors JOIN books ON books.author_id = authors.id
    GROUP BY authors.id;
""")
repo = LibraryRepository(conn)
loaded, rejected = 0, []
reader = csv.reader(io.StringIO(text), delimiter=";")
next(reader)
for line_no, row in enumerate(reader, start=2):
    try:
        if len(row) != 5:
            raise ValueError(f"expected 5 fields, got {len(row)}")
        title, author, year, pages, price = row
        price_cents = round(float(price.replace("$", "").replace(",", "")) * 100)
        repo.add_book(title, author, year=int(year), pages=int(pages), price_cents=price_cents)
        loaded += 1
    except (ValueError, sqlite3.IntegrityError) as e:
        rejected.append((line_no, row[0], f"{type(e).__name__}: {e}"))
print("loaded", loaded, "rejected", len(rejected))
for r in rejected:
    print(r)
print(conn.execute("SELECT COUNT(*) FROM book_log").fetchone()[0])
show(conn.execute("SELECT * FROM books_per_author WHERE author IN ('Dan Simmons', 'Frank Herbert', 'Susanna Clarke') ORDER BY author"))
cur = conn.execute("SELECT author, books, pages FROM books_per_author ORDER BY books DESC, author LIMIT 3")
cols = [c[0] for c in cur.description]
out = WORK / "r4_authors.json"
out.write_text(json.dumps([dict(zip(cols, r)) for r in cur], indent=2), encoding="utf-8")
print(json.loads(out.read_text(encoding="utf-8"))[0])
print(conn.execute("SELECT json_group_array(json_object('author', author, 'books', books)) FROM (SELECT * FROM books_per_author ORDER BY books DESC, author LIMIT 2)").fetchone()[0])
