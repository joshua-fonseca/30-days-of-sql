"""Run every reference solution and fail loudly on any exception.

    uv run python tools/check_all.py

Rebuilds data/shop.db first, verifies its quirks, then runs solutions/day_*.py and solutions/review_*.py
(each as its own process, from the repo root) and prints a pass/fail summary.
"""

import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
py = sys.executable


def run(label, args, quiet=True):
    start = time.perf_counter()
    proc = subprocess.run([py, *args], cwd=root, capture_output=True, text=True)
    ok = proc.returncode == 0
    print(f"{'PASS' if ok else 'FAIL'}  {label}  ({time.perf_counter() - start:.1f}s)")
    if not ok:
        print(proc.stdout[-1500:], proc.stderr[-2500:], sep="\n")
    return ok


results = [
    run("build shop.db", ["tools/build_shop_db.py"]),
    run("verify shop.db quirks", ["tools/verify_shop.py"]),
]
for path in sorted((root / "solutions").glob("day_*.py")) + sorted((root / "solutions").glob("review_*.py")):
    results.append(run(f"solutions/{path.name}", [str(path.relative_to(root))]))

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
