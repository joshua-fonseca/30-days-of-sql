# Day 28 reference solution: the Library Manager CLI lives in solutions/day_28/.
# This wrapper plays the sample sessions from the lesson (real output) and runs the project's pytest suite.
import subprocess
import sys
from pathlib import Path

from helpers import WORK

here = Path(__file__).resolve().parent / "day_28"
cli = here / "library_cli.py"
db = WORK / "d28_library.db"
for suffix in ("", "-wal", "-shm"):
    Path(str(db) + suffix).unlink(missing_ok=True)

SESSION = [
    ["init", "--demo"],
    ["--today", "2025-03-14", "search", "--author", "austen"],
    ["--today", "2025-03-14", "add-book", "Hyperion", "Dan Simmons", "--year", "1989", "--genre", "Sci-Fi", "--price", "12.99"],
    ["--today", "2025-03-01", "lend", "1", "1"],
    ["--today", "2025-03-01", "lend", "3", "1"],
    ["--today", "2025-03-02", "lend", "1", "2"],
    ["--today", "2025-03-03", "lend", "6", "1"],
    ["--today", "2025-03-04", "lend", "7", "1"],
    ["--today", "2025-03-04", "lend", "99", "1"],
    ["--today", "2025-03-14", "loans"],
    ["--today", "2025-03-16", "overdue"],
    ["--today", "2025-03-16", "return", "1"],
    ["--today", "2025-03-16", "return", "1"],
    ["--today", "2025-03-16", "stats"],
    ["--today", "2025-03-16", "add-member", "Imposter", "alice@example.com"],
]
for args in SESSION:
    full = [sys.executable, str(cli), "--db", str(db), *args]
    proc = subprocess.run(full, capture_output=True, text=True, cwd=WORK)
    shown = " ".join(a for a in args)
    print(f"$ python library_cli.py --db library.db {shown}   [exit {proc.returncode}]")
    print(proc.stdout.rstrip().replace(str(db), "library.db") or "", end="\n" if proc.stdout else "")
    if proc.stderr:
        print(proc.stderr.rstrip().replace(str(db), "library.db"))

proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(here)],
                      capture_output=True, text=True, cwd=here)
print(proc.stdout.strip().splitlines()[-1])
if proc.returncode != 0:
    print(proc.stdout[-3000:])
    raise SystemExit("pytest failed")
