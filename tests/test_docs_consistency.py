"""Verify agent-written docs/assets match the code contracts.

Run: python tests/test_docs_consistency.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "fitness-tracker", "scripts")
sys.path.insert(0, SCRIPTS)

import backend_notion as bn  # noqa: E402
import backend_sheets as bs  # noqa: E402
import dates  # noqa: E402

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


# ---- notion-schema.json must match backend_notion contracts ----
with open(os.path.join(ROOT, "fitness-tracker", "assets", "notion-schema.json"), encoding="utf-8") as f:
    schema = json.load(f)
for kind, defs in bn.SCHEMAS.items():
    db = schema["databases"][kind]
    check(f"notion title {kind}", db["title"], bn.DB_TITLES[kind])
    props = db["properties"]
    check(f"notion prop names {kind}", set(props), {n for n, _, _ in defs})
    for name, ptype, _field in defs:
        check(f"notion type {kind}.{name}", props.get(name, {}).get("type"), ptype)
        if ptype == "select":
            check(f"notion opts {kind}.{name}", props[name].get("options"),
                  bn.SELECT_OPTIONS.get(name))

# ---- sheet-template.csv header must match COLUMNS['food'] ----
with open(os.path.join(ROOT, "fitness-tracker", "assets", "sheet-template.csv"), encoding="utf-8-sig") as f:
    header = f.readline().strip().split(",")
check("sheet csv header", header, bs.COLUMNS["food"])

# ---- date examples claimed in date-handling.md (today=2026-06-07 Sunday) ----
T = "2026-06-07"
for text, exp in [
    ("вчера", "2026-06-06"), ("позавчера", "2026-06-05"),
    ("5 июня", "2026-06-05"), ("05.06", "2026-06-05"),
    ("3 дня назад", "2026-06-04"), ("в понедельник", "2026-06-01"),
    ("неделю назад", "2026-05-31"), ("June 5", "2026-06-05"),
]:
    check(f"date {text}", dates.resolve(text, T), exp)

if fails:
    print("FAILED:")
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("OK: docs/assets consistent with code contracts")
