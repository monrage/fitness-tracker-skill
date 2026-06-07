"""Google Sheets backend.

Auth uses the OAuth **refresh-token** flow (not a service account): the user
obtains client_id / client_secret / refresh_token once (see
references/backends/google-sheets.md) and the skill exchanges the refresh token
for a short-lived access token with a plain POST. This keeps the backend
pure-stdlib — a service account would need RS256 JWT signing (the `cryptography`
package), which isn't guaranteed in the sandbox.

One worksheet (tab) per kind: Food / Workout / Bodyweight, each with a header row.
"""
from __future__ import annotations
import json
import urllib.error
import urllib.parse
import urllib.request

from storage import Backend, KINDS

TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"

TABS = {"food": "Food", "workout": "Workout", "bodyweight": "Bodyweight"}
COLUMNS = {
    "food": ["date", "meal", "item", "qty_g", "kcal", "protein_g", "fat_g", "carbs_g", "source", "notes"],
    "workout": ["date", "type", "exercise", "sets", "reps", "weight_kg", "duration_min",
                "distance_km", "rpe", "volume", "notes"],
    "bodyweight": ["date", "weight_kg", "notes"],
}
NUMERIC = {
    "food": {"qty_g", "kcal", "protein_g", "fat_g", "carbs_g"},
    "workout": {"sets", "reps", "weight_kg", "duration_min", "distance_km", "rpe", "volume"},
    "bodyweight": {"weight_kg"},
}


def row_from_record(kind, record):
    """record -> flat row in COLUMNS order. Pure; unit-testable offline."""
    out = []
    for f in COLUMNS[kind]:
        v = record.get(f)
        out.append("" if v is None else v)
    return out


def record_from_row(kind, header, row, rownum=0):
    """header + row -> record dict, coercing numeric columns. Pure; offline-testable."""
    rec = {}
    for i, col in enumerate(header):
        val = row[i] if i < len(row) else ""
        if col in NUMERIC.get(kind, ()):
            rec[col] = None if val in ("", None) else float(val)
        else:
            rec[col] = val if val != "" else (None if col not in ("notes",) else "")
    rec["id"] = f"{kind[:1]}{rownum}"
    return rec


class SheetsBackend(Backend):
    def __init__(self, config):
        s = (config.get("backend") or {}).get("sheets") or {}
        self.spreadsheet_id = s.get("spreadsheet_id")
        o = s.get("oauth") or {}
        self.client_id = o.get("client_id")
        self.client_secret = o.get("client_secret")
        self.refresh_token = o.get("refresh_token")
        self._token = None
        if not self.spreadsheet_id:
            raise RuntimeError("Sheets: backend.sheets.spreadsheet_id is missing")
        if not (self.client_id and self.client_secret and self.refresh_token):
            raise RuntimeError("Sheets: backend.sheets.oauth client_id/client_secret/refresh_token missing")

    # ---- auth ----
    def _access_token(self):
        if self._token:
            return self._token
        body = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")
        req = urllib.request.Request(TOKEN_URL, data=body, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                self._token = json.load(r)["access_token"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Google token refresh failed {e.code}: {e.read().decode('utf-8','replace')[:300]}")
        return self._token

    def _api(self, method, url, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Sheets API {e.code}: {e.read().decode('utf-8','replace')[:400]}")

    # ---- schema ----
    def _existing_tabs(self):
        meta = self._api("GET", f"{SHEETS}/{self.spreadsheet_id}?fields=sheets.properties.title")
        return {s["properties"]["title"] for s in meta.get("sheets", [])}

    def ensure_schema(self):
        existing = self._existing_tabs()
        requests = [{"addSheet": {"properties": {"title": TABS[k]}}}
                    for k in KINDS if TABS[k] not in existing]
        if requests:
            self._api("POST", f"{SHEETS}/{self.spreadsheet_id}:batchUpdate", {"requests": requests})
        for k in KINDS:
            self._ensure_header(k)
        return {"backend": "sheets", "spreadsheet_id": self.spreadsheet_id, "tabs": list(TABS.values())}

    def _ensure_header(self, kind):
        tab = TABS[kind]
        rng = f"{tab}!1:1"
        got = self._api("GET", f"{SHEETS}/{self.spreadsheet_id}/values/{urllib.parse.quote(rng)}")
        if not got.get("values"):
            self._api("PUT",
                      f"{SHEETS}/{self.spreadsheet_id}/values/{urllib.parse.quote(rng)}"
                      "?valueInputOption=RAW",
                      {"values": [COLUMNS[kind]]})

    # ---- data ----
    def append(self, kind, record):
        tab = TABS[kind]
        self._ensure_header(kind)
        rng = f"{tab}!A:Z"
        self._api("POST",
                  f"{SHEETS}/{self.spreadsheet_id}/values/{urllib.parse.quote(rng)}"
                  ":append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
                  {"values": [row_from_record(kind, record)]})
        return dict(record)

    def _read(self, kind):
        tab = TABS[kind]
        rng = f"{tab}!A:Z"
        got = self._api("GET", f"{SHEETS}/{self.spreadsheet_id}/values/{urllib.parse.quote(rng)}")
        values = got.get("values") or []
        if not values:
            return []
        header = values[0]
        return [record_from_row(kind, header, row, i + 2) for i, row in enumerate(values[1:])]

    def query_range(self, kind, date_from, date_to):
        rows = [r for r in self._read(kind) if date_from <= (r.get("date") or "") <= date_to]
        return sorted(rows, key=lambda r: r.get("date", ""))

    def list_all(self, kind):
        return sorted(self._read(kind), key=lambda r: r.get("date", ""))
