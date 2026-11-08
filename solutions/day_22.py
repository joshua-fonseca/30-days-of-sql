# Day 22 reference solutions: views and triggers
import sqlite3
from contextlib import closing

from helpers import DATA, TODAY, WORK, library_full_conn, show
from library_repo import AlreadyLoanedError, LibraryRepository, LoanLimitError


def shop_copy() -> sqlite3.Connection:
    """An in-memory copy of shop.db (Day 19's backup), so destructive exercises never touch the original."""
    src = sqlite3.connect(DATA / "shop.db")
    dest = sqlite3.connect(":memory:")
    src.backup(dest)
    src.close()
    dest.execute("PRAGMA foreign_keys = ON")
    return dest


# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1: view current_loans")
lib = library_full_conn()
lib.execute("""
    CREATE VIEW current_loans AS
    SELECT loans.id AS loan_id, books.title, members.name AS member, loans.loaned_on, loans.due_on
    FROM loans
    JOIN books   ON books.id = loans.book_id
    JOIN members ON members.id = loans.member_id
    WHERE loans.returned_on IS NULL
""")
show(lib.execute("SELECT * FROM current_loans ORDER BY due_on, loan_id"))

print("# Level 1, Q2: the stored definition")
print(lib.execute("SELECT type, name FROM sqlite_master WHERE type = 'view'").fetchall())

print("# Level 1, Q3: view overdue_loans")
lib.execute("""
    CREATE VIEW overdue_loans AS
    SELECT loan_id, title, member, due_on,
           CAST(julianday('2025-03-14') - julianday(due_on) AS INTEGER) AS days_overdue
    FROM current_loans
    WHERE due_on < '2025-03-14'
""")
show(lib.execute("SELECT * FROM overdue_loans ORDER BY due_on, loan_id"))

print("# Level 1, Q4: a view stores no data")
print(lib.execute("SELECT COUNT(*) FROM current_loans").fetchone())
lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (4, 5, '2025-03-14', '2025-03-28')")
print(lib.execute("SELECT COUNT(*) FROM current_loans").fetchone())

print("# Level 1, Q5: you cannot insert into a view")
try:
    lib.execute("INSERT INTO current_loans (title) VALUES ('x')")
except sqlite3.OperationalError as e:
    print("OperationalError:", e)

print("# Level 1, Q6: drop and recreate a view")
lib.execute("DROP VIEW IF EXISTS overdue_loans")
lib.execute("DROP VIEW IF EXISTS overdue_loans")  # no error
print(lib.execute("SELECT name FROM sqlite_master WHERE type = 'view'").fetchall())

print("# Level 1, Q7: a trigger that logs every new loan")
lib = library_full_conn()
lib.executescript("""
    CREATE TABLE loan_log (
        id        INTEGER PRIMARY KEY,
        loan_id   INTEGER NOT NULL,
        action    TEXT NOT NULL,
        logged_at TEXT NOT NULL DEFAULT (datetime('now'))
    ) STRICT;

    CREATE TRIGGER trg_loans_log_insert
    AFTER INSERT ON loans
    BEGIN
        INSERT INTO loan_log (loan_id, action) VALUES (NEW.id, 'loaned');
    END;
""")
lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (4, 5, '2025-03-14', '2025-03-28')")
show(lib.execute("SELECT loan_id, action FROM loan_log ORDER BY id"))

print("# Level 1, Q8: more loans, counted per action")
lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (6, 5, '2025-03-14', '2025-03-28')")
lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (8, 5, '2025-03-14', '2025-03-28')")
show(lib.execute("SELECT action, COUNT(*) AS n FROM loan_log GROUP BY action"))

print("# Level 1, Q9: a trigger that logs returns")
lib.execute("""
    CREATE TRIGGER trg_loans_log_return
    AFTER UPDATE OF returned_on ON loans
    WHEN OLD.returned_on IS NULL AND NEW.returned_on IS NOT NULL
    BEGIN
        INSERT INTO loan_log (loan_id, action) VALUES (NEW.id, 'returned');
    END
""")
lib.execute("UPDATE loans SET returned_on = '2025-03-14' WHERE id = 11")
lib.execute("UPDATE loans SET returned_on = '2025-03-15' WHERE id = 11")  # already returned: the WHEN clause skips it
show(lib.execute("SELECT loan_id, action FROM loan_log ORDER BY id"))

print("# Level 1, Q10: list the triggers")
print(lib.execute("SELECT name, tbl_name FROM sqlite_master WHERE type = 'trigger' ORDER BY name").fetchall())

print("# Level 1, Q11: drop a trigger")
lib.execute("DROP TRIGGER trg_loans_log_return")
lib.execute("UPDATE loans SET returned_on = '2025-03-14' WHERE id = 12")
print(lib.execute("SELECT COUNT(*) FROM loan_log WHERE action = 'returned'").fetchone())

print("# Level 1, Q12: a TEMP view lives only as long as the connection")
path = WORK / "d22_temp_view.db"
path.unlink(missing_ok=True)
with closing(sqlite3.connect(path)) as c:
    c.executescript("CREATE TABLE t (x INTEGER); INSERT INTO t VALUES (1), (2), (3);")
    c.execute("CREATE TEMP VIEW big AS SELECT x FROM t WHERE x >= 2")
    print(c.execute("SELECT COUNT(*) FROM big").fetchone())
with closing(sqlite3.connect(path)) as c:
    try:
        c.execute("SELECT COUNT(*) FROM big")
    except sqlite3.OperationalError as e:
        print("OperationalError:", e)

print("# Level 1, Q13-14: explain")
# A view is a saved SELECT: it holds no rows of its own, every use of it runs the query again on the current data.
# A table holds its rows, which only change when you change them.
# Triggers run by themselves when data changes, without the calling code mentioning them. Somebody reading the
# Python code that does the INSERT cannot see the extra work, which makes surprises and bugs hard to trace.

print("# Level 1, Q15: a view that hides a join")
lib = library_full_conn()
lib.execute("""
    CREATE VIEW book_catalog AS
    SELECT books.id, books.title, authors.name AS author, books.year, books.genre
    FROM books JOIN authors ON authors.id = books.author_id
""")
show(lib.execute("SELECT * FROM book_catalog WHERE genre = 'Sci-Fi' ORDER BY year, id"))

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1: block a loan of a book that is already out")
lib = library_full_conn()
lib.execute("""
    CREATE TRIGGER trg_loans_no_double_loan
    BEFORE INSERT ON loans
    WHEN EXISTS (SELECT 1 FROM loans WHERE book_id = NEW.book_id AND returned_on IS NULL)
    BEGIN
        SELECT RAISE(ABORT, 'book is already on loan');
    END
""")
try:
    lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (9, 5, '2025-03-14', '2025-03-28')")
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)
lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (4, 5, '2025-03-14', '2025-03-28')")
print(lib.execute("SELECT COUNT(*) FROM loans").fetchone()[0])
# the repository still catches this first with its own, friendlier check
repo = LibraryRepository(lib)
try:
    repo.lend(9, 5, "2025-03-14")
except AlreadyLoanedError as e:
    print("AlreadyLoanedError:", e)

print("# Level 2, Q2: updated_at on books")
lib.execute("ALTER TABLE books ADD COLUMN updated_at TEXT")
lib.execute("""
    CREATE TRIGGER trg_books_updated_at
    AFTER UPDATE ON books
    WHEN NEW.updated_at IS OLD.updated_at
    BEGIN
        UPDATE books SET updated_at = datetime('now') WHERE id = NEW.id;
    END
""")
print(lib.execute("SELECT COUNT(*) FROM books WHERE updated_at IS NOT NULL").fetchone()[0])
lib.execute("UPDATE books SET rating = 4.9 WHERE id = 1")
show(lib.execute("SELECT id, title, updated_at IS NOT NULL AS touched FROM books WHERE id IN (1, 2) ORDER BY id"))
print(lib.execute("SELECT length(updated_at) FROM books WHERE id = 1").fetchone()[0])

print("# Level 2, Q3: the order_totals view used three times")
shop = shop_copy()
shop.execute("""
    CREATE VIEW order_totals AS
    SELECT orders.order_id, orders.customer_id, orders.order_date, orders.status,
           COUNT(*) AS line_count,
           SUM(order_items.quantity * order_items.unit_price_cents) AS total_cents
    FROM orders
    JOIN order_items ON order_items.order_id = orders.order_id
    GROUP BY orders.order_id
""")
print("(a) the five biggest orders")
show(shop.execute("SELECT order_id, customer_id, total_cents FROM order_totals ORDER BY total_cents DESC, order_id LIMIT 5"))
print("(b) delivered revenue per year")
show(shop.execute("""
    SELECT substr(order_date, 1, 4) AS year, COUNT(*) AS orders, SUM(total_cents) / 100.0 AS revenue
    FROM order_totals WHERE status = 'delivered' GROUP BY year ORDER BY year
"""))
print("(c) the top 3 customers by spend")
show(shop.execute("""
    SELECT customers.first_name || ' ' || customers.last_name AS customer, SUM(order_totals.total_cents) / 100.0 AS spent
    FROM order_totals JOIN customers ON customers.customer_id = order_totals.customer_id
    WHERE order_totals.status <> 'cancelled'
    GROUP BY customers.customer_id ORDER BY SUM(order_totals.total_cents) DESC, customers.customer_id LIMIT 3
"""))

print("# Level 2, Q4: at most 3 open loans per member")
lib = library_full_conn()
lib.execute("""
    CREATE TRIGGER trg_loans_max_three
    BEFORE INSERT ON loans
    WHEN (SELECT COUNT(*) FROM loans WHERE member_id = NEW.member_id AND returned_on IS NULL) >= 3
    BEGIN
        SELECT RAISE(ABORT, 'member already has 3 books out');
    END
""")
for book in (4, 6, 8, 11):
    try:
        lib.execute("INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (?, 5, '2025-03-14', '2025-03-28')", (book,))
        print("lent", book)
    except sqlite3.IntegrityError as e:
        print("refused", book, "-", e)
repo = LibraryRepository(lib)
try:
    repo.lend(11, 5, "2025-03-14")
except LoanLimitError as e:
    print("LoanLimitError:", e)

print("# Level 2, Q5: a price history trigger")
lib = library_full_conn()
lib.executescript("""
    CREATE TABLE price_history (
        id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL, old_price_cents INTEGER, new_price_cents INTEGER,
        changed_at TEXT NOT NULL DEFAULT (datetime('now'))
    ) STRICT;
    CREATE TRIGGER trg_books_price_history
    AFTER UPDATE OF price_cents ON books
    WHEN OLD.price_cents IS NOT NEW.price_cents
    BEGIN
        INSERT INTO price_history (book_id, old_price_cents, new_price_cents) VALUES (NEW.id, OLD.price_cents, NEW.price_cents);
    END;
""")
lib.execute("UPDATE books SET price_cents = price_cents + 100 WHERE genre = 'Tech'")
lib.execute("UPDATE books SET price_cents = 5099 WHERE id = 9")   # same value again: nothing logged
show(lib.execute("SELECT book_id, old_price_cents, new_price_cents FROM price_history ORDER BY id"))

print("# Level 2, Q6: generated column or trigger?")
# A generated column is right when the value is computed from other columns of the same row (title_length).
# A trigger is needed when the effect touches other rows or tables (a log, a stock count) or depends on the old
# value (updated_at, price history). A view is right when you only want a different way to look at existing data.
gen = sqlite3.connect(":memory:")
gen.execute("""
    CREATE TABLE lines (qty INTEGER, unit_cents INTEGER, total_cents INTEGER GENERATED ALWAYS AS (qty * unit_cents) STORED) STRICT
""")
gen.execute("INSERT INTO lines (qty, unit_cents) VALUES (3, 250)")
print(gen.execute("SELECT * FROM lines").fetchall())
try:
    gen.execute("UPDATE lines SET total_cents = 1")
except sqlite3.OperationalError as e:
    print("OperationalError:", e)

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1: stock management")
shop = shop_copy()
shop.executescript("""
    CREATE TRIGGER trg_items_check_stock
    BEFORE INSERT ON order_items
    WHEN NEW.quantity > (SELECT stock FROM products WHERE product_id = NEW.product_id)
    BEGIN
        SELECT RAISE(ABORT, 'not enough stock');
    END;

    CREATE TRIGGER trg_items_take_stock
    AFTER INSERT ON order_items
    BEGIN
        UPDATE products SET stock = stock - NEW.quantity WHERE product_id = NEW.product_id;
    END;

    CREATE TRIGGER trg_items_return_stock
    AFTER DELETE ON order_items
    BEGIN
        UPDATE products SET stock = stock + OLD.quantity WHERE product_id = OLD.product_id;
    END;
""")
shop.execute("INSERT INTO orders (order_id, customer_id, order_date, status) VALUES (400, 1, '2026-01-05', 'pending')")
shop.execute("INSERT INTO orders (order_id, customer_id, order_date, status) VALUES (401, 2, '2026-01-05', 'pending')")
print(shop.execute("SELECT product_id, stock FROM products WHERE product_id IN (1, 2, 3) ORDER BY product_id").fetchall())
steps = [
    (400, 1, 3, 2499),    # ok: product 1 stock 23 -> 20
    (400, 2, 2, 999),     # ok: product 2 stock 2 -> 0
    (401, 2, 1, 999),     # refused: product 2 is sold out
    (401, 1, 10, 2499),   # ok: product 1 stock 20 -> 10
    (401, 3, 100, 5999),  # refused: only 63 in stock
    (401, 3, 13, 5999),   # ok: product 3 stock 63 -> 50
]
for order_id, product_id, qty, price in steps:
    try:
        with shop:
            shop.execute("INSERT INTO order_items VALUES (?, ?, ?, ?)", (order_id, product_id, qty, price))
        print("ok     ", (order_id, product_id, qty))
    except sqlite3.IntegrityError as e:
        print("refused", (order_id, product_id, qty), "-", e)
print(shop.execute("SELECT product_id, stock FROM products WHERE product_id IN (1, 2, 3) ORDER BY product_id").fetchall())
with shop:
    shop.execute("DELETE FROM order_items WHERE order_id = 400 AND product_id = 1")   # the customer removes the mouse
print(shop.execute("SELECT product_id, stock FROM products WHERE product_id IN (1, 2, 3) ORDER BY product_id").fetchall())
print(shop.execute("SELECT COUNT(*) FROM products WHERE stock < 0").fetchone())
