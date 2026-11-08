# Day 27 reference tests: Level 2 (Q2, five LibraryRepository tests) and Level 3 (migration runner)
import sqlite3

import pytest

from day_27 import migrate, sort_books
from helpers import LIBRARY_SCHEMA, library_conn
from library_repo import LibraryRepository, LoanLimitError, NotFoundError


@pytest.fixture
def repo():
    conn = sqlite3.connect(":memory:")
    conn.executescript(LIBRARY_SCHEMA)
    repo = LibraryRepository(conn)
    for i in range(1, 5):
        repo.add_book(f"Book {i}", "An Author", year=2000 + i)
    repo.add_member("Alice", "alice@example.com", "2025-01-01")
    yield repo
    repo.close()


# ---- Level 2, Q2
def test_return_makes_book_available_again(repo):
    repo.lend(1, 1, "2025-03-01")
    assert not repo.is_available(1)
    repo.return_book(1, "2025-03-05")
    assert repo.is_available(1)


def test_returning_a_book_that_is_not_out_fails(repo):
    with pytest.raises(NotFoundError):
        repo.return_book(1, "2025-03-05")


def test_fourth_loan_hits_the_limit(repo):
    for book_id in (1, 2, 3):
        repo.lend(book_id, 1, "2025-03-01")
    with pytest.raises(LoanLimitError):
        repo.lend(4, 1, "2025-03-01")
    assert len(repo.active_loans(1)) == 3  # the failed call left nothing behind


def test_overdue_counts_days_past_due(repo):
    repo.lend(1, 1, "2025-03-01")  # due 2025-03-15
    assert repo.overdue("2025-03-15") == []
    (late,) = repo.overdue("2025-03-20")
    assert late.days_overdue == 5


def test_search_is_case_insensitive_and_ordered(repo):
    assert [b.title for b in repo.search_books("BOOK")] == ["Book 1", "Book 2", "Book 3", "Book 4"]


# ---- Level 1/2: safe sorting
def test_sort_books_allowlist():
    conn = library_conn()
    assert sort_books(conn, "year", "desc")[0][1] == "Project Hail Mary"
    with pytest.raises(ValueError):
        sort_books(conn, "year; DROP TABLE books", "asc")


# ---- Level 3: the migration runner
@pytest.fixture
def folder(tmp_path):
    (tmp_path / "001_notes.sql").write_text("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT);")
    (tmp_path / "002_tags.sql").write_text("CREATE TABLE tags (id INTEGER PRIMARY KEY);")
    return tmp_path


def test_migrations_apply_in_order_and_once(folder):
    conn = sqlite3.connect(":memory:")
    assert migrate(conn, folder) == [1, 2]
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    assert migrate(conn, folder) == []


def test_new_file_is_applied_later(folder):
    conn = sqlite3.connect(":memory:")
    migrate(conn, folder)
    (folder / "003_more.sql").write_text("ALTER TABLE notes ADD COLUMN created_on TEXT;")
    assert migrate(conn, folder) == [3]


def test_failed_migration_changes_nothing(folder):
    conn = sqlite3.connect(":memory:")
    migrate(conn, folder)
    (folder / "003_bad.sql").write_text("CREATE TABLE half (id INTEGER);\nINSERT INTO missing VALUES (1);")
    with pytest.raises(sqlite3.OperationalError):
        migrate(conn, folder)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM sqlite_master WHERE name = 'half'").fetchone()[0] == 0
