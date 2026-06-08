"""Storage abstraction for fitness-tracker.

Defines the canonical record shapes and the Backend interface that every storage
adapter (local / notion / sheets) implements. The assistant builds records via
the make_* helpers so every backend receives identical, validated data.

Pure stdlib — runs in any sandbox without pip installs.
"""
from __future__ import annotations
import datetime as _dt

KINDS = ("food", "workout", "bodyweight", "energy")
MEALS = ("breakfast", "lunch", "dinner", "snack")
WORKOUT_TYPES = ("strength", "cardio", "mobility", "sport")
FOOD_SOURCES = ("claude", "off", "label", "manual")


def _num(v, default=0.0):
    if v is None or v == "":
        return default
    return round(float(v), 2)


def _onum(v):
    """Optional number: None when the value is absent, else a rounded float."""
    return None if v in (None, "") else _num(v)


def _int(v):
    if v is None or v == "":
        return None
    return int(round(float(v)))


def validate_date(d: str) -> str:
    """Raise ValueError unless d is an ISO YYYY-MM-DD date."""
    _dt.date.fromisoformat(str(d))
    return str(d)


def make_food(date, item, kcal, protein_g, fat_g, carbs_g, *,
              meal="snack", qty_g=None, source="manual", notes=""):
    validate_date(date)
    return {
        "date": date,
        "meal": meal if meal in MEALS else "snack",
        "item": str(item).strip(),
        "qty_g": _num(qty_g) if qty_g not in (None, "") else None,
        "kcal": _num(kcal),
        "protein_g": _num(protein_g),
        "fat_g": _num(fat_g),
        "carbs_g": _num(carbs_g),
        "source": source if source in FOOD_SOURCES else "manual",
        "notes": str(notes or "").strip(),
    }


def make_workout(date, exercise, *, wtype="strength", sets=None, reps=None,
                 weight_kg=None, duration_min=None, distance_km=None,
                 rpe=None, notes=""):
    validate_date(date)
    wtype = wtype if wtype in WORKOUT_TYPES else "strength"
    sets_i, reps_i = _int(sets), _int(reps)
    w = _num(weight_kg) if weight_kg not in (None, "") else None
    volume = None
    if wtype == "strength" and sets_i and reps_i and w:
        volume = round(sets_i * reps_i * w, 1)
    return {
        "date": date,
        "type": wtype,
        "exercise": str(exercise).strip(),
        "sets": sets_i,
        "reps": reps_i,
        "weight_kg": w,
        "duration_min": _num(duration_min) if duration_min not in (None, "") else None,
        "distance_km": _num(distance_km) if distance_km not in (None, "") else None,
        "rpe": _num(rpe) if rpe not in (None, "") else None,
        "volume": volume,
        "notes": str(notes or "").strip(),
    }


_BODYCOMP_FIELDS = ("weight_kg", "muscle_kg", "fat_kg", "fat_pct", "water_kg")


def make_bodyweight(date, weight_kg=None, *, muscle_kg=None, fat_kg=None,
                    fat_pct=None, water_kg=None, notes=""):
    """One daily body measurement. weight_kg stays the first positional arg for
    back-compat; every metric is optional but at least one must be present."""
    validate_date(date)
    rec = {
        "date": date,
        "weight_kg": _onum(weight_kg),
        "muscle_kg": _onum(muscle_kg),
        "fat_kg": _onum(fat_kg),
        "fat_pct": _onum(fat_pct),
        "water_kg": _onum(water_kg),
        "notes": str(notes or "").strip(),
    }
    if all(rec[f] is None for f in _BODYCOMP_FIELDS):
        raise ValueError("bodyweight needs at least one metric: " + "/".join(_BODYCOMP_FIELDS))
    return rec


def make_energy(date, *, activity_kcal=None, basal_kcal=None,
                total_out_kcal=None, notes=""):
    """Daily energy expenditure. The caller (fittrack) resolves basal (resting /
    BMR) from the profile when omitted; here we only fill the missing member of
    the basal / activity / total trio via total = basal + activity."""
    validate_date(date)
    a, b, t = _onum(activity_kcal), _onum(basal_kcal), _onum(total_out_kcal)
    if t is None and b is not None and a is not None:
        t = round(b + a, 2)
    elif a is None and t is not None and b is not None:
        a = round(t - b, 2)
    elif b is None and t is not None and a is not None:
        b = round(t - a, 2)
    if t is None and a is None:
        raise ValueError("energy needs at least activity_kcal or total_out_kcal")
    return {
        "date": date,
        "activity_kcal": a,
        "basal_kcal": b,
        "total_out_kcal": t,
        "notes": str(notes or "").strip(),
    }


class Backend:
    """Interface for storage adapters. Subclasses implement all methods."""

    def ensure_schema(self):
        """Create databases/tabs/file if missing. Idempotent. Returns info dict."""
        raise NotImplementedError

    def append(self, kind: str, record: dict) -> dict:
        """Persist one record of `kind`; return the stored record (with id)."""
        raise NotImplementedError

    def query_range(self, kind: str, date_from: str, date_to: str) -> list:
        """Return records of `kind` with date in [date_from, date_to], date-sorted."""
        raise NotImplementedError

    def list_all(self, kind: str) -> list:
        """Return every record of `kind`, date-sorted."""
        raise NotImplementedError


def get_backend(config: dict) -> Backend:
    btype = (config.get("backend") or {}).get("type", "local")
    if btype == "local":
        from backend_local import LocalBackend
        return LocalBackend(config)
    if btype == "notion":
        from backend_notion import NotionBackend
        return NotionBackend(config)
    if btype == "sheets":
        from backend_sheets import SheetsBackend
        return SheetsBackend(config)
    raise ValueError(f"Unknown backend type: {btype!r}")
