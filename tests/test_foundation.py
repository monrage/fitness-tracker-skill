"""Foundation smoke tests: dates, records, local backend, config.

Run: python tests/test_foundation.py   (stdlib only, no pytest needed)
"""
import datetime as dt
import os
import sys
import tempfile

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "fitness-tracker", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import config as cfg  # noqa: E402
import dates  # noqa: E402
import storage  # noqa: E402
from backend_local import LocalBackend  # noqa: E402

T = dt.date(2026, 6, 7)  # reference "today" (a Sunday)
fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


# ---- dates.resolve ----
check("today", dates.resolve("сегодня", T), "2026-06-07")
check("empty->today", dates.resolve("", T), "2026-06-07")
check("yesterday", dates.resolve("вчера", T), "2026-06-06")
check("pozavchera", dates.resolve("позавчера", T), "2026-06-05")  # must beat 'вчера' substring
check("3 days ago ru", dates.resolve("3 дня назад", T), "2026-06-04")
check("week ago ru", dates.resolve("неделю назад", T), "2026-05-31")
check("5 ijunya", dates.resolve("ел 5 июня творог", T), "2026-06-05")
check("dd.mm", dates.resolve("05.06", T), "2026-06-05")
check("iso", dates.resolve("2026-06-01", T), "2026-06-01")
check("june 5 en", dates.resolve("June 5", T), "2026-06-05")
check("days ago en", dates.resolve("2 days ago", T), "2026-06-05")

# weekday -> most recent past (computed, not hardcoded)
for name, wd in (("в понедельник", 0), ("в пятницу", 4), ("в воскресенье", 6)):
    expected = (T - dt.timedelta(days=(T.weekday() - wd) % 7)).isoformat()
    check(f"weekday {name}", dates.resolve(name, T), expected)

# period bounds (T is Sunday -> Mon-week is 2026-06-01..06-07)
check("week_bounds mon", dates.week_bounds(T, "mon"), ("2026-06-01", "2026-06-07"))
check("month_bounds", dates.month_bounds(T), ("2026-06-01", "2026-06-30"))
check("year_bounds", dates.year_bounds(T), ("2026-01-01", "2026-12-31"))
check("days_in", dates.days_in("2026-06-01", "2026-06-07"), 7)

# ---- record builders ----
f = storage.make_food("2026-06-07", "куриная грудка", 330, 62, 7.2, 0,
                      meal="lunch", qty_g=200, source="claude")
check("food kcal", f["kcal"], 330.0)
check("food meal", f["meal"], "lunch")
check("food source", f["source"], "claude")
w = storage.make_workout("2026-06-07", "жим лёжа", wtype="strength",
                         sets=5, reps=5, weight_kg=80)
check("workout volume", w["volume"], 2000.0)
check("workout type", w["type"], "strength")
bw = storage.make_bodyweight("2026-06-07", 84.5)
check("bodyweight", bw["weight_kg"], 84.5)

# invalid date must raise
try:
    storage.make_food("07.06.2026", "x", 1, 1, 1, 1)
    fails.append("invalid date: expected ValueError")
except ValueError:
    pass

# ---- local backend ----
with tempfile.TemporaryDirectory() as d:
    data_path = os.path.join(d, "data.json")
    be = LocalBackend({"backend": {"type": "local", "local": {"path": data_path}}})
    be.ensure_schema()
    r1 = be.append("food", f)
    r2 = be.append("food", storage.make_food("2026-06-05", "рис", 130, 2.7, 0.3, 28))
    check("append id", r1["id"], "f000001")
    check("append seq2", r2["id"], "f000002")
    rng = be.query_range("food", "2026-06-06", "2026-06-08")
    check("query_range filter", len(rng), 1)
    check("query_range item", rng[0]["item"], "куриная грудка")
    check("list_all sorted", [x["date"] for x in be.list_all("food")],
          ["2026-06-05", "2026-06-07"])

# ---- relative data path resolves next to config, not CWD ----
with tempfile.TemporaryDirectory() as d:
    saved = os.environ.get("FITTRACK_CONFIG")
    os.environ["FITTRACK_CONFIG"] = os.path.join(d, "fitness-config.json")
    try:
        be2 = LocalBackend({"backend": {"type": "local", "local": {"path": "fitness-data.json"}}})
        check("relative path co-located", os.path.dirname(be2.path), os.path.abspath(d))
    finally:
        if saved is None:
            os.environ.pop("FITTRACK_CONFIG", None)
        else:
            os.environ["FITTRACK_CONFIG"] = saved

# ---- config ----
with tempfile.TemporaryDirectory() as d:
    cpath = os.path.join(d, "cfg.json")
    check("load missing", cfg.load(cpath), None)
    c = cfg.load_or_default(cpath)
    check("default not onboarded", cfg.is_onboarded(c), False)
    c["onboarded"] = True
    c["goals"] = {"kcal": 2200, "protein_g": 165, "fat_g": 70, "carbs_g": 220}
    cfg.save(c, cpath)
    c2 = cfg.load(cpath)
    check("roundtrip lang", c2["lang"], "ru")
    check("roundtrip goal", c2["goals"]["kcal"], 2200)
    check("is_onboarded true", cfg.is_onboarded(c2), True)
    check("defaults merged", c2["units"]["energy"], "kcal")

if fails:
    print("FAILED:")
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("OK: all foundation checks passed")
