# Цели по калориям и макросам

Цели можно задать напрямую или вычислить из антропометрии по формуле Mifflin-St Jeor.  
Вычисленные значения — **научно обоснованные стартовые точки**, не жёсткие предписания; пользователь корректирует их до сохранения.

---

## Формула Mifflin-St Jeor

### BMR (базовый обмен)

```
BMR = 10 × weight_kg + 6.25 × height_cm − 5 × age + s
```

где `s`:
- **мужской пол** → `+5`
- **женский пол** → `−161`

### TDEE (суточные затраты с учётом активности)

```
TDEE = BMR × activity_factor
```

| `--activity` | Коэффициент | Описание |
|---|---|---|
| `sedentary` | 1.2 | Нет нагрузок / сидячая работа |
| `light` | 1.375 | 1–3 тренировки в неделю |
| `moderate` | 1.55 | 3–5 тренировок в неделю |
| `active` | 1.725 | 6–7 тренировок в неделю |
| `very_active` | 1.9 | Ежедневные тяжёлые тренировки / физическая работа |

### Целевые калории

```
target_kcal = TDEE × goal_factor
```

| `--goal` | Коэффициент | Фаза |
|---|---|---|
| `cut` | 0.82 | Сушка / дефицит |
| `maintain` | 1.0 | Поддержание |
| `bulk` | 1.12 | Набор массы |

### Макросплит (расчёт по умолчанию)

```
protein_g = protein_per_kg × weight_kg   (default protein_per_kg = 1.8, диапазон 1.6–2.2)
fat_g     = fat_per_kg     × weight_kg   (default fat_per_kg     = 0.9, диапазон 0.8–1.0)
carbs_g   = (target_kcal − protein_g×4 − fat_g×9) / 4
```

Углеводы — остаточная переменная; не могут быть отрицательными (пол = 0).

---

## Вычислить цели через CLI

```
python scripts/fittrack.py compute-goals \
  --sex male --age 30 --height 182 --weight 85 \
  --activity moderate --goal cut
```

**Флаги `compute-goals`:**
| Флаг | Обязателен | Значение |
|---|---|---|
| `--sex` | да | `male` / `female` |
| `--age` | да | лет |
| `--height` | да | см |
| `--weight` | да | кг |
| `--activity` | нет (default `moderate`) | см. таблицу выше |
| `--goal` | нет (default `maintain`) | `cut` / `maintain` / `bulk` |

### Пример ответа

```json
{
  "bmr": 1842,
  "tdee": 2856,
  "kcal": 2342,
  "protein_g": 153,
  "fat_g": 76,
  "carbs_g": 261,
  "assumptions": {
    "activity": "moderate",
    "activity_factor": 1.55,
    "goal": "cut",
    "goal_factor": 0.82,
    "protein_per_kg": 1.8,
    "fat_per_kg": 0.9
  }
}
```

**Интерпретация для пользователя:**  
*«BMR 1 842 ккал → TDEE 2 856 ккал (умеренная активность). На сушке (−18%): цель 2 342 ккал — Б 153 г, Ж 76 г, У 261 г. Это стартовая точка — хочешь что-то изменить?»*

---

## Скорректировать и сохранить

После обсуждения с пользователем сохраняй согласованные цели через `config-set`:

```
python scripts/fittrack.py config-set \
  --patch '{"goals":{"kcal":2342,"protein_g":153,"fat_g":76,"carbs_g":261}}'
```

Также сохраняй `profile` — чтобы цели можно было пересчитать позже без повторного ввода данных:

```
python scripts/fittrack.py config-set \
  --patch '{"profile":{"sex":"male","age":30,"height_cm":182,"weight_kg":85,"activity":"moderate","goal":"cut"}}'
```

Оба патча можно объединить в один вызов:

```
python scripts/fittrack.py config-set --patch '{
  "goals":   {"kcal":2342,"protein_g":153,"fat_g":76,"carbs_g":261},
  "profile": {"sex":"male","age":30,"height_cm":182,"weight_kg":85,"activity":"moderate","goal":"cut"}
}'
```

На claude.ai после любого `config-set` напомни пользователю **пересохранить** `fitness-config.json` как файл знаний проекта.

---

## Когда пересчитывать цели

Предложи пересчитать при наличии сохранённого `profile`, если:

- **Вес изменился на ≥ 3 кг (≈5% массы тела)** — TDEE и макросплит сдвигаются ощутимо.
- **Смена фазы**: переход cut → maintain → bulk или обратно.
- Пользователь сам просит пересмотреть цели.

Пересчёт: вызвать `compute-goals` с обновлёнными параметрами, обсудить, затем `config-set`.

---

## `tolerance_pct` — допуск «попадания в цель»

Поле `goals.tolerance_pct` (default `7`) задаёт симметричный ± коридор вокруг целевых ккал, в котором день считается **«выполненным»** при подсчёте adherence в сводках.

Пример: цель 2 400 ккал, tolerance 7% → коридор 2 232–2 568 ккал.  
Любой день в этом диапазоне засчитывается как «on target».  
Изменить: `config-set --patch '{"goals":{"tolerance_pct":10}}'`.
