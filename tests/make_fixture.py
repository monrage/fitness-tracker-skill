"""Build an isolated onboarded fixture (config + a week of realistic data) for eval runs.

Usage: python tests/make_fixture.py <target_dir>
Creates <target_dir>/fitness-config.json (local backend, goals, profile, onboarded)
and <target_dir>/fitness-data.json with logs for 2026-06-01..2026-06-07 (06-03 is a
deliberate gap), 6 workouts incl. two PRs, and 3 bodyweight points.
"""
import os
import sys

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "fitness-tracker", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import config as cfg  # noqa: E402
import storage  # noqa: E402
from backend_local import LocalBackend  # noqa: E402

FOOD = {
    "2026-06-01": [("breakfast", "овсянка с бананом", 420, 14, 9, 72),
                   ("lunch", "курица с рисом", 650, 55, 12, 70),
                   ("dinner", "лосось с овощами", 600, 42, 30, 25),
                   ("snack", "творог", 180, 20, 5, 8)],
    "2026-06-02": [("breakfast", "яичница 3 яйца", 300, 20, 22, 2),
                   ("lunch", "говядина с гречкой", 700, 52, 25, 68),
                   ("dinner", "салат с тунцом", 480, 38, 20, 22)],
    # 2026-06-03 — пропуск (нет записей)
    "2026-06-04": [("breakfast", "протеин + овсянка", 400, 35, 8, 45),
                   ("lunch", "индейка с булгуром", 680, 58, 14, 72),
                   ("dinner", "омлет с овощами", 520, 34, 30, 18),
                   ("snack", "орехи", 200, 6, 18, 6)],
    "2026-06-05": [("breakfast", "сырники", 450, 28, 16, 40),
                   ("lunch", "курица с пастой", 720, 50, 18, 82),
                   ("dinner", "творог с ягодами", 260, 30, 6, 18)],
    "2026-06-06": [("breakfast", "овсянка", 380, 12, 8, 66),
                   ("lunch", "плов с курицей", 780, 40, 28, 88),
                   ("dinner", "рыба с салатом", 520, 40, 24, 20),
                   ("snack", "кефир", 120, 9, 3, 12)],
    "2026-06-07": [("breakfast", "яйца с тостом", 350, 22, 18, 24),
                   ("lunch", "куриная грудка с рисом", 650, 60, 10, 72)],
}
WORKOUTS = [
    {"date": "2026-06-01", "exercise": "жим лёжа", "wtype": "strength", "sets": 5, "reps": 5, "weight_kg": 80},
    {"date": "2026-06-01", "exercise": "присед", "wtype": "strength", "sets": 5, "reps": 5, "weight_kg": 100},
    {"date": "2026-06-02", "exercise": "бег", "wtype": "cardio", "duration_min": 30, "distance_km": 5.0},
    {"date": "2026-06-04", "exercise": "жим лёжа", "wtype": "strength", "sets": 5, "reps": 5, "weight_kg": 82.5},
    {"date": "2026-06-04", "exercise": "становая тяга", "wtype": "strength", "sets": 5, "reps": 5, "weight_kg": 110},
    {"date": "2026-06-06", "exercise": "присед", "wtype": "strength", "sets": 5, "reps": 5, "weight_kg": 102.5},
]
BODYWEIGHT = [("2026-06-01", 85.0), ("2026-06-04", 84.6), ("2026-06-07", 84.2)]


def build(dirpath):
    os.makedirs(dirpath, exist_ok=True)
    data_path = os.path.join(dirpath, "fitness-data.json")
    cfg_path = os.path.join(dirpath, "fitness-config.json")
    c = {
        "version": 1, "onboarded": True, "lang": "ru",
        "units": {"mass": "g", "body_mass": "kg", "distance": "km", "energy": "kcal"},
        "timezone": "Europe/Moscow", "week_start": "mon",
        "backend": {"type": "local", "local": {"path": data_path}},
        "nutrition": {"provider": "claude+off", "off_enabled": True, "off_country": "ru"},
        "goals": {"kcal": 2200, "protein_g": 165, "fat_g": 70, "carbs_g": 220,
                  "workouts_per_week": 4, "bodyweight_target_kg": 82, "tolerance_pct": 7},
        "profile": {"sex": "male", "age": 30, "height_cm": 182, "weight_kg": 85,
                    "activity": "moderate", "goal": "cut"},
    }
    cfg.save(c, cfg_path)
    be = LocalBackend(c)
    be.ensure_schema()
    for d, items in FOOD.items():
        for meal, item, k, p, f, cb in items:
            be.append("food", storage.make_food(d, item, k, p, f, cb, meal=meal, source="claude"))
    for w in WORKOUTS:
        be.append("workout", storage.make_workout(
            w["date"], w["exercise"], wtype=w["wtype"], sets=w.get("sets"), reps=w.get("reps"),
            weight_kg=w.get("weight_kg"), duration_min=w.get("duration_min"), distance_km=w.get("distance_km")))
    for d, wt in BODYWEIGHT:
        be.append("bodyweight", storage.make_bodyweight(d, wt))
    print("seeded:", os.path.abspath(dirpath))


if __name__ == "__main__":
    build(sys.argv[1])
