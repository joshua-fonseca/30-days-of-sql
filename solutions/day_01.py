# Day 1 reference solutions
import sqlite3
from pathlib import Path

from helpers import WORK

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
print(sqlite3.sqlite_version)

print("# Level 1, Q2")
print(sqlite3.sqlite_version_info >= (3, 39, 0))

print("# Level 1, Q3")
conn = sqlite3.connect(":memory:")
cur = conn.cursor()

print("# Level 1, Q4")
print(cur.execute("SELECT 2 + 3").fetchone())  # (5,)

print("# Level 1, Q5")
print(cur.execute("SELECT 'Hello, SQL'").fetchone()[0])  # Hello, SQL

print("# Level 1, Q6")
print(cur.execute("SELECT 10 / 3, 10 / 3.0").fetchone())  # (3, 3.3333333333333335)
# Answer: with two integers SQLite does integer division and drops the decimals.
# One decimal operand makes the whole division a decimal division.

print("# Level 1, Q7")
print(cur.execute("SELECT 17 % 5").fetchone())  # (2,)

print("# Level 1, Q8")
product, difference = cur.execute("SELECT 6 * 7, 100 - 58").fetchone()
print(product, difference)  # 42 42

print("# Level 1, Q9")
print(cur.execute("SELECT 'SQL' || ' is fun'").fetchone()[0])  # SQL is fun

print("# Level 1, Q10")
print(conn.execute("SELECT 1 + 1").fetchone())  # (2,)

print("# Level 1, Q11")
print(conn.execute("SELECT 1 + 2 -- add\n /* and a block comment */").fetchone())  # (3,)

print("# Level 1, Q12")
db_path = WORK / "day01_library.db"
db_path.unlink(missing_ok=True)
file_conn = sqlite3.connect(db_path)
print(Path(db_path).exists())  # True
file_conn.close()

print("# Level 1, Q13")
try:
    conn.execute("SELEKT 1")
except sqlite3.Error as e:
    print(type(e).__name__, e)  # OperationalError near "SELEKT": syntax error

print("# Level 1, Q14")
# Terminal: uv run python -m sqlite3   then   SELECT 6 * 7;   prints (42,)   then   .quit

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
# Declarative = describe the result you want and let the system find the steps.
# Imperative = write each step yourself (loops, ifs, appending).
scores = [("Ana", 82), ("Ben", 67), ("Cy", 91), ("Di", 74), ("Eli", 70)]
passed = []
for name, score in scores:
    if score > 70:
        passed.append(name)
print(passed)  # ['Ana', 'Cy', 'Di']

conn.execute("CREATE TABLE scores (name TEXT, score INTEGER)")
conn.executemany("INSERT INTO scores VALUES (?, ?)", scores)
print([row[0] for row in conn.execute("SELECT name FROM scores WHERE score > 70")])  # ['Ana', 'Cy', 'Di']

print("# Level 2, Q2")
week, leap_hours, day_minutes = conn.execute("SELECT 7 * 24 * 3600, 366 * 24, 24 * 60").fetchone()
print(f"A week has {week} seconds, a leap year has {leap_hours} hours and a day has {day_minutes} minutes.")

print("# Level 2, Q3")
# 10 / 4 is integer division (both operands are integers), so the .5 is dropped.
print(conn.execute("SELECT 10 * 1.0 / 4").fetchone())  # (2.5,)

print("# Level 2, Q4")
print(conn.execute("select 1+1").fetchone(), conn.execute("Select 1 + 1").fetchone(), conn.execute("SELECT 1+1").fetchone())
# Uppercase keywords stand out from table and column names, so queries are quicker to read.

print("# Level 2, Q5")


def scalar(conn, sql):
    """Return the first value of the first row."""
    return conn.execute(sql).fetchone()[0]


print(scalar(conn, "SELECT 6 * 7"))  # 42
