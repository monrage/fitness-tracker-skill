"""Validate the live Cloudflare deployment: served zip contents + page integrity.

Run: python tests/validate_deploy.py
"""
import io
import os
import urllib.request
import zipfile

BASE = "https://fitness-tracker-skill.monrage.workers.dev"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "fitness-tracker")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "validate/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


print("== served skill zip ==")
st, ct, data = fetch(BASE + "/fitness-tracker.zip")
print(f"HTTP {st} | {ct} | {len(data)} bytes")
zf = zipfile.ZipFile(io.BytesIO(data))
bad = zf.testzip()
print("zip integrity:", "OK" if bad is None else f"CORRUPT at {bad}")
served = set(n for n in zf.namelist() if not n.endswith("/"))

expected = set()
for root, dirs, files in os.walk(SKILL):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith((".pyc", ".pyo")):
            continue
        expected.add(os.path.relpath(os.path.join(root, f), SKILL).replace(os.sep, "/"))

print(f"entries: served={len(served)} expected={len(expected)}")
print("missing (in skill, NOT in zip):", sorted(expected - served) or "none")
print("extra   (in zip, NOT in skill):", sorted(served - expected) or "none")
print("SKILL.md at root:", "SKILL.md" in served)
print("junk (__pycache__/.pyc):", [n for n in served if "__pycache__" in n or n.endswith(".pyc")] or "none")
print("secret-ish (config/data):", [n for n in served if "fitness-config" in n or "fitness-data" in n] or "none")

print("\n== served guide page ==")
st2, ct2, html = fetch(BASE + "/")
print(f"HTTP {st2} | {ct2} | {len(html)} bytes")
local = os.path.join(ROOT, "docs", "index.html")
if os.path.exists(local):
    print("served bytes == local docs/index.html:", len(html) == os.path.getsize(local))
checks = {
    "lang toggle (.langbar)": b'class="langbar"',
    "backend tabs (.tabs)": b'class="tabs"',
    "GitHub link": b'github.com/monrage/fitness-tracker-skill',
    "download (relative)": b'href="fitness-tracker.zip"',
    "Capabilities mockup": b'Settings \xc2\xb7 Capabilities',
    "leaked token ntn_274 (must be 0)": b'ntn_274',
}
for label, needle in checks.items():
    print(f"  {label}:", html.count(needle))
