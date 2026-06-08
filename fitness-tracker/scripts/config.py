"""Bootstrap config for fitness-tracker.

The config holds user settings + goals + profile + backend pointer + secrets. It
lives in a LOCAL JSON file (default ./fitness-config.json, override FITTRACK_CONFIG)
— NOT in the cloud backend, since the skill needs it to reach the backend at all.
On claude.ai keep it as a Project knowledge file so it persists across sessions.
"""
from __future__ import annotations
import copy
import json
import os

CONFIG_PATH = os.environ.get("FITTRACK_CONFIG", "fitness-config.json")

DEFAULTS = {
    "version": 1,
    "onboarded": False,
    "lang": "ru",
    "units": {"mass": "g", "body_mass": "kg", "distance": "km", "energy": "kcal"},
    "timezone": "Europe/Moscow",
    "week_start": "mon",
    "backend": {"type": "local", "local": {"path": "fitness-data.json"}},
    "nutrition": {"provider": "claude+off", "off_enabled": True, "off_country": "ru"},
    "goals": {},
    "profile": {},
    "energy": {},
}


def _deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def merge(base, over):
    """Public deep-merge (used by `fittrack config-set` to apply a JSON patch)."""
    return _deep_merge(base, over)


def load(path=None):
    """Load config merged over DEFAULTS, or None if no file exists yet."""
    path = path or CONFIG_PATH
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return _deep_merge(DEFAULTS, json.load(f))


def load_or_default(path=None):
    return load(path) or copy.deepcopy(DEFAULTS)


def save(config, path=None):
    path = path or CONFIG_PATH
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return os.path.abspath(path)


def is_onboarded(config):
    """True only when setup finished AND at least calorie goal is set."""
    return bool(config and config.get("onboarded") and (config.get("goals") or {}).get("kcal"))
