"""LibraryRepository: the data-access layer for the normalized library (authors, books, members, loans).

Defined on Day 19, reused by Day 22 (triggers), Day 27 (pytest tests) and Day 28 (the CLI project).
All dates are ISO text ('YYYY-MM-DD') passed in by the caller, so nothing depends on today's date.
"""

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


class LibraryError(Exception):
    """Base class for every business-rule error raised by the repository."""


class NotFoundError(LibraryError):
    """A book, member or loan that was asked for does not exist."""


class AlreadyLoanedError(LibraryError):
    """The book is currently out on loan."""


class LoanLimitError(LibraryError):
    """The member already has MAX_LOANS books out."""


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str
    year: int | None
    pages: int | None
    genre: str | None
    price_cents: int | None
    rating: float | None


@dataclass(frozen=True)
class Loan:
    id: int
    book_id: int
    member_id: int
    loaned_on: str
    due_on: str
    returned_on: str | None


@dataclass(frozen=True)
class OverdueLoan:
    loan_id: int
    title: str
    member: str
    due_on: str
    days_overdue: int


BOOK_SELECT = """
    SELECT books.id, books.title, authors.name AS author, books.year, books.pages,
           books.genre, books.price_cents, books.rating
    FROM books
    JOIN authors ON authors.id = books.author_id
"""


class LibraryRepository:
    MAX_LOANS = 3
    LOAN_DAYS = 14

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    @classmethod
    def open(cls, path: str | Path) -> "LibraryRepository":
        return cls(sqlite3.connect(path))

    def close(self) -> None:
        self.conn.close()

    # ---- books and authors
    def add_author(self, name: str) -> int:
        """Return the id of the author, creating the row if the name is new."""
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (name,))
            return self.conn.execute("SELECT id FROM authors WHERE name = ?", (name,)).fetchone()["id"]

    def add_book(self, title: str, author: str, *, year: int | None = None, pages: int | None = None,
                 genre: str | None = None, price_cents: int | None = None, rating: float | None = None) -> int:
        """Insert a book (creating its author if needed) and return the new book id."""
        author_id = self.add_author(author)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO books (title, author_id, year, pages, genre, price_cents, rating)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, author_id, year, pages, genre, price_cents, rating),
            )
            return cur.lastrowid

    def get_book(self, book_id: int) -> Book | None:
        row = self.conn.execute(BOOK_SELECT + " WHERE books.id = ?", (book_id,)).fetchone()
        return Book(**row) if row else None

    def find_by_author(self, fragment: str) -> list[Book]:
        """Books whose author name contains `fragment` (case-insensitive), ordered by year then title."""
        rows = self.conn.execute(
            BOOK_SELECT + " WHERE authors.name LIKE '%' || ? || '%' ORDER BY books.year, books.title",
            (fragment,),
        ).fetchall()
        return [Book(**r) for r in rows]

    def search_books(self, keyword: str) -> list[Book]:
        """Books whose title contains `keyword` (case-insensitive), ordered by title."""
        rows = self.conn.execute(
            BOOK_SELECT + " WHERE books.title LIKE '%' || ? || '%' ORDER BY books.title", (keyword,)
        ).fetchall()
        return [Book(**r) for r in rows]

    # ---- members
    def add_member(self, name: str, email: str, joined_on: str) -> int:
        """Insert a member and return the new id. A duplicate email raises sqlite3.IntegrityError."""
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO members (name, email, joined_on) VALUES (?, ?, ?)", (name, email, joined_on)
            )
            return cur.lastrowid

    # ---- loans
    def is_available(self, book_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM loans WHERE book_id = ? AND returned_on IS NULL", (book_id,)
        ).fetchone()
        return row is None

    def lend(self, book_id: int, member_id: int, on: str) -> int:
        """Lend a book on date `on`; due LOAN_DAYS later. Return the new loan id.

        Raises NotFoundError (unknown book/member), AlreadyLoanedError, LoanLimitError.
        Everything runs in one transaction, so a failed check leaves nothing behind.
        """
        with self.conn:
            if self.conn.execute("SELECT 1 FROM books WHERE id = ?", (book_id,)).fetchone() is None:
                raise NotFoundError(f"no book with id {book_id}")
            if self.conn.execute("SELECT 1 FROM members WHERE id = ?", (member_id,)).fetchone() is None:
                raise NotFoundError(f"no member with id {member_id}")
            if not self.is_available(book_id):
                raise AlreadyLoanedError(f"book {book_id} is already on loan")
            (count,) = self.conn.execute(
                "SELECT COUNT(*) FROM loans WHERE member_id = ? AND returned_on IS NULL", (member_id,)
            ).fetchone()
            if count >= self.MAX_LOANS:
                raise LoanLimitError(f"member {member_id} already has {count} books out")
            due = (date.fromisoformat(on) + timedelta(days=self.LOAN_DAYS)).isoformat()
            cur = self.conn.execute(
                "INSERT INTO loans (book_id, member_id, loaned_on, due_on) VALUES (?, ?, ?, ?)",
                (book_id, member_id, on, due),
            )
            return cur.lastrowid

    def return_book(self, book_id: int, on: str) -> None:
        """Mark the open loan of `book_id` as returned on date `on`. Raises NotFoundError if it is not out."""
        with self.conn:
            cur = self.conn.execute(
                "UPDATE loans SET returned_on = ? WHERE book_id = ? AND returned_on IS NULL", (on, book_id)
            )
            if cur.rowcount == 0:
                raise NotFoundError(f"book {book_id} is not on loan")

    def active_loans(self, member_id: int | None = None) -> list[Loan]:
        """Loans not yet returned (optionally for one member), ordered by due date then loan id."""
        sql = "SELECT * FROM loans WHERE returned_on IS NULL"
        params: tuple = ()
        if member_id is not None:
            sql += " AND member_id = ?"
            params = (member_id,)
        rows = self.conn.execute(sql + " ORDER BY due_on, id", params).fetchall()
        return [Loan(**r) for r in rows]

    def overdue(self, today: str) -> list[OverdueLoan]:
        """Unreturned loans whose due date is before `today`, oldest due date first."""
        rows = self.conn.execute(
            """
            SELECT loans.id AS loan_id, books.title, members.name AS member, loans.due_on,
                   CAST(julianday(:today) - julianday(loans.due_on) AS INTEGER) AS days_overdue
            FROM loans
            JOIN books   ON books.id = loans.book_id
            JOIN members ON members.id = loans.member_id
            WHERE loans.returned_on IS NULL AND loans.due_on < :today
            ORDER BY loans.due_on, loans.id
            """,
            {"today": today},
        ).fetchall()
        return [OverdueLoan(**r) for r in rows]
