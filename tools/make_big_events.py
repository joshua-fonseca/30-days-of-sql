"""Generate data/big_events.csv: 1,000,000 seeded rows for the indexing (Day 21) and DuckDB-vs-SQLite (Day 23) lessons.

    uv run python tools/make_big_events.py

Columns: event_id, user_id, event_type, ts (ISO 'YYYY-MM-DD HH:MM:SS', all of 2025), amount (empty unless a purchase).
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

ROWS = 1_000_000
USERS = 50_000
TYPES = ["view", "click", "add_to_cart", "purchase", "refund"]
WEIGHTS = [55, 25, 12, 7, 1]

random.seed(30)
out = Path(__file__).resolve().parent.parent / "data" / "big_events.csv"
start = datetime(2025, 1, 1)
seconds_in_year = 365 * 24 * 3600

with out.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["event_id", "user_id", "event_type", "ts", "amount"])
    types = random.choices(TYPES, WEIGHTS, k=ROWS)
    offsets = sorted(random.randrange(seconds_in_year) for _ in range(ROWS))  # ids follow time order
    for i in range(ROWS):
        t = types[i]
        amount = ""
        if t == "purchase":
            amount = f"{random.randint(5, 400) + random.choice([0, 0.49, 0.99]):.2f}"
        elif t == "refund":
            amount = f"-{random.randint(5, 200)}.00"
        w.writerow([i + 1, random.randint(1, USERS), t, (start + timedelta(seconds=offsets[i])).strftime("%Y-%m-%d %H:%M:%S"), amount])

print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
