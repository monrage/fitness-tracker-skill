# Contributing

Thanks for your interest in improving **fitness-tracker**! Issues, ideas and PRs
are all welcome.

## Ways to help
- Report bugs or rough edges (open an issue).
- Improve the install guide / translations.
- Add a storage backend, refine the macro logic, extend summaries.

## Dev setup
No dependencies — the skill runs on the **Python standard library only** (so it
works in the claude.ai sandbox without `pip install`). You need **Python 3.10+**.

```bash
git clone https://github.com/monrage/fitness-tracker-skill.git
cd fitness-tracker-skill
```

## Running tests
The suite is plain-Python (no pytest needed). On Windows prefix with
`$env:PYTHONUTF8=1;` so Cyrillic prints correctly.

```bash
python tests/test_foundation.py        # dates, records, local backend, config
python tests/test_logic.py             # goals (Mifflin-St Jeor), summaries, scaling
python tests/test_backends_mapping.py  # Notion/Sheets record mapping (offline)
python tests/test_docs_consistency.py  # docs/assets ↔ code contracts
python tests/check_desc.py             # SKILL.md description length (<1024)
python tests/test_off_live.py          # live Open Food Facts (network; optional)
```
CI runs all of these except the live network test.

## Project layout
```
fitness-tracker/   The skill: SKILL.md (router), references/ (on-demand docs),
                   scripts/ (stdlib CLI + backends/logic), assets/, evals/
guide/             Install-guide source: template.html (bilingual) + img/ + build.py
docs/              Built guide (committed; served by Cloudflare Pages) — run build.py, don't edit by hand
tests/             Plain-Python test suite + eval fixtures
.github/workflows/ CI, Release (zips the skill), Pages
```

## Changing the skill
1. Edit files under `fitness-tracker/`.
2. If you touch the data model, CLI flags, or backends, update the matching tests
   in `tests/` and keep `references/` accurate (`SKILL.md` is the router).
3. Run the test suite — it must stay green.

## Changing the install guide
The guide is bilingual: every translatable string exists twice, as
`<span class="ru">…</span><span class="en">…</span>` (or a `.ru`/`.en` block).
Edit `guide/template.html`, then rebuild:

```bash
python guide/build.py   # → docs/index.html (self-contained)
```
Add/adjust **both** languages for any text you change.

## Conventions
- Keep scripts stdlib-only (portability is a feature).
- Explain *why* in `SKILL.md`/references, not just *what*.
- **Never commit secrets** — tokens and personal logs live in the user's own
  `fitness-config.json` / `fitness-data.json`, which are git-ignored.
- Conventional, descriptive commit messages are appreciated.
