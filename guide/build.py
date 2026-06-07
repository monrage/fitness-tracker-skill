"""Build the install guide: inline screenshots as base64 into one HTML file.

Reads guide/template.html + guide/img/{1.png,2.png,3.png,4.webp}, replaces the
{{IMG1..4}} placeholders, and writes docs/index.html — a fully self-contained
page used both for GitHub Pages and as a standalone handout.

Run from anywhere:  python guide/build.py
"""
import base64
import os

SELF = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SELF)
IMG = os.path.join(SELF, "img")
TEMPLATE = os.path.join(SELF, "template.html")
OUT = os.path.join(ROOT, "docs", "index.html")

MIME = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
SLOTS = {}  # guide is now fully CSS mockups — no embedded screenshots


def data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{MIME.get(ext, 'application/octet-stream')};base64,{b64}"


def main():
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()
    for slot, fname in SLOTS.items():
        if slot not in html:
            raise SystemExit(f"placeholder {slot} missing from template")
        path = os.path.join(IMG, fname)
        if not os.path.exists(path):
            raise SystemExit(f"image not found: {path}")
        html = html.replace(slot, data_uri(path))
    left = [s for s in SLOTS if s in html]
    if left:
        raise SystemExit(f"unreplaced placeholders: {left}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"built {OUT} ({round(os.path.getsize(OUT) / 1024)} KB)")


if __name__ == "__main__":
    main()
