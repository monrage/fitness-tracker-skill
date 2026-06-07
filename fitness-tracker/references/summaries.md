# Summaries — форматирование отчётов

CLI агрегирует данные; ты форматируешь результат в читаемый русскоязычный отчёт.

## Вызов CLI

```
# День (текущий)
python scripts/fittrack.py summary --period day --today 2026-06-07

# Конкретный день
python scripts/fittrack.py summary --period day --today 2026-06-07 --date 2026-06-05

# Неделя / месяц / год
python scripts/fittrack.py summary --period week  --today 2026-06-07
python scripts/fittrack.py summary --period month --today 2026-06-07
python scripts/fittrack.py summary --period year  --today 2026-06-07

# Произвольный период
python scripts/fittrack.py summary --period custom --date-from 2026-05-01 --date-to 2026-05-15
```

CLI возвращает `{"period": "...", "summary": {...}}`. Нужно только `summary`.

---

## Структура: daily()

Используется для `--period day`. Поля:

| поле | тип | содержание |
|---|---|---|
| `date` | string | ISO-дата |
| `totals` | object | `{kcal, protein_g, fat_g, carbs_g}` — итог дня |
| `meals` | object | по приёму пищи: `{breakfast, lunch, dinner, snack}` → `{kcal, protein_g, fat_g, carbs_g}` |
| `workouts` | array | сырые записи тренировок за день |
| `bodyweight` | number\|null | вес тела в кг (или null) |
| `entries` | int | количество food-записей |
| `vs_goal` | object | только если цели заданы: `{kcal, protein_g, fat_g, carbs_g}` → `{target, actual, pct, remaining}` |
| `on_target` | bool | только если цели заданы; `true` = ккал и белок в пределах `tolerance_pct` (дефолт ±7%) |

---

## Структура: period()

Используется для `week / month / year / custom`. Поля:

| поле | тип | содержание |
|---|---|---|
| `from` / `to` | string | ISO-границы периода |
| `days` | int | календарных дней в периоде |
| `days_logged` | int | дней с хоть одной food-записью |
| `totals` | object | `{kcal, protein_g, fat_g, carbs_g}` — сумма за период |
| `avg_per_logged_day` | object | среднее только по залогированным дням |
| `avg_per_calendar_day` | object | среднее по всем календарным дням периода |
| `on_target_days` | int | дней в цели (только если `goals.kcal` задан) |
| `adherence_pct` | int | `on_target_days / days_logged × 100` (только если цели заданы) |
| `streaks.longest` | int | максимальная серия подряд "в цели" |
| `streaks.current` | int | текущая серия (заканчивается на `to`) |
| `workouts.entries` | int | всего записей тренировок |
| `workouts.sessions` | int | уникальных дней с тренировкой |
| `workouts.by_type` | object | `{strength, cardio, ...}` → количество записей |
| `workouts.by_exercise` | object | `{"жим лёжа": 3, ...}` |
| `workouts.total_volume` | float | суммарный объём (sets·reps·weight_kg) |
| `workouts.total_duration_min` | float | суммарное время кардио/тренировок |
| `personal_records` | object | `{<exercise>: {max_weight, max_weight_date, max_volume, max_volume_date}}` |
| `bodyweight.start` / `.end` | float | первый и последний вес в периоде |
| `bodyweight.delta` | float | разница (end − start), кг |
| `bodyweight.start_date` / `.end_date` | string | даты замеров |
| `bodyweight.points` | int | количество замеров |

### avg_per_logged_day vs avg_per_calendar_day

Эти два поля дают разные углы зрения:

- **`avg_per_logged_day`** — честное среднее по дням, когда человек вёл учёт. Отражает качество питания в залогированные дни.
- **`avg_per_calendar_day`** — с учётом пропусков. Может быть искусственно занижено из-за незалогированных дней.

Всегда указывай покрытие: *"залогировано X из Y дней"*. Не делай выводов о среднем без этого контекста.

---

## Шаблон дневного отчёта

```
📅 Воскресенье, 7 июня 2026

КБЖУ: 1 840 / 2 200 ккал (84%) · Б 142/165 г · Ж 58/70 г · У 198/220 г
По приёмам: завтрак 420 · обед 780 · ужин 640 ккал

Тренировка: жим лёжа 5×5 80 кг, присед 5×5 100 кг
Вес тела: 84.2 кг

До цели: −360 ккал · −23 г белка
✅ Цель по калориям выполнена  /  ⚠️ Белок немного не добрал
```

Подстраивай под факт: если тренировок нет — не показывай строку; если нет замера веса — пропусти.

---

## Шаблон недельного отчёта

```
📊 Неделя 2–8 июня 2026 · залогировано 6/7 дней

Средний день (по залогированным): 2 150 ккал · Б 158 г · Ж 68 г · У 215 г
Цель выполнена: 5/6 дней (83%) 🔥 серия 3 дня подряд

Тренировок: 4 сессии
  Силовые: жим лёжа ×3, присед ×2, тяга ×1
  PR этой недели: жим лёжа — 85 кг (новый рекорд!) 🏆

Вес: 84.5 → 84.0 кг (−0.5 кг)
```

---

## Месяц и год — акцент на тренды

Для длинных периодов не перечисляй каждый день — выдели главное:

- **Adherence %** — какой процент залогированных дней в цели (+ покрытие дней).
- **Серии** — максимальная серия "в цели" подряд.
- **Новые PRs** — отметь каждый (`max_weight`, `max_volume` с датой).
- **Вес тела** — delta + направление. Сравни с `bodyweight_target_kg` из goals, если задан.
- **Макро-паттерны** — что стабильно западает (белок, перекорм по жирам и т. д.).
- **Тренировочный объём** — `total_volume`, `sessions`, `by_type`.

Формулируй кратко, без перечисления каждой цифры подряд. Читатель — не бухгалтер.
