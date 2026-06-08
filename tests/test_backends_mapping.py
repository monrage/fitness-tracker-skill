"""Offline tests for backend mapping logic (no network / no credentials).

Notion create-format vs read-format are intentionally asymmetric, so build and
parse are tested with their own correct fixtures. Sheets row<->record is
symmetric and round-tripped. HTTP plumbing requires live user credentials and is
verified separately on a user's real Notion/Sheets account.

Run: python tests/test_backends_mapping.py
"""
import os
import sys

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "fitness-tracker", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import storage  # noqa: E402
import backend_notion as bn  # noqa: E402
import backend_sheets as bs  # noqa: E402

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


rec = storage.make_food("2026-06-07", "куриная грудка", 330, 62, 7.2, 0,
                        meal="lunch", qty_g=200, source="claude", notes="")

# ---- Notion build (create format) ----
props = bn.build_props("food", rec)
check("notion title", props["Item"], {"title": [{"text": {"content": "куриная грудка"}}]})
check("notion number", props["Calories"], {"number": 330.0})
check("notion select", props["Meal"], {"select": {"name": "lunch"}})
check("notion date", props["Date"], {"date": {"start": "2026-06-07"}})
check("notion empty rich_text", props["Notes"], {"rich_text": []})
check("notion None number", bn.build_props("workout",
      storage.make_workout("2026-06-07", "бег", wtype="cardio", duration_min=30))["Sets"],
      {"number": None})

# ---- Notion parse (read format, includes plain_text) ----
page = {"id": "page-123", "properties": {
    "Item": {"title": [{"plain_text": "куриная грудка"}]},
    "Date": {"date": {"start": "2026-06-07"}},
    "Meal": {"select": {"name": "lunch"}},
    "Qty g": {"number": 200},
    "Calories": {"number": 330},
    "Protein g": {"number": 62},
    "Fat g": {"number": 7.2},
    "Carbs g": {"number": 0},
    "Source": {"select": {"name": "claude"}},
    "Notes": {"rich_text": []},
}}
parsed = bn.parse_page("food", page)
check("parse item", parsed["item"], "куриная грудка")
check("parse date", parsed["date"], "2026-06-07")
check("parse meal", parsed["meal"], "lunch")
check("parse kcal", parsed["kcal"], 330)
check("parse protein", parsed["protein_g"], 62)
check("parse id", parsed["id"], "page-123")
check("parse null select", bn.parse_page("food", {"id": "x", "properties": {
    "Source": {"select": None}}})["source"], None)

# schema_props sanity
sp = bn.schema_props("food")
check("schema title", sp["Item"], {"title": {}})
check("schema select options", sp["Meal"], {"select": {"options": [
    {"name": "breakfast"}, {"name": "lunch"}, {"name": "dinner"}, {"name": "snack"}]}})

# ---- Sheets round-trip (symmetric) ----
row = bs.row_from_record("food", rec)
check("sheets row len", len(row), len(bs.COLUMNS["food"]))
check("sheets row date", row[0], "2026-06-07")
back = bs.record_from_row("food", bs.COLUMNS["food"], row, 2)
check("sheets rt item", back["item"], "куриная грудка")
check("sheets rt kcal float", back["kcal"], 330.0)
check("sheets rt carbs zero", back["carbs_g"], 0.0)
check("sheets rt meal", back["meal"], "lunch")
check("sheets id synth", back["id"], "f2")

# workout round-trip with None cells
w = storage.make_workout("2026-06-07", "бег", wtype="cardio", duration_min=30)
wrow = bs.row_from_record("workout", w)
wback = bs.record_from_row("workout", bs.COLUMNS["workout"], wrow, 2)
check("sheets workout type", wback["type"], "cardio")
check("sheets workout duration", wback["duration_min"], 30.0)
check("sheets workout empty sets->None", wback["sets"], None)

# ---- energy + body-composition mapping ----
en = storage.make_energy("2026-06-08", activity_kcal=1200, basal_kcal=2000, total_out_kcal=3200)
ep = bn.build_props("energy", en)
check("notion energy activity", ep["Activity kcal"], {"number": 1200.0})
check("notion energy total", ep["Total out kcal"], {"number": 3200.0})
check("notion energy prop names", set(ep), {n for n, _, _ in bn.SCHEMAS["energy"]})
erow = bs.row_from_record("energy", en)
check("sheets energy row len", len(erow), len(bs.COLUMNS["energy"]))
eback = bs.record_from_row("energy", bs.COLUMNS["energy"], erow, 2)
check("sheets energy rt activity", eback["activity_kcal"], 1200.0)
check("sheets energy rt total", eback["total_out_kcal"], 3200.0)

bwc = storage.make_bodyweight("2026-06-08", 100.8, muscle_kg=40.1, fat_kg=26.9, fat_pct=26.7, water_kg=54.1)
bp = bn.build_props("bodyweight", bwc)
check("notion bw muscle", bp["Muscle kg"], {"number": 40.1})
check("notion bw fat_pct", bp["Fat %"], {"number": 26.7})
check("notion bw prop names", set(bp), {n for n, _, _ in bn.SCHEMAS["bodyweight"]})
bwrow = bs.row_from_record("bodyweight", bwc)
bwback = bs.record_from_row("bodyweight", bs.COLUMNS["bodyweight"], bwrow, 2)
check("sheets bw muscle rt", bwback["muscle_kg"], 40.1)
check("sheets bw water rt", bwback["water_kg"], 54.1)

# ---- local meta KV round-trip ----
import tempfile  # noqa: E402

_tmp = tempfile.mkdtemp()
os.environ["FITTRACK_CONFIG"] = os.path.join(_tmp, "fitness-config.json")
_be = storage.get_backend({"backend": {"type": "local", "local": {"path": "data.json"}}})
_be.ensure_schema()
check("meta empty initially", _be.read_meta(), {})
_be.write_meta({"last_weekly": "2026-06-07"})
_be.write_meta({"last_monthly": "2026-05"})
check("meta persisted weekly", _be.read_meta().get("last_weekly"), "2026-06-07")
check("meta merge keeps both", sorted(_be.read_meta()), ["last_monthly", "last_weekly"])

if fails:
    print("FAILED:")
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("OK: all backend-mapping checks passed")
