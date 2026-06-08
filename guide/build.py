"""Build the install-guide site into docs/ — served by Cloudflare Pages.

Produces:
  docs/index.html            self-contained bilingual install guide (from guide/template.html)
  docs/fitness-tracker.zip   the packaged skill (contents of fitness-tracker/, SKILL.md at root)

Cloudflare Pages settings:  Build command = `python guide/build.py`, Output directory = `docs`.
Run locally the same way:   python guide/build.py
Pure stdlib; no images, no dependencies.
"""
import os
import zipfile

SELF = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SELF)
TEMPLATE = os.path.join(SELF, "template.html")
DOCS = os.path.join(ROOT, "docs")
SKILL = os.path.join(ROOT, "fitness-tracker")


def build_guide():
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()
    os.makedirs(DOCS, exist_ok=True)
    out = os.path.join(DOCS, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


def build_zip():
    """Zip the skill so the guide's Download button can serve it same-origin."""
    os.makedirs(DOCS, exist_ok=True)
    out = os.path.join(DOCS, "fitness-tracker.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(SKILL):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    continue
                if fn.lower().startswith("readme"):
                    continue  # docs belong in the repo, not in the distributed skill
                full = os.path.join(root, fn)
                arc = os.path.relpath(full, SKILL).replace(os.sep, "/")  # forward slashes
                z.write(full, arc)
    return out


def main():
    g = build_guide()
    z = build_zip()
    print(f"built {g} ({round(os.path.getsize(g) / 1024)} KB)")
    print(f"built {z} ({round(os.path.getsize(z) / 1024)} KB)")


if __name__ == "__main__":
    main()
