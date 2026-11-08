<div align="center">
  <h1> 30 Days Of SQL: Day 3 - Inserting Data</h1>
</div>

[<< Day 2](../02_Day_Creating_tables/02_creating_tables.md) | [Day 4 >>](../04_Day_Select/04_select.md)

- [Day 3](#day-3)
  - [INSERT INTO](#insert-into)
    - [Always Name Your Columns](#always-name-your-columns)
    - [Inserting Several Rows at Once](#inserting-several-rows-at-once)
    - [Leaving Columns Out](#leaving-columns-out)
  - [Saving Your Changes: commit()](#saving-your-changes-commit)
  - [Placeholders: Passing Python Values Safely](#placeholders-passing-python-values-safely)
    - [Question-Mark Placeholders](#question-mark-placeholders)
    - [Named Placeholders](#named-placeholders)
    - [Why Not f-strings?](#why-not-f-strings)
  - [Inserting Many Rows: executemany](#inserting-many-rows-executemany)
  - [What Happened? lastrowid and rowcount](#what-happened-lastrowid-and-rowcount)
  - [When an Insert Fails](#when-an-insert-fails)
  - [ Exercises: Day 3](#exercises-day-3)
    - [Exercises: Level 1](#exercises-level-1)
    - [Exercises: Level 2](#exercises-level-2)
    - [Exercises: Level 3](#exercises-level-3)

# Day 3

## INSERT INTO

Yesterday you created tables. Today you fill them. `INSERT INTO` adds one or more new rows to a table.

```sql
-- syntax
INSERT INTO table_name (column1, column2, ...)
VALUES (value1, value2, ...);
```

We will use this small table all day:

```py
import sqlite3

conn = sqlite3.connect(':memory:')
conn.execute('''
    CREATE TABLE students (
        id   INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age  INTEGER,
        city TEXT DEFAULT 'Unknown'
    ) STRICT
''')

conn.execute("INSERT INTO students (name, age, city) VALUES ('Ana', 21, 'Toronto')")
print(conn.execute('SELECT * FROM students').fetchall())
# [(1, 'Ana', 21, 'Toronto')]
```

The values must be in the same order as the column list. Text goes in single quotes, numbers do not. We did not mention `id`, so SQLite
filled in the next number (1) for us, as you learned yesterday.

### Always Name Your Columns

SQL lets you leave the column list out and give a value for every column, in table order:

```py
try:
    conn.execute("INSERT INTO students VALUES ('Zed', 30, 'Rome')")
except sqlite3.Error as e:
    print(type(e).__name__, e)      # OperationalError table students has 4 columns but 3 values were supplied
```

That fails because we forgot the `id`. Even when it works, it is fragile: if someone adds or reorders a column later, your insert
silently puts values in the wrong places. **Always write the column list.** It documents your intent and survives schema changes.

### Inserting Several Rows at Once

Put several value lists after `VALUES`, separated by commas:

```py
conn.execute('''
    INSERT INTO students (name, age, city) VALUES
        ('Ben', 23, 'London'),
        ('Cy',  22, 'Toronto'),
        ('Di',  20, 'Paris')
''')
```

One statement with many rows is faster than many statements with one row each, and it is all-or-nothing: if any row is invalid, none
of them are inserted.

### Leaving Columns Out

Columns you do not mention get their `DEFAULT`, or `NULL` if there is no default. (A `NOT NULL` column with no default must be given.)

```py
conn.execute("INSERT INTO students (name) VALUES ('Eli')")
print(conn.execute('SELECT * FROM students').fetchall())
# [(1, 'Ana', 21, 'Toronto'), (2, 'Ben', 23, 'London'), (3, 'Cy', 22, 'Toronto'),
# (4, 'Di', 20, 'Paris'), (5, 'Eli', None, 'Unknown')]
```

Eli has no age, so `age` is `NULL` (Python's `None`), and `city` took its default `'Unknown'`.

## Saving Your Changes: commit()

Here is the most important thing to know about writing to a database from Python. When you insert, update or delete, the changes
sit in an open **transaction**. They are visible to your own connection but are **not saved** until you call `conn.commit()`. If your
program closes the connection without a commit, the changes are thrown away.

Let's prove it with a database file:

```py
conn1 = sqlite3.connect('demo.db')
conn1.execute('CREATE TABLE t (x INTEGER)')
conn1.execute('INSERT INTO t VALUES (1)')
conn1.close()                                       # closed without commit

conn2 = sqlite3.connect('demo.db')
print(conn2.execute('SELECT COUNT(*) FROM t').fetchone())      # (0,)   the insert was lost
```

(`SELECT COUNT(*) FROM t` simply counts the rows in a table. Day 7 explains it properly. Until then, use it as a quick "how many rows" check.)

Now commit:

```py
conn2.execute('INSERT INTO t VALUES (1)')
conn2.commit()                                      # save it
conn2.close()

conn3 = sqlite3.connect('demo.db')
print(conn3.execute('SELECT COUNT(*) FROM t').fetchone())      # (1,)
```

Other connections cannot see your uncommitted changes either, which is the point: nobody sees half-finished work.

```py
conn3.execute('INSERT INTO t VALUES (2)')
conn4 = sqlite3.connect('demo.db')
print(conn4.execute('SELECT COUNT(*) FROM t').fetchone())      # (1,)   conn3 has not committed yet
conn3.commit()
print(conn4.execute('SELECT COUNT(*) FROM t').fetchone())      # (2,)
```

Notice that `CREATE TABLE` took effect immediately, but `INSERT` needed a commit. Statements that change data (`INSERT`, `UPDATE`,
`DELETE`) open a transaction. Day 8 explains transactions properly, including tidier ways to commit than calling `commit()` by hand.
For now: **after you insert, call `conn.commit()`**.

## Placeholders: Passing Python Values Safely

So far we typed the values into the SQL text. Real programs get their values from Python variables, files and users. To pass them
in, you use **placeholders**. You write a marker in the SQL and hand the real values over separately. This is also called a
**parameterized query** or a **prepared statement**.

### Question-Mark Placeholders

```sql
-- syntax
INSERT INTO table_name (column1, column2) VALUES (?, ?);
```

```py
name, age, city = 'Fay', 25, 'Oslo'
conn.execute('INSERT INTO students (name, age, city) VALUES (?, ?, ?)', (name, age, city))
```

Each `?` is filled with the next item of the tuple, in order. Note that the values are passed as a **tuple** (or list), even if
there is only one: `('Fay',)`, with that trailing comma. Passing `'Fay'` alone would be treated as three characters.

### Named Placeholders

With many columns, counting question marks gets hard to follow. Use `:name` markers and pass a dictionary:

```py
person = {'name': 'Gus', 'age': 27, 'city': 'Rome'}
conn.execute('INSERT INTO students (name, age, city) VALUES (:name, :age, :city)', person)
```

The dictionary can even have extra keys. Only the names that appear in the SQL are used. If the counts do not match with `?`
placeholders, you get an error:

```py
try:
    conn.execute('INSERT INTO students (name, age) VALUES (?, ?)', ('X',))
except sqlite3.Error as e:
    print(type(e).__name__, e)
    # ProgrammingError Incorrect number of bindings supplied. The current statement uses 2, and there are 1 supplied.
```

### Why Not f-strings?

You know f-strings, and it is tempting to build SQL with them. **Don't.**

```py
name = "O'Brien"
try:
    conn.execute(f"INSERT INTO students (name) VALUES ('{name}')")
except sqlite3.Error as e:
    print(type(e).__name__, e)      # OperationalError near "Brien": syntax error
```

The apostrophe in O'Brien ended the SQL string early and broke the statement. That is the *harmless* outcome. If the text came from a user,
a person could write SQL into it on purpose and make your program run it. That attack is called **SQL injection**, and Day 27 covers it properly.

With a placeholder, the value is never glued into the SQL text, so it is always safe, whatever it contains:

```py
conn.execute('INSERT INTO students (name) VALUES (?)', (name,))
print(conn.execute("SELECT name FROM students WHERE name LIKE 'O%'").fetchall())      # [("O'Brien",)]
```

**Rule for the whole course:** values go in through placeholders, never through f-strings or `+`. (f-strings are fine for
*printing*.) Table and column names cannot be placeholders, a topic we return to on Day 27.

## Inserting Many Rows: executemany

To insert a whole list of rows, use `executemany`. It runs the same statement once for every item in the list.

```py
rows = [('H1', 1), ('H2', 2), ('H3', 3)]
conn.executemany('INSERT INTO students (name, age) VALUES (?, ?)', rows)
```

It works with a list of dictionaries and named placeholders too:

```py
people = [{'name': 'D1', 'age': 5}, {'name': 'D2', 'age': 6}]
conn.executemany('INSERT INTO students (name, age) VALUES (:name, :age)', people)
```

This is much faster than calling `execute` in a Python loop, and you only need one `commit()` at the end. Loading a CSV file or JSON
file into a table is typically "read the file into a list, then `executemany`". You will do exactly that in the Level 3 exercises.

## What Happened? lastrowid and rowcount

After an insert, the cursor tells you what happened:

- `cursor.rowcount`: how many rows the statement changed,
- `cursor.lastrowid`: the `id` of the last row inserted.

```py
cur = conn.execute("INSERT INTO students (name, age, city) VALUES ('Hal', 30, 'Lima')")
print(cur.rowcount, cur.lastrowid)       # 1 14

cur = conn.execute('''
    INSERT INTO students (name) VALUES ('Ivy'), ('Jo'), ('Kai')
''')
print(cur.rowcount, cur.lastrowid)       # 3 17     three rows, and the last one has id 17
```

`lastrowid` is very handy: after you insert a new student you get their id straight away, without another query. It is how
you connect new rows to one another (a new order and its order lines, for example).

**Common mistake:** `lastrowid` is only updated by `execute`, **not** by `executemany`. After `executemany` it is `None` on a
fresh cursor. If you need ids from a bulk insert, query for them afterwards. `rowcount` does work with `executemany`:

```py
cur = conn.executemany('INSERT INTO students (name, age) VALUES (?, ?)', [('P1', 9), ('P2', 8)])
print(cur.rowcount, cur.lastrowid)       # 2 None
```

## When an Insert Fails

If a row breaks a rule, SQLite raises `sqlite3.IntegrityError`, and the row is not inserted.

```py
try:
    conn.execute('INSERT INTO students (age) VALUES (3)')
except sqlite3.IntegrityError as e:
    print(e)        # NOT NULL constraint failed: students.name

try:
    conn.execute("INSERT INTO students (id, name) VALUES (1, 'Duplicate')")
except sqlite3.IntegrityError as e:
    print(e)        # UNIQUE constraint failed: students.id
```

Constraints (rules a table enforces) are the subject of Day 9. For now, note that the database protects your data even when your Python
code makes a mistake.

You can now put data into a database and keep it there. Tomorrow you start getting it back out. Now do some exercises.

## Exercises: Day 3

### Exercises: Level 1

Continue with `00_practice/library.db` from Day 2 (with the final 9-column `books` table). If it is not in that shape, rerun your
Day 2 final `CREATE TABLE` first. Because exercises from here on use the **same twelve books**, please insert exactly these:

| id | title | author | year | pages | genre | price_cents | rating |
|---|---|---|---|---|---|---|---|
| 1 | Dune | Frank Herbert | 1965 | 612 | Sci-Fi | 1099 | 4.5 |
| 2 | Neuromancer | William Gibson | 1984 | 271 | Sci-Fi | 899 | 4.0 |
| 3 | The Hobbit | J.R.R. Tolkien | 1937 | 310 | Fantasy | 799 | 4.7 |
| 4 | The Name of the Wind | Patrick Rothfuss | 2007 | 662 | Fantasy | 1299 | 4.4 |
| 5 | Pride and Prejudice | Jane Austen | 1813 | 279 | Romance | 599 | 4.3 |
| 6 | Emma | Jane Austen | 1815 | 474 | Romance | 649 | *(none)* |
| 7 | 1984 | George Orwell | 1949 | 328 | Dystopian | 799 | 4.6 |
| 8 | Brave New World | Aldous Huxley | 1932 | 311 | Dystopian | 849 | *(none)* |
| 9 | The Pragmatic Programmer | Andrew Hunt | 1999 | 352 | Tech | 4999 | 4.8 |
| 10 | Clean Code | Robert C. Martin | 2008 | 464 | Tech | 3999 | 4.1 |
| 11 | Project Hail Mary | Andy Weir | 2021 | 476 | Sci-Fi | 1599 | *(none)* |
| 12 | The Martian | Andy Weir | 2011 | 369 | Sci-Fi | 1199 | 4.6 |

*(none)* means the rating is `NULL` (not rated yet). Don't insert the `id`, `title_length` or any other generated value: ids come out
1 to 12 in order if you insert the books in table order.

1. Connect to `00_practice/library.db`.
2. Insert book 1 (Dune) with a single `INSERT ... VALUES` that names its columns. Don't forget `commit()`.
3. Insert books 2, 3 and 4 with **one** statement that has three value lists.
4. Insert book 5 using `?` placeholders and a tuple.
5. Insert book 6 (Emma) using `:name` placeholders and a dictionary. Leave `rating` out of the column list entirely.
6. Insert books 7 to 12 with one `executemany` call. Use `None` for a missing rating.
7. Print `cursor.lastrowid` after the insert in steps 2, 4 and 5. What do you get after the `executemany` in step 6?
8. Commit, then print the number of books with `SELECT COUNT(*) FROM books`. It should be `12`.
9. Print `id` and `title` for all books to check they are in the right order.
10. Close the connection, reconnect, and confirm there are still 12 books.
11. Insert a book titled `'Test Book'` by `'Nobody'`, **do not commit**, close the connection, reconnect and count again. Explain why
    you still have 12.
12. Print the book with `id = 6` and confirm its `rating` is `None` and its `title_length` is `4`.

```sh
# expected for step 9
[(1, 'Dune'), (2, 'Neuromancer'), (3, 'The Hobbit'), (4, 'The Name of the Wind'), (5, 'Pride and Prejudice'), (6, 'Emma'),
 (7, '1984'), (8, 'Brave New World'), (9, 'The Pragmatic Programmer'), (10, 'Clean Code'), (11, 'Project Hail Mary'), (12, 'The Martian')]
```

### Exercises: Level 2

1. Here is a list of dictionaries. Create a table `students (id, name, age, city)` in an in-memory database (`name` required, `city`
   defaults to `'Unknown'`) and insert all of them with **named placeholders** and a single `executemany`. Print how many rows were inserted.

   ```py
   people = [
       {'name': 'Ana', 'age': 21, 'city': 'Toronto'},
       {'name': 'Ben', 'age': 23, 'city': 'London'},
       {'name': 'Cy',  'age': 22, 'city': 'Toronto'},
       {'name': 'Di',  'age': 20, 'city': 'Paris'},
   ]
   ```

2. Write a function `add_book(conn, title, author, year=None, pages=None, genre=None, price_cents=None, rating=None)` that inserts a
   book with placeholders, commits, and **returns the new id**. Test it on a separate **in-memory** database with the same `books`
   table (so your `library.db` keeps exactly 12 books). Adding one book to an empty table should return `1`, and a second book `2`.

3. Create a table `tasks (id integer primary key, title text not null, done integer default 0, created text default CURRENT_TIMESTAMP)`
   and insert a task giving only a `title`. Print the row. What are `done` and `created`? (`CURRENT_TIMESTAMP` is a built-in
   value that holds the current date and time, so `created` will differ for you.)

   ```sh
   (1, 'Write Day 3 notes', 0, '2025-03-14 09:30:12')
   ```

4. Using the `students` table from exercise 1, make the three mistakes below, catch each error, and print its type and message.
   a. Write an `INSERT` with two `?` placeholders but pass three values.
   b. Insert a row that has no value for the `NOT NULL` column `name`.
   c. Insert two rows in **one** statement that have the same `id`. Afterwards, check that *neither* of the two rows was inserted.

   ```sh
   a ProgrammingError Incorrect number of bindings supplied. The current statement uses 2, and there are 3 supplied.
   b IntegrityError NOT NULL constraint failed: students.name
   c IntegrityError UNIQUE constraint failed: students.id
   ```

5. Someone wrote this code to insert a student named `D'Arcy`. It crashes. Explain why, then fix it:

   ```py
   name = "D'Arcy"
   conn.execute(f"INSERT INTO students (name) VALUES ('{name}')")
   ```

### Exercises: Level 3

These two exercises create `00_practice/datasets.db`, which we reuse in many later days. Keep it.

1. Load `data/countries_data.json` into a table
   `countries (name, capital, population, currency)`. Ignore the `languages` list for now. We will come back to it on Day 10.
   Some countries have an empty capital: store those as `NULL`, not as an empty string. Use `executemany` and a single commit. Verify:

   ```py
   print(conn.execute('SELECT COUNT(*) FROM countries').fetchone())                              # (250,)
   print(conn.execute('SELECT COUNT(*) FROM countries WHERE capital IS NULL').fetchone())        # (5,)
   print(conn.execute('SELECT COUNT(*) FROM countries WHERE population = 0').fetchone())         # (2,)
   print(conn.execute('SELECT name, capital FROM countries LIMIT 3').fetchall())
   # [('Afghanistan', 'Kabul'), ('Åland Islands', 'Mariehamn'), ('Albania', 'Tirana')]
   ```

2. Load `data/hacker_news.csv` into a table
   `hn_posts (id, title, url, num_points, num_comments, author, created_at)`. Use `csv.DictReader`. Convert `id`, `num_points` and
   `num_comments` to integers, store an empty `url` as `NULL`, and leave `created_at` as the text it is (we deal with its odd format
   on Day 16). Verify:

   ```py
   print(conn.execute('SELECT COUNT(*) FROM hn_posts').fetchone())                       # (20099,)
   print(conn.execute('SELECT COUNT(*) FROM hn_posts WHERE url IS NULL').fetchone())     # (2440,)
   print(conn.execute('SELECT id, title FROM hn_posts LIMIT 2').fetchall())
   # [(12224879, 'Interactive Dynamic Video'), (11964716, "Florida DJs May Face Felony for April Fools' Water Joke")]
   ```

3. Put the loading code for exercises 1 and 2 into two functions, `load_countries(conn)` and `load_hn_posts(conn)`, that first
   `DROP TABLE IF EXISTS` the table, so running your script twice still leaves exactly 250 and 20,099 rows.

CONGRATULATIONS !

[<< Day 2](../02_Day_Creating_tables/02_creating_tables.md) | [Day 4 >>](../04_Day_Select/04_select.md)
