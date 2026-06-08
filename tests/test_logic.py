"""Logic tests: goals (Mifflin-St Jeor), summaries, nutrition scaling. Offline.

Run: python tests/test_logic.py
"""
import os
import sys

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "fitness-tracker", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import charts  # noqa: E402
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

# ---- energy balance ----
energy = [
    storage.make_energy("2026-06-01", activity_kcal=600, basal_kcal=1800),    # total 2400
    storage.make_energy("2026-06-04", total_out_kcal=2500, basal_kcal=1800),  # activity 700
]
check("energy total derived", energy[0]["total_out_kcal"], 2400.0)
check("energy activity derived", energy[1]["activity_kcal"], 700.0)
check("energy basal derived (3200-1200)",
      storage.make_energy("2026-06-05", activity_kcal=1200, total_out_kcal=3200)["basal_kcal"], 2000.0)

de = summarize.daily(food, workout, bw, "2026-06-01", G, energy=energy, basal_default=1800)
check("daily energy total_out", de["energy"]["total_out_kcal"], 2400.0)
check("daily net (2000-2400)", de["energy"]["net_kcal"], -400.0)
check("daily balance deficit", de["energy"]["balance"], "deficit")

# basal fallback when the record was logged without basal
e2 = [storage.make_energy("2026-06-02", activity_kcal=500)]
d2 = summarize.daily(food, workout, bw, "2026-06-02", G, energy=e2, basal_default=1800)
check("daily basal fallback out (1800+500)", d2["energy"]["total_out_kcal"], 2300.0)
check("daily net fallback (2050-2300)", d2["energy"]["net_kcal"], -250.0)

pe = summarize.period(food, workout, bw, "2026-06-01", "2026-06-04", G, energy=energy, basal_default=1800)
check("period energy days", pe["energy"]["days"], 2)
check("period net_days", pe["energy"]["net_days"], 2)
check("period cumulative_net", pe["energy"]["cumulative_net"], -900.0)
check("period avg_net", pe["energy"]["avg_net_per_day"], -450.0)
check("period expected_fat_change", pe["energy"]["expected_fat_change_kg"], round(-900 / 7700, 2))

# ---- body composition (optional fields) ----
bw2 = [
    storage.make_bodyweight("2026-06-01", 85.0, muscle_kg=40.0, fat_kg=20.0),
    storage.make_bodyweight("2026-06-04", 84.0, muscle_kg=40.5, fat_kg=19.0),
]
pc = summarize.period(food, workout, bw2, "2026-06-01", "2026-06-04", G)
check("bodycomp muscle delta", pc["bodycomp"]["muscle_kg"]["delta"], 0.5)
check("bodycomp fat delta", pc["bodycomp"]["fat_kg"]["delta"], -1.0)
check("bodycomp weight end", pc["bodycomp"]["weight_kg"]["end"], 84.0)

# sparse: a measurement with only one optional metric still records that metric
bw3 = [storage.make_bodyweight("2026-06-02", fat_pct=22.5)]
d3 = summarize.daily(food, workout, bw3, "2026-06-02", G)
check("daily bodycomp fat_pct", d3["bodycomp"]["fat_pct"], 22.5)
check("daily weight none when not logged", d3["bodyweight"], None)

# ---- charts: sparkline + SVG + series helpers ----
sp = charts.sparkline([1, 2, 3, 4, 5])
check("sparkline len", len(sp), 5)
check("sparkline rises", sp[0] < sp[-1], True)
check("sparkline empty", charts.sparkline([]), "")
check("sparkline gap is space", charts.sparkline([1, None, 5])[1], " ")
svg = charts.line_chart_svg([{"label": "вес", "values": [85.0, 84.5, 84.0]}],
                            ["06-01", "06-02", "06-03"], title="Вес")
check("svg starts", svg.startswith("<svg"), True)
check("svg has polyline", "polyline" in svg, True)
check("svg closed", svg.strip().endswith("</svg>"), True)
check("svg empty-data safe", charts.line_chart_svg([{"label": "x", "values": [None]}], ["a"]).startswith("<svg"), True)
svg_pct = charts.line_chart_svg([{"label": "fat", "values": [0.0, -3.0, -7.0]}],
                                ["d1", "d2", "d3"], value_fmt="{:+.1f}%", baseline=0.0)
check("svg baseline dashed", "stroke-dasharray" in svg_pct, True)
bar = charts.bar_chart_svg([-400.0, -300.0, 200.0, None, -100.0], ["a", "b", "c", "d", "e"], title="net")
check("bar starts", bar.startswith("<svg"), True)
check("bar has bars", bar.count("<rect") >= 4, True)
check("bar closed", bar.strip().endswith("</svg>"), True)
bvg = charts.bars_vs_goal_svg([2000.0, 2500.0, 1800.0], ["a", "b", "c"], 2100, title="kcal")
check("bars_vs_goal starts", bvg.startswith("<svg"), True)
check("bars_vs_goal has goal line", "stroke-dasharray" in bvg, True)
check("bars_vs_goal bar count", bvg.count("<rect") >= 4, True)
hm = charts.heatmap_calendar_svg([("2026-06-01", "on"), ("2026-06-02", "off"), ("2026-06-03", "none")], title="adh")
check("heatmap starts", hm.startswith("<svg"), True)
check("heatmap closed", hm.strip().endswith("</svg>"), True)
area = charts.line_chart_svg([{"label": "cum", "values": [-100.0, -400.0, -900.0]}],
                             ["a", "b", "c"], baseline=0.0, fill=True)
check("area has polygon", "<polygon" in area, True)
mk = summarize.macro_split(food)
check("macro_split protein kcal", mk["kcal"]["protein"], round(525 * 4, 1))
check("macro_split carbs kcal", mk["kcal"]["carbs"], round(705 * 4, 1))
dn = charts.donut_svg([("P", 2100, "#3b82f6"), ("F", 1890, "#eab308"), ("C", 2820, "#16a34a")],
                      title="m", center="6810")
check("donut starts", dn.startswith("<svg"), True)
check("donut has slice", "<path" in dn, True)
check("donut closed", dn.strip().endswith("</svg>"), True)

ns = summarize.net_series(food, energy, 1800)
check("net_series len", len(ns), 2)
check("net_series first", ns[0], ("2026-06-01", -400.0))
check("net_series second", ns[1], ("2026-06-04", -500.0))
check("metric_series muscle", summarize.metric_series(bw2, "muscle_kg"),
      [("2026-06-01", 40.0), ("2026-06-04", 40.5)])

# ---- report-series helpers for the new charts ----
dk = summarize.daily_kcal_series(food)
check("daily_kcal len", len(dk), 4)
check("daily_kcal first", dk[0], ("2026-06-01", 2000.0))
cum = summarize.cumulative_net_series(food, energy, 1800)
check("cumnet len", len(cum), 2)
check("cumnet running -400-500", cum[1], ("2026-06-04", -900.0))
adh = summarize.adherence_calendar(food, G, "2026-06-01", "2026-06-04")
check("adherence days", len(adh), 4)
check("adherence on day1", adh[0], ("2026-06-01", "on"))
check("adherence off day3", adh[2], ("2026-06-03", "off"))
prs = summarize.pr_series(workout, "жим лёжа", "weight")
check("pr series", prs, [("2026-06-01", 80.0), ("2026-06-04", 85.0)])

if fails:
    print("FAILED:")
    for x in fails:
        print("  -", x)
    sys.exit(1)
print("OK: all logic checks passed")
