"""Goal calculation: Mifflin-St Jeor BMR -> TDEE -> calorie target -> macro split.

Used during onboarding (and whenever the user wants targets recomputed from body
stats). The assistant presents the result and lets the user adjust — these are
evidence-based starting points, not commandments.
"""
from __future__ import annotations

ACTIVITY = {
    "sedentary": 1.2,   # little/no exercise
    "light": 1.375,     # 1-3 days/week
    "moderate": 1.55,   # 3-5 days/week
    "active": 1.725,    # 6-7 days/week
    "very_active": 1.9, # hard daily / physical job
}
GOAL_FACTOR = {"cut": 0.82, "maintain": 1.0, "bulk": 1.12}


def bmr_mifflin(sex, age, height_cm, weight_kg):
    s = 5 if str(sex).lower().startswith("m") or str(sex).lower().startswith("м") else -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + s


def compute_targets(sex, age, height_cm, weight_kg, activity="moderate", goal="maintain",
                    protein_per_kg=1.8, fat_per_kg=0.9):
    """Return a dict of macro targets plus the assumptions used."""
    bmr = bmr_mifflin(sex, age, height_cm, weight_kg)
    af = ACTIVITY.get(str(activity).lower(), 1.55)
    gf = GOAL_FACTOR.get(str(goal).lower(), 1.0)
    tdee = bmr * af
    target_kcal = tdee * gf

    protein_g = round(protein_per_kg * weight_kg)
    fat_g = round(fat_per_kg * weight_kg)
    kcal_from_pf = protein_g * 4 + fat_g * 9
    carbs_g = round(max(0.0, (target_kcal - kcal_from_pf)) / 4)

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "kcal": round(target_kcal),
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carbs_g": carbs_g,
        "assumptions": {
            "activity": activity, "activity_factor": af,
            "goal": goal, "goal_factor": gf,
            "protein_per_kg": protein_per_kg, "fat_per_kg": fat_per_kg,
        },
    }
