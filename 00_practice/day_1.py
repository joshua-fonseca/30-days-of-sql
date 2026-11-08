import sqlite3


def lesson():
    # print(sqlite3.sqlite_version)
    # print(sqlite3.sqlite_version_info)

    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()

    cur.execute('SELECT 1 + 1')
    print(cur.fetchone())

    print(cur.execute("SELECT 'Hello SQL'").fetchone())
    print(cur.execute("SELECT 'SQL' || ' is fun'").fetchone())

    # unpacking
    a, b, c = cur.execute("SELECT 2 * 3, 'a' || 'b', 10 - 4").fetchone()
    print(a, b, c)

    # connecting to a db file
    # If the file does not exist, SQLite creates it

    # errors
    try:
        conn.execute('SELEC 1')
    except sqlite3.Error as e:
        print(type(e).__name__, e)

    try:
        conn.execute('SELECT * FROM nope')
    except sqlite3.Error as e:
        print(type(e).__name__, e)

# exercises
print(sqlite3.sqlite_version)
print(sqlite3.sqlite_version_info)

print("True") if (3, 39, 0) < sqlite3.sqlite_version_info else print("False")

conn = sqlite3.connect(':memory:')
cur = conn.cursor()

val = cur.execute('SELECT 2 + 3').fetchone()
print(val)

val = cur.execute('select "Hello, SQL"').fetchone()
print(*val)

val = cur.execute('select 10/3, 10/3.0').fetchone()
print(val)
# the difference is that the first is integer division so decimals are truncated
# while the second one is float division, specified by the .0 in the 3, hence decimals will be kept

val = cur.execute('select 6*7, 100-58').fetchone()
a, b = val
print(a, b)

val = cur.execute("""
    select 'SQL' || ' is fun'
""").fetchone()
print(val)

val = conn.execute('select 1 + 1').fetchone()
print(val)

val = conn.execute("""
    -- this is a single comment
    select 1 + 1
    /* and then this is a multi
    line comment
    yes */
""").fetchone()
print(val)

# creates a db if it does not exist
conn = sqlite3.connect('library.db')

from pathlib import Path
d = Path(__file__).resolve().parent

db = d / 'library.db'
print("exists") if db.exists() else print("does not exist")

# close
conn.close()

try:
    conn = sqlite3.connect(':memory:')
    conn.execute('SELEKT 1')
except sqlite3.Error as e:
    print(type(e).__name__, e) 

# level 2
# declarative code is "what you want" (desired outcome)
# imperative code is "how to do it" (step-by-step control)

# input: scores = [('Ana', 82), ('Ben', 67), ('Cy', 91), ('Di', 74), ('Eli', 70)]
# output: ['Ana', 'Cy', 'Di']

scores = [('Ana', 82), ('Ben', 67), ('Cy', 91), ('Di', 74), ('Eli', 70)]
out = []
for x in scores:
    name, score = x
    if score > 70:
        out.append(name)
print(out)
# out = [name for name, score in scores if score > 70]

conn = sqlite3.connect(':memory:')
conn.execute('CREATE TABLE scores (name TEXT, score INTEGER)')
conn.executemany('INSERT INTO scores VALUES (?, ?)', scores)

out = conn.execute('select name from scores where score > 70').fetchall()
print([row[0] for row in out])

out = conn.execute("""
    select
        366 * 24 as hours_in_leap,
        7 * 24 * 60 * 60 as seconds_in_week,
        24*60 as minutes_in_day
""").fetchone()
a,b,c = out
print(f"A week has {b} seconds, a leap year has {a} hours and a day has {c} minutes.")

# select 10 / 4 returns 2 because its truncated
out = conn.execute('select 1.0 * 10 / 4').fetchone()
print(out)
# i put the decimal at the start to convert it immediately to floating point math
# if i put the decimal at the end, it would still be truncated because it thinks integer math is being done

# many people still write in upper case because it makes it stand out from the words

def scalar(conn, sql):
    return conn.execute(sql).fetchone()[0]

out = scalar(conn, 'select 6 * 7')
print(out)