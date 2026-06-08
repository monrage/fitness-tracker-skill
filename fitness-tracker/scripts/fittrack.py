#!/usr/bin/env python3
"""fittrack — CLI entrypoint the assistant calls for deterministic operations.

Division of labour: the assistant handles natural language, macro estimation and
vision (reading nutrition-label photos); this CLI handles persistence, date math,
Open Food Facts lookups, goal math and aggregation. Every command prints ONE JSON
object to stdout so the assistant can parse the result reliably.

Examples (assistant-invoked):
  python fittrack.py status
  python fittrack.py resolve-date --text "позавчера" --today 2026-06-07
  python fittrack.py lookup --barcode 3017620422003 --grams 30
  python fittrack.py lookup --query "молоко простоквашино" --grams 250
  python fittrack.py log-food --date 2026-06-07 --item "куриная грудка" \
      --kcal 330 --protein 62 --fat 7.2 --carbs 0 --meal lunch --qty-g 200 --source claude
  python fittrack.py log-workout --date 2026-06-07 --exercise "жим лёжа" \
      --type strength --sets 5 --reps 5 --weight 80
  python fittrack.py log-weight --date 2026-06-07 --weight 100.8 --muscle 40.1 --fat 26.9 --water 54.1
  python fittrack.py log-energy --date 2026-06-07 --total 3200 --activity 1200
  python fittrack.py compute-goals --sex male --age 30 --height 182 --weight 85 \
      --activity moderate --goal cut
  python fittrack.py summary --period week --today 2026-06-07
  python fittrack.py config-set --patch '{"onboarded": true, "goals": {"kcal": 2200}}'

Config path: --config, else env FITTRACK_CONFIG, else ./fitness-config.json.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as cfg  # noqa: E402
import dates as D  # noqa: E402
import goals as G  # noqa: E402
import nutrition as N  # noqa: E402
import storage  # noqa: E402
import summarize as S  # noqa: E402


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _cfg(args):
    return cfg.load_or_default(getattr(args, "config", None))


def _running_day(c, date):
    be = storage.get_backend(c)
    return S.daily(be.query_range("food", date, date),
                   be.query_range("workout", date, date),
                   be.query_range("bodyweight", date, date),
                   date, c.get("goals") or None,
                   energy=be.query_range("energy", date, date),
                   basal_default=_resolve_basal(c)[0])


def _resolve_basal(c, override=None):
    """Resting daily burn (kcal) + its source. Priority: explicit override >
    config.energy.basal_kcal > Mifflin-St Jeor BMR from profile."""
    if override not in (None, ""):
        return round(float(override)), "override"
    en = c.get("energy") or {}
    if en.get("basal_kcal") not in (None, ""):
        return round(float(en["basal_kcal"])), "config"
    p = c.get("profile") or {}
    if all(p.get(k) not in (None, "") for k in ("sex", "age", "height_cm", "weight_kg")):
        return round(G.bmr_mifflin(p["sex"], p["age"], p["height_cm"], p["weight_kg"])), "profile_bmr"
    return None, "none"


def cmd_status(args):
    c = cfg.load(getattr(args, "config", None))
    if not c:
        _out({"onboarded": False, "config_found": False})
        return
    _out({
        "onboarded": cfg.is_onboarded(c),
        "config_found": True,
        "backend": (c.get("backend") or {}).get("type"),
        "lang": c.get("lang"),
        "timezone": c.get("timezone"),
        "week_start": c.get("week_start"),
        "goals": c.get("goals") or {},
        "nutrition": c.get("nutrition") or {},
    })


def cmd_resolve_date(args):
    _out({"input": args.text, "date": D.resolve(args.text, args.today)})


def cmd_lookup(args):
    c = _cfg(args)
    country = (c.get("nutrition") or {}).get("off_country", "world")
    if args.barcode:
        r = N.lookup_barcode(args.barcode, country=country)
        res = [r] if r else []
    elif args.query:
        res = N.search(args.query, country=country, limit=args.limit)
    else:
        _out({"error": "provide --barcode or --query"})
        return
    if args.grams:
        for r in res:
            r["scaled"] = N.scale(r["per100g"], args.grams)
            r["grams"] = args.grams
    _out({"results": res, "count": len(res)})


def cmd_log_food(args):
    c = _cfg(args)
    rec = storage.make_food(args.date, args.item, args.kcal, args.protein,
                            args.fat, args.carbs, meal=args.meal,
                            qty_g=args.qty_g, source=args.source, notes=args.notes or "")
    be = storage.get_backend(c)
    _out({"stored": be.append("food", rec), "day": _running_day(c, args.date)})


def cmd_log_workout(args):
    c = _cfg(args)
    rec = storage.make_workout(args.date, args.exercise, wtype=args.type,
                               sets=args.sets, reps=args.reps, weight_kg=args.weight,
                               duration_min=args.duration, distance_km=args.distance,
                               rpe=args.rpe, notes=args.notes or "")
    be = storage.get_backend(c)
    _out({"stored": be.append("workout", rec)})


def cmd_log_weight(args):
    c = _cfg(args)
    rec = storage.make_bodyweight(args.date, args.weight, muscle_kg=args.muscle,
                                  fat_kg=args.fat, fat_pct=args.fat_pct,
                                  water_kg=args.water, notes=args.notes or "")
    be = storage.get_backend(c)
    _out({"stored": be.append("bodyweight", rec)})


def cmd_log_energy(args):
    c = _cfg(args)
    if args.basal not in (None, ""):
        basal, basal_src = round(float(args.basal)), "override"
    elif args.total not in (None, "") and args.activity not in (None, ""):
        # both numbers came from the watch → basal is exactly total − activity;
        # don't inject the BMR estimate (it would contradict the given totals)
        basal, basal_src = None, "derived"
    else:
        basal, basal_src = _resolve_basal(c)  # config override or profile BMR
    rec = storage.make_energy(args.date, activity_kcal=args.activity,
                              basal_kcal=basal, total_out_kcal=args.total,
                              notes=args.notes or "")
    be = storage.get_backend(c)
    _out({"stored": be.append("energy", rec), "basal_source": basal_src,
          "day": _running_day(c, args.date)})


def cmd_compute_goals(args):
    _out(G.compute_targets(args.sex, args.age, args.height, args.weight,
                           activity=args.activity, goal=args.goal))


def cmd_summary(args):
    c = _cfg(args)
    be = storage.get_backend(c)
    goalsd = c.get("goals") or None
    ws = c.get("week_start", "mon")
    if args.period == "day":
        date = D.resolve(args.date or "", args.today)
        _out({"period": "day",
              "summary": S.daily(be.query_range("food", date, date),
                                 be.query_range("workout", date, date),
                                 be.query_range("bodyweight", date, date),
                                 date, goalsd,
                                 energy=be.query_range("energy", date, date),
                                 basal_default=_resolve_basal(c)[0])})
        return
    if args.period == "week":
        a, b = D.week_bounds(args.today, ws)
    elif args.period == "month":
        a, b = D.month_bounds(args.today)
    elif args.period == "year":
        a, b = D.year_bounds(args.today)
    else:
        a, b = args.date_from, args.date_to
        if not (a and b):
            _out({"error": "custom period needs --date-from and --date-to"})
            return
    _out({"period": args.period, "from": a, "to": b,
          "summary": S.period(be.query_range("food", a, b),
                              be.query_range("workout", a, b),
                              be.query_range("bodyweight", a, b),
                              a, b, goalsd,
                              energy=be.query_range("energy", a, b),
                              basal_default=_resolve_basal(c)[0])})


def cmd_config_set(args):
    c = cfg.load_or_default(getattr(args, "config", None))
    c = cfg.merge(c, json.loads(args.patch))
    path = cfg.save(c, getattr(args, "config", None))
    _out({"saved": path, "onboarded": cfg.is_onboarded(c),
          "backend": (c.get("backend") or {}).get("type")})


def cmd_config_show(args):
    c = cfg.load(getattr(args, "config", None))
    if not c:
        _out({"config_found": False})
        return
    r = json.loads(json.dumps(c))
    b = r.get("backend", {})
    if b.get("notion", {}).get("token"):
        b["notion"]["token"] = "***"
    oauth = b.get("sheets", {}).get("oauth", {})
    for k in ("client_secret", "refresh_token"):
        if oauth.get(k):
            oauth[k] = "***"
    nx = r.get("nutrition", {}).get("nutritionix", {})
    if nx.get("app_key"):
        nx["app_key"] = "***"
    _out(r)


def cmd_ensure_schema(args):
    _out({"result": storage.get_backend(_cfg(args)).ensure_schema()})


def build_parser():
    p = argparse.ArgumentParser(prog="fittrack")
    p.add_argument("--config", help="path to fitness-config.json")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("config-show").set_defaults(func=cmd_config_show)
    sub.add_parser("ensure-schema").set_defaults(func=cmd_ensure_schema)

    sp = sub.add_parser("resolve-date")
    sp.add_argument("--text", required=True)
    sp.add_argument("--today")
    sp.set_defaults(func=cmd_resolve_date)

    sp = sub.add_parser("lookup")
    sp.add_argument("--barcode")
    sp.add_argument("--query")
    sp.add_argument("--grams", type=float)
    sp.add_argument("--limit", type=int, default=5)
    sp.set_defaults(func=cmd_lookup)

    sp = sub.add_parser("log-food")
    sp.add_argument("--date", required=True)
    sp.add_argument("--item", required=True)
    sp.add_argument("--kcal", type=float, required=True)
    sp.add_argument("--protein", type=float, required=True)
    sp.add_argument("--fat", type=float, required=True)
    sp.add_argument("--carbs", type=float, required=True)
    sp.add_argument("--meal", default="snack")
    sp.add_argument("--qty-g", dest="qty_g", type=float)
    sp.add_argument("--source", default="manual")
    sp.add_argument("--notes")
    sp.set_defaults(func=cmd_log_food)

    sp = sub.add_parser("log-workout")
    sp.add_argument("--date", required=True)
    sp.add_argument("--exercise", required=True)
    sp.add_argument("--type", default="strength")
    sp.add_argument("--sets", type=float)
    sp.add_argument("--reps", type=float)
    sp.add_argument("--weight", type=float)
    sp.add_argument("--duration", type=float)
    sp.add_argument("--distance", type=float)
    sp.add_argument("--rpe", type=float)
    sp.add_argument("--notes")
    sp.set_defaults(func=cmd_log_workout)

    sp = sub.add_parser("log-weight")
    sp.add_argument("--date", required=True)
    sp.add_argument("--weight", type=float)
    sp.add_argument("--muscle", type=float)
    sp.add_argument("--fat", type=float)
    sp.add_argument("--fat-pct", dest="fat_pct", type=float)
    sp.add_argument("--water", type=float)
    sp.add_argument("--notes")
    sp.set_defaults(func=cmd_log_weight)

    sp = sub.add_parser("log-energy")
    sp.add_argument("--date", required=True)
    sp.add_argument("--activity", type=float)
    sp.add_argument("--basal", type=float)
    sp.add_argument("--total", type=float)
    sp.add_argument("--notes")
    sp.set_defaults(func=cmd_log_energy)

    sp = sub.add_parser("compute-goals")
    sp.add_argument("--sex", required=True)
    sp.add_argument("--age", type=int, required=True)
    sp.add_argument("--height", type=float, required=True)
    sp.add_argument("--weight", type=float, required=True)
    sp.add_argument("--activity", default="moderate")
    sp.add_argument("--goal", default="maintain")
    sp.set_defaults(func=cmd_compute_goals)

    sp = sub.add_parser("summary")
    sp.add_argument("--period", default="day",
                    choices=["day", "week", "month", "year", "custom"])
    sp.add_argument("--date")
    sp.add_argument("--today")
    sp.add_argument("--date-from", dest="date_from")
    sp.add_argument("--date-to", dest="date_to")
    sp.set_defaults(func=cmd_summary)

    sp = sub.add_parser("config-set")
    sp.add_argument("--patch", required=True)
    sp.set_defaults(func=cmd_config_set)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if getattr(args, "config", None):
        # Let the local backend resolve a relative data path next to the config.
        os.environ["FITTRACK_CONFIG"] = os.path.abspath(args.config)
    args.func(args)


if __name__ == "__main__":
    main()
