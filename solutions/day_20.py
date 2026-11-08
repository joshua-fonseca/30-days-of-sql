# Day 20 reference solutions: importing, cleaning and exporting data
import csv
import io
import json
import sqlite3
from contextlib import closing
from itertools import batched

from helpers import DATA, WORK, show

COLUMNS = ["id", "rank", "name", "employees", "previousrank", "revenues", "revenuechange",
           "profits", "profitschange", "assets", "marketvalue"]


def load_f500_raw(conn: sqlite3.Connection) -> int:
    """Create the TEMP staging table f500_raw (all TEXT) and load F500.csv into it in batches of 100."""
    conn.execute("""
        CREATE TEMP TABLE f500_raw (
            id TEXT, rank TEXT, name TEXT, employees TEXT, previousrank TEXT, revenues TEXT,
            revenuechange TEXT, profits TEXT, profitschange TEXT, assets TEXT, marketvalue TEXT
        )
    """)
    with open(DATA / "F500.csv", newline="", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)  # skip the header
        for chunk in batched(reader, 100):
            conn.executemany("INSERT INTO f500_raw VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", chunk)
    return conn.execute("SELECT COUNT(*) FROM f500_raw").fetchone()[0]


# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1: the raw first lines")
lines = (DATA / "F500.csv").read_text(encoding="utf-8").splitlines()
print(lines[0])
print(lines[1])

print("# Level 1, Q2: csv.reader with a delimiter")
with open(DATA / "F500.csv", newline="", encoding="utf-8") as f:
    reader = csv.reader(f, delimiter=";")
    header = next(reader)
    first = next(reader)
print(header)
print(first)

print("# Level 1, Q3: how many data rows")
with open(DATA / "F500.csv", newline="", encoding="utf-8") as f:
    print(sum(1 for _ in csv.reader(f, delimiter=";")) - 1)

print("# Level 1, Q4: TEMP staging table")
conn = sqlite3.connect(WORK / "d20.db")
print(load_f500_raw(conn))

print("# Level 1, Q5: everything is text")
print(conn.execute("SELECT typeof(employees), typeof(revenues), typeof(rank) FROM f500_raw LIMIT 1").fetchone())

print("# Level 1, Q6: commas and dollar signs")
print(conn.execute("SELECT SUM(employees LIKE '%,%'), SUM(revenues LIKE '%$%') FROM f500_raw").fetchone())

print("# Level 1, Q7: the one profit without a dollar sign")
show(conn.execute("SELECT name, profits FROM f500_raw WHERE profits NOT LIKE '%$%'"))

print("# Level 1, Q8: negative profits")
print(conn.execute("SELECT COUNT(*) FROM f500_raw WHERE profits LIKE '-$%'").fetchone())

print("# Level 1, Q9: dashes and empty strings")
print(conn.execute("SELECT SUM(marketvalue = '-'), SUM(previousrank = '') FROM f500_raw").fetchone())

print("# Level 1, Q10: CAST of a non-number")
print(conn.execute("SELECT CAST('-' AS INTEGER), CAST('12abc' AS INTEGER), CAST('2,300,000' AS INTEGER)").fetchone())

print("# Level 1, Q11: strip the formatting")
print(conn.execute("SELECT replace(replace(trim(revenues), '$', ''), ',', '') FROM f500_raw WHERE name = 'Walmart'").fetchone())

print("# Level 1, Q12: total revenue of all 500 companies")
print(conn.execute("""
    SELECT SUM(CAST(replace(replace(trim(revenues), '$', ''), ',', '') AS INTEGER)) FROM f500_raw
""").fetchone())

print("# Level 1, Q13: NULLIF for empty strings")
print(conn.execute("SELECT COUNT(*) FROM f500_raw WHERE NULLIF(trim(previousrank), '') IS NULL").fetchone())

print("# Level 1, Q14: explain in your own words")
# A staging table is all TEXT so that nothing can fail or be silently changed while loading. We look at what
# is really in the file with SQL, decide the rules, and only then write the clean typed table.

print("# Level 1, Q15: a TEMP table disappears with its connection")
conn.close()
conn = sqlite3.connect(WORK / "d20.db")
try:
    conn.execute("SELECT COUNT(*) FROM f500_raw")
except sqlite3.OperationalError as e:
    print("OperationalError:", e)

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1: the clean table")
load_f500_raw(conn)
conn.execute("""
    CREATE TEMP VIEW f500_stripped AS
    SELECT CAST(rank AS INTEGER) AS rank, name,
           replace(replace(trim(employees), ',', ''), '$', '')   AS employees,
           NULLIF(trim(previousrank), '')                        AS previous_rank,
           replace(replace(trim(revenues), ',', ''), '$', '')    AS revenues,
           replace(trim(revenuechange), '%', '')                 AS revenue_change,
           replace(replace(trim(profits), ',', ''), '$', '')     AS profits,
           replace(trim(profitschange), '%', '')                 AS profits_change,
           replace(replace(trim(assets), ',', ''), '$', '')      AS assets,
           replace(replace(trim(marketvalue), ',', ''), '$', '') AS market_value
    FROM f500_raw
""")
conn.execute("DROP TABLE IF EXISTS f500")
conn.execute("""
    CREATE TABLE f500 (
        rank               INTEGER PRIMARY KEY,
        name               TEXT NOT NULL,
        employees          INTEGER NOT NULL,
        previous_rank      INTEGER,
        revenue_usd        INTEGER NOT NULL,
        revenue_change_pct REAL,
        profit_usd         INTEGER,
        profit_change_pct  REAL,
        assets_usd         INTEGER NOT NULL,
        market_value_usd   INTEGER
    ) STRICT
""")
conn.execute("""
    INSERT INTO f500
    SELECT rank, name,
           CAST(employees AS INTEGER),
           CAST(previous_rank AS INTEGER),
           CAST(revenues AS INTEGER) * 1000000,
           CASE WHEN revenue_change GLOB '*[0-9]*' AND revenue_change NOT GLOB '*[^0-9.-]*' THEN CAST(revenue_change AS REAL) END,
           CASE WHEN profits GLOB '*[0-9]*' AND profits NOT GLOB '*[^0-9.-]*' THEN CAST(ROUND(CAST(profits AS REAL) * 1000000) AS INTEGER) END,
           CASE WHEN profits_change GLOB '*[0-9]*' AND profits_change NOT GLOB '*[^0-9.-]*' THEN CAST(profits_change AS REAL) END,
           CAST(assets AS INTEGER) * 1000000,
           CASE WHEN market_value GLOB '*[0-9]*' AND market_value NOT GLOB '*[^0-9.-]*' THEN CAST(market_value AS INTEGER) * 1000000 END
    FROM f500_stripped
""")
conn.commit()
print(conn.execute("SELECT COUNT(*) FROM f500").fetchone())
show(conn.execute("SELECT rank, name, employees, revenue_usd, profit_usd, market_value_usd FROM f500 WHERE rank IN (1, 34, 500) ORDER BY rank"))

print("# Level 2, Q2: the values that failed to convert")
show(conn.execute("""
    SELECT 'revenue_change' AS field, COUNT(*) AS failed FROM f500_stripped
        WHERE NOT (revenue_change GLOB '*[0-9]*' AND revenue_change NOT GLOB '*[^0-9.-]*')
    UNION ALL
    SELECT 'profits', COUNT(*) FROM f500_stripped WHERE NOT (profits GLOB '*[0-9]*' AND profits NOT GLOB '*[^0-9.-]*')
    UNION ALL
    SELECT 'profits_change', COUNT(*) FROM f500_stripped WHERE NOT (profits_change GLOB '*[0-9]*' AND profits_change NOT GLOB '*[^0-9.-]*')
    UNION ALL
    SELECT 'market_value', COUNT(*) FROM f500_stripped WHERE NOT (market_value GLOB '*[0-9]*' AND market_value NOT GLOB '*[^0-9.-]*')
"""))
show(conn.execute("""
    SELECT rank, name FROM f500_stripped
    WHERE NOT (revenue_change GLOB '*[0-9]*' AND revenue_change NOT GLOB '*[^0-9.-]*')
    ORDER BY rank
"""))
print(conn.execute("SELECT COUNT(*) FROM f500 WHERE profit_usd IS NULL OR revenue_change_pct IS NULL OR profit_change_pct IS NULL OR market_value_usd IS NULL").fetchone())

print("# Level 2, Q3: deduplicate while loading")
shop = sqlite3.connect(DATA / "shop.db")
shop_rows = shop.execute("SELECT email, signed_up_at FROM newsletter_signups ORDER BY signed_up_at").fetchall()
d = sqlite3.connect(":memory:")
d.execute("CREATE TABLE subscribers (email TEXT PRIMARY KEY, first_signup TEXT NOT NULL) STRICT")
d.executemany("""
    INSERT INTO subscribers (email, first_signup) VALUES (lower(trim(?)), ?)
    ON CONFLICT (email) DO NOTHING
""", shop_rows)
print(len(shop_rows), d.execute("SELECT COUNT(*) FROM subscribers").fetchone())
show(d.execute("SELECT email, first_signup FROM subscribers ORDER BY first_signup, email LIMIT 5"))
# the same with INSERT ... SELECT and GROUP BY
alt = shop.execute("""
    SELECT lower(trim(email)) AS email, MIN(signed_up_at) AS first_signup
    FROM newsletter_signups GROUP BY lower(trim(email)) ORDER BY first_signup, email LIMIT 5
""").fetchall()
assert alt == d.execute("SELECT email, first_signup FROM subscribers ORDER BY first_signup, email LIMIT 5").fetchall()

print("# Level 2, Q4: log and skip bad rows")
text = """sku,name,price
PEN,Pen,1.50
NOTE,Notebook,4.00
BAD1,Broken row
STAP,Stapler,nine
GLUE,Glue stick,2.25
"""
good, rejects = [], []
for line_no, row in enumerate(csv.reader(io.StringIO(text)), start=1):
    if line_no == 1:
        continue
    try:
        if len(row) != 3:
            raise ValueError(f"expected 3 fields, got {len(row)}")
        good.append((row[0], row[1], round(float(row[2]) * 100)))
    except ValueError as e:
        rejects.append((line_no, row, str(e)))
t = sqlite3.connect(":memory:")
t.execute("CREATE TABLE products (sku TEXT PRIMARY KEY, name TEXT NOT NULL, price_cents INTEGER NOT NULL) STRICT")
t.executemany("INSERT INTO products VALUES (?, ?, ?)", good)
print(t.execute("SELECT COUNT(*) FROM products").fetchone())
for r in rejects:
    print("rejected", r)

print("# Level 2, Q5: JSON functions")
doc = ('{"order": 1001, "customer": {"name": "Ana", "tags": ["vip", "newsletter"]}, '
       '"items": [{"sku": "PEN", "qty": 2, "price_cents": 150}, {"sku": "NOTE", "qty": 1, "price_cents": 400}]}')
j = sqlite3.connect(":memory:")
print(j.execute("SELECT :doc ->> '$.customer.name', json_array_length(:doc, '$.items'), :doc -> '$.customer.tags'", {"doc": doc}).fetchone())
print(j.execute("SELECT COUNT(*) FROM json_each(:doc, '$.customer.tags') WHERE value = 'vip'", {"doc": doc}).fetchone())
print(j.execute("SELECT SUM(item.value ->> 'qty' * (item.value ->> 'price_cents')) FROM json_each(:doc, '$.items') AS item", {"doc": doc}).fetchone())
show(j.execute("SELECT item.value ->> 'sku' AS sku, item.value ->> 'qty' AS qty FROM json_each(:doc, '$.items') AS item ORDER BY sku", {"doc": doc}))

print("# Level 2, Q6: round trip through CSV")
out = WORK / "d20_signups.csv"
cur = shop.execute("SELECT lower(trim(email)) AS email, MIN(signed_up_at) AS first_signup FROM newsletter_signups GROUP BY 1 ORDER BY 2, 1")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([c[0] for c in cur.description])
    w.writerows(cur)
with open(out, newline="", encoding="utf-8") as f:
    back = list(csv.DictReader(f))
print(len(back), back[0])

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1: most profitable companies")
show(conn.execute("""
    SELECT rank, name, profit_usd / 1000000 AS profit_millions,
           revenue_usd / employees AS revenue_per_employee_usd
    FROM f500
    WHERE profit_usd IS NOT NULL
    ORDER BY profit_usd DESC, name
    LIMIT 10
"""))

print("# Level 3, Q2: languages from raw JSON")
conn.execute("DROP TABLE IF EXISTS countries_raw")
conn.execute("CREATE TABLE countries_raw (doc TEXT NOT NULL CHECK (json_valid(doc))) STRICT")
countries = json.loads((DATA / "countries_data.json").read_text(encoding="utf-8"))
conn.executemany("INSERT INTO countries_raw (doc) VALUES (?)", [(json.dumps(c),) for c in countries])
print(conn.execute("SELECT COUNT(*) FROM countries_raw").fetchone())
top_languages = """
    SELECT lang.value AS language, COUNT(*) AS countries
    FROM countries_raw AS c
    JOIN json_each(c.doc, '$.languages') AS lang
    GROUP BY lang.value
    ORDER BY countries DESC, language
    LIMIT 10
"""
show(conn.execute(top_languages))
# JSONB: the same documents in the binary format, same answer
conn.execute("ALTER TABLE countries_raw ADD COLUMN bdoc BLOB")
conn.execute("UPDATE countries_raw SET bdoc = jsonb(doc)")
print(conn.execute("SELECT typeof(doc), typeof(bdoc) FROM countries_raw LIMIT 1").fetchone())
same = conn.execute("""
    SELECT lang.value AS language, COUNT(*) AS countries
    FROM countries_raw AS c JOIN json_each(c.bdoc, '$.languages') AS lang
    GROUP BY lang.value ORDER BY countries DESC, language LIMIT 10
""").fetchall()
assert same == conn.execute(top_languages).fetchall()

print("# Level 3, Q3: export to CSV and JSON")
cur = conn.execute(top_languages)
rows = cur.fetchall()
header = [c[0] for c in cur.description]
csv_path = WORK / "d20_top_languages.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)
print(csv_path.read_text(encoding="utf-8").splitlines()[:3])
json_path = WORK / "d20_top_languages.json"
json_path.write_text(json.dumps([dict(zip(header, r)) for r in rows], indent=2), encoding="utf-8")
print(json.loads(json_path.read_text(encoding="utf-8"))[0])
# the same JSON built inside SQL
print(conn.execute("SELECT json_group_array(json_object('language', language, 'countries', countries)) FROM (SELECT * FROM (" + top_languages + ") LIMIT 3)").fetchone()[0])
