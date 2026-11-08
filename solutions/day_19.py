# Day 19 reference solutions: the sqlite3 module in depth
import re
import sqlite3
import threading
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from helpers import TODAY, WORK, datasets_conn, library_full_conn, show, DATA, ROOT

# The LibraryRepository reference implementation lives in solutions/library_repo.py (an importable module,
# because Days 22, 27 and 28 reuse it). Level 2, Q1 below uses it.
from library_repo import (AlreadyLoanedError, LibraryError, LibraryRepository, LoanLimitError, NotFoundError)


def fresh_copy(name: str) -> Path:
    """Level 1, Q1: work on a copy of the library so the original stays safe (conn.backup)."""
    path = WORK / name
    for suffix in ("", "-wal", "-shm"):
        Path(str(path) + suffix).unlink(missing_ok=True)
    src = library_full_conn()
    with closing(sqlite3.connect(path)) as dest:
        src.backup(dest)
    return path


# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1: copy the library with backup()")
copy_path = fresh_copy("d19_library.db")
conn = sqlite3.connect(copy_path)
print(conn.execute("SELECT COUNT(*) FROM books").fetchone())

print("# Level 1, Q2: sqlite3.Row, access by name")
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT id, title, year FROM books ORDER BY id LIMIT 1").fetchone()
print(row["title"], row["year"])

print("# Level 1, Q3: rows as dicts")
for r in conn.execute("SELECT id, title, year FROM books ORDER BY year DESC, title LIMIT 3"):
    print(dict(r))

print("# Level 1, Q4: column names of a row")
print(row.keys())

print("# Level 1, Q5: fetchmany in batches of 5")
cur = conn.execute("SELECT id FROM books ORDER BY id")
sizes = []
while batch := cur.fetchmany(5):
    sizes.append(len(batch))
print(sizes)

print("# Level 1, Q6: OperationalError from a typo")
try:
    conn.execute("SELECT titel FROM books")
except sqlite3.OperationalError as e:
    print("OperationalError:", e)

print("# Level 1, Q7: IntegrityError from a duplicate email")
try:
    conn.execute("INSERT INTO members (name, email, joined_on) VALUES ('Imposter', 'alice@example.com', '2025-03-14')")
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)

print("# Level 1, Q8: with conn rolls back, closing() closes")
try:
    with conn:
        conn.execute("DELETE FROM loans")
        raise RuntimeError("changed my mind")
except RuntimeError:
    pass
print(conn.execute("SELECT COUNT(*) FROM loans").fetchone()[0])
conn.close()
with closing(sqlite3.connect(copy_path)) as c:
    print(c.execute("SELECT COUNT(*) FROM members").fetchone()[0])
try:
    c.execute("SELECT 1")
except sqlite3.ProgrammingError as e:
    print("ProgrammingError:", e)

print("# Level 1, Q9: executescript from a schema file")
schema_file = WORK / "d19_reading.sql"
schema_file.write_text("""
CREATE TABLE reading_lists (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE) STRICT;
CREATE TABLE reading_list_items (
    list_id INTEGER NOT NULL REFERENCES reading_lists (id),
    book_id INTEGER NOT NULL REFERENCES books (id),
    PRIMARY KEY (list_id, book_id)
) STRICT;
INSERT INTO reading_lists (name) VALUES ('Summer'), ('Classics');
""", encoding="utf-8")
conn = sqlite3.connect(copy_path)
conn.executescript(schema_file.read_text(encoding="utf-8"))
print(conn.execute("SELECT name FROM reading_lists ORDER BY name").fetchall())

print("# Level 1, Q10: journal mode")
print(conn.execute("PRAGMA journal_mode").fetchone()[0])
print(conn.execute("PRAGMA journal_mode = WAL").fetchone()[0])
conn.close()
conn = sqlite3.connect(copy_path)
print(conn.execute("PRAGMA journal_mode").fetchone()[0], "(the setting is stored in the file)")

print("# Level 1, Q11: dataclass records")
@dataclass
class Member:
    id: int
    name: str
    email: str
    joined_on: str

conn.row_factory = sqlite3.Row
members = [Member(**r) for r in conn.execute("SELECT * FROM members ORDER BY id")]
print(members[-1])
print(len(members))

print("# Level 1, Q12: ATTACH and schema.table")
conn.execute("ATTACH DATABASE ? AS backup_db", (str(copy_path),))
print(conn.execute("SELECT COUNT(*) FROM backup_db.books").fetchone()[0])
print([r[1] for r in conn.execute("PRAGMA database_list")])

print("# Level 1, Q13: iterdump")
dump = list(conn.iterdump())
print(len(dump) > 40, dump[0])

print("# Level 1, Q14: a registered SQL function")
conn.create_function("shout", 1, lambda s: None if s is None else s.upper() + "!", deterministic=True)
print(conn.execute("SELECT shout(title) FROM books WHERE id = 1").fetchone()[0])

print("# Level 1, Q15: explain in your own words")
# `with conn:` ends a transaction (commit on success, rollback on an exception). It never closes the
# connection, because a connection often outlives many transactions. closing() is what closes it.
# SQLite has no stored procedures because it has no server: your Python code already runs next to the data,
# so a function that does several steps in one transaction plays the role of the procedure.
conn.close()

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1: LibraryRepository")
repo = LibraryRepository(library_full_conn())
new_book = repo.add_book("Hyperion", "Dan Simmons", year=1989, pages=482, genre="Sci-Fi")
new_member = repo.add_member("Farid Haddad", "farid@example.com", "2025-03-01")
print(new_book, new_member)
print(repo.get_book(new_book))
loan_id = repo.lend(new_book, new_member, "2025-03-14")
print(loan_id, repo.active_loans(new_member))
for attempt in (lambda: repo.lend(new_book, 1, "2025-03-14"), lambda: repo.lend(999, 1, "2025-03-14")):
    try:
        attempt()
    except LibraryError as e:
        print(type(e).__name__ + ":", e)
for book in (4, 6):
    repo.lend(book, new_member, "2025-03-14")
try:
    repo.lend(8, new_member, "2025-03-14")
except LoanLimitError as e:
    print("LoanLimitError:", e)
repo.return_book(new_book, "2025-03-20")
print(repo.lend(8, new_member, "2025-03-21"))
print([b.title for b in repo.find_by_author("weir")])
print(repo.overdue(TODAY))

print("# Level 2, Q2: word_count()")
conn = library_full_conn()
conn.create_function("word_count", 1, lambda s: len(s.split()) if s else 0, deterministic=True)
show(conn.execute("SELECT title, word_count(title) AS words FROM books WHERE word_count(title) >= 3 ORDER BY words DESC, title"))

print("# Level 2, Q3: a median aggregate")
class Median:
    def __init__(self):
        self.values = []

    def step(self, value):
        if value is not None:
            self.values.append(value)

    def finalize(self):
        if not self.values:
            return None
        s = sorted(self.values)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2

conn.create_aggregate("median", 1, Median)
show(conn.execute("SELECT genre, median(pages) AS median_pages, COUNT(*) AS n FROM books GROUP BY genre ORDER BY genre"))

print("# Level 2, Q4: ATTACH a backup and find what was deleted")
old_path = WORK / "d19_old.db"
old_path.unlink(missing_ok=True)
with closing(sqlite3.connect(old_path)) as dest:
    conn.backup(dest)
conn.execute("DELETE FROM loans WHERE book_id = 12")  # a loan points at book 12, so it goes first
conn.execute("DELETE FROM books WHERE id = 12")
conn.execute("ATTACH DATABASE ? AS old", (str(old_path),))
show(conn.execute("""
    SELECT old.books.id, old.books.title
    FROM old.books
    LEFT JOIN main.books ON main.books.id = old.books.id
    WHERE main.books.id IS NULL
"""))

print("# Level 2, Q5: database is locked")
lock_path = WORK / "d19_lock.db"
for suffix in ("", "-wal", "-shm"):
    Path(str(lock_path) + suffix).unlink(missing_ok=True)
writer = sqlite3.connect(lock_path, autocommit=True)
other = sqlite3.connect(lock_path, timeout=0, autocommit=True)
writer.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT) STRICT")
writer.execute("BEGIN IMMEDIATE")
writer.execute("INSERT INTO notes (body) VALUES ('first')")
try:
    other.execute("INSERT INTO notes (body) VALUES ('second')")
except sqlite3.OperationalError as e:
    print("OperationalError:", e)
writer.execute("COMMIT")
other.execute("INSERT INTO notes (body) VALUES ('second')")
print(other.execute("SELECT COUNT(*) FROM notes").fetchone()[0])
writer.close()
other.close()

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1: REGEXP on Hacker News titles")
hn = datasets_conn()
hn.create_function("regexp", 2, lambda pattern, text: text is not None and re.search(pattern, text) is not None, deterministic=True)
show(hn.execute(r"""
    SELECT SUM(title REGEXP '^Ask HN')                          AS ask_hn,
           SUM(title REGEXP '^Show HN')                         AS show_hn,
           SUM(title REGEXP '\?\s*$')                           AS ends_with_question,
           SUM(title REGEXP '^(Ask|Show) HN' AND title REGEXP '\?\s*$') AS both
    FROM hn_posts
"""))
show(hn.execute(r"""
    SELECT title, num_points FROM hn_posts
    WHERE title REGEXP '^Ask HN' AND title REGEXP '\?\s*$'
    ORDER BY num_points DESC, title LIMIT 3
"""))

print("# Level 3, Q2: back up shop.db and compare counts")
shop = sqlite3.connect(DATA / "shop.db")
shop_copy_path = WORK / "d19_shop_copy.db"
shop_copy_path.unlink(missing_ok=True)
with closing(sqlite3.connect(shop_copy_path)) as dest:
    shop.backup(dest)
tables = [r[0] for r in shop.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
with closing(sqlite3.connect(shop_copy_path)) as copy:
    ok = True
    for t in tables:
        a = shop.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        b = copy.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t:20} {a:5} {b:5} {'ok' if a == b else 'MISMATCH'}")
        ok = ok and a == b
print("all equal:", ok)
shop.close()

print("# Level 3, Q3: four writer threads")
def make_db(path: Path, wal: bool) -> None:
    for suffix in ("", "-wal", "-shm"):
        Path(str(path) + suffix).unlink(missing_ok=True)
    with closing(sqlite3.connect(path)) as c:
        if wal:
            c.execute("PRAGMA journal_mode = WAL")
        c.execute("CREATE TABLE inserts (id INTEGER PRIMARY KEY, worker INTEGER NOT NULL, n INTEGER NOT NULL) STRICT")
        c.commit()


def worker(path: Path, worker_id: int, timeout: float, errors: list) -> None:
    conn = sqlite3.connect(path, timeout=timeout)  # one connection per thread
    failed = 0
    for n in range(1000):
        try:
            with conn:
                conn.execute("INSERT INTO inserts (worker, n) VALUES (?, ?)", (worker_id, n))
        except sqlite3.OperationalError:
            failed += 1
    conn.close()
    errors.append(failed)


def run(path: Path, timeout: float):
    errors: list[int] = []
    threads = [threading.Thread(target=worker, args=(path, i, timeout, errors)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    with closing(sqlite3.connect(path)) as c:
        saved = c.execute("SELECT COUNT(*) FROM inserts").fetchone()[0]
    return saved, sum(errors)

path = WORK / "d19_threads.db"
make_db(path, wal=False)
saved, failed = run(path, timeout=0)
print("default journal, timeout=0: some inserts failed:", failed > 0, "| saved + failed =", saved + failed)
make_db(path, wal=True)
saved, failed = run(path, timeout=30)
print("WAL + timeout=30: saved", saved, "failed", failed)
assert saved == 4000 and failed == 0
