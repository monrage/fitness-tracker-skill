"""Aggregate logged records into daily / period summaries.

Returns structured data only — the assistant formats it for the user (see
references/summaries.md). Pure stdlib, no network. Records are plain dicts in the
shapes defined in references/data-model.md.
"""
from __future__ import annotations
import datetime as _dt

_MACROS = ("kcal", "protein_g", "fat_g", "carbs_g")


def _sum_macros(food_records):
    out = {k: 0.0 for k in _MACROS}
    for r in food_records:
        for k in _MACROS:
            out[k] += float(r.get(k) or 0)
    return {k: round(v, 1) for k, v in out.items()}


def _by_meal(food_records):
    meals = {}
    for r in food_records:
        m = r.get("meal", "snack")
        meals.setdefault(m, {k: 0.0 for k in _MACROS})
        for k in _MACROS:
            meals[m][k] += float(r.get(k) or 0)
    return {m: {k: round(v, 1) for k, v in d.items()} for m, d in meals.items()}


def _vs_goal(totals, goals):
    out = {}
    for k in _MACROS:
        target = goals.get(k)
        if not target:
            continue
        actual = totals.get(k, 0)
        out[k] = {
            "target": target,
            "actual": round(actual, 1),
            "pct": round(100 * actual / target) if target else None,
            "remaining": round(target - actual, 1),
        }
    return out


def _on_target(totals, goals, tol_pct):
    """A day counts as on-target when kcal is within ±tol and protein is not far short."""
    gk = goals.get("kcal")
    if not gk:
        return False
    lo, hi = gk * (1 - tol_pct / 100), gk * (1 + tol_pct / 100)
    if not (lo <= totals.get("kcal", 0) <= hi):
        return False
    gp = goals.get("protein_g")
    if gp and totals.get("protein_g", 0) < gp * (1 - tol_pct / 100):
        return False
    return True


def daily(food, workout, bodyweight, date, goals=None):
    fday = [r for r in food if r.get("date") == date]
    wday = [r for r in workout if r.get("date") == date]
    bw = next((r for r in bodyweight if r.get("date") == date), None)
    totals = _sum_macros(fday)
    out = {
        "date": date,
        "totals": totals,
        "meals": _by_meal(fday),
        "workouts": wday,
        "bodyweight": bw["weight_kg"] if bw else None,
        "entries": len(fday),
    }
    if goals:
        out["vs_goal"] = _vs_goal(totals, goals)
        out["on_target"] = _on_target(totals, goals, goals.get("tolerance_pct", 7))
    return out


def summarize_workouts(workout):
    by_type, by_exercise = {}, {}
    total_volume = total_duration = 0.0
    for r in workout:
        by_type[r.get("type", "strength")] = by_type.get(r.get("type", "strength"), 0) + 1
        total_volume += float(r.get("volume") or 0)
        total_duration += float(r.get("duration_min") or 0)
        by_exercise[r.get("exercise", "?")] = by_exercise.get(r.get("exercise", "?"), 0) + 1
    return {
        "entries": len(workout),
        "sessions": len({r.get("date") for r in workout}),
        "by_type": by_type,
        "by_exercise": by_exercise,
        "total_volume": round(total_volume, 1),
        "total_duration_min": round(total_duration, 1),
    }


def personal_records(workout):
    prs = {}
    for r in workout:
        ex = r.get("exercise", "?")
        w = r.get("weight_kg")
        v = r.get("volume")
        cur = prs.setdefault(ex, {"max_weight": None, "max_weight_date": None,
                                  "max_volume": None, "max_volume_date": None})
        if w is not None and (cur["max_weight"] is None or w > cur["max_weight"]):
            cur["max_weight"], cur["max_weight_date"] = w, r.get("date")
        if v is not None and (cur["max_volume"] is None or v > cur["max_volume"]):
            cur["max_volume"], cur["max_volume_date"] = v, r.get("date")
    return prs


def _streaks(per_day_totals, date_from, date_to, goals, tol_pct):
    """Longest and current (ending at date_to) consecutive on-target-day streaks."""
    a = _dt.date.fromisoformat(date_from)
    b = _dt.date.fromisoformat(date_to)
    longest = current = run = 0
    d = a
    while d <= b:
        iso = d.isoformat()
        t = per_day_totals.get(iso)
        if t and _on_target(t, goals, tol_pct):
            run += 1
            longest = max(longest, run)
        else:
            run = 0
        d += _dt.timedelta(days=1)
    current = run  # run as it stands at date_to
    return {"longest": longest, "current": current}


def period(food, workout, bodyweight, date_from, date_to, goals=None):
    from dates import days_in
    tol = (goals or {}).get("tolerance_pct", 7)
    logged_days = sorted({r["date"] for r in food})
    per_day = {d: _sum_macros([r for r in food if r["date"] == d]) for d in logged_days}
    n_logged = len(logged_days)
    n_days = days_in(date_from, date_to)
    sum_all = _sum_macros(food)
    avg_logged = {k: round(v / n_logged, 1) if n_logged else 0.0 for k, v in sum_all.items()}
    avg_calendar = {k: round(v / n_days, 1) if n_days else 0.0 for k, v in sum_all.items()}

    on_target_days = sum(1 for t in per_day.values() if goals and _on_target(t, goals, tol))

    bwl = sorted([r for r in bodyweight], key=lambda r: r["date"])
    bw = None
    if bwl:
        bw = {
            "start": bwl[0]["weight_kg"], "start_date": bwl[0]["date"],
            "end": bwl[-1]["weight_kg"], "end_date": bwl[-1]["date"],
            "delta": round(bwl[-1]["weight_kg"] - bwl[0]["weight_kg"], 1),
            "points": len(bwl),
        }

    out = {
        "from": date_from, "to": date_to,
        "days": n_days, "days_logged": n_logged,
        "totals": sum_all,
        "avg_per_logged_day": avg_logged,
        "avg_per_calendar_day": avg_calendar,
        "workouts": summarize_workouts(workout),
        "personal_records": personal_records(workout),
        "bodyweight": bw,
    }
    if goals and goals.get("kcal"):
        out["on_target_days"] = on_target_days
        out["adherence_pct"] = round(100 * on_target_days / n_logged) if n_logged else 0
        out["streaks"] = _streaks(per_day, date_from, date_to, goals, tol)
    return out
