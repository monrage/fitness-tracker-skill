# Data model

The canonical schema. Every backend (local / Notion / Sheets) maps these exact
fields. The assistant builds records via `scripts/storage.py` (`make_food`,
`make_workout`, `make_bodyweight`) so all backends receive identical, validated
data. Logic scripts (`summarize.py`) read these shapes back.

## Two tiers: config vs records

There are two separate stores. Don't mix them.

- **Bootstrap config** — `fitness-config.json`, a **local** file (default `./fitness-config.json`,
  override with env `FITTRACK_CONFIG`). Holds settings, goals, profile, backend pointer **and
  secrets** (Notion token / Sheets OAuth). It must be local because the skill needs it to know how
  to reach the backend in the first place — storing it in the cloud backend would be circular.
  On claude.ai keep it as a **Project knowledge file** so it survives across sessions.
- **Records** — the logged data (food / workout / bodyweight). Live in the chosen backend
  (local JSON `fitness-data.json`, Notion databases, or Sheets tabs). This is the part that grows.

## Records

### food
| field | type | notes |
|---|---|---|
| `date` | ISO `YYYY-MM-DD` | required; resolved via `dates.py` |
| `meal` | enum | `breakfast` / `lunch` / `dinner` / `snack` |
| `item` | string | what was eaten, e.g. "куриная грудка" |
| `qty_g` | number \| null | grams (or serving size); null if unknown |
| `kcal` | number | calories |
| `protein_g` / `fat_g` / `carbs_g` | number | macros (Б / Ж / У) |
| `source` | enum | `claude` (estimate) / `off` (Open Food Facts) / `label` (photo) / `manual` |
| `notes` | string | free text |

### workout
| field | type | notes |
|---|---|---|
| `date` | ISO date | required |
| `type` | enum | `strength` / `cardio` / `mobility` / `sport` |
| `exercise` | string | e.g. "жим лёжа" |
| `sets` / `reps` | int \| null | strength |
| `weight_kg` | number \| null | working weight |
| `duration_min` | number \| null | cardio / session length |
| `distance_km` | number \| null | cardio |
| `rpe` | number \| null | perceived exertion 1–10 |
| `volume` | number \| null | auto = sets·reps·weight (strength only) |
| `notes` | string | |

### bodyweight
| field | type | notes |
|---|---|---|
| `date` | ISO date | required |
| `weight_kg` | number | |
| `notes` | string | |

Backends also attach an opaque `id` (and `_seq` for local) on append — never set by the assistant.

## Config shape

See `assets/config.example.json` for a full example. Key fields:

- `lang` (`ru`/`en`), `units` (metric defaults: g / kg / km / kcal), `timezone`, `week_start` (`mon`/`sun`)
- `backend.type` = `local` | `notion` | `sheets`, plus a per-type sub-object with credentials/ids
- `nutrition.provider` (`claude+off` | `claude` | `manual` | `nutritionix`), `off_enabled`, `off_country`
- `goals`: `kcal`, `protein_g`, `fat_g`, `carbs_g`, optional `workouts_per_week`,
  `bodyweight_target_kg`, `tolerance_pct` (default 7 — the ± band that counts a day "on target")
- `profile` (optional): `sex`, `age`, `height_cm`, `weight_kg`, `activity`, `goal` — used by
  `goals.py` to compute targets (Mifflin-St Jeor). Not required if goals are set directly.

## Units convention
Metric is the default and what scripts compute in: mass in **grams** (food) / **kg** (body, weight
lifted), distance in **km**, energy in **kcal**. If a user works in lb/oz, the assistant converts to
metric before calling `make_*` and converts back for display.
