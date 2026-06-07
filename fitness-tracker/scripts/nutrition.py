"""Nutrition lookup via Open Food Facts (free, no API key) + portion scaling.

Open Food Facts is best for branded / packaged products and barcodes. For whole
foods and home cooking the assistant's own estimate is usually better — see
references/nutrition-lookup.md for the decision cascade.

Pure stdlib (urllib). All network calls are best-effort: on any failure they
return None so the caller falls back to a Claude estimate or manual entry.
"""
from __future__ import annotations
import json
import urllib.parse
import urllib.request

_UA = "fitness-tracker-skill/1.0 (Claude skill; https://claude.ai)"
_TIMEOUT = 10


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.load(resp)


def _per100g(nutriments):
    """Extract per-100g macros from an OFF nutriments object; None if no energy."""
    def g(*keys):
        for k in keys:
            v = nutriments.get(k)
            if v not in (None, ""):
                try:
                    return round(float(v), 2)
                except (TypeError, ValueError):
                    continue
        return None
    kcal = g("energy-kcal_100g", "energy-kcal")
    if kcal is None:
        kj = g("energy_100g", "energy")
        if kj is not None:
            kcal = round(kj / 4.184, 1)
    if kcal is None:
        return None
    return {
        "kcal": kcal,
        "protein_g": g("proteins_100g", "proteins") or 0.0,
        "fat_g": g("fat_100g", "fat") or 0.0,
        "carbs_g": g("carbohydrates_100g", "carbohydrates") or 0.0,
    }


def lookup_barcode(barcode, country="world"):
    """Return {item, barcode, per100g, source} for a product barcode, or None."""
    barcode = str(barcode).strip()
    url = (f"https://{country or 'world'}.openfoodfacts.org/api/v2/product/"
           f"{urllib.parse.quote(barcode)}.json"
           "?fields=product_name,brands,nutriments,code")
    try:
        data = _get(url)
    except Exception:
        return None
    if data.get("status") != 1 and not data.get("product"):
        return None
    p = data.get("product") or {}
    per = _per100g(p.get("nutriments") or {})
    if not per:
        return None
    name = p.get("product_name") or p.get("brands") or barcode
    return {"item": name, "barcode": barcode, "per100g": per, "source": "off"}


def search(query, country="world", limit=5):
    """Free-text product search; returns up to `limit` candidates with per-100g macros."""
    params = urllib.parse.urlencode({
        "search_terms": query, "search_simple": 1, "action": "process",
        "json": 1, "page_size": limit,
        "fields": "product_name,brands,nutriments,code",
    })
    url = f"https://{country or 'world'}.openfoodfacts.org/cgi/search.pl?{params}"
    try:
        data = _get(url)
    except Exception:
        return []
    out = []
    for p in (data.get("products") or [])[:limit]:
        per = _per100g(p.get("nutriments") or {})
        if not per:
            continue
        out.append({
            "item": p.get("product_name") or p.get("brands") or query,
            "barcode": p.get("code"),
            "per100g": per,
            "source": "off",
        })
    return out


def scale(per100g, grams):
    """Scale per-100g macros to `grams`. Pure; safe to unit-test offline."""
    f = float(grams) / 100.0
    return {
        "kcal": round(per100g["kcal"] * f, 1),
        "protein_g": round(per100g.get("protein_g", 0) * f, 1),
        "fat_g": round(per100g.get("fat_g", 0) * f, 1),
        "carbs_g": round(per100g.get("carbs_g", 0) * f, 1),
    }
