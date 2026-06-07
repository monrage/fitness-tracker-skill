---
name: fitness-tracker
description: >-
  Personal fitness and nutrition tracker: logs meals with calories and macros
  (КБЖУ — calories/protein/fat/carbs), workouts (sets/reps/weight, cardio) and
  bodyweight against the user's daily goals, and builds weekly/monthly/yearly
  progress summaries. Data is stored in the user's own Notion, Google Sheets or
  a local file, configured on first run. Use whenever the user logs what they
  ate or how they trained, mentions calories/protein/fat/carbs/macros/КБЖУ, sets
  or changes nutrition or fitness goals, logs their weight, sends a photo of a
  food label, or asks for a diet or training summary, progress or stats for any
  period — including casual phrasing like «запиши на обед 200 г курицы» or "log
  breakfast: 2 eggs". Also handles first-time integration setup.
---

# Fitness Tracker

Turn the chat into a personal КБЖУ + training journal backed by the user's own
Notion / Google Sheets / local file. You handle the conversation; a bundled CLI
(`scripts/fittrack.py`) handles all deterministic work (persistence, date math,
food-database lookups, goal math, aggregation) and prints JSON you parse.

## Invocation protocol — do this every turn

0. **Bring config into the sandbox.** The CLI reads `./fitness-config.json` in the
   working directory. On claude.ai the durable copy lives in the **Project**, so at the
   start of a session recreate it before any CLI call: if a `fitness-config.json` is
   attached to this Project/conversation, write its exact contents to
   `./fitness-config.json` (and `fitness-data.json` too, for the local backend). If no file
   by that exact name is attached but the Project contains a JSON that looks like this config
   (has `backend` / `goals` / `onboarded` keys), use it anyway and recreate it as
   `./fitness-config.json`. If neither the sandbox nor the Project has it → treat as first run.
1. **Check setup.** Run `status` (see *Running the CLI*). If `config_found` is
   false or `onboarded` is false → load `references/onboarding.md` and guide
   setup. Never log or summarize before onboarding is complete.
2. **Classify intent**: log food · log workout · log bodyweight · set/compute
   goals · summary (day/week/month/year) · change settings · question.
3. **Route** to the matching reference + CLI command below.

## You ↔ CLI: division of labour

- **You** understand natural language, resolve what the user means, ESTIMATE
  macros from your own nutrition knowledge, read nutrition-label photos (vision),
  and present results warmly in the user's language.
- **The CLI** persists records, resolves dates deterministically, queries Open
  Food Facts, computes goal targets, and aggregates summaries. Always go through
  it for data — never hand-maintain the store yourself.

## Running the CLI

The script lives in this skill's `scripts/` directory. Invoke it with the user's
config (defaults to `./fitness-config.json` in the working directory):

```
python scripts/fittrack.py [--config PATH] <command> [args]
```

`status` first to learn state:

```
python scripts/fittrack.py status
```

Every command prints one JSON object. Read it; surface the meaningful parts.

## Dates — always resolve, echo when unsure

Logging is retrospective. Determine **today's date from the conversation
context** and pass it as `--today YYYY-MM-DD` to any command that needs it. To
turn a phrase into a date, use the CLI (it knows RU + EN, relative terms,
weekdays, `DD.MM`, ISO):

```
python scripts/fittrack.py resolve-date --text "позавчера" --today 2026-06-07
```

A bare weekday means the most recent past one. If a date is ambiguous, state the
resolved date back to the user before writing ("записал на пятницу, 5 июня —
верно?"). No date mentioned → today. See `references/date-handling.md`.

## Logging food

Decide the macros first (cascade in `references/nutrition-lookup.md`):
barcode/brand → `lookup`; label photo → read it yourself; whole food/dish → your
own estimate; user gave numbers → use them. Confirm estimated macros, then:

```
python scripts/fittrack.py log-food --date 2026-06-07 \
  --item "куриная грудка" --kcal 330 --protein 62 --fat 7.2 --carbs 0 \
  --meal lunch --qty-g 200 --source claude
```

`--source`: `claude` (you estimated) · `off` (Open Food Facts) · `label` (photo)
· `manual` (user-provided). The reply includes the day's running totals vs goals
— relay them ("после обеда: 330/2200 ккал, белок 62/165").

## Logging workouts

```
python scripts/fittrack.py log-workout --date 2026-06-07 --exercise "жим лёжа" \
  --type strength --sets 5 --reps 5 --weight 80
```

Cardio uses `--duration` / `--distance`; `--type` is strength/cardio/mobility/
sport. Strength volume (sets·reps·weight) is computed automatically.

## Logging bodyweight

```
python scripts/fittrack.py log-weight --date 2026-06-07 --weight 84.5
```

## Goals

Set directly, or compute from body stats (Mifflin-St Jeor) then save — see
`references/goals.md`:

```
python scripts/fittrack.py compute-goals --sex male --age 30 --height 182 \
  --weight 85 --activity moderate --goal cut
python scripts/fittrack.py config-set --patch '{"goals":{"kcal":2200,"protein_g":165,"fat_g":70,"carbs_g":220}}'
```

## Summaries

```
python scripts/fittrack.py summary --period day   --today 2026-06-07
python scripts/fittrack.py summary --period week  --today 2026-06-07
python scripts/fittrack.py summary --period month --today 2026-06-07
python scripts/fittrack.py summary --period year  --today 2026-06-07
```

The CLI returns structured stats (totals, averages, adherence, streaks, PRs,
bodyweight trend). YOU format them into a clear, encouraging report — see
`references/summaries.md` for layout and what to highlight.

## Proactive coaching

After logging or summarizing, look for one useful, non-nagging observation
(protein trending low, a new PR, a missed-training pattern, weight off-trend).
Offer it briefly. Rules and tone in `references/coaching.md`.

## Persistence on claude.ai (important)

The skill is stateless between sessions; durability comes from the Project + the store.
**The one file the user must keep is always named exactly `fitness-config.json`** (settings,
goals, **secrets**, backend pointer).

- **Loading (session start):** recreate `fitness-config.json` in the working dir from the
  Project before running the CLI — see *Invocation protocol* step 0.
- **Saving (after onboarding or any `config-set`):** you **cannot write to the Project's
  knowledge yourself** — hand the file to the user to save. Show the full updated
  `fitness-config.json` (the sandbox file / an artifact) and tell them, in plain words, to
  **save it into this Project's knowledge, named exactly `fitness-config.json`** (replacing any
  previous version). State that exact filename explicitly every time — the user types it by hand,
  and the stable name is how you find it next session. Never claim it's saved; confirm only what
  the user reports doing.
- With **Notion / Sheets**, logged records live in the user's cloud — only this small config
  file must persist. With the **local** backend, `fitness-data.json` holds the records too and
  must be saved to the Project the same way. See `references/backends/local.md`.

## Network access (sandbox egress)

The bundled CLI calls external APIs, which the claude.ai sandbox blocks by default. If a backend
or food lookup fails with a connection/network error, it is almost certainly egress — tell the
user to allow the domain under **Settings → Capabilities → Allow network egress → Domain
allowlist** (or set *All domains*). Domains the skill uses:

| Feature | Domain(s) to allow |
|---|---|
| Notion backend | `api.notion.com` |
| Google Sheets backend | `sheets.googleapis.com`, `oauth2.googleapis.com` |
| Open Food Facts (auto-КБЖУ) | `*.openfoodfacts.org` |

**The allowlist is captured when the sandbox session starts.** Editing it inside an already-open
chat does NOT take effect — after changing the domain allowlist the user must **start a NEW chat**
(in the same Project) and continue there. So prefer to get network access set up *before* onboarding;
and if a backend call fails mid-setup, tell the user to fix the allowlist, **save the config first**
(see *Persistence*), then reopen in a new chat — you will resume from the saved config (see
*Resuming* in `references/onboarding.md`).

## Reference map

| Need | Read |
|---|---|
| First-run setup wizard | `references/onboarding.md` |
| Data fields & config shape | `references/data-model.md` |
| Determining food macros (OFF / photo / estimate) | `references/nutrition-lookup.md` |
| Calorie & macro goal math | `references/goals.md` |
| Formatting day/week/month/year summaries | `references/summaries.md` |
| Relative-date rules | `references/date-handling.md` |
| Proactive suggestions | `references/coaching.md` |
| Notion setup & API | `references/backends/notion.md` |
| Google Sheets setup | `references/backends/google-sheets.md` |
| Local file backend | `references/backends/local.md` |
