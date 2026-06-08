"""Notion backend.

Uses the stable classic API (Notion-Version 2022-06-28): databases addressed by
`database_id`, rows created with `parent.database_id`, queried via
`/databases/{id}/query`. This avoids the newer data-source indirection and is the
most battle-tested surface for a third-party skill. Pure stdlib (urllib).

Provisioning (creating the three databases) happens once during onboarding via
`ensure_schema()`, which returns the new database ids for the caller to persist
into config. Logging never creates databases.
"""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.request

from storage import Backend, KINDS

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"

DB_TITLES = {
    "food": "FitnessLife — Food log",
    "workout": "FitnessLife — Workout log",
    "bodyweight": "FitnessLife — Bodyweight",
    "energy": "FitnessLife — Energy",
}
# A tiny key/value database for app state (last-viewed report dates, etc.).
META_TITLE = "FitnessLife — Meta"
META_PROPS = {"Key": {"title": {}}, "Value": {"rich_text": {}}}

# (Notion property name, type, our record field). First title prop per db is the row label.
SCHEMAS = {
    "food": [
        ("Item", "title", "item"), ("Date", "date", "date"), ("Meal", "select", "meal"),
        ("Qty g", "number", "qty_g"), ("Calories", "number", "kcal"),
        ("Protein g", "number", "protein_g"), ("Fat g", "number", "fat_g"),
        ("Carbs g", "number", "carbs_g"), ("Source", "select", "source"),
        ("Notes", "rich_text", "notes"),
    ],
    "workout": [
        ("Exercise", "title", "exercise"), ("Date", "date", "date"), ("Type", "select", "type"),
        ("Sets", "number", "sets"), ("Reps", "number", "reps"),
        ("Weight kg", "number", "weight_kg"), ("Duration min", "number", "duration_min"),
        ("Distance km", "number", "distance_km"), ("RPE", "number", "rpe"),
        ("Volume", "number", "volume"), ("Notes", "rich_text", "notes"),
    ],
    "bodyweight": [
        ("Entry", "title", "date"), ("Date", "date", "date"),
        ("Weight kg", "number", "weight_kg"), ("Muscle kg", "number", "muscle_kg"),
        ("Fat kg", "number", "fat_kg"), ("Fat %", "number", "fat_pct"),
        ("Water kg", "number", "water_kg"), ("Notes", "rich_text", "notes"),
    ],
    "energy": [
        ("Entry", "title", "date"), ("Date", "date", "date"),
        ("Activity kcal", "number", "activity_kcal"),
        ("Basal kcal", "number", "basal_kcal"),
        ("Total out kcal", "number", "total_out_kcal"),
        ("Notes", "rich_text", "notes"),
    ],
}
SELECT_OPTIONS = {
    "Meal": ["breakfast", "lunch", "dinner", "snack"],
    "Type": ["strength", "cardio", "mobility", "sport"],
    "Source": ["claude", "off", "label", "manual"],
}


def _value(ptype, v):
    if ptype == "title":
        return {"title": [{"text": {"content": "" if v is None else str(v)}}]}
    if ptype == "rich_text":
        return {"rich_text": [{"text": {"content": str(v)}}]} if v else {"rich_text": []}
    if ptype == "number":
        return {"number": None if v in (None, "") else float(v)}
    if ptype == "select":
        return {"select": {"name": str(v)} if v else None}
    if ptype == "date":
        return {"date": {"start": v} if v else None}
    raise ValueError(ptype)


def _pval(ptype, prop):
    if prop is None:
        return None
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", [])) or None
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if ptype == "number":
        return prop.get("number")
    if ptype == "select":
        s = prop.get("select")
        return s.get("name") if s else None
    if ptype == "date":
        d = prop.get("date")
        return d.get("start") if d else None
    return None


def build_props(kind, record):
    """record -> Notion page properties payload. Pure; unit-testable offline."""
    return {name: _value(ptype, record.get(field)) for name, ptype, field in SCHEMAS[kind]}


def parse_page(kind, page):
    """Notion page -> our record dict. Pure; unit-testable offline."""
    props = page.get("properties", {})
    rec = {}
    for name, ptype, field in SCHEMAS[kind]:
        rec[field] = _pval(ptype, props.get(name))
    rec["id"] = page.get("id")
    return rec


def schema_props(kind):
    out = {}
    for name, ptype, _field in SCHEMAS[kind]:
        if ptype == "title":
            out[name] = {"title": {}}
        elif ptype == "date":
            out[name] = {"date": {}}
        elif ptype == "number":
            out[name] = {"number": {"format": "number"}}
        elif ptype == "rich_text":
            out[name] = {"rich_text": {}}
        elif ptype == "select":
            out[name] = {"select": {"options": [{"name": o} for o in SELECT_OPTIONS.get(name, [])]}}
    return out


class NotionBackend(Backend):
    def __init__(self, config):
        n = (config.get("backend") or {}).get("notion") or {}
        self.token = n.get("token")
        self.version = n.get("version") or VERSION
        self.parent_page_id = n.get("parent_page_id")
        self.dbs = dict(n.get("databases") or {})
        if not self.token:
            raise RuntimeError("Notion: backend.notion.token is missing")

    def _api(self, method, path, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(API + path, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.version,
            "Content-Type": "application/json",
        })
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    time.sleep(float(e.headers.get("Retry-After", 1)))
                    continue
                raise RuntimeError(f"Notion API {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
        raise RuntimeError("Notion API: exhausted retries")

    def _db(self, kind):
        db = self.dbs.get(kind)
        if not db:
            raise RuntimeError(f"Notion: database id for '{kind}' not configured — run onboarding/ensure-schema")
        return db

    def ensure_schema(self):
        missing = [k for k in KINDS if not self.dbs.get(k)]
        if not self.dbs.get("meta"):
            missing.append("meta")
        if not missing:
            return {"backend": "notion", "databases": self.dbs}
        if not self.parent_page_id:
            raise RuntimeError("Notion: set backend.notion.parent_page_id, then run ensure-schema")
        created = {}
        for k in missing:
            title = META_TITLE if k == "meta" else DB_TITLES[k]
            props = META_PROPS if k == "meta" else schema_props(k)
            res = self._api("POST", "/databases", {
                "parent": {"type": "page_id", "page_id": self.parent_page_id},
                "title": [{"type": "text", "text": {"content": title}}],
                "properties": props,
            })
            self.dbs[k] = res["id"]
            created[k] = res["id"]
        return {"backend": "notion", "databases": self.dbs, "created": created}

    def append(self, kind, record):
        res = self._api("POST", "/pages", {
            "parent": {"database_id": self._db(kind)},
            "properties": build_props(kind, record),
        })
        out = dict(record)
        out["id"] = res["id"]
        return out

    def _query(self, kind, body):
        db = self._db(kind)
        results, cursor = [], None
        while True:
            b = dict(body)
            if cursor:
                b["start_cursor"] = cursor
            data = self._api("POST", f"/databases/{db}/query", b)
            results.extend(parse_page(kind, pg) for pg in data.get("results", []))
            if data.get("has_more"):
                cursor = data.get("next_cursor")
            else:
                return results

    def query_range(self, kind, date_from, date_to):
        return self._query(kind, {
            "filter": {"and": [
                {"property": "Date", "date": {"on_or_after": date_from}},
                {"property": "Date", "date": {"on_or_before": date_to}},
            ]},
            "sorts": [{"property": "Date", "direction": "ascending"}],
            "page_size": 100,
        })

    def list_all(self, kind):
        return self._query(kind, {
            "sorts": [{"property": "Date", "direction": "ascending"}],
            "page_size": 100,
        })

    def read_meta(self):
        db = self.dbs.get("meta")
        if not db:
            return {}
        out = {}
        for pg in self._api("POST", f"/databases/{db}/query", {"page_size": 100}).get("results", []):
            props = pg.get("properties", {})
            k = "".join(t.get("plain_text", "") for t in props.get("Key", {}).get("title", []))
            v = "".join(t.get("plain_text", "") for t in props.get("Value", {}).get("rich_text", []))
            if k:
                out[k] = v
        return out

    def write_meta(self, patch):
        db = self.dbs.get("meta")
        if not db:
            raise RuntimeError("Notion: meta database not configured — run ensure-schema")
        for k, v in (patch or {}).items():
            val = {"rich_text": [{"text": {"content": str(v)}}]} if v != "" else {"rich_text": []}
            found = self._api("POST", f"/databases/{db}/query",
                              {"filter": {"property": "Key", "title": {"equals": str(k)}}, "page_size": 1})
            res = found.get("results")
            if res:
                self._api("PATCH", f"/pages/{res[0]['id']}", {"properties": {"Value": val}})
            else:
                self._api("POST", "/pages", {"parent": {"database_id": db}, "properties": {
                    "Key": {"title": [{"text": {"content": str(k)}}]}, "Value": val}})
        return self.read_meta()
