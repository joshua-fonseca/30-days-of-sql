import sqlite3

import pytest

from library_cli import main

TODAY = "--today=2025-03-14"


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "lib.db"
    assert main(["--db", str(path), "init", "--demo"]) == 0
    return str(path)


def run(db, *args, capsys):
    code = main(["--db", db, TODAY, *args])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_init_refuses_to_overwrite(db, capsys):
    assert main(["--db", db, "init"]) == 1
    assert "already exists" in capsys.readouterr().err


def test_missing_database(tmp_path, capsys):
    assert main(["--db", str(tmp_path / "nope.db"), "stats"]) == 1
    assert "run 'init' first" in capsys.readouterr().err


def test_add_book_stores_cents(db, capsys):
    code, out, _ = run(db, "add-book", "Hyperion", "Dan Simmons", "--year", "1989", "--price", "12.99", capsys=capsys)
    assert code == 0 and "added book 9" in out
    assert sqlite3.connect(db).execute("SELECT price_cents FROM books WHERE id = 9").fetchone() == (1299,)


def test_search_by_title_and_author(db, capsys):
    _, out, _ = run(db, "search", "--title", "the", capsys=capsys)
    assert "The Hobbit" in out and "The Martian" in out and "Dune" not in out
    _, out, _ = run(db, "search", "--author", "austen", capsys=capsys)
    assert out.index("Pride and Prejudice") < out.index("Emma")  # ordered by year
    _, out, _ = run(db, "search", "--title", "zzz", capsys=capsys)
    assert out.strip() == "no books found"


def test_injection_text_is_just_text(db, capsys):
    code, out, _ = run(db, "search", "--title", "'; DROP TABLE books; --", capsys=capsys)
    assert code == 0 and out.strip() == "no books found"
    assert sqlite3.connect(db).execute("SELECT count(*) FROM books").fetchone() == (8,)


def test_lend_return_cycle(db, capsys):
    code, out, _ = run(db, "lend", "1", "1", capsys=capsys)
    assert code == 0 and "due 2025-03-28" in out
    code, _, err = run(db, "lend", "1", "2", capsys=capsys)
    assert code == 1 and "already on loan" in err
    code, out, _ = run(db, "return", "1", capsys=capsys)
    assert code == 0 and "returned" in out
    code, _, err = run(db, "return", "1", capsys=capsys)
    assert code == 1 and "not on loan" in err


def test_loan_limit(db, capsys):
    for book in ("1", "2", "3"):
        assert run(db, "lend", book, "1", capsys=capsys)[0] == 0
    code, _, err = run(db, "lend", "4", "1", capsys=capsys)
    assert code == 1 and "already has 3" in err


def test_unknown_ids(db, capsys):
    assert "no book with id 99" in run(db, "lend", "99", "1", capsys=capsys)[2]
    assert "no member with id 99" in run(db, "lend", "1", "99", capsys=capsys)[2]


def test_duplicate_member_email(db, capsys):
    code, _, err = run(db, "add-member", "Imposter", "alice@example.com", capsys=capsys)
    assert code == 1 and "UNIQUE" in err


def test_overdue_report(db, capsys):
    main(["--db", db, "--today=2025-03-01", "lend", "1", "1"])
    capsys.readouterr()
    _, out, _ = run(db, "overdue", capsys=capsys)  # 2025-03-14: due 2025-03-15, not late yet
    assert out.strip() == "nothing is overdue"
    main(["--db", db, "--today=2025-03-20", "overdue"])
    last = capsys.readouterr().out.splitlines()[-1].split()
    assert last[-2:] == ["2025-03-15", "5"]


def test_stats(db, capsys):
    run(db, "lend", "1", "1", capsys=capsys)
    _, out, _ = run(db, "stats", capsys=capsys)
    assert out.startswith("books: 8  members: 3  on loan: 1  overdue: 0")
    assert "Dune" in out


def test_argparse_usage_errors(db):
    with pytest.raises(SystemExit) as exc:
        main(["--db", db, "lend", "one", "two"])
    assert exc.value.code == 2
