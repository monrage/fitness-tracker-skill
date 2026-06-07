# Onboarding — first-run setup wizard

Triggered when `status` reports `onboarded: false`. Goal: get the user from zero
to a working tracker in a friendly, guided way. Go **one step at a time**, in the
user's language (default Russian). Confirm each step; don't dump the whole form
at once. Apply every choice with `config-set` so progress is saved as you go.

## Step 0 — Welcome & orient

Briefly explain what the tracker will do (log food КБЖУ + workouts + weight
against goals, with weekly/monthly/yearly summaries) and that everything is
stored in **their own** account. Then start the wizard.

## Step 1 — Basics

Ask (offer the defaults, let them just say "да"):
- **Language** — ru / en (default ru)
- **Units** — metric (kg / g / km / kcal) is the default; switch only if asked
- **Timezone** — needed so "today" is correct (default Europe/Moscow)
- **Week start** — mon / sun (default mon)

Save:
```
python scripts/fittrack.py config-set --patch '{"lang":"ru","timezone":"Europe/Moscow","week_start":"mon"}'
```

## Step 2 — Choose where data lives

Present the three options honestly (details + setup steps in
`references/backends/<choice>.md`):

| Backend | Best for | Setup effort | Cross-device |
|---|---|---|---|
| **Notion** (recommended) | structured views, phone app, summaries | paste one integration token | yes (cloud) |
| **Google Sheets** | spreadsheet lovers, custom charts | one-time OAuth (more steps) | yes (cloud) |
| **Local file** | no cloud / maximum privacy | none | no — manual export |

Explain the persistence reality on claude.ai (see SKILL.md → *Persistence*):
config + secrets live in a local `fitness-config.json` they should keep as a
**Claude Project** file; with local backend the data file must be preserved too.

⚠️ **Network access first.** The sandbox blocks external APIs by default, so a cloud
backend will fail until the user allows its domain in **Settings → Capabilities → Allow
network egress → Domain allowlist** (or *All domains*): Notion → `api.notion.com`; Sheets
→ `sheets.googleapis.com` + `oauth2.googleapis.com`; Open Food Facts → `*.openfoodfacts.org`.
If `ensure-schema` or a lookup returns a connection error, this is the cause — point them here.

‼️ **Allowlist changes need a NEW chat.** The sandbox fixes the allowed domains when the session
starts, so editing the list in the *current* chat changes nothing. If a backend fails on a
connection error: have the user (1) fix the allowlist, (2) **save the config** (Step 5), then
(3) open a **new chat in the same Project** — you resume from the saved config (see *Resuming*).
Best to get network access set up *before* starting onboarding.

Then open the matching backend reference and walk the user through it. The end
state of that walkthrough is: credentials written to config, and the store
provisioned.

Apply backend choice + credentials, e.g. Notion:
```
python scripts/fittrack.py config-set --patch '{"backend":{"type":"notion","notion":{"token":"ntn_...","parent_page_id":"<page id>"}}}'
python scripts/fittrack.py ensure-schema          # creates the databases, returns their ids
python scripts/fittrack.py config-set --patch '{"backend":{"notion":{"databases":{"food":"<id>","workout":"<id>","bodyweight":"<id>"}}}}'
```
(For Sheets/local the steps differ — follow the backend reference.)
Verify with `ensure-schema` (idempotent) or a `status` check.

## Step 3 — Set goals

Two paths — ask which they prefer:

**A. They know their targets** → save directly:
```
python scripts/fittrack.py config-set --patch '{"goals":{"kcal":2200,"protein_g":165,"fat_g":70,"carbs_g":220,"workouts_per_week":4,"tolerance_pct":7}}'
```

**B. Compute from body stats** (Mifflin-St Jeor) → collect sex, age, height,
weight, activity (sedentary/light/moderate/active/very_active), goal
(cut/maintain/bulk), then:
```
python scripts/fittrack.py compute-goals --sex male --age 30 --height 182 --weight 85 --activity moderate --goal cut
```
Show the result, let them adjust, then save the agreed numbers with `config-set`
(and store the profile too so goals can be recomputed later). Details in
`references/goals.md`.

## Step 4 — Nutrition lookup preference

Confirm how macros get determined (default works for most):
- `claude+off` (default) — you estimate whole foods; Open Food Facts for
  branded/barcoded products; label photos read on demand
- `claude` — your estimates only, no external lookups
- `manual` — user always enters numbers

Set `off_country` for better local product hits (e.g. `ru`):
```
python scripts/fittrack.py config-set --patch '{"nutrition":{"provider":"claude+off","off_enabled":true,"off_country":"ru"}}'
```

## Step 5 — Finish & save the config to the Project

Mark setup complete and confirm:
```
python scripts/fittrack.py config-set --patch '{"onboarded":true}'
python scripts/fittrack.py status
```

Then **hand the config back for safekeeping** — this is the step that makes the setup survive
future sessions, so do it explicitly. You **cannot** save into the Project's knowledge yourself,
so the user does it manually:
1. Show the full `fitness-config.json` (the sandbox file and/or an artifact) so the user can take it.
2. Tell them — spelling out the exact name — to **save it into this Project's knowledge as a file
   named `fitness-config.json`** (they type the name themselves; replace any previous version).
   If their UI shows **Add to project** on the artifact, that works too — but the name must end up
   exactly `fitness-config.json`, otherwise step 0 won't find it next time.
3. For the **local** backend, do the same with `fitness-data.json` after each session.

Don't tell the user it's "saved" — you can't verify the Project write; confirm only what they report.

Then show 3–4 example things they can say now:
- «запиши на обед 200 г куриной грудки и 150 г риса»
- «сегодня жал 80 кг 5×5 и присед 100×5×5»
- «мой вес утром 84.5»
- «сводка за неделю»

## Resuming an interrupted setup

Onboarding is incremental — every choice was saved with `config-set`, so a setup that broke off
(e.g. a domain wasn't allowed and the user had to open a new chat) **continues, never restarts**:
- Step 0 brings the saved `fitness-config.json` back into the sandbox; run `status` to see state.
- Fill only what's missing: if a Notion backend + token are set but `databases` ids are empty, run
  `ensure-schema` now (network should work in the new chat) and save the returned ids; if goals or
  `onboarded` are still missing, finish those. Then re-hand the updated config to the user to save.

Never re-ask for anything already present in the config.

## Re-running / changing setup later

Any setting can be changed with `config-set` (switch backend, edit goals, change
timezone). To recompute goals after a weight change, re-run `compute-goals` and
save. Switching backends does not migrate old records — mention that.
