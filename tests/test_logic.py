"""Logic tests: goals (Mifflin-St Jeor), summaries, nutrition scaling. Offline.

Run: python tests/test_logic.py
"""
import os
import sys

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "fitness-tracker", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import goals  # noqa: E402
import nutrition  # noqa: E402
import storage  # noqa: E402
import summarize  # noqa: E402

fails = []


def check(name, got, want):
    if got != want:
        fails.append(f"{name}: got {got!r}, want {want!r}")


def approx(name, got, want, eps=0.05):
    if abs(got - want) > eps:
        fails.append(f"{name}: got {got!r}, want ~{want!r}")


# ---- goals ----
t = goals.compute_targets("male", 30, 182, 85, activity="moderate", goal="cut")
expected_bmr = round(10 * 85 + 6.25 * 182 - 5 * 30 + 5)
check("bmr", t["bmr"], expected_bmr)
check("protein 1.8/kg", t["protein_g"], round(1.8 * 85))
assert_target = round(round(10 * 85 + 6.25 * 182 - 5 * 30 + 5) * 1.55 * 0.82) if False else None
check("carbs non-negative", t["carbs_g"] >= 0, True)
check("kcal < tdee for cut", t["kcal"] < t["tdee"], True)
f = goals.compute_targets("female", 28, 165, 60, activity="light", goal="maintain")
check("female bmr", f["bmr"], round(10 * 60 + 6.25 * 165 - 5 * 28 - 161))

# ---- nutrition.scale ----
per = {"kcal": 165, "protein_g": 31, "fat_g": 3.6, "carbs_g": 0}
s = nutrition.scale(per, 200)
check("scale kcal", s["kcal"], 330.0)
check("scale protein", s["protein_g"], 62.0)
approx("scale fat", s["fat_g"], 7.2)

# ---- summaries ----
G = {"kcal": 2000, "protein_g": 150, "fat_g": 60, "carbs_g": 200, "tolerance_pct": 10}
food = [
    storage.make_food("2026-06-01", "meal", 2000, 150, 60, 200, meal="lunch"),
    storage.make_food("2026-06-02", "meal", 2050, 145, 60, 205, meal="lunch"),
    storage.make_food("2026-06-03", "meal", 1000, 80, 30, 100, meal="lunch"),
    storage.make_food("2026-06-04", "meal", 2000, 150, 60, 200, meal="lunch"),
]
workout = [
    storage.make_workout("2026-06-01", "жим лёжа", sets=5, reps=5, weight_kg=80),
    storage.make_workout("2026-06-01", "присед", sets=5, reps=5, weight_kg=100),
    storage.make_workout("2026-06-04", "жим лёжа", sets=5, reps=5, weight_kg=85),
]
bw = [
    storage.make_bodyweight("2026-06-01", 85.0),
    storage.make_bodyweight("2026-06-04", 84.0),
]

d1 = summarize.daily(food, workout, bw, "2026-06-01", G)
check("daily kcal", d1["totals"]["kcal"], 2000.0)
check("daily on_target", d1["on_target"], True)
check("daily vs_goal pct", d1["vs_goal"]["kcal"]["pct"], 100)
check("daily workouts", len(d1["workouts"]), 2)
check("daily bodyweight", d1["bodyweight"], 85.0)

p = summarize.period(food, workout, bw, "2026-06-01", "2026-06-04", G)
check("period days", p["days"], 4)
check("period days_logged", p["days_logged"], 4)
check("period on_target_days", p["on_target_days"], 3)
check("period adherence", p["adherence_pct"], 75)
check("period streak longest", p["streaks"]["longest"], 2)
check("period streak current", p["streaks"]["current"], 1)
check("period sessions", p["workouts"]["sessions"], 2)
check("period entries", p["workouts"]["entries"], 3)
check("period volume", p["workouts"]["total_volume"], 6625.0)
check("PR жим weight", p["personal_records"]["жим лёжа"]["max_weight"], 85.0)
check("PR жим volume", p["personal_records"]["жим лёжа"]["max_volume"], 2125.0)
check("PR присед weight", p["personal_records"]["присед"]["max_weight"], 100.0)
check("bw delta", p["bodyweight"]["delta"], -1.0)

if fails:
    print("FAILED:")
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("OK: all logic checks passed")
