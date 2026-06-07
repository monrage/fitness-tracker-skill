"""Local JSON backend: stores records in a single JSON file.

Persistence note (claude.ai): the data file lives in the sandbox / project. For
durable cross-session storage keep it as a Claude Project knowledge file and
re-save after changes, or use a cloud backend (Notion / Sheets).
"""
from __future__ import annotations
import json
import os
from storage import Backend, KINDS


class LocalBackend(Backend):
    def __init__(self, config):
        loc = (config.get("backend") or {}).get("local") or {}
        path = loc.get("path") or os.environ.get("FITTRACK_DATA", "fitness-data.json")
        if not os.path.isabs(path):
            # Resolve a relative data path next to the config file (not the CWD),
            # so onboarding's default lands beside fitness-config.json regardless
            # of where python is invoked from. fittrack sets FITTRACK_CONFIG.
            cfgp = os.environ.get("FITTRACK_CONFIG")
            base = os.path.dirname(os.path.abspath(cfgp)) if cfgp else os.getcwd()
            path = os.path.join(base, path)
        self.path = path

    def _load(self):
        if not os.path.exists(self.path):
            return {k: [] for k in KINDS}
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in KINDS:
            data.setdefault(k, [])
        return data

    def _save(self, data):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def ensure_schema(self):
        if not os.path.exists(self.path):
            self._save({k: [] for k in KINDS})
        return {"backend": "local", "path": os.path.abspath(self.path)}

    def append(self, kind, record):
        if kind not in KINDS:
            raise ValueError(kind)
        data = self._load()
        seq = max((r.get("_seq", 0) for r in data[kind]), default=0) + 1
        stored = dict(record)
        stored["_seq"] = seq
        stored["id"] = f"{kind[:1]}{seq:06d}"
        data[kind].append(stored)
        self._save(data)
        return stored

    def query_range(self, kind, date_from, date_to):
        data = self._load()
        rows = [r for r in data[kind] if date_from <= r.get("date", "") <= date_to]
        return sorted(rows, key=lambda r: (r.get("date", ""), r.get("_seq", 0)))

    def list_all(self, kind):
        data = self._load()
        return sorted(data[kind], key=lambda r: (r.get("date", ""), r.get("_seq", 0)))
