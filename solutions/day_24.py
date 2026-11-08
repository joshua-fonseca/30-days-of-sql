# Day 24 reference solutions: Querying files directly
import csv
import shutil
import sqlite3
from datetime import datetime

import duckdb

from helpers import DATA, WORK, show

HN = f"'{DATA / 'hacker_news.csv'}'"
BIG_HN = f"'{DATA / 'HN_posts_year_to_Sep_26_2016.csv'}'"
EVENTS = f"'{DATA / 'big_events.csv'}'"
COUNTRIES = f"'{DATA / 'countries_data.json'}'"
F500 = f"'{DATA / 'F500.csv'}'"
WH = f"'{DATA / 'weight-height.csv'}'"

# ---------------------------------------------------------------- Level 1
print("# Level 1, Q1")
show(duckdb.sql(f"SELECT id, num_points, num_comments, author, created_at FROM {HN} LIMIT 5"))

print("# Level 1, Q2")
show(duckdb.sql(f"DESCRIBE SELECT * FROM {HN}"))

print("# Level 1, Q3")
show(duckdb.sql(f"SUMMARIZE SELECT num_points, num_comments FROM {HN}"))

print("# Level 1, Q4")
print(duckdb.sql(f"SELECT COUNT(*) AS posts, COUNT(*) FILTER (WHERE url IS NULL) AS without_url FROM {HN}").fetchall())

print("# Level 1, Q5")
show(duckdb.sql(f"SELECT author, COUNT(*) AS posts FROM {HN} GROUP BY author ORDER BY posts DESC, author LIMIT 3"))

print("# Level 1, Q6")
show(duckdb.sql(f"SELECT name, employees, revenues FROM read_csv({F500}, delim=';') LIMIT 3"))
show(duckdb.sql(f"DESCRIBE SELECT rank, name, employees, revenues FROM read_csv({F500}, delim=';')"))
# employees and revenues contain commas and dollar signs ("2,300,000", "$485,873"), so DuckDB can only call them VARCHAR.

print("# Level 1, Q7")
show(duckdb.sql(f"""
    SELECT name, CAST(replace(replace(revenues, '$', ''), ',', '') AS INTEGER) AS revenue_millions
    FROM read_csv({F500}, delim=';')
    ORDER BY revenue_millions DESC, name
    LIMIT 3
"""))

print("# Level 1, Q8")
show(duckdb.sql(f"""
    SELECT Gender, COUNT(*) AS n, round(AVG(Height), 2) AS avg_height, round(AVG(Weight), 2) AS avg_weight
    FROM {WH} GROUP BY Gender ORDER BY Gender
"""))

print("# Level 1, Q9")
show(duckdb.sql(f"DESCRIBE SELECT * FROM read_json({COUNTRIES})"))
show(duckdb.sql(f"SELECT name, population FROM {COUNTRIES} WHERE population > 100000000 ORDER BY population DESC"))

print("# Level 1, Q10")
print(duckdb.sql(f"SELECT COUNT(*) FROM {COUNTRIES} WHERE currency = 'Euro'").fetchall())

print("# Level 1, Q11")
show(duckdb.sql(f"DESCRIBE SELECT * FROM read_csv({HN}, all_varchar = true)"))

print("# Level 1, Q12")
try:
    duckdb.sql(f"SELECT * FROM read_csv({HN}, delim = '|')").fetchall()
except duckdb.Error as e:
    print(type(e).__name__, "-", str(e).splitlines()[0])

print("# Level 1, Q13")
try:
    duckdb.sql("SELECT * FROM 'data/nothere.csv'").fetchall()
except duckdb.Error as e:
    print(type(e).__name__, "-", str(e).splitlines()[0])

print("# Level 1, Q14")
n = duckdb.sql(f"SELECT COUNT(*) FROM glob('{DATA}/*.csv')").fetchall()[0][0]
print("csv files in data/:", n)  # 6 once big_events.csv exists

print("# Level 1, Q15")
dbfile = WORK / "day24_datasets.duckdb"
dbfile.unlink(missing_ok=True)
con = duckdb.connect(str(dbfile))
con.execute(f"CREATE TABLE hn AS SELECT * FROM {HN}")
con.execute(f"CREATE TEMP TABLE hn_python AS SELECT * FROM hn WHERE title LIKE '%Python%'")
print(con.execute("SELECT (SELECT COUNT(*) FROM hn), (SELECT COUNT(*) FROM hn_python)").fetchall())
con.close()
con = duckdb.connect(str(dbfile))
print(con.execute("SELECT table_name, temporary FROM duckdb_tables() ORDER BY table_name").fetchall())
con.execute(f"CREATE VIEW hn_view AS SELECT * FROM {HN}")  # re-reads the file on every query
print(con.execute("SELECT COUNT(*) FROM hn_view").fetchall())

print("# Level 1, Q16")
# table: a copy inside the database file, fast, but it does not follow the file. view: a saved query, always fresh, slower,
# needs the file to stay where it is. Querying the file directly: no setup at all, nothing is saved.

print("# Level 1, Q17")
out = WORK / "day24_top_authors.csv"
duckdb.sql(f"""
    COPY (SELECT author, COUNT(*) AS posts FROM {HN} GROUP BY author ORDER BY posts DESC, author LIMIT 10)
    TO '{out}' (HEADER, DELIMITER ',')
""")
print(out.read_text().splitlines()[:3])
out_json = WORK / "day24_top_authors.json"
duckdb.sql(f"COPY (SELECT * FROM '{out}') TO '{out_json}' (FORMAT json, ARRAY true)")
print(duckdb.sql(f"SELECT COUNT(*) FROM read_json('{out_json}')").fetchall())

# ---------------------------------------------------------------- Level 2
print("# Level 2, Q1")
show(duckdb.sql(f"DESCRIBE SELECT created_at FROM read_csv({HN}, dateformat = '%m/%d/%Y %H:%M')"))  # DATE: the time is lost!
show(duckdb.sql(f"SELECT created_at FROM read_csv({HN}, timestampformat = '%m/%d/%Y %H:%M') LIMIT 2"))
a = duckdb.sql(f"SELECT id, strptime(created_at, '%m/%d/%Y %H:%M') AS ts FROM {HN} ORDER BY id").fetchall()
b = duckdb.sql(f"SELECT id, created_at AS ts FROM read_csv({HN}, types = {{'created_at': 'TIMESTAMP'}}, timestampformat = '%m/%d/%Y %H:%M') ORDER BY id").fetchall()
print("strptime == read_csv types:", a == b)
show(duckdb.sql(f"""
    SELECT hour(strptime(created_at, '%m/%d/%Y %H:%M')) AS hour, COUNT(*) AS posts, round(AVG(num_points), 1) AS avg_points
    FROM {HN}
    GROUP BY hour
    ORDER BY avg_points DESC, hour
    LIMIT 3
"""))
# cross-check with plain Python
tot, cnt = {}, {}
with (DATA / "hacker_news.csv").open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        h = datetime.strptime(r["created_at"], "%m/%d/%Y %H:%M").hour
        tot[h] = tot.get(h, 0) + int(r["num_points"])
        cnt[h] = cnt.get(h, 0) + 1
best = max(tot, key=lambda h: (round(tot[h] / cnt[h], 1), -h))
print("python agrees on the best hour:", best)

print("# Level 2, Q2")
pq = WORK / "day24_hn_big.parquet"
duckdb.sql(f"COPY (SELECT * FROM read_csv({BIG_HN}, timestampformat = '%m/%d/%Y %H:%M')) TO '{pq}' (FORMAT parquet)")
csv_mb = (DATA / "HN_posts_year_to_Sep_26_2016.csv").stat().st_size / 1e6
pq_mb = pq.stat().st_size / 1e6
print(f"csv {csv_mb:.1f} MB, parquet {pq_mb:.1f} MB, parquet is smaller: {pq_mb < csv_mb}")
show(duckdb.sql(f"DESCRIBE SELECT * FROM '{pq}'"))
print(duckdb.sql(f"SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM '{pq}'").fetchall())

import time
q_csv = f"SELECT author, SUM(num_points) AS pts FROM read_csv({BIG_HN}) GROUP BY author ORDER BY pts DESC, author LIMIT 3"
q_pq = f"SELECT author, SUM(num_points) AS pts FROM '{pq}' GROUP BY author ORDER BY pts DESC, author LIMIT 3"
t0 = time.perf_counter(); r1 = duckdb.sql(q_csv).fetchall(); t_csv = time.perf_counter() - t0
t0 = time.perf_counter(); r2 = duckdb.sql(q_pq).fetchall(); t_pq = time.perf_counter() - t0
print("same answer:", r1 == r2, "  parquet faster:", t_pq < t_csv)
show(duckdb.sql(q_pq))

print("# Level 2, Q3")
pq_z = WORK / "day24_hn_big_zstd.parquet"
duckdb.sql(f"COPY (SELECT * FROM '{pq}') TO '{pq_z}' (FORMAT parquet, COMPRESSION zstd)")
print("zstd smaller than the default:", pq_z.stat().st_size < pq.stat().st_size)

print("# Level 2, Q4")
show(duckdb.sql(f"""
    SELECT len(languages) AS languages_spoken, COUNT(*) AS countries
    FROM read_json({COUNTRIES})
    GROUP BY languages_spoken
    ORDER BY languages_spoken
"""))
show(duckdb.sql(f"""
    SELECT name, languages FROM read_json({COUNTRIES}) WHERE len(languages) >= 6 ORDER BY len(languages) DESC, name
"""))

print("# Level 2, Q5")
rt = WORK / "day24_roundtrip"
rt.mkdir(exist_ok=True)
query = f"SELECT name, capital, population FROM {COUNTRIES} ORDER BY name"
for ext, opts in [("csv", "(HEADER)"), ("json", "(FORMAT json, ARRAY true)"), ("parquet", "(FORMAT parquet)")]:
    duckdb.sql(f"COPY ({query}) TO '{rt / ('countries.' + ext)}' {opts}")
print([duckdb.sql(f"SELECT COUNT(*), SUM(population) FROM '{rt / ('countries.' + e)}'").fetchall()[0] for e in ("csv", "json", "parquet")])

print("# Level 2, Q6 (optional, needs internet)")
try:
    show(duckdb.sql("SELECT * FROM 'https://duckdb.org/data/flights.csv' LIMIT 2"))
except duckdb.Error as e:
    print("skipped (offline?):", type(e).__name__)

# ---------------------------------------------------------------- Level 3
print("# Level 3, Q1")
parts = WORK / "day24_months"
shutil.rmtree(parts, ignore_errors=True)
duckdb.sql(f"""
    COPY (SELECT *, strftime(ts, '%Y-%m') AS month FROM {EVENTS})
    TO '{parts}' (FORMAT csv, PARTITION_BY (month))
""")
print(sorted(p.name for p in parts.iterdir())[:3], len(list(parts.iterdir())), "folders")
print(duckdb.sql(f"SELECT COUNT(*) AS files FROM glob('{parts}/*/*.csv')").fetchall())
show(duckdb.sql(f"""
    SELECT month,
           COUNT(*) AS events,
           COUNT(*) FILTER (WHERE event_type = 'purchase') AS purchases,
           SUM(CAST(amount AS DECIMAL(12, 2))) FILTER (WHERE event_type = 'purchase') AS purchase_total
    FROM read_csv('{parts}/*/*.csv', hive_partitioning = true)
    GROUP BY month
    ORDER BY month
"""))
print(duckdb.sql(f"SELECT COUNT(*) FROM '{parts}/*/*.csv'").fetchall())

print("# Level 3, Q2")
show(duckdb.sql(f"""
    SELECT strftime(created_at, '%Y-%m') AS month, COUNT(*) AS posts, round(AVG(num_points), 1) AS avg_points,
           MAX(num_points) AS best
    FROM '{pq}'
    GROUP BY month
    ORDER BY month
"""))
show(duckdb.sql(f"""
    SELECT author, COUNT(*) AS posts, SUM(num_points) AS points
    FROM '{pq}'
    GROUP BY author
    HAVING COUNT(*) >= 100
    ORDER BY points DESC, author
    LIMIT 5
"""))
