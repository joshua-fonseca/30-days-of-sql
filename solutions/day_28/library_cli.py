"""Library Manager CLI: the Day 28 reference solution.

    python library_cli.py --db library.db init --demo
    python library_cli.py --db library.db lend 4 5

A thin layer over LibraryRepository: argparse turns the command line into repository calls,
and the results are printed as tables. Business-rule errors become a one-line message and exit code 1.
"""

import argparse
import sqlite3
import sys
from datetime import date
from pathlib import Path

# Reference-only: in your own project library_repo.py sits next to this file.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library_repo import LibraryError, LibraryRepository  # noqa: E402

SCHEMA = """
CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE) STRICT;
CREATE TABLE books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL CHECK (length(title) > 0),
    author_id INTEGER NOT NULL REFERENCES authors (id),
    year INTEGER CHECK (year BETWEEN 1000 AND 2100),
    pages INTEGER CHECK (pages > 0),
    genre TEXT,
    price_cents INTEGER CHECK (price_cents >= 0),
    rating REAL CHECK (rating BETWEEN 0 AND 5),
    UNIQUE (title, author_id)
) STRICT;
CREATE TABLE members (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, joined_on TEXT NOT NULL
) STRICT;
CREATE TABLE loans (
    id INTEGER PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books (id),
    member_id INTEGER NOT NULL REFERENCES members (id),
    loaned_on TEXT NOT NULL,
    due_on TEXT NOT NULL,
    returned_on TEXT
) STRICT;
"""

DEMO_BOOKS = [
    ("Dune", "Frank Herbert", 1965, 612, "Sci-Fi", 1099, 4.5),
    ("Neuromancer", "William Gibson", 1984, 271, "Sci-Fi", 899, 4.0),
    ("The Hobbit", "J.R.R. Tolkien", 1937, 310, "Fantasy", 799, 4.7),
    ("Pride and Prejudice", "Jane Austen", 1813, 279, "Romance", 599, 4.3),
    ("Emma", "Jane Austen", 1815, 474, "Romance", 649, None),
    ("1984", "George Orwell", 1949, 328, "Dystopian", 799, 4.6),
    ("Clean Code", "Robert C. Martin", 2008, 464, "Tech", 3999, 4.1),
    ("The Martian", "Andy Weir", 2011, 369, "Sci-Fi", 1199, 4.6),
]
DEMO_MEMBERS = [
    ("Alice Nguyen", "alice@example.com", "2024-01-15"),
    ("Bruno Silva", "bruno@example.com", "2024-02-20"),
    ("Chloe Martin", "chloe@example.com", "2024-03-05"),
]


def dollars(cents: int | None) -> str:
    return "-" if cents is None else f"${cents / 100:.2f}"


def table(headers: list[str], rows: list[list], out) -> None:
    cells = [["-" if v is None else str(v) for v in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths)).rstrip(), file=out)
    print("  ".join("-" * w for w in widths), file=out)
    for r in cells:
        print("  ".join(v.ljust(w) for v, w in zip(r, widths)).rstrip(), file=out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="library_cli.py", description="Manage a small library.")
    p.add_argument("--db", type=Path, default=Path("library.db"), help="database file (default: library.db)")
    p.add_argument("--today", default=None, help="ISO date to use instead of the real date (for tests and demos)")
    sub = p.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create the tables")
    init.add_argument("--demo", action="store_true", help="also load demo books and members")

    add = sub.add_parser("add-book", help="add a book")
    add.add_argument("title")
    add.add_argument("author")
    add.add_argument("--year", type=int)
    add.add_argument("--pages", type=int)
    add.add_argument("--genre")
    add.add_argument("--price", type=float, help="price in dollars, e.g. 12.99")

    search = sub.add_parser("search", help="find books by title or author")
    group = search.add_mutually_exclusive_group(required=True)
    group.add_argument("--title")
    group.add_argument("--author")

    member = sub.add_parser("add-member", help="register a member")
    member.add_argument("name")
    member.add_argument("email")

    lend = sub.add_parser("lend", help="lend a book to a member")
    lend.add_argument("book_id", type=int)
    lend.add_argument("member_id", type=int)

    ret = sub.add_parser("return", help="return a book")
    ret.add_argument("book_id", type=int)

    loans = sub.add_parser("loans", help="list books currently on loan")
    loans.add_argument("--member", type=int, dest="member_id")

    sub.add_parser("overdue", help="list overdue loans")
    sub.add_parser("stats", help="a few numbers about the library")
    return p


def cmd_init(args, out) -> int:
    if args.db.exists() and args.db.stat().st_size > 0:
        print(f"error: {args.db} already exists", file=sys.stderr)
        return 1
    conn = sqlite3.connect(args.db)
    conn.executescript(SCHEMA)
    repo = LibraryRepository(conn)
    if args.demo:
        for title, author, year, pages, genre, price, rating in DEMO_BOOKS:
            repo.add_book(title, author, year=year, pages=pages, genre=genre, price_cents=price, rating=rating)
        for name, email, joined in DEMO_MEMBERS:
            repo.add_member(name, email, joined)
    repo.close()
    print(f"created {args.db}" + (" with demo data" if args.demo else ""), file=out)
    return 0


def book_rows(books) -> list[list]:
    return [[b.id, b.title, b.author, b.year, b.genre, dollars(b.price_cents)] for b in books]


BOOK_HEADERS = ["id", "title", "author", "year", "genre", "price"]


def run(repo: LibraryRepository, args, today: str, out) -> int:
    cmd = args.command
    if cmd == "add-book":
        price = None if args.price is None else round(args.price * 100)
        book_id = repo.add_book(args.title, args.author, year=args.year, pages=args.pages,
                                genre=args.genre, price_cents=price)
        print(f"added book {book_id}: {args.title}", file=out)
    elif cmd == "search":
        books = repo.search_books(args.title) if args.title is not None else repo.find_by_author(args.author)
        if not books:
            print("no books found", file=out)
        else:
            table(BOOK_HEADERS, book_rows(books), out)
    elif cmd == "add-member":
        member_id = repo.add_member(args.name, args.email, today)
        print(f"added member {member_id}: {args.name}", file=out)
    elif cmd == "lend":
        loan_id = repo.lend(args.book_id, args.member_id, today)
        due = next(loan.due_on for loan in repo.active_loans() if loan.id == loan_id)
        print(f"loan {loan_id}: book {args.book_id} to member {args.member_id}, due {due}", file=out)
    elif cmd == "return":
        repo.return_book(args.book_id, today)
        print(f"book {args.book_id} returned", file=out)
    elif cmd == "loans":
        rows = repo.conn.execute(
            """
            SELECT loans.id, books.title, members.name, loans.loaned_on, loans.due_on
            FROM loans
            JOIN books ON books.id = loans.book_id
            JOIN members ON members.id = loans.member_id
            WHERE loans.returned_on IS NULL AND (:member IS NULL OR loans.member_id = :member)
            ORDER BY loans.due_on, loans.id
            """,
            {"member": args.member_id},
        ).fetchall()
        if not rows:
            print("no books on loan", file=out)
        else:
            table(["loan", "title", "member", "loaned_on", "due_on"], [list(r) for r in rows], out)
    elif cmd == "overdue":
        late = repo.overdue(today)
        if not late:
            print("nothing is overdue", file=out)
        else:
            table(["loan", "title", "member", "due_on", "days_late"],
                  [[x.loan_id, x.title, x.member, x.due_on, x.days_overdue] for x in late], out)
    elif cmd == "stats":
        q = repo.conn.execute
        books = q("SELECT count(*) FROM books").fetchone()[0]
        members = q("SELECT count(*) FROM members").fetchone()[0]
        on_loan = q("SELECT count(*) FROM loans WHERE returned_on IS NULL").fetchone()[0]
        print(f"books: {books}  members: {members}  on loan: {on_loan}  overdue: {len(repo.overdue(today))}", file=out)
        top = q(
            """
            SELECT books.title, count(*) AS times
            FROM loans JOIN books ON books.id = loans.book_id
            GROUP BY books.id
            ORDER BY times DESC, books.title
            LIMIT 3
            """
        ).fetchall()
        print("", file=out)
        print("most borrowed", file=out)
        table(["title", "times"], [list(r) for r in top], out) if top else print("(no loans yet)", file=out)
        genres = q("SELECT genre, count(*) AS n FROM books GROUP BY genre ORDER BY n DESC, genre").fetchall()
        print("", file=out)
        print("books per genre", file=out)
        table(["genre", "books"], [list(r) for r in genres], out)
    return 0


def main(argv: list[str] | None = None, out=None) -> int:
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    if args.command == "init":
        return cmd_init(args, out)
    if not args.db.exists():
        print(f"error: {args.db} not found; run 'init' first", file=sys.stderr)
        return 1
    today = args.today or date.today().isoformat()
    repo = LibraryRepository.open(args.db)
    try:
        return run(repo, args, today, out)
    except LibraryError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    except sqlite3.IntegrityError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    finally:
        repo.close()


if __name__ == "__main__":
    sys.exit(main())
