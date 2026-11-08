"""Build data/shop.db from data/shop.sql (deletes any existing shop.db first).

    uv run python tools/build_shop_db.py
"""

import sqlite3
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sql_file = root / "data" / "shop.sql"
db_file = root / "data" / "shop.db"

db_file.unlink(missing_ok=True)

conn = sqlite3.connect(db_file)
conn.executescript(sql_file.read_text())
conn.close()

check = sqlite3.connect(db_file)
for (table,) in check.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"):
    count = check.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # table names come from sqlite_master
    print(f"{table:20} {count:>5} rows")
check.close()
