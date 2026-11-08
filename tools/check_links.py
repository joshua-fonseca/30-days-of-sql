"""Check relative links and in-page TOC anchors in every lesson markdown file."""
import re, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent

def slug(h):
    h = re.sub(r"[`*]", "", h.strip().lower())
    h = re.sub(r"[^\w\- ]", "", h, flags=re.UNICODE)
    return h.replace(" ", "-")

bad = 0
files = sorted(p for p in root.glob("*/*.md") if re.match(r"\d\d", p.parent.name)) + [root / "readme.md"]
for f in files:
    text = f.read_text(encoding="utf-8")
    body = re.sub(r"```.*?```", "", text, flags=re.S)
    anchors = {slug(m.group(1)) for m in re.finditer(r"^#+\s+(.*)$", body, flags=re.M)}
    for m in re.finditer(r"\]\(([^)\s]+)\)", body):
        t = m.group(1)
        if t.startswith("http"):
            continue
        if t.startswith("#"):
            if t[1:] not in anchors:
                print(f"{f.relative_to(root)}: dead anchor {t}"); bad += 1
        else:
            path = t.split("#")[0]
            if not (f.parent / path).exists():
                print(f"{f.relative_to(root)}: dead link {t}"); bad += 1
print(f"{len(files)} files checked, {bad} problems")
sys.exit(1 if bad else 0)
