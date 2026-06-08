"""Aggregate logged records into daily / period summaries.

Returns structured data only — the assistant formats it for the user (see
references/summaries.md). Pure stdlib, no network. Records are plain dicts in the
shapes defined in references/data-model.md.
"""
from __future__ import annotations
import datetime as _dt

_MACROS = ("kcal", "protein_g", "fat_g", "carbs_g")
_BODYCOMP = ("weight_kg", "muscle_kg", "fat_kg", "fat_pct", "water_kg")
_KCAL_PER_KG_FAT = 7700  # rough energy density of body fat, for deficit -> fat-loss estimates


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


def _metric_trend(records, field):
    """start/end/delta for one body-composition metric across the records that
    actually carry it (None values are skipped). Returns None if no data."""
    pts = [(r["date"], r[field]) for r in sorted(records, key=lambda r: r.get("date", ""))
           if r.get(field) is not None]
    if not pts:
        return None
    return {
        "start": pts[0][1], "start_date": pts[0][0],
        "end": pts[-1][1], "end_date": pts[-1][0],
        "delta": round(pts[-1][1] - pts[0][1], 2),
        "points": len(pts),
    }


def _resolve_total_out(rec, basal_default):
    """Total daily burn from an energy record: trust an explicit total, else fill
    basal from the default (config / BMR) and use total = basal + activity."""
    t = rec.get("total_out_kcal")
    if t is not None:
        return t
    b = rec.get("basal_kcal")
    b = b if b is not None else basal_default
    a = rec.get("activity_kcal")
    if b is not None and a is not None:
        return round(b + a, 2)
    return None


def _energy_day(rec, intake_kcal, basal_default):
    """One day's energy balance: intake (food) vs out (basal + activity)."""
    if not rec:
        return None
    b = rec.get("basal_kcal")
    out = {
        "intake_kcal": round(intake_kcal, 1),
        "basal_kcal": b if b is not None else basal_default,
        "activity_kcal": rec.get("activity_kcal"),
        "total_out_kcal": _resolve_total_out(rec, basal_default),
    }
    t = out["total_out_kcal"]
    if t is not None:
        net = round(intake_kcal - t, 1)
        out["net_kcal"] = net  # < 0 = deficit, > 0 = surplus
        out["balance"] = "deficit" if net < 0 else ("surplus" if net > 0 else "even")
    return out


def _energy_period(energy, per_day_kcal, basal_default):
    """Period energy aggregate: avg burn, cumulative net and the fat change it
    predicts (cumulative_net / 7700). Net is only summed for days that have both
    an energy record and logged food, so the figure is honest about coverage."""
    erecs = sorted((energy or []), key=lambda r: r.get("date", ""))
    if not erecs:
        return None
    sum_out = sum_act = 0.0
    n_out = n_act = 0
    nets = []
    for r in erecs:
        to = _resolve_total_out(r, basal_default)
        if to is not None:
            sum_out += to
            n_out += 1
        if r.get("activity_kcal") is not None:
            sum_act += r["activity_kcal"]
            n_act += 1
        intake = per_day_kcal.get(r.get("date"))
        if to is not None and intake is not None:
            nets.append(round(intake - to, 1))
    res = {
        "days": len(erecs),
        "avg_total_out": round(sum_out / n_out, 1) if n_out else None,
        "avg_activity": round(sum_act / n_act, 1) if n_act else None,
    }
    if nets:
        cum = round(sum(nets), 1)
        res["net_days"] = len(nets)
        res["cumulative_net"] = cum
        res["avg_net_per_day"] = round(cum / len(nets), 1)
        res["expected_fat_change_kg"] = round(cum / _KCAL_PER_KG_FAT, 2)
    return res


def metric_series(records, field):
    """[(date, value), ...] for a body-measurement field, sorted, skipping gaps."""
    return [(r["date"], r[field]) for r in sorted(records, key=lambda r: r.get("date", ""))
            if r.get(field) is not None]


def net_series(food, energy, basal_default):
    """[(date, net_kcal), ...] for days with both logged food and a resolvable
    total burn. net = intake − total_out (`<0` = deficit). Feeds charts/sparklines."""
    per_day = {}
    for r in food:
        per_day[r["date"]] = per_day.get(r["date"], 0.0) + float(r.get("kcal") or 0)
    out = []
    for r in sorted((energy or []), key=lambda r: r.get("date", "")):
        to = _resolve_total_out(r, basal_default)
        intake = per_day.get(r.get("date"))
        if to is not None and intake is not None:
            out.append((r["date"], round(intake - to, 1)))
    return out


def daily_kcal_series(food):
    """[(date, kcal), ...] — total food calories per logged day, sorted."""
    per = {}
    for r in food:
        per[r["date"]] = per.get(r["date"], 0.0) + float(r.get("kcal") or 0)
    return [(d, round(per[d], 1)) for d in sorted(per)]


def adherence_calendar(food, goals, date_from, date_to):
    """Per calendar day in [from, to]: 'on' (kcal+protein in goal) / 'off'
    (logged but off target) / 'none' (nothing logged). Feeds the adherence heatmap."""
    tol = (goals or {}).get("tolerance_pct", 7)
    per = {d: _sum_macros([r for r in food if r["date"] == d])
           for d in {r["date"] for r in food}}
    out, a, b = [], _dt.date.fromisoformat(date_from), _dt.date.fromisoformat(date_to)
    d = a
    while d <= b:
        iso = d.isoformat()
        if iso not in per:
            st = "none"
        elif goals and goals.get("kcal") and _on_target(per[iso], goals, tol):
            st = "on"
        else:
            st = "off"
        out.append((iso, st))
        d += _dt.timedelta(days=1)
    return out


def cumulative_net_series(food, energy, basal_default):
    """[(date, running_total_net), ...] — accumulates net_series (`<0` = banked deficit)."""
    cum, out = 0.0, []
    for d, net in net_series(food, energy, basal_default):
        cum += net
        out.append((d, round(cum, 1)))
    return out


def pr_series(workout, exercise, kind="weight"):
    """[(date, best), ...] — best working weight (kind='weight') or volume
    (kind='volume') for one exercise per day it appears, sorted."""
    field = "weight_kg" if kind == "weight" else "volume"
    by_day = {}
    for r in workout:
        if r.get("exercise") != exercise:
            continue
        v = r.get(field)
        if v is None:
            continue
        by_day[r["date"]] = max(by_day.get(r["date"], v), v)
    return [(d, by_day[d]) for d in sorted(by_day)]


def macro_split(food):
    """Total macro grams + their calorie shares (P×4 / F×9 / C×4) for a donut."""
    t = _sum_macros(food)
    return {"protein_g": t["protein_g"], "fat_g": t["fat_g"], "carbs_g": t["carbs_g"],
            "kcal": {"protein": round(t["protein_g"] * 4, 1),
                     "fat": round(t["fat_g"] * 9, 1),
                     "carbs": round(t["carbs_g"] * 4, 1)}}


def daily(food, workout, bodyweight, date, goals=None, energy=None, basal_default=None):
    fday = [r for r in food if r.get("date") == date]
    wday = [r for r in workout if r.get("date") == date]
    bw = next((r for r in bodyweight if r.get("date") == date), None)
    eday = next((r for r in (energy or []) if r.get("date") == date), None)
    totals = _sum_macros(fday)
    out = {
        "date": date,
        "totals": totals,
        "meals": _by_meal(fday),
        "workouts": wday,
        "bodyweight": bw.get("weight_kg") if bw else None,
        "bodycomp": ({f: bw[f] for f in _BODYCOMP if bw.get(f) is not None} or None) if bw else None,
        "energy": _energy_day(eday, totals["kcal"], basal_default),
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


def period(food, workout, bodyweight, date_from, date_to, goals=None,
           energy=None, basal_default=None):
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

    bw = _metric_trend(bodyweight, "weight_kg")  # weight trend (back-compat block)
    bodycomp = {}
    for f in _BODYCOMP:
        t = _metric_trend(bodyweight, f)
        if t:
            bodycomp[f] = t

    out = {
        "from": date_from, "to": date_to,
        "days": n_days, "days_logged": n_logged,
        "totals": sum_all,
        "avg_per_logged_day": avg_logged,
        "avg_per_calendar_day": avg_calendar,
        "workouts": summarize_workouts(workout),
        "personal_records": personal_records(workout),
        "bodyweight": bw,
        "bodycomp": bodycomp or None,
        "energy": _energy_period(energy, {d: per_day[d]["kcal"] for d in per_day}, basal_default),
    }
    if goals and goals.get("kcal"):
        out["on_target_days"] = on_target_days
        out["adherence_pct"] = round(100 * on_target_days / n_logged) if n_logged else 0
        out["streaks"] = _streaks(per_day, date_from, date_to, goals, tol)
    return out
