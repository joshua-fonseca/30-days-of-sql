<div align="center">
  <h1> 30 Days Of SQL: Review 1 - Foundations (Days 1-10)</h1>
</div>

[<< Day 10](../10_Day_Database_design/10_database_design.md) | [Day 11 >>](../11_Day_Inner_join/11_inner_join.md)

- [Review 1](#review-1)
  - [How to Use This Review](#how-to-use-this-review)
  - [Part A: Write the Query](#part-a-write-the-query)
  - [Part B: Predict the Output](#part-b-predict-the-output)
  - [Part C: Find the Bug](#part-c-find-the-bug)
  - [Part D: Explain](#part-d-explain)
  - [Part E: Normalized Library and Transactions](#part-e-normalized-library-and-transactions)
  - [Mini-Project: Reading Journal](#mini-project-reading-journal)

# Review 1

No new material today. This is a checkpoint for Days 1 to 10, with mixed problems and no hints about which day they come from. If something feels shaky, go back to that day before moving on: the next
days build on all of it.

## How to Use This Review

- Parts A to C use the **flat** library from Day 3 (the `books` table with an `author` text column, as it was before Day 10). Build it in memory with your Day 3 code, or open the backup you made at the start of Day 10, `00_practice/library_flat.db`.
- Part E uses the normalized library you built on Day 10.
- Try each problem **before** looking at the expected output. For Part B, write your prediction first, then run it.
- Put your work in `00_practice/review_1.py`.

## Part A: Write the Query

1. List the Sci-Fi books with their year, newest first.

   ```sh
   title              year
   -----------------  ----
   Project Hail Mary  2021
   The Martian        2011
   Neuromancer        1984
   Dune               1965
   (4 rows)
   ```

2. List the books rated 4.5 or higher, highest rating first, ties by title.

   ```sh
   title                     rating
   ------------------------  ------
   The Pragmatic Programmer  4.8
   The Hobbit                4.7
   1984                      4.6
   The Martian               4.6
   Dune                      4.5
   (5 rows)
   ```

3. List the titles of the books that have no rating, alphabetically. Expect `Brave New World`, `Emma`, `Project Hail Mary`.
4. Show each title with its price in dollars as text with two decimals (use `printf`) for books costing between $10 and $20 inclusive, cheapest first, ties by title.

   ```sh
   title                 price
   --------------------  -----
   Dune                  10.99
   The Martian           11.99
   The Name of the Wind  12.99
   Project Hail Mary     15.99
   (4 rows)
   ```

5. For each genre show the number of books and the average page count rounded to a whole **integer**, ordered by most books first, ties by genre.

   ```sh
   genre      books  avg_pages
   ---------  -----  ---------
   Sci-Fi     4      432
   Dystopian  2      320
   Fantasy    2      486
   Romance    2      377
   Tech       2      408
   (5 rows)
   ```

6. Show the genres whose books cost more than 2500 cents in total, with that total.

   ```sh
   genre   total_cents
   ------  -----------
   Sci-Fi  4796
   Tech    8998
   (2 rows)
   ```

7. Label every book `short` (under 300 pages), `medium` (300 to 500 inclusive) or `long`, ordered by pages then title. Show title and the label. The first rows should be `Neuromancer` and `Pride and Prejudice` as `short`, and the last two `Dune` and
   `The Name of the Wind` as `long`.
8. Which authors wrote more than one book in the library? Show the author and count.

   ```sh
   author       books
   -----------  -----
   Andy Weir    2
   Jane Austen  2
   (2 rows)
   ```

## Part B: Predict the Output

Write down what you think each query returns, then run it.

1. `SELECT COUNT(*), COUNT(rating), ROUND(AVG(rating), 2) FROM books`
2. `SELECT COUNT(*) FROM books WHERE genre NOT IN ('Sci-Fi', 'Fantasy', NULL)`
3. `SELECT 7 / 2, 7 / 2.0, 7 % 2, 10 / 0, NULL + 1, 'a' || NULL`
4. `SELECT MAX(year) - MIN(year) FROM books`

```sh
(12, 9, 4.44)         # 1
(0,)                  # 2   a NULL inside NOT IN ruins it
(3, 3.5, 1, None, None, None)   # 3
(208,)                # 4
```

## Part C: Find the Bug

Each snippet is wrong. Say what is wrong, then fix it.

1. `SELECT genre, COUNT(*) FROM books WHERE COUNT(*) > 1 GROUP BY genre`  fails with `misuse of aggregate: COUNT()`.
2. `SELECT COUNT(*) FROM books WHERE rating = NULL` prints `(0,)`, but three books have no rating.
3. This program inserts a row, closes the connection, and the row is gone when you reopen the file:

   ```py
   a = sqlite3.connect(path)
   a.execute('INSERT INTO t VALUES (1)')
   a.close()
   ```

4. A search box runs `conn.execute(f"SELECT * FROM books WHERE title = '{text}'")`. A visitor types `' OR 1=1 --` and sees all 12 books. What is this attack called and what is the fix? (Day 27 returns to this.)

## Part D: Explain

Answer in a sentence or two, in your own words.

1. Why does `WHERE` not accept `COUNT(*)`, and what do you use instead?
2. Explain the difference between `PRIMARY KEY` and `UNIQUE`.
3. What are the three anomalies of a badly designed table?
4. What does the `A` in ACID mean, and how do you get it in Python's `sqlite3`?
5. Why do we store prices as integer cents?
6. Why does a Python program need `PRAGMA foreign_keys = ON` for every connection?

## Part E: Normalized Library and Transactions

Use the four-table library from Day 10 (`authors`, `books`, `members`, `loans`).

1. Show the titles written by Andy Weir (looking up his id in `authors`, using the old comma-join style: `FROM books, authors WHERE books.author_id = authors.id ...`), alphabetically.

   ```sh
   title              name
   -----------------  ---------
   Project Hail Mary  Andy Weir
   The Martian        Andy Weir
   (2 rows)
   ```

2. Print the row counts of the four tables as a list. Expected: `[10, 12, 5, 10]`.
3. How many loans have not been returned yet? Expected: `(6,)`.
4. A table `acc (id, bal)` has account 1 with 100 and account 2 with 50, and `bal` has `CHECK (bal >= 0)`. Inside `with conn:`, add 150 to account 2 and then subtract 150 from account 1. Catch the error and show that both balances are unchanged.

   ```sh
   CHECK constraint failed: bal >= 0
   [(1, 100), (2, 50)]
   ```

## Mini-Project: Reading Journal

Design and build a small database for a reading journal in an in-memory connection (with foreign keys on):

- `entries`: a title, the date written, and the minutes spent (must be positive),
- `tags`: a unique name,
- a junction table `entry_tags` between them. Deleting an entry must also remove its tag links, but a tag that is in use must not be deletable.

Then:

1. Insert four entries and three tags (`basics`, `hard`, `design`) and link them as you like.
2. Show, for each tag, how many entries use it and the total minutes. (You can use the comma-join style: `FROM entry_tags, tags, entries WHERE ...`.)
3. Delete one entry and verify its links disappeared.

With the data in `solutions/review_1.py` you get:

```sh
tag     entries  minutes
------  -------  -------
hard    3        125
basics  1        30
design  1        60
(3 rows)
(3,)         # links left after deleting entry 3 (it had two)
```

Tomorrow the comma-join stops being a trick and becomes the main event: joins.

CONGRATULATIONS !

[<< Day 10](../10_Day_Database_design/10_database_design.md) | [Day 11 >>](../11_Day_Inner_join/11_inner_join.md)
