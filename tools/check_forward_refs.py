"""Flag SQL keywords used (inside code blocks or exercises) in a lesson before the day that teaches them."""
import re
from pathlib import Path
root = Path(__file__).resolve().parent.parent
# keyword regex -> first day that teaches it
RULES = {
 r"\bJOIN\b": 11, r"\bWITH\s+\w+\s+AS\b|\bWITH RECURSIVE\b": 14, r"\bUNION\b|\bINTERSECT\b|\bEXCEPT\b": 15,
 r"\bOVER\s*\(": 17, r"\bCREATE (UNIQUE )?INDEX\b|\bEXPLAIN QUERY PLAN\b": 21,
 r"\bCREATE (TEMP |TEMPORARY )?(VIEW|TRIGGER)\b": 22, r"\bjulianday\(|\bstrftime\(": 16,
 r"\bduckdb\b": 23, r"\bQUALIFY\b|\bGROUP BY ALL\b|\bPIVOT\b": 25,
 r"\bIN \(\s*SELECT\b|\bEXISTS\s*\(\s*SELECT\b|\(\s*SELECT [^)]*\bFROM\b": 13,
 r"\bGROUP BY\b": 7, r"\bHAVING\b": 7, r"\bCASE\b": 6, r"\bCOALESCE\(": 6,
 r"\bUPDATE\b|\bDELETE FROM\b": 8, r"\bON CONFLICT\b|\bPRAGMA foreign_keys\b": 9,
}
days = {}
for p in sorted(root.glob("*/*.md")):
    m = re.match(r"(\d\d)(R?)_", p.parent.name)
    if m: days[p] = int(m.group(1)) + (0.5 if m.group(2) else 0)
for p, d in days.items():
    text = p.read_text(encoding="utf-8")
    for pat, first in RULES.items():
        if d >= first: continue
        for ln, line in enumerate(text.splitlines(), 1):
            if re.search(pat, line, flags=re.I if pat.islower() else 0) and not line.lstrip().startswith(("|", ">", "- [")):
                print(f"{p.parent.name}:{ln} (Day {first} topic) {line.strip()[:110]}")
