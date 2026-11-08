# Day 27 reference solutions: security and best practices
#
# Reusable pieces (sort_books, migrate) are importable by test_day_27.py; the demos only run as a script.
import hashlib
import hmac
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

from helpers import LIBRARY_SCHEMA, WORK, library_conn, library_full_conn, show
from library_repo import LibraryRepository


# ------------------------------------------------------------------------------------------------
# Code shown in the lesson
# ------------------------------------------------------------------------------------------------
def login_vulnerable(conn: sqlite3.Connection, name: str, password: str):
    """DO NOT WRITE CODE LIKE THIS. SQL is built by pasting the user's text into a string."""
    sql = f"SELECT id, name FROM users WHERE name = '{name}' AND password = '{password}'"
    return conn.execute(sql).fetchone()


def login_safe(conn: sqlite3.Connection, name: str, password: str):
    sql = "SELECT id, name FROM users WHERE name = ? AND password = ?"
    return conn.execute(sql, (name, password)).fetchone()


BOOK_SORT_COLUMNS = {"title": "title", "author": "author", "year": "year", "pages": "pages", "price": "price_cents"}
SORT_DIRECTIONS = {"asc": "ASC", "desc": "DESC"}


def sort_books(conn: sqlite3.Connection, column: str, direction: str = "asc") -> list[tuple]:
    """Titles with the chosen column, sorted safely. Level 2, Q1.

    Identifiers cannot be placeholders, so the *user's text* only ever selects a value from a fixed dictionary;
    the SQL text itself is built from our own constants.
    """
    try:
        col = BOOK_SORT_COLUMNS[column]
        way = SORT_DIRECTIONS[direction.lower()]
    except KeyError:
        raise ValueError(f"cannot sort by {column!r} {direction!r}") from None
    # `id` is the tie-breaker, so equal values always come out in the same order
    return conn.execute(f"SELECT id, title, {col} FROM books ORDER BY {col} {way}, id").fetchall()


def migrate(conn: sqlite3.Connection, folder: Path) -> list[int]:
    """Apply every NNN_name.sql file in `folder` whose number is above PRAGMA user_version.

    Each file runs in its own transaction together with the version bump, so a failing file changes nothing.
    Returns the versions applied by this call.
    """
    files = {}
    for path in sorted(folder.glob("[0-9][0-9][0-9]_*.sql")):
        version = int(path.name.split("_", 1)[0])
        if version in files:
            raise ValueError(f"two migrations share version {version}")
        files[version] = path
    (current,) = conn.execute("PRAGMA user_version").fetchone()
    applied = []
    for version in sorted(files):
        if version <= current:
            continue
        script = f"BEGIN;\n{files[version].read_text(encoding='utf-8')}\nPRAGMA user_version = {int(version)};\nCOMMIT;"
        try:
            conn.executescript(script)
        except sqlite3.Error:
            if conn.in_transaction:
                conn.rollback()
            raise
        applied.append(version)
    return applied


def search_title_literal(conn: sqlite3.Connection, text: str) -> list[str]:
    """Level 2, Q3: titles containing `text`, where % and _ in `text` mean themselves."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = conn.execute(
        "SELECT title FROM books WHERE title LIKE '%' || ? || '%' ESCAPE '\\' ORDER BY title", (escaped,)
    ).fetchall()
    return [r[0] for r in rows]


def backup_with_rotation(db: Path, folder: Path, today: str, keep: int = 3) -> list[str]:
    """Level 3, Q2: write folder/library-<today>.db with VACUUM INTO, keep only the newest `keep` snapshots."""
    folder.mkdir(exist_ok=True)
    target = folder / f"library-{today}.db"
    target.unlink(missing_ok=True)
    with closing(sqlite3.connect(db)) as src:
        src.execute("VACUUM INTO ?", (str(target),))
    snapshots = sorted(folder.glob("library-*.db"))  # ISO dates sort in time order
    for old in snapshots[:-keep]:
        old.unlink()
    return [p.name for p in sorted(folder.glob("library-*.db"))]


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + digest.hex()


def check_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":")
    again = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(again.hex(), digest_hex)


def users_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, password TEXT NOT NULL);
        INSERT INTO users (name, password) VALUES ('alice', 's3cret'), ('bob', 'hunter2');
        CREATE TABLE api_keys (owner TEXT, secret TEXT);
        INSERT INTO api_keys VALUES ('alice', 'key-ALICE-123'), ('bob', 'key-BOB-456');
        """
    )
    return conn


MESSY_QUERIES = [
    "select * from books where genre='Sci-Fi' order by year",
    "SELECT title,author,year FROM books WHERE year>2000 AND genre = 'Fantasy'ORDER BY year",
    "select b.title, a.name from books b join authors a on a.id=b.author_id where a.name like 'J%'",
]


def lint_codes(sql: str) -> list[str]:
    import sqlfluff

    return [f"{v['code']} {v['description']}" for v in sqlfluff.lint(sql, dialect="sqlite")]


def lint_names(sql: str) -> list[str]:
    import sqlfluff

    return sorted({v["code"] for v in sqlfluff.lint(sql, dialect="sqlite")})


def main() -> None:
    # ---------------------------------------------------------------- the attack
    print("# Injection demo: vulnerable login")
    conn = users_conn()
    print(login_vulnerable(conn, "alice", "wrong"))
    print(login_vulnerable(conn, "alice' --", "anything"))
    print(login_vulnerable(conn, "nobody", "' OR '1'='1"))
    name = "alice' --"
    print(f"SELECT id, name FROM users WHERE name = '{name}' AND password = 'anything'")
    union_name = "x' UNION SELECT 0, secret FROM api_keys WHERE owner = 'bob' --"
    print(login_vulnerable(conn, union_name, ""))
    print(login_safe(conn, "alice' --", "anything"))
    print(login_safe(conn, "alice", "s3cret"))

    print("# Stacked statements")
    try:
        conn.execute("SELECT 1; DROP TABLE users")
    except sqlite3.ProgrammingError as err:
        print(type(err).__name__, err)
    print(conn.execute("SELECT count(*) FROM users").fetchone())
    conn.executescript("SELECT 1; DROP TABLE users")
    try:
        conn.execute("SELECT count(*) FROM users")
    except sqlite3.OperationalError as err:
        print(type(err).__name__, err)

    # ---------------------------------------------------------------- identifiers
    print("# ORDER BY ? silently does nothing")
    lib = library_conn()
    print(lib.execute("SELECT title FROM books ORDER BY ? LIMIT 3", ("year",)).fetchall())
    print(lib.execute("SELECT title FROM books ORDER BY year LIMIT 3").fetchall())
    print("# sort_books")
    print(sort_books(lib, "year", "desc")[:3])
    print(sort_books(lib, "price", "ASC")[:3])
    for bad in [("year; DROP TABLE books", "asc"), ("year", "sideways")]:
        try:
            sort_books(lib, *bad)
        except ValueError as err:
            print("ValueError:", err)

    # ---------------------------------------------------------------- LIKE wildcards
    print("# LIKE wildcards from users")
    print(lib.execute("SELECT count(*) FROM books WHERE title LIKE '%' || ? || '%'", ("%",)).fetchone())
    print(lib.execute("SELECT count(*) FROM books WHERE title LIKE '%' || ? || '%' ESCAPE '\\'", ("\\%",)).fetchone())

    # ---------------------------------------------------------------- read-only
    print("# Read-only connection")
    path = WORK / "d27_library.db"
    for suffix in ("", "-wal", "-shm"):
        Path(str(path) + suffix).unlink(missing_ok=True)
    with closing(sqlite3.connect(path)) as w:
        library_full_conn().backup(w)
    uri = path.resolve().as_uri() + "?mode=ro"
    print(uri.replace(str(WORK.parent), "<repo>/solutions"))
    with closing(sqlite3.connect(uri, uri=True)) as ro:
        print(ro.execute("SELECT count(*) FROM books").fetchone())
        try:
            ro.execute("DELETE FROM books")
        except sqlite3.OperationalError as err:
            print(type(err).__name__, err)
    try:
        sqlite3.connect((WORK / "does_not_exist.db").resolve().as_uri() + "?mode=ro", uri=True)
    except sqlite3.OperationalError as err:
        print(type(err).__name__, err)
    with closing(sqlite3.connect(path)) as q:
        q.execute("PRAGMA query_only = ON")
        try:
            q.execute("DELETE FROM books")
        except sqlite3.OperationalError as err:
            print(type(err).__name__, err)

    print("# Authorizer")
    with closing(sqlite3.connect(path)) as a:
        def deny_writes(action, arg1, arg2, db_name, trigger):
            if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE, sqlite3.SQLITE_DROP_TABLE):
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        a.set_authorizer(deny_writes)
        print(a.execute("SELECT count(*) FROM books").fetchone())
        try:
            a.execute("DELETE FROM books")
        except sqlite3.DatabaseError as err:
            print(type(err).__name__, err)

    print("# search_title_literal")
    lib.execute("INSERT INTO books (title, author, genre) VALUES ('100% Pure_Python', 'X Y', 'Tech')")
    print(search_title_literal(lib, "%"), search_title_literal(lib, "_"), search_title_literal(lib, "the"))

    # ---------------------------------------------------------------- secrets
    print("# Secrets")
    db_path = Path(os.environ.get("LIBRARY_DB", "00_practice/library.db"))
    print(db_path)
    stored = hash_password("s3cret")
    print(len(stored), stored.count(":"))
    print(check_password("s3cret", stored), check_password("wrong", stored))

    # ---------------------------------------------------------------- backups
    print("# Backups")
    snap = WORK / "d27_snapshot.db"
    snap.unlink(missing_ok=True)
    with closing(sqlite3.connect(path)) as src:
        src.execute("VACUUM INTO ?", (str(snap),))
    with closing(sqlite3.connect(snap)) as s:
        print(s.execute("PRAGMA integrity_check").fetchone(), s.execute("SELECT count(*) FROM loans").fetchone())

    print("# Rotation")
    for day in ("2025-03-10", "2025-03-11", "2025-03-12", "2025-03-13"):
        names = backup_with_rotation(path, WORK / "d27_backups", day)
    print(names)

    # ---------------------------------------------------------------- migrations
    print("# Migrations")
    folder = WORK / "d27_migrations"
    folder.mkdir(exist_ok=True)
    for old in folder.glob("*.sql"):
        old.unlink()
    (folder / "001_create_notes.sql").write_text("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL) STRICT;\n")
    (folder / "002_add_created_on.sql").write_text("ALTER TABLE notes ADD COLUMN created_on TEXT;\n")
    mconn = sqlite3.connect(":memory:")
    print(mconn.execute("PRAGMA user_version").fetchone())
    print(migrate(mconn, folder), mconn.execute("PRAGMA user_version").fetchone())
    print(migrate(mconn, folder), mconn.execute("PRAGMA user_version").fetchone())
    (folder / "003_broken.sql").write_text("CREATE TABLE tags (id INTEGER PRIMARY KEY);\nINSERT INTO nope VALUES (1);\n")
    try:
        migrate(mconn, folder)
    except sqlite3.OperationalError as err:
        print(type(err).__name__, err)
    print(mconn.execute("PRAGMA user_version").fetchone(), [r[0] for r in mconn.execute("SELECT name FROM sqlite_master ORDER BY name")])
    (folder / "003_broken.sql").write_text("CREATE TABLE tags (id INTEGER PRIMARY KEY, label TEXT);\n")
    print(migrate(mconn, folder), mconn.execute("PRAGMA user_version").fetchone())

    # ---------------------------------------------------------------- SQLFluff and sqlglot
    print("# SQLFluff")
    for q in MESSY_QUERIES:
        print(q)
        for line in lint_codes(q):
            print("   ", line)
    import sqlfluff
    import sqlglot

    print(sqlfluff.fix(MESSY_QUERIES[0], dialect="sqlite"))
    print(sqlglot.transpile(MESSY_QUERIES[1], read="sqlite", write="sqlite", pretty=True)[0])
    try:
        sqlglot.parse_one("SELEC title FROM books WHERE", read="sqlite")
    except sqlglot.errors.ParseError as err:
        print(type(err).__name__)

    # ---------------------------------------------------------------- pytest
    print("# pytest")
    here = Path(__file__).resolve().parent
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         str(here / "test_day_27_lesson.py"), str(here / "test_day_27.py")],
        capture_output=True, text=True, cwd=here,
    )
    print(proc.stdout.strip().splitlines()[-1])
    if proc.returncode != 0:
        print(proc.stdout[-3000:], proc.stderr[-2000:])
        raise SystemExit("pytest failed")


if __name__ == "__main__":
    main()
