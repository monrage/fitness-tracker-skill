"""Measure the SKILL.md frontmatter description length (chars + UTF-8 bytes).

claude.ai requires description <= 1024 characters. Run: python tests/check_desc.py
"""
import os
import re

SKILL = os.path.join(os.path.dirname(__file__), "..", "fitness-tracker", "SKILL.md")
text = open(SKILL, encoding="utf-8").read()
fm = text.split("---", 2)[1]
m = re.search(r"description:\s*>-?\s*\n(.*?)(?:\n[A-Za-z_]+:|\Z)", fm, re.S)
body = m.group(1)
# YAML '>-' folding: join non-empty lines with single spaces, strip indentation
folded = " ".join(line.strip() for line in body.strip().splitlines() if line.strip())
chars = len(folded)
nbytes = len(folded.encode("utf-8"))
print(f"description chars: {chars}")
print(f"description bytes (utf-8): {nbytes}")
print("LIMIT 1024 ->", "OK" if chars <= 1024 and nbytes <= 1024 else "TOO LONG")
print("---folded preview---")
print(folded)
