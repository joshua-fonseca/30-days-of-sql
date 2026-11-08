# The tests shown in the Day 27 lesson (00_practice/test_library_repo.py in the learner's project)
import sqlite3

import pytest

from helpers import LIBRARY_SCHEMA  # learners: read their own Day 10 schema file instead
from library_repo import AlreadyLoanedError, LibraryRepository, NotFoundError


@pytest.fixture
def repo():
    conn = sqlite3.connect(":memory:")  # a brand new, empty database for every test
    conn.executescript(LIBRARY_SCHEMA)
    repo = LibraryRepository(conn)
    yield repo
    repo.close()


def test_add_book_returns_id_and_book_is_found(repo):
    book_id = repo.add_book("Dune", "Frank Herbert", year=1965)
    book = repo.get_book(book_id)
    assert book.title == "Dune"
    assert book.author == "Frank Herbert"


def test_lend_sets_due_date_14_days_later(repo):
    book_id = repo.add_book("Dune", "Frank Herbert")
    member_id = repo.add_member("Alice", "alice@example.com", "2025-01-01")
    repo.lend(book_id, member_id, "2025-03-14")
    (loan,) = repo.active_loans()
    assert loan.due_on == "2025-03-28"


def test_second_loan_of_same_book_is_rejected(repo):
    book_id = repo.add_book("Dune", "Frank Herbert")
    alice = repo.add_member("Alice", "alice@example.com", "2025-01-01")
    bob = repo.add_member("Bob", "bob@example.com", "2025-01-01")
    repo.lend(book_id, alice, "2025-03-14")
    with pytest.raises(AlreadyLoanedError):
        repo.lend(book_id, bob, "2025-03-15")


@pytest.mark.parametrize("book_id, member_id", [(999, 1), (1, 999)])
def test_unknown_book_or_member(repo, book_id, member_id):
    repo.add_book("Dune", "Frank Herbert")
    repo.add_member("Alice", "alice@example.com", "2025-01-01")
    with pytest.raises(NotFoundError):
        repo.lend(book_id, member_id, "2025-03-14")
