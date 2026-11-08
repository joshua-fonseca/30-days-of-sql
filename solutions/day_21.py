# Day 21 reference solutions: indexes and query performance
import csv
import shutil
import sqlite3
import time
from itertools import batched

from helpers import DATA, WORK, datasets_conn, events_db_path, library_full_conn, show


def best_time(conn, sql, params=(), repeat=3):
    """Smallest wall-clock time of `repeat` runs, in seconds."""
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        conn.execute(sql, params).fetchall()
        times.append(time.perf_counter() - start)
    return min(times)


def plan(conn, sql, params=()):
    """The detail column of EXPLAIN QUERY PLAN, one string per step."""
    return [row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params)]


# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1: the big file exists")
csv_path = DATA / "big_events.csv"
print(csv_path.exists(), csv_path.stat().st_size > 40_000_000)

print("# Level 1, Q2: load it into SQLite")
db_path = WORK / "d21_events.db"
db_path.unlink(missing_ok=True)
conn = sqlite3.connect(db_path)
conn.execute("""
    CREATE TABLE events (
        event_id     INTEGER PRIMARY KEY,
        user_id      INTEGER NOT NULL,
        event_type   TEXT NOT NULL,
        ts           TEXT NOT NULL,
        amount_cents INTEGER
    ) STRICT
""")
with open(csv_path, newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)
    rows = ((int(i), int(u), t, ts, round(float(a) * 100) if a else None) for i, u, t, ts, a in reader)
    for chunk in batched(rows, 50_000):
        conn.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?)", chunk)
conn.commit()
print(conn.execute("SELECT COUNT(*) FROM events").fetchone())
print(conn.execute("SELECT * FROM events ORDER BY event_id LIMIT 1").fetchone())

print("# Level 1, Q3: one user's events")
Q = "SELECT COUNT(*), SUM(amount_cents) FROM events WHERE user_id = ?"
print(conn.execute(Q, (12345,)).fetchone())

print("# Level 1, Q4: the plan without an index")
print(plan(conn, Q, (12345,)))

print("# Level 1, Q5: time it")
before = best_time(conn, Q, (12345,))
print("took", round(before * 1000, 1), "ms (varies)")

print("# Level 1, Q6: add the index and read the plan again")
conn.execute("CREATE INDEX idx_events_user ON events (user_id)")
print(plan(conn, Q, (12345,)))

print("# Level 1, Q7: time again")
after = best_time(conn, Q, (12345,))
print("speedup is more than 100x:", before / after > 100)

print("# Level 1, Q8: which indexes exist")
print(conn.execute("PRAGMA index_list('events')").fetchall())
print(conn.execute("SELECT name, tbl_name FROM sqlite_master WHERE type = 'index'").fetchall())

print("# Level 1, Q9: lookup by primary key")
print(plan(conn, "SELECT * FROM events WHERE event_id = 500000"))
# The INTEGER PRIMARY KEY is the rowid: the table itself is the B-tree keyed by it, so no extra index is needed.

print("# Level 1, Q10: events per type")
show(conn.execute("SELECT event_type, COUNT(*) AS n FROM events GROUP BY event_type ORDER BY n DESC, event_type"))
print(plan(conn, "SELECT event_type, COUNT(*) FROM events GROUP BY event_type"))

print("# Level 1, Q11: drop and recreate")
conn.execute("DROP INDEX idx_events_user")
conn.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON events (user_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_events_user ON events (user_id)")  # no error the second time
print(conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall())

print("# Level 1, Q12: a UNIQUE index")
toy = sqlite3.connect(":memory:")
toy.execute("CREATE TABLE people (id INTEGER PRIMARY KEY, email TEXT) STRICT")
toy.execute("CREATE UNIQUE INDEX idx_people_email ON people (email)")
toy.execute("INSERT INTO people (email) VALUES ('a@x.com')")
try:
    toy.execute("INSERT INTO people (email) VALUES ('a@x.com')")
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)

print("# Level 1, Q13: SCAN vs SEARCH")
# SCAN reads every row (or every entry of an index), SEARCH jumps straight to the matching rows through a B-tree.

print("# Level 1, Q14: foreign key columns in the library")
lib = library_full_conn()
Q14 = "SELECT id, book_id FROM loans WHERE member_id = 1"
print(plan(lib, Q14))
lib.execute("CREATE INDEX idx_loans_member ON loans (member_id)")
lib.execute("CREATE INDEX idx_loans_book ON loans (book_id)")
print(plan(lib, Q14))

print("# Level 1, Q15: explain")
# SQLite does not index foreign key columns for you. Joins and "all loans of member 1" would scan the child
# table every time; and deleting a parent row has to check the child table for references, which scans it too.

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1: a composite index and which queries use it")
conn.execute("DROP INDEX idx_events_user")
conn.execute("CREATE INDEX idx_events_user_ts ON events (user_id, ts)")
queries = {
    "user_id =": "SELECT event_id FROM events WHERE user_id = 777",
    "user_id = and ts range": "SELECT event_id FROM events WHERE user_id = 777 AND ts >= '2025-06-01'",
    "user_id = order by ts": "SELECT event_id FROM events WHERE user_id = 777 ORDER BY ts",
    "ts range only": "SELECT event_id FROM events WHERE ts >= '2025-06-01' AND ts < '2025-06-02'",
    "event_type =": "SELECT event_id FROM events WHERE event_type = 'refund'",
}
for name, sql in queries.items():
    print(f"{name:24} {plan(conn, sql)[0]}")

print("# Level 2, Q2: LIKE and indexes")
conn.execute("CREATE INDEX idx_events_ts ON events (ts)")
for label, sql in [
    ("ts LIKE 'x%'", "SELECT COUNT(*) FROM events WHERE ts LIKE '2025-06-01%'"),
    ("ts LIKE '%x'", "SELECT COUNT(*) FROM events WHERE ts LIKE '%01'"),
    ("ts GLOB 'x*'", "SELECT COUNT(*) FROM events WHERE ts GLOB '2025-06-01*'"),
    ("range", "SELECT COUNT(*) FROM events WHERE ts >= '2025-06-01' AND ts < '2025-06-02'"),
]:
    print(f"{label:14} {plan(conn, sql)[0]}")
print(conn.execute("SELECT COUNT(*) FROM events WHERE ts LIKE '2025-06-01%'").fetchone(),
      conn.execute("SELECT COUNT(*) FROM events WHERE ts GLOB '2025-06-01*'").fetchone())

print("# Level 2, Q3: covering index")
for label, sql in [
    ("user_id, ts", "SELECT user_id, ts FROM events WHERE user_id = 777"),
    ("*", "SELECT * FROM events WHERE user_id = 777"),
]:
    print(f"{label:12} {plan(conn, sql)[0]}")

print("# Level 2, Q4: partial index")
conn.execute("CREATE INDEX idx_purchases_user ON events (user_id) WHERE event_type = 'purchase'")
print(plan(conn, "SELECT COUNT(*) FROM events WHERE event_type = 'purchase' AND user_id = 777")[0])
print(plan(conn, "SELECT COUNT(*) FROM events WHERE event_type = 'view' AND user_id = 777")[0])
print(conn.execute("SELECT COUNT(*) FROM events WHERE event_type = 'purchase' AND user_id = 777").fetchone())

print("# Level 2, Q5: expression index")
Q5 = "SELECT COUNT(*) FROM events WHERE date(ts) = '2025-06-01'"
print(plan(conn, Q5)[0])
conn.execute("CREATE INDEX idx_events_date ON events (date(ts))")
print(plan(conn, Q5)[0])
print(conn.execute(Q5).fetchone())

print("# Level 2, Q6: indexes slow writes down")
def insert_time(n_indexes):
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE e (event_id INTEGER PRIMARY KEY, user_id INTEGER, event_type TEXT, ts TEXT, amount_cents INTEGER) STRICT")
    for stmt in ["CREATE INDEX i1 ON e (user_id)", "CREATE INDEX i2 ON e (ts)", "CREATE INDEX i3 ON e (event_type, user_id)"][:n_indexes]:
        c.execute(stmt)
    data = conn.execute("SELECT * FROM events LIMIT 200000").fetchall()
    start = time.perf_counter()
    c.executemany("INSERT INTO e VALUES (?, ?, ?, ?, ?)", data)
    c.commit()
    return time.perf_counter() - start
t0, t3 = insert_time(0), insert_time(3)
print("with 3 indexes the insert takes longer:", t3 > t0, "| more than 1.5x:", t3 / t0 > 1.5)

print("# Level 2, Q7: ANALYZE")
conn.execute("ANALYZE")
show(conn.execute("SELECT idx, stat FROM sqlite_stat1 WHERE idx NOT LIKE '%purchases%' ORDER BY idx"))

print("# Level 2, Q8: keyset pagination")
def next_page(conn, last_id, size=3):
    return conn.execute(
        "SELECT event_id, user_id, event_type FROM events WHERE event_id > ? ORDER BY event_id LIMIT ?",
        (last_id, size),
    ).fetchall()
last = 0
for _ in range(3):
    page = next_page(conn, last)
    print(page)
    last = page[-1][0]

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1: five slow queries")
conn.execute("DROP INDEX idx_events_user_ts")
conn.execute("DROP INDEX idx_events_ts")
conn.execute("DROP INDEX idx_purchases_user")
conn.execute("DROP INDEX idx_events_date")
conn.execute("DROP TABLE IF EXISTS sqlite_stat1")
slow = {
    "Q1 user 777 by time": ("SELECT event_id, ts FROM events WHERE user_id = 777 ORDER BY ts",
                            "CREATE INDEX idx_q1 ON events (user_id, ts)"),
    "Q2 events on a day": ("SELECT COUNT(*) FROM events WHERE date(ts) = '2025-03-14'",
                           "CREATE INDEX idx_q2 ON events (date(ts))"),
    "Q3 March refunds": ("SELECT COUNT(*), SUM(amount_cents) FROM events WHERE event_type = 'refund' AND ts >= '2025-03-01' AND ts < '2025-04-01'",
                         "CREATE INDEX idx_q3 ON events (event_type, ts)"),
    "Q4 last purchase": ("SELECT event_id, ts FROM events WHERE user_id = 777 AND event_type = 'purchase' ORDER BY ts DESC LIMIT 1",
                         "CREATE INDEX idx_q4 ON events (user_id, event_type, ts)"),
    "Q5 types for a user": ("SELECT DISTINCT event_type FROM events WHERE user_id = 777",
                            "CREATE INDEX idx_q5 ON events (user_id, event_type)"),
}
print(f"{'query':20} {'plan after':72} faster")
for name, (sql, create) in slow.items():
    t_before = best_time(conn, sql)
    assert plan(conn, sql)[0] == "SCAN events"
    conn.execute(create)
    t_after = best_time(conn, sql)
    p_after = plan(conn, sql)[0]
    print(f"{name:20} {p_after:72} {'>10x' if t_before / t_after > 10 else 'NOT 10x'}")
    conn.execute("DROP INDEX " + create.split()[2])

print("# Level 3, Q2: OFFSET vs keyset")
def page_offset(conn, page, size=20):
    return conn.execute("SELECT event_id FROM events ORDER BY event_id LIMIT ? OFFSET ?", (size, (page - 1) * size)).fetchall()

def page_keyset(conn, last_id, size=20):
    return conn.execute("SELECT event_id FROM events WHERE event_id > ? ORDER BY event_id LIMIT ?", (last_id, size)).fetchall()

a = page_offset(conn, 40_000)
b = page_keyset(conn, 40_000 * 20 - 20)
print(a == b, a[0], a[-1])
t_off = min(best_time(conn, "SELECT event_id FROM events ORDER BY event_id LIMIT 20 OFFSET 799980") for _ in range(2))
t_key = min(best_time(conn, "SELECT event_id FROM events WHERE event_id > 799980 ORDER BY event_id LIMIT 20") for _ in range(2))
print("keyset is more than 100x faster:", t_off / t_key > 100)
print(plan(conn, "SELECT event_id FROM events ORDER BY event_id LIMIT 20 OFFSET 799980"))
print(plan(conn, "SELECT event_id FROM events WHERE event_id > 799980 ORDER BY event_id LIMIT 20"))

print("# Level 3, Q3 (bonus): FTS5 on Hacker News titles")
hn = datasets_conn()
hn.execute("CREATE VIRTUAL TABLE hn_fts USING fts5(title)")
hn.execute("INSERT INTO hn_fts (rowid, title) SELECT id, title FROM hn_posts")
print(hn.execute("SELECT COUNT(*) FROM hn_fts").fetchone())
like = hn.execute("SELECT COUNT(*) FROM hn_posts WHERE title LIKE '%python%' OR title LIKE '%rust%'").fetchone()
fts = hn.execute("SELECT COUNT(*) FROM hn_fts WHERE hn_fts MATCH 'python OR rust'").fetchone()
print("LIKE:", like, "FTS5:", fts)
show(hn.execute("""
    SELECT hn_posts.title, round(bm25(hn_fts), 2) AS score
    FROM hn_fts JOIN hn_posts ON hn_posts.id = hn_fts.rowid
    WHERE hn_fts MATCH 'python OR rust'
    ORDER BY bm25(hn_fts), hn_posts.id
    LIMIT 5
"""))
print(hn.execute("SELECT highlight(hn_fts, 0, '[', ']') FROM hn_fts WHERE hn_fts MATCH 'rust' ORDER BY rowid LIMIT 2").fetchall())
# why FTS5 finds more/less: LIKE '%rust%' also matches 'trust' and 'frustrating'; FTS5 matches whole words
t_like = best_time(hn, "SELECT COUNT(*) FROM hn_posts WHERE title LIKE '%python%' OR title LIKE '%rust%'")
t_fts = best_time(hn, "SELECT COUNT(*) FROM hn_fts WHERE hn_fts MATCH 'python OR rust'")
print("FTS5 faster than LIKE:", t_fts < t_like)
