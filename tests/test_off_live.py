"""Live Open Food Facts smoke test (network). Tolerant: never fails the build —
prints what it gets so we can eyeball that the integration works end to end.

Run: python tests/test_off_live.py
"""
import os
import sys

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "fitness-tracker", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))
import nutrition  # noqa: E402

print("== barcode 3017620422003 (Nutella) ==")
r = nutrition.lookup_barcode("3017620422003", country="world")
if r:
    print(" item:", r["item"])
    print(" per100g:", r["per100g"])
    print(" 30g:", nutrition.scale(r["per100g"], 30))
else:
    print(" (no result / network unavailable)")

print("== search 'молоко' (ru) ==")
res = nutrition.search("молоко", country="ru", limit=3)
for x in res:
    print(" -", x["item"], "| per100g kcal:", x["per100g"]["kcal"], "| code:", x.get("barcode"))
if not res:
    print(" (no results / network unavailable)")
print("done")
