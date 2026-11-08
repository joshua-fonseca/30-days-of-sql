<div align="center">
  <h1> 30 Days Of SQL: Review 4 - Python and SQLite (Days 19-22)</h1>
</div>

[<< Day 22](../22_Day_Views_and_triggers/22_views_and_triggers.md) | [Day 23 >>](../23_Day_Meet_duckdb/23_meet_duckdb.md)

- [Review 4](#review-4)
  - [How to Use This Review](#how-to-use-this-review)
  - [Part A: Write the Query](#part-a-write-the-query)
  - [Part B: Predict the Output](#part-b-predict-the-output)
  - [Part C: Find the Bug](#part-c-find-the-bug)
  - [Part D: Explain](#part-d-explain)
  - [Part E: Mini-Project: New Acquisitions](#part-e-mini-project-new-acquisitions)

# Review 4

No new material today. This is a checkpoint for Days 19 to 22: the `sqlite3` module in depth, importing and cleaning data, JSON, indexes, views and triggers. The problems are mixed, so part of the work is
recognising which tool fits. If something feels shaky, go back to that day before starting DuckDB: it assumes all of this.

## How to Use This Review

- Parts A to C and E use the normalized library from Day 10 (12 books, 5 members, 10 loans). **Work on a fresh copy** (`backup()`, Day 19) for each problem that changes data, so the problems do not disturb each other.
  Where a problem says "the library", assume the data exactly as it was at the end of Day 10.
- Try each problem **before** looking at the expected output. For Part B, write your prediction down first, then run the code.
- Put your work in `00_practice/review_4.py`.

## Part A: Write the Query

1. Open the library with `sqlite3.Row` as the row factory. Print the name and join date of the two most recent members (by `joined_on`), using **column names**.

   ```sh
   Elena Rossi 2024-09-02
   Dev Patel 2024-06-18
   ```

2. Read the ids of all loans with `fetchmany(4)` in a loop and print the size of each batch. Expected: `[4, 4, 2]`.
3. Register a Python function `initials(name)` that returns the first letters of each word in upper case (`'Alice Nguyen'` becomes `'AN'`) and use it to list each member with their initials, in id order.

   ```sh
   name          initials
   ------------  --------
   Alice Nguyen  AN
   Bruno Silva   BS
   Chloe Martin  CM
   Dev Patel     DP
   Elena Rossi   ER
   (5 rows)
   ```

4. This semicolon-delimited text is an export from a till. Load it into a TEMP staging table (all `TEXT`), then compute, **in SQL**, the total value in integer cents (`price * qty`) of the rows whose price is a valid number, and the number of rows rejected. Prices can contain `$` and thousands commas; `n/a` is not a price. Expected: `(452700, 1)`.

   ```
   item;price;qty
   "Pen";"$1.50";"10"
   "Notebook";"$4.00";"3"
   "Stapler";"n/a";"1"
   "Glue";"$2,250.00";"2"
   ```

5. A list of orders arrives as JSON text. Using only SQL (`json_each`, `->>`), compute how much each customer spent, in cents, highest first.

   ```py
   doc = json.dumps([
       {"customer": "Ana", "items": [{"sku": "PEN", "cents": 150, "qty": 2}, {"sku": "NOTE", "cents": 400, "qty": 1}]},
       {"customer": "Ben", "items": [{"sku": "PEN", "cents": 150, "qty": 5}]},
       {"customer": "Ana", "items": [{"sku": "BAG", "cents": 2500, "qty": 1}]},
   ])
   ```

   ```sh
   customer  spent_cents
   --------  -----------
   Ana       3200
   Ben       750
   (2 rows)
   ```

6. Build an in-memory table `t (id INTEGER PRIMARY KEY, grp INTEGER, val INTEGER)` with 200,000 rows where `grp = id % 1000` and `val = id % 7`. Print the query plan of `SELECT COUNT(*), SUM(val) FROM t WHERE grp = 17`, create an index that fixes it, print the plan again and the result.

   ```sh
   ['SCAN t']
   ['SEARCH t USING INDEX idx_t_grp (grp=?)']
   (200, 594)
   ```

7. Create a view `member_loan_counts` with one row per member (including members who never borrowed): their name, total loans and loans still open. Show it ordered by total loans (highest first), then name.

   ```sh
   member        total_loans  open_loans
   ------------  -----------  ----------
   Alice Nguyen  3            1
   Bruno Silva   3            2
   Chloe Martin  2            1
   Dev Patel     2            2
   Elena Rossi   0            0
   (5 rows)
   ```

8. Create a table `deleted_members (name, email)` and a trigger that copies a member into it whenever the member is deleted. Delete Elena Rossi and print the table. Expected: `[('Elena Rossi', 'elena@example.com')]`.

## Part B: Predict the Output

Write your answer first, then run the code and compare.

1. What does each `print` show, and what happens on the last line?

   ```py
   conn.row_factory = sqlite3.Row
   row = conn.execute("SELECT id AS book_id, title FROM books WHERE id = 3").fetchone()
   print(row["book_id"], row[1], len(row), row.keys(), row["BOOK_ID"])
   row["id"]
   ```

   ```sh
   3 The Hobbit 2 ['book_id', 'title'] 3
   IndexError: No item with that key
   ```

2. What is printed?

   ```py
   c = sqlite3.connect(":memory:")
   c.execute("CREATE TABLE t (x INTEGER PRIMARY KEY CHECK (x > 0)) STRICT")
   try:
       with c:
           c.execute("INSERT INTO t VALUES (1)")
           c.execute("INSERT INTO t VALUES (2)")
           c.execute("INSERT INTO t VALUES (-3)")
   except sqlite3.IntegrityError:
       print("error")
   with c:
       c.execute("INSERT INTO t VALUES (4)")
   print(c.execute("SELECT x FROM t").fetchall())
   print(c.execute("SELECT 1").fetchone())
   ```

   ```sh
   error
   [(4,)]
   (1,)
   ```

   (Two things to explain: where did rows 1 and 2 go, and why does the last line work after the `with` blocks?)

3. Predict all eight values.

   ```py
   print(sqlite3.connect(":memory:").execute("""
       SELECT CAST('abc' AS INTEGER), CAST('12abc' AS INTEGER), CAST('3.9' AS INTEGER), NULLIF('', '') IS NULL,
              '5' + '5', json_valid('{"a": 1'), '{"a": [1, 2]}' ->> '$.a', '{"a": [1, 2]}' ->> '$.a[1]'
   """).fetchone())
   ```

   ```sh
   (0, 12, 3, 1, 10, 0, '[1,2]', 2)
   ```

4. Which orders are accepted, and what are the final stock and the number of rows in `orders`?

   ```py
   s.executescript("""
       CREATE TABLE stock (sku TEXT PRIMARY KEY, qty INTEGER NOT NULL) STRICT;
       CREATE TABLE orders (sku TEXT NOT NULL, qty INTEGER NOT NULL) STRICT;
       INSERT INTO stock VALUES ('A', 10);
       CREATE TRIGGER trg_orders_check BEFORE INSERT ON orders
       WHEN NEW.qty > (SELECT qty FROM stock WHERE sku = NEW.sku)
       BEGIN SELECT RAISE(ABORT, 'too many'); END;
       CREATE TRIGGER trg_orders_take AFTER INSERT ON orders
       BEGIN UPDATE stock SET qty = qty - NEW.qty WHERE sku = NEW.sku; END;
   """)
   for qty in (4, 7, 6, 1):          # each in its own `with s:` block and try/except IntegrityError
       ...
   ```

   ```sh
   ok 4
   refused 7 too many
   ok 6
   refused 1 too many
   (0,) (2,)
   ```

5. A table `t (a, b, c)` has one index, `idx_ab ON t (a, b)`. For each condition, predict whether `EXPLAIN QUERY PLAN SELECT a, b FROM t WHERE ...` says `SEARCH` or `SCAN`: (i) `a = 1`, (ii) `b = 1`, (iii) `a = 1 AND b > 5`, (iv) `a > 1 AND b = 1`, (v) `a = 1 ORDER BY b`. And for `SELECT c FROM t WHERE a = 1`, will the plan say `COVERING`?

   ```sh
   WHERE a = 1                ['SEARCH t USING COVERING INDEX idx_ab (a=?)']
   WHERE b = 1                ['SCAN t USING COVERING INDEX idx_ab']
   WHERE a = 1 AND b > 5      ['SEARCH t USING COVERING INDEX idx_ab (a=? AND b>?)']
   WHERE a > 1 AND b = 1      ['SEARCH t USING COVERING INDEX idx_ab (a>?)']
   WHERE a = 1 ORDER BY b     ['SEARCH t USING COVERING INDEX idx_ab (a=?)']
   SELECT c ... WHERE a = 1: ['SEARCH t USING INDEX idx_ab (a=?)']
   ```

   (The `COVERING` part is because the query reads only `a` and `b`, both inside the index. Case (iv): the search can use `a > 1` only; `b = 1` is checked row by row.)

## Part C: Find the Bug

Each of these runs without an error but gives a wrong or slow result. Find the cause and fix it.

1. The average market value of three firms should ignore the one whose value is missing (`'-'`). The result is wrong. Why? Fix it two ways.

   ```py
   m.execute("CREATE TABLE firms (name TEXT, market_value TEXT)")
   m.executemany("INSERT INTO firms VALUES (?, ?)", [("A", "100"), ("B", "-"), ("C", "300")])
   print(m.execute("SELECT AVG(CAST(market_value AS INTEGER)) FROM firms").fetchone())
   ```

   ```sh
   (133.33333333333334,)      # the bug: the dash became 0
   (200.0,)                   # correct, after the fix
   ```

2. There is an index on `email`, yet a lookup is slow. Why, and what are two ways to fix it?

   ```py
   u.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL) STRICT")
   u.execute("CREATE INDEX idx_users_email ON users (email)")
   Q = "SELECT id FROM users WHERE lower(email) = 'ana@example.com'"
   print([r[3] for r in u.execute("EXPLAIN QUERY PLAN " + Q)])
   ```

   ```sh
   ['SCAN users']                                               # the bug
   ['SEARCH users USING INDEX idx_users_email_lower (<expr>=?)']   # after one fix
   ```

   (Fix 1: an expression index on `lower(email)`. Fix 2: store the e-mail already lower-cased, constrain it, and query with `email = lower(?)`.)

3. A program shares one connection between worker threads and crashes with a `ProgrammingError`. Why? What is the safe pattern?

   ```py
   shared = sqlite3.connect(":memory:")
   def use_it():
       shared.execute("SELECT 1")          # runs in another thread
   threading.Thread(target=use_it).start()
   ```

   ```sh
   SQLite objects created in a thread can only be used in that same thread
   42      # the fix: each thread opens its own connection
   ```

4. We page through `posts` two at a time, sorted by `created`, by remembering the last `created` value. One post is never shown. Which one, and how do you fix it?

   ```py
   k.executemany("INSERT INTO posts VALUES (?, ?)", [(1, "a"), (2, "a"), (3, "a"), (4, "b"), (5, "c")])
   page1 = k.execute("SELECT id, created FROM posts ORDER BY created LIMIT 2").fetchall()
   page2 = k.execute("SELECT id, created FROM posts WHERE created > ? ORDER BY created LIMIT 2", (page1[-1][1],)).fetchall()
   print(page1, page2)
   ```

   ```sh
   [(1, 'a'), (2, 'a')] [(4, 'b'), (5, 'c')]       # the bug: post 3 is lost
   [(1, 'a'), (2, 'a')] [(3, 'a'), (4, 'b')]       # after the fix
   ```

   (The sort key is not unique. Sort by `(created, id)` and compare the pair: `WHERE (created, id) > (?, ?)`.)

## Part D: Explain

Answer in your own words, in a sentence or two.

1. `with conn:` ends a transaction. Does it close the connection? What do you use if you want that?
2. What does `PRAGMA journal_mode = WAL` change, and who can still block whom afterwards?
3. Give three situations where an index does **not** help (or hurts).
4. When would you choose a generated column, a view, or a trigger? Give one example for each from the library or the shop.

## Part E: Mini-Project: New Acquisitions

The library receives a delivery list as a semicolon-separated text. Write a script that:

1. Starts from a copy of the library. **Before loading**, creates a table `book_log (id, book_id, title)` and a trigger that writes a row for each new book, and a view `books_per_author (author, books, pages)`.
2. Reads the text with `csv`, converts the year and pages to integers and the price (`"$7.99"`) to integer cents, and adds each book through your `LibraryRepository.add_book`.
3. **Logs and skips** any bad row instead of stopping: wrong number of fields, a year that is not a number, or a book the database refuses as a duplicate. Print each rejected row with its line number, title and reason.
4. Prints how many books were loaded and how many log rows exist, shows the view for the authors `Dan Simmons`, `Frank Herbert` and `Susanna Clarke`, and exports the three authors with the most books to a JSON file (and builds the first two as JSON inside SQL).

```
title;author;year;pages;price
"Hyperion";"Dan Simmons";"1989";"482";"$7.99"
"The Left Hand of Darkness";"Ursula K. Le Guin";"1969";"304";"$8.50"
"Broken row";"Nobody"
"Dune";"Frank Herbert";"1965";"612";"$10.99"
"Ancillary Justice";"Ann Leckie";"two thousand";"386";"$9.99"
"Piranesi";"Susanna Clarke";"2020";"272";"$11.25"
```

With the data in `solutions/review_4.py` you get:

```sh
loaded 3 rejected 3
(4, 'Broken row', 'ValueError: expected 5 fields, got 2')
(5, 'Dune', 'IntegrityError: UNIQUE constraint failed: books.title, books.author_id')
(6, 'Ancillary Justice', "ValueError: invalid literal for int() with base 10: 'two thousand'")
3
author          books  pages
--------------  -----  -----
Dan Simmons     1      482
Frank Herbert   1      612
Susanna Clarke  1      272
(3 rows)
{'author': 'Andy Weir', 'books': 2, 'pages': 845}
[{"author":"Andy Weir","books":2},{"author":"Jane Austen","books":2}]
```

(Line numbers count the header as line 1. The last two lines are the first object read back from the JSON file, and the JSON built inside SQL.)

Next: the engine changes. SQLite was built for apps that read and write rows; DuckDB is built for questions that scan millions of them. Almost everything you know carries over.

CONGRATULATIONS !

[<< Day 22](../22_Day_Views_and_triggers/22_views_and_triggers.md) | [Day 23 >>](../23_Day_Meet_duckdb/23_meet_duckdb.md)
