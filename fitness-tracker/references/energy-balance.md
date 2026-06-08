# Energy balance & body composition

Two optional habits beyond food and plain weight: tracking **calories burned**
(to see daily energy balance) and **body composition** (muscle / fat / water).
The user logs only what they want — every field is optional.

## Energy balance = intake − expenditure

- **Intake** = the day's food calories (already logged via `log-food`).
- **Expenditure** = **basal (resting / BMR)** + **activity**.
- **Net** = intake − expenditure. `net < 0` is a **deficit** (toward fat loss),
  `net > 0` a **surplus**. Daily/period summaries compute and label this.

### Basal is BMR, not TDEE
Basal is the *resting* burn (Mifflin-St Jeor BMR from the profile). Do **not** use
TDEE: TDEE already multiplies BMR by an activity factor, and here activity is
measured separately, so TDEE would double-count it. `goals.bmr_mifflin` provides it.

### Logging — match the user's phrasing
`log-energy` fills the missing member of the basal/activity/total trio
(`total = basal + activity`) and resolves basal automatically. Priority for basal:
explicit `--basal` → derived `total − activity` (when both given) →
`config.energy.basal_kcal` → profile BMR.

```
# total + activity given → basal derived as total − activity (trust the watch)
python scripts/fittrack.py log-energy --date 2026-06-07 --total 3200 --activity 1200
# only activity → basal auto from profile BMR, total = basal + activity
python scripts/fittrack.py log-energy --date 2026-06-07 --activity 1200
# only total → basal auto, activity = total − basal
python scripts/fittrack.py log-energy --date 2026-06-07 --total 3200
# explicit resting override
python scripts/fittrack.py log-energy --date 2026-06-07 --activity 900 --basal 1850
```

Phrasings → flags: «сегодня сожжено 3200, 1200 за активность» → `--total 3200
--activity 1200`; «потратил 600 на тренировке» → `--activity 600`; «расход 2900» →
`--total 2900`. The response carries `basal_source` (`derived` / `profile_bmr` /
`config` / `override`) and the day's energy block — relay the **net**.

### No profile yet?
Auto-basal needs `profile` (sex/age/height/weight). If it's missing and the user
gives only activity, basal stays unknown and net can't be computed — either ask for
the day's **total** burn, or capture the profile (onboarding / `compute-goals`).

## Body composition

`log-weight` carries optional metrics beyond weight — log whatever the scale shows:

```
python scripts/fittrack.py log-weight --date 2026-06-07 --weight 100.8 \
  --muscle 40.1 --fat 26.9 --fat-pct 26.7 --water 54.1
```

Plain flags: `--weight` `--muscle` `--fat` `--fat-pct` `--water`. At least one
metric is required; any subset is fine. Summaries trend each metric that has data.

## In summaries
- **Daily**: an `energy` block (intake / basal / activity / total_out / net /
  balance) and a `bodycomp` snapshot of that day's measurement.
- **Period**: `energy` (avg burn, `cumulative_net`, `expected_fat_change_kg` =
  cumulative_net ÷ 7700 kcal/kg) and `bodycomp` trends per metric. Put the predicted
  fat change next to the **actual** fat/weight delta — that comparison is the
  correlation the user is after. See `references/summaries.md`.
