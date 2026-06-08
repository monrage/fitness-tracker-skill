# 🏋️ fitness-tracker

> A personal **nutrition & training tracker** that lives inside a Claude chat — logs
> meals with calories and macros (КБЖУ), workouts, and bodyweight against your goals,
> and builds weekly / monthly / yearly summaries. Your data stays in **your own**
> Notion, Google Sheets, or a local file.

[![Release](https://img.shields.io/github/v/release/monrage/fitness-tracker-skill?sort=semver)](https://github.com/monrage/fitness-tracker-skill/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Install guide RU | EN](https://img.shields.io/badge/guide-RU%20%7C%20EN-d97757)](https://fitness-tracker-skill.monrage.workers.dev)

**English** · [Русский](README.ru.md)

It's a [Claude **Skill**](https://www.anthropic.com/news/skills): drop it into Claude,
talk to it in plain language, and it keeps a structured fitness diary for you.

```
you →  log lunch: 200g chicken breast and 150g rice
you →  today's workout: bench 80×5×5, squat 100×5×5
you →  how much protein do I have left today?
you →  weekly summary
```

## ✨ Features
- **Food + macros (КБЖУ):** describe a meal in words — Claude estimates the
  calories/protein/fat/carbs itself, looks them up by **barcode** via Open Food Facts,
  or reads a **nutrition-label photo**. Manual entry too.
- **Workouts:** sets × reps × weight (volume auto-computed), cardio, duration, and
  personal records.
- **Bodyweight** trend toward your goal.
- **Goals:** set them directly or compute from body stats (Mifflin-St Jeor).
- **Dates:** understands "yesterday", "on Monday", `05.06`, ISO — places entries on the
  right day (RU + EN).
- **Summaries:** day / week / month / year — adherence, streaks, PRs, weight trajectory.
- **Bilingual** UX (Russian + English).

## 🚀 Install
1. **Download** the skill: [`fitness-tracker.zip`](https://fitness-tracker-skill.monrage.workers.dev/fitness-tracker.zip).
2. **Follow the step-by-step guide** → **https://fitness-tracker-skill.monrage.workers.dev**
   (RU/EN). It covers the easy-to-miss bits: opening sandbox **network access**,
   uploading the skill, creating a **project**, preparing **Notion**, and **saving the
   config** to the project.

Requirements: a paid claude.ai plan (Pro / Max / Team) with **code execution** enabled, using the
**Sonnet or Opus** model (verified — Haiku is not recommended, it can mis-scale food macros).

## 🧠 How it works
- **You ↔ CLI split.** Claude handles language, macro estimation, and vision (label
  photos). A bundled CLI, [`scripts/fittrack.py`](fitness-tracker/scripts/fittrack.py),
  does the deterministic work — persistence, date math, Open Food Facts lookups, goal
  math, aggregation — and prints JSON the assistant reads.
- **Stdlib only.** Every script uses the Python standard library, so it runs in the
  claude.ai sandbox with no `pip install`.
- **Stateless skill, durable storage.** The skill remembers nothing between chats;
  durability comes from your chosen backend + a small `fitness-config.json` kept in your
  Claude Project.

## 🗄 Storage backends
| Backend | Best for | Setup |
|---|---|---|
| **Notion** (recommended) | structured views + phone app | one integration token |
| **Google Sheets** | spreadsheet lovers / charts | one-time OAuth |
| **Local file** | no cloud / max privacy | none |

## 🔒 Privacy
Your data stays yours. Tokens live only in your own `fitness-config.json` (kept in your Claude Project, never
committed); records go only to the backend you chose; the code calls only the APIs you
enable. No telemetry. See [SECURITY.md](SECURITY.md).

## 🛠 Development
No dependencies — Python 3.10+. Run the test suite (plain Python):

```bash
python tests/test_foundation.py
python tests/test_logic.py
python tests/test_backends_mapping.py
python tests/test_docs_consistency.py
```

```
fitness-tracker/   the skill (SKILL.md + references/ + scripts/ + assets/ + evals/)
guide/             install-guide source (bilingual template + img + build.py)
docs/              built guide for GitHub Pages (generated)
tests/             plain-Python test suite
```
See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

## 🙏 Credits
Created by [**monrage**](https://github.com/monrage), from an idea by a friend (to be
credited 🙂). Designed and built in collaboration with **Claude** (Anthropic).

## 📄 License
[MIT](LICENSE) © 2026 monrage
