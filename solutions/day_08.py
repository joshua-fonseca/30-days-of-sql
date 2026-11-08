# Day 8 reference solutions
import sqlite3

from helpers import WORK, datasets_conn, library_conn, show

lib = library_conn()
ds = datasets_conn()

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
lib.execute("CREATE TABLE books_copy AS SELECT id, title, author, year, pages, genre, price_cents, rating FROM books")
lib.commit()
print(lib.execute("SELECT COUNT(*) FROM books_copy").fetchone())  # (12,)

print("# Level 1, Q2")
lib.execute("UPDATE books_copy SET rating = 4.2 WHERE title = 'Emma'")
lib.commit()
print(lib.execute("SELECT title, rating FROM books_copy WHERE title = 'Emma'").fetchone())

print("# Level 1, Q3")
lib.execute("UPDATE books_copy SET pages = pages + 1")
lib.commit()
print(lib.execute("SELECT SUM(pages) FROM books_copy").fetchone())  # (4920,)

print("# Level 1, Q4")
cur = lib.execute("UPDATE books_copy SET genre = 'Science Fiction' WHERE genre = 'Sci-Fi'")
lib.commit()
print(cur.rowcount)  # 4
show(lib.execute("SELECT genre, COUNT(*) AS books FROM books_copy GROUP BY genre ORDER BY genre"))

print("# Level 1, Q5")
lib.execute("UPDATE books_copy SET price_cents = price_cents * 9 / 10 WHERE genre = 'Tech'")
lib.commit()
show(lib.execute("SELECT title, price_cents FROM books_copy WHERE genre = 'Tech' ORDER BY title"))

print("# Level 1, Q6")
cur = lib.execute("DELETE FROM books_copy WHERE id = 12")
lib.commit()
print(cur.rowcount, lib.execute("SELECT COUNT(*) FROM books_copy").fetchone())  # 1 (11,)

print("# Level 1, Q7")
cur = lib.execute("DELETE FROM books_copy WHERE year < 1900 RETURNING id, title")
print(cur.fetchall())
lib.commit()

print("# Level 1, Q8")
cur = lib.execute("DELETE FROM books_copy")  # forgot the WHERE!
print("deleted", cur.rowcount, "->", lib.execute("SELECT COUNT(*) FROM books_copy").fetchone())
lib.rollback()
print("after rollback", lib.execute("SELECT COUNT(*) FROM books_copy").fetchone())  # (9,)

print("# Level 1, Q9")
cur = lib.execute("UPDATE books_copy SET rating = 4.9 WHERE title = 'Dune' RETURNING id, title, rating")
print(cur.fetchone())
lib.commit()

print("# Level 1, Q10")
with lib:
    lib.execute("UPDATE books_copy SET rating = 4.0 WHERE title = 'Neuromancer'")
    lib.execute("UPDATE books_copy SET rating = 4.8 WHERE title = 'The Hobbit'")
show(lib.execute("SELECT title, rating FROM books_copy WHERE title IN ('Neuromancer', 'The Hobbit') ORDER BY title"))

print("# Level 1, Q11")
cur = lib.execute("UPDATE books_copy SET rating = 1 WHERE title = 'No Such Book'")
print(cur.rowcount)  # 0
lib.rollback()

print("# Level 1, Q12")
lib.execute("DROP TABLE books_copy")
lib.commit()
print([r[0] for r in lib.execute("SELECT name FROM sqlite_master WHERE type = 'table'")])

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
bank = sqlite3.connect(":memory:")
bank.execute("""
    CREATE TABLE accounts (
        id            INTEGER PRIMARY KEY,
        owner         TEXT NOT NULL,
        balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0)
    ) STRICT
""")
bank.executemany("INSERT INTO accounts (owner, balance_cents) VALUES (?, ?)", [("Ana", 10000), ("Ben", 5000), ("Cy", 0)])
bank.commit()


def balances():
    return bank.execute("SELECT owner, balance_cents FROM accounts ORDER BY id").fetchall()


def transfer(conn, from_id, to_id, amount_cents):
    """Move money between accounts. Either both updates happen or neither does."""
    with conn:  # commits on success, rolls back if anything raises
        taken = conn.execute(
            "UPDATE accounts SET balance_cents = balance_cents - ? WHERE id = ?", (amount_cents, from_id)
        ).rowcount
        given = conn.execute(
            "UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?", (amount_cents, to_id)
        ).rowcount
        if taken != 1 or given != 1:
            raise ValueError("unknown account")


transfer(bank, 1, 2, 2500)
print(balances())  # Ana 7500, Ben 7500
for args in [(1, 2, 999999), (1, 99, 100)]:
    try:
        transfer(bank, *args)
    except (sqlite3.IntegrityError, ValueError) as e:
        print(type(e).__name__, e)
    print(balances())  # unchanged

print("# Level 2, Q2")
bank.execute("DELETE FROM accounts")
bank.executemany("INSERT INTO accounts (owner, balance_cents) VALUES (?, ?)", [("Ana", 10000), ("Ben", 5000), ("Cy", 0)])
bank.execute("""
    UPDATE accounts
    SET balance_cents = balance_cents + balance_cents * CASE WHEN balance_cents >= 10000 THEN 2 ELSE 1 END / 100
""")
bank.commit()
print(balances())

print("# Level 2, Q3")
lib.execute("CREATE TABLE books_soft AS SELECT id, title FROM books")
lib.execute("ALTER TABLE books_soft ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0")
lib.execute("UPDATE books_soft SET is_deleted = 1 WHERE id IN (1, 2)")  # soft delete
print(lib.execute("SELECT COUNT(*) FROM books_soft WHERE is_deleted = 0").fetchone())  # (10,)
lib.execute("UPDATE books_soft SET is_deleted = 0 WHERE id = 1")  # restore
print(lib.execute("SELECT COUNT(*) FROM books_soft WHERE is_deleted = 0").fetchone())  # (11,)
lib.execute("DROP TABLE books_soft")
lib.commit()

print("# Level 2, Q4")
lib.execute("CREATE TABLE books_copy AS SELECT id, title, price_cents FROM books")
lib.execute("CREATE TABLE new_prices (title TEXT, new_price_cents INTEGER)")
lib.executemany("INSERT INTO new_prices VALUES (?, ?)", [("Dune", 1199), ("Emma", 699), ("Unknown Book", 100)])
cur = lib.execute("""
    UPDATE books_copy SET price_cents = new_price_cents
    FROM new_prices WHERE books_copy.title = new_prices.title
    RETURNING books_copy.title, books_copy.price_cents
""")
print(sorted(cur.fetchall()))
lib.rollback()

print("# Level 2, Q5")
# Without a transaction, a crash between the two UPDATEs would take money from Ana and never give it to Ben.
# A transaction makes both updates one unit: it commits together or rolls back together.

print("# Level 2, Q6")
path = WORK / "day08_isolation.db"
path.unlink(missing_ok=True)
a = sqlite3.connect(path)
a.execute("CREATE TABLE t (x INTEGER)")
a.commit()
b = sqlite3.connect(path)
a.execute("INSERT INTO t VALUES (1)")
print("writer sees:", a.execute("SELECT COUNT(*) FROM t").fetchone()[0], "| other connection sees:", b.execute("SELECT COUNT(*) FROM t").fetchone()[0])
a.commit()
print("after commit, other connection sees:", b.execute("SELECT COUNT(*) FROM t").fetchone()[0])

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
ds.execute("CREATE TABLE countries_copy AS SELECT * FROM countries")
new_pops = {"Canada": 38000000, "Finland": 5500000, "Japan": 125000000, "Brazil": 212000000, "Norway": 5400000}
cur = ds.executemany(
    "UPDATE countries_copy SET population = :pop WHERE name = :name",
    [{"name": n, "pop": p} for n, p in new_pops.items()],
)
ds.commit()
print(cur.rowcount)  # 5
show(ds.execute("SELECT name, population FROM countries_copy WHERE name IN ('Canada', 'Finland', 'Japan', 'Brazil', 'Norway') ORDER BY name"))

print("# Level 3, Q2")
cur = ds.execute("DELETE FROM countries_copy WHERE population = 0 RETURNING name")
removed = [n for (n,) in cur.fetchall()]
ds.commit()
print(len(removed), sorted(removed))
print(ds.execute("SELECT COUNT(*) FROM countries_copy").fetchone())  # (248,)

print("# Level 3, Q3")
ds.execute("CREATE TABLE hn_copy AS SELECT * FROM hn_posts")
ds.commit()
cur = ds.execute("UPDATE hn_copy SET author = lower(author) WHERE author <> lower(author)")
print("authors changed:", cur.rowcount)
cur = ds.execute("DELETE FROM hn_copy WHERE num_points < 3")
print("posts removed:", cur.rowcount)
print("posts left:", ds.execute("SELECT COUNT(*) FROM hn_copy").fetchone()[0])
ds.rollback()
print("after rollback:", ds.execute("SELECT COUNT(*) FROM hn_copy").fetchone()[0])
